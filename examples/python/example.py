import asyncio
from base64 import b64encode
from sys import stdin
from datetime import datetime, timezone
from io import BytesIO

from sia_storage import (
    generate_recovery_phrase,
    AppMeta,
    Builder,
    PinnedObject,
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

    def warn(self, msg):
        print("WARNING", msg)

    def error(self, msg):
        print("ERROR", msg)


set_logger(PrintLogger(), "debug")


def on_upload(progress):
    print(
        f"  uploaded slab {progress.slab_index} shard {progress.shard_index} "
        f"({progress.shard_size} bytes) to {progress.host_key} in {progress.elapsed_ms}ms"
    )


def on_download(progress):
    print(
        f"  downloaded slab {progress.slab_index} shard {progress.shard_index} "
        f"({progress.shard_size} bytes) from {progress.host_key} in {progress.elapsed_ms}ms"
    )


async def main():
    app_id = b"\x01" * 32

    builder = Builder(
        "https://sia.storage",
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
    obj = await sdk.upload(
        PinnedObject(),
        BytesIO(b"hello from upload()!"),
        UploadOptions(shard_uploaded=on_upload),
    )
    await sdk.pin_object(obj)
    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    print(f"Uploaded and pinned {obj.size()} bytes with upload() in {elapsed:.2f}s")

    start = datetime.now(timezone.utc)
    async with sdk.download(obj, DownloadOptions(shard_downloaded=on_download)) as d:
        data = await d.read_all()
    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    print(f"Downloaded with download(): {data.decode()!r} in {elapsed:.2f}s")

    print("\nUpload Packing Example...")

    start = datetime.now(timezone.utc)
    upload = await sdk.upload_packed(UploadOptions())

    for i in range(10):
        data = f"hello, world {i}!"
        size = await upload.add(BytesIO(data.encode()))
        rem = upload.remaining()
        print(f"upload {i} added {size} bytes ({rem} remaining)")

    objects = await upload.finalize()
    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    print(f"Upload finished {len(objects)} objects in {elapsed:.2f}s")

    # Pin each object to the indexer
    for obj in objects:
        await sdk.pin_object(obj)
        print(f"Pinned object {obj.id()}")

    start = datetime.now(timezone.utc)
    buffer = BytesIO()
    print(f"Downloading object {objects[-1].id()} {objects[-1].size()} bytes")
    async with sdk.download(objects[-1]) as d:
        total = await d.write_to(buffer)
    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    print(f"Downloaded object {objects[-1].id()} with {total} bytes in {elapsed:.2f}s")


asyncio.run(main())
