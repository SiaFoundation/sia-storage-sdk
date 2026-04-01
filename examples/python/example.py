import asyncio
from base64 import b64encode
from sys import stdin
from datetime import datetime, timezone
from io import BytesIO

from sia_storage import (
    generate_recovery_phrase,
    AppMeta,
    Builder,
    UploadOptions,
    DownloadOptions,
    set_logger,
    Logger,
)


class PrintLogger(Logger):
    def debug(self, msg):
        print("DEBUG", msg)

    def info(self, msg):
        print("INFO", msg)

    def warning(self, msg):
        print("WARNING", msg)

    def error(self, msg):
        print("ERROR", msg)


set_logger(PrintLogger(), "debug")


async def main():
    app_id = b"\x01" * 32

    builder = Builder(
        "https://app.sia.storage",
        AppMeta(
            id=app_id,
            name="python example",
            description="an example app",
            service_url="https://example.com",
            logo_url=None,
            callback_url=None,
        )
    )
    await builder.request_connection()

    print(f"Please approve connection {builder.response_url()}")
    await builder.wait_for_approval()

    print("Enter mnemonic (or leave empty to generate new):")
    mnemonic = stdin.readline().strip()
    if not mnemonic:
        mnemonic = generate_recovery_phrase()
        print("mnemonic:", mnemonic)

    sdk = await builder.register(mnemonic)

    # Store the app key for later use
    app_key = sdk.app_key()
    print("App registered:", b64encode(app_key.export()).decode())

    print("Connected to indexer")

    start = datetime.now(timezone.utc)
    obj = await sdk.upload(BytesIO(b"hello from upload()!"))
    print(f"Uploaded {obj.size()} bytes with upload() in {datetime.now(timezone.utc) - start}")

    data = BytesIO()
    start = datetime.now(timezone.utc)
    await sdk.download(data, obj)
    print(f"Downloaded with download(): {data.getvalue().decode()!r} in {datetime.now(timezone.utc) - start}")

    print("\nUpload Packing Example...")
    
    start = datetime.now(timezone.utc)
    upload = await sdk.upload_packed(UploadOptions())

    for i in range(10):
        data = f"hello, world {i}!"
        size = await upload.add(BytesIO(data.encode()))
        rem = upload.remaining()
        print(f"upload {i} added {size} bytes ({rem} remaining)")

    objects = await upload.finalize()
    elapsed = datetime.now(timezone.utc) - start
    print(f"Upload finished {len(objects)} objects in {elapsed}")

    start = datetime.now(timezone.utc)
    buffer = BytesIO()
    print(f"Downloading object {objects[-1].id()} {objects[-1].size()} bytes")
    await sdk.download(buffer, objects[-1], DownloadOptions())
    elapsed = datetime.now(timezone.utc) - start
    print(
        f"Downloaded object {objects[-1].id()} with {len(buffer.getvalue())} bytes in {elapsed}"
    )




asyncio.run(main())
