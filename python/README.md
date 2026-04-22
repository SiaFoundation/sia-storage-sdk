# Sia Storage SDK for Python

Python bindings for Sia Storage, built with Rust and UniFFI.

## Requirements

- Python 3.9+

## Installation

### PyPI

```sh
pip install sia-storage
```

## Example

```python
import asyncio
from io import BytesIO

from sia_storage import (
    generate_recovery_phrase,
    AppMeta,
    Builder,
    DownloadOptions,
    PinnedObject,
    UploadOptions,
)


class PrintLogger(Logger):
    def debug(self, msg): print("DEBUG", msg)
    def info(self, msg): print("INFO", msg)
    def warn(self, msg): print("WARNING", msg)
    def error(self, msg): print("ERROR", msg)


set_logger(PrintLogger(), "debug")



async def main():
    app_id = b"\x01" * 32

    builder = Builder(
        "https://sia.storage",
        AppMeta(
            id=app_id,
            name="My App",
            description="App description",
            service_url="https://myapp.com",
            logo_url=None,
            callback_url=None,
        ),
    )
    await builder.request_connection()

    # Wait for user approval
    print(f"Please approve connection {builder.response_url()}")
    await builder.wait_for_approval()

    # Register with a recovery phrase
    mnemonic = generate_recovery_phrase()
    sdk = await builder.register(mnemonic)

    # Upload a single object. Progress callbacks accept plain callables.
    def on_upload(p):
        print(f"uploaded shard {p.shard_index} of slab {p.slab_index} in {p.elapsed_ms}ms")

    obj = await sdk.upload(
        PinnedObject(),
        BytesIO(b"hello, world!"),
        UploadOptions(shard_uploaded=on_upload),
    )
    await sdk.pin_object(obj)

    # Download streams via an async context manager.
    def on_download(p):
        print(f"downloaded shard {p.shard_index} of slab {p.slab_index} in {p.elapsed_ms}ms")

    async with sdk.download(obj, DownloadOptions(shard_downloaded=on_download)) as d:
        data = await d.read_all()
    print(data)


asyncio.run(main())
```

A complete working example is available in [examples/python/](../examples/python/).

## Local Development

```sh
cd python
python3 -m venv .venv
source .venv/bin/activate
pip3 install maturin

# Build and install the wheel
maturin develop

# Run the example
cd ../examples/python
python example.py
```

## License

MIT License - see [LICENSE](../LICENSE) for details.
