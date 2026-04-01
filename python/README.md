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
    set_logger,
    AppMeta,
    Builder,
    Logger,
    UploadOptions,
    BytesReader,
    download_bytes,
)


class PrintLogger(Logger):
    def debug(self, msg): print("DEBUG", msg)
    def info(self, msg): print("INFO", msg)
    def warning(self, msg): print("WARNING", msg)
    def error(self, msg): print("ERROR", msg)


set_logger(PrintLogger(), "debug")


async def main():
    app_id = b"\x01" * 32

    builder = Builder(
        "https://app.sia.storage",
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

    # Upload data
    upload = await sdk.upload_packed(UploadOptions())
    reader = BytesReader(BytesIO(b"hello, world!"))
    await upload.add(reader)
    objects = await upload.finalize()

    # Download data
    data = await download_bytes(sdk, objects[-1])


asyncio.run(main())
```

`PrintLogger` is a user-defined class that extends the SDK's `Logger` base class.
`BytesReader` is provided by the SDK to adapt any file-like object to the `Reader` interface.

A complete working example is available in [examples/python/](../examples/python/).

## Local Development

```sh
cd python
pip install maturin

# Build and install the wheel
maturin develop

# Run the example
cd ../examples/python
python example.py
```

## License

MIT License - see [LICENSE](../LICENSE) for details.
