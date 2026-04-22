"""Idiomatic Python wrappers for the Sia SDK.

This module provides convenience classes that make the SDK feel native to
Python developers: file-like reader/writer support for upload/download,
async iteration and context-manager semantics for streaming downloads, and
plain-callable progress callbacks.
"""

from __future__ import annotations

import asyncio
from io import BytesIO
from typing import Any, BinaryIO, Callable, Optional, Union

from .sia_storage.sia_storage_ffi import (
    AppKey,
    AppMeta,
    Builder as _Builder,
    Download as _Download,
    DownloadOptions,
    PackedUpload as _PackedUpload,
    PinnedObject,
    ProgressCallback,
    Reader,
    Sdk as _Sdk,
    ShardProgress,
    UploadOptions,
    uniffi_set_event_loop,
)


ProgressHandler = Union[ProgressCallback, Callable[[ShardProgress], Any]]


class _CallableProgress(ProgressCallback):
    """Adapts a plain callable into a ProgressCallback trait implementation."""

    def __init__(self, fn: Callable[[ShardProgress], Any]):
        self._fn = fn

    def progress(self, progress: ShardProgress) -> None:
        self._fn(progress)


def _wrap_progress(cb):
    if cb is None or isinstance(cb, ProgressCallback):
        return cb
    if callable(cb):
        return _CallableProgress(cb)
    raise TypeError(
        f"progress callback must be a ProgressCallback or callable, got {type(cb).__name__}"
    )


def _prepare_upload_options(options: Optional[UploadOptions]) -> UploadOptions:
    if options is None:
        return UploadOptions()
    options.shard_uploaded = _wrap_progress(options.shard_uploaded)
    return options


def _prepare_download_options(options: Optional[DownloadOptions]) -> DownloadOptions:
    if options is None:
        return DownloadOptions()
    options.shard_downloaded = _wrap_progress(options.shard_downloaded)
    return options


class Builder(_Builder):
    """Creates a new SDK builder with the provided indexer URL.

    After creating the builder, call connected() to attempt to connect
    using an existing app key, or request_connection() to request a new
    connection.
    """

    def __init__(self, indexer_url: str, app_meta: AppMeta):
        try:
            uniffi_set_event_loop(asyncio.get_running_loop())
        except RuntimeError:
            pass  # No running loop yet
        super().__init__(indexer_url, app_meta)

    async def connected(self, app_key: AppKey) -> Optional[Sdk]:
        """Attempts to connect using the provided app key.

        If the app key is valid, returns an Sdk instance, otherwise returns None.
        If you receive None, call request_connection() to request a new connection.

        Args:
            app_key: The application key used for authentication.
        """
        result = await super().connected(app_key)
        if result is not None:
            return Sdk._from_ffi(result)
        return None

    async def register(self, mnemonic: str) -> Sdk:
        """Registers the application with the indexer using the provided mnemonic.

        Once registered, returns an Sdk instance that can be used to interact
        with the indexer.

        Args:
            mnemonic: The user's mnemonic phrase used to derive the application key.
        """
        return Sdk._from_ffi(await super().register(mnemonic))


class Sdk(_Sdk):
    """The main SDK for interacting with the Sia decentralized storage network.

    Accepts standard Python file-like objects (BinaryIO) for uploads, returns
    an async-iterable Download handle for downloads, and accepts plain Python
    callables for progress reporting.
    """

    def __init__(self, *args, **kwargs):
        raise ValueError("Use Builder.connected() or Builder.register() to create an SDK instance")

    @classmethod
    def _from_ffi(cls, inner: _Sdk):
        # exploits UniFFI's internals to wrap the class
        return cls._uniffi_make_instance(inner._uniffi_clone_handle())

    async def upload(
        self,
        obj: PinnedObject,
        r: Union[bytes, bytearray, memoryview, BinaryIO],
        options: Optional[UploadOptions] = None,
    ) -> PinnedObject:
        """Uploads data to the Sia network.

        Pass `PinnedObject()` for a new upload. To resume a previous upload,
        pass the object returned from the earlier call. Appending data changes
        the object's ID, so any existing references must be updated and the
        object must be re-pinned afterward.

        Args:
            obj: The object to upload into. Use `PinnedObject()` for a new upload.
            r: The data to upload. Accepts a `bytes`-like value or any file-like
                object with a `read(n)` method.
            options: The upload options. `shard_uploaded` accepts either a
                ProgressCallback or any callable taking a ShardProgress.

        Returns:
            An object containing all slabs from `obj` plus the newly uploaded
            slabs. The caller is responsible for pinning the returned object.
        """
        if isinstance(r, (bytes, bytearray, memoryview)):
            r = BytesIO(bytes(r))
        return await super().upload(
            obj,
            BytesReader(r),
            _prepare_upload_options(options),
        )

    async def upload_packed(self, options: Optional[UploadOptions] = None) -> PackedUpload:
        """Creates a new packed upload.

        This allows multiple objects to be packed together for more efficient
        uploads. The returned PackedUpload can be used to add objects to the
        upload, and then finalized to get the resulting objects.

        Args:
            options: The upload options. `shard_uploaded` accepts either a
                ProgressCallback or any callable taking a ShardProgress.

        Returns:
            A PackedUpload that can be used to add objects and finalize the upload.
        """
        return PackedUpload._from_ffi(
            await super().upload_packed(_prepare_upload_options(options))
        )

    def download(self, obj: PinnedObject, options: Optional[DownloadOptions] = None) -> Download:
        """Starts a download of the data referenced by the object.

        Returns a Download handle that streams chunks of decoded data. Use it
        as an async context manager, iterate over it to consume chunks, or
        call read_all() / write_to() for common patterns.

        Args:
            obj: The pinned object to download.
            options: The download options. `shard_downloaded` accepts either a
                ProgressCallback or any callable taking a ShardProgress.

        Returns:
            A Download handle.
        """
        return Download(super().download(obj, _prepare_download_options(options)))


class Download:
    """An async stream of bytes from a downloaded object.

    The handle starts yielding chunks as soon as they become available. Drop
    the handle (via `async with`) or call close() to cancel an in-flight
    download.

    Example:
        # Read into memory
        async with sdk.download(obj) as d:
            data = await d.read_all()

        # Stream chunks to a file
        async with sdk.download(obj) as d:
            with open("out.bin", "wb") as f:
                await d.write_to(f)

        # Iterate over chunks
        async with sdk.download(obj) as d:
            async for chunk in d:
                process(chunk)
    """

    def __init__(self, inner: _Download):
        self._inner = inner

    async def __aenter__(self) -> Download:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    def __aiter__(self) -> Download:
        return self

    async def __anext__(self) -> bytes:
        chunk = await self._inner.read()
        if not chunk:
            raise StopAsyncIteration
        return chunk

    async def read(self) -> bytes:
        """Reads the next chunk of decoded data. Returns b'' on EOF."""
        return await self._inner.read()

    async def read_all(self) -> bytes:
        """Reads the entire remaining stream into memory and returns it."""
        parts = []
        while True:
            chunk = await self._inner.read()
            if not chunk:
                break
            parts.append(chunk)
        return b"".join(parts)

    async def write_to(self, w: BinaryIO) -> int:
        """Streams the remaining data to a file-like writer.

        Args:
            w: Any object with a write(data) method.

        Returns:
            The total number of bytes written.
        """
        total = 0
        while True:
            chunk = await self._inner.read()
            if not chunk:
                break
            w.write(chunk)
            total += len(chunk)
        return total

    async def close(self) -> None:
        """Cancels the download and releases any in-flight recovery tasks."""
        await self._inner.cancel()


class PackedUpload(_PackedUpload):
    """A packed upload allows multiple objects to be uploaded together in a single upload.

    This can be more efficient than uploading each object separately if the size
    of the object is less than the minimum slab size.
    """

    def __init__(self, *args, **kwargs):
        raise ValueError("Use SDK.upload_packed() to create a PackedUpload instance")

    @classmethod
    def _from_ffi(cls, inner: _PackedUpload):
        return cls._uniffi_make_instance(inner._uniffi_clone_handle())

    async def add(self, reader: Union[bytes, bytearray, memoryview, BinaryIO]) -> int:
        """Adds a new object to the upload.

        The data will be read until EOF and packed into the upload. The caller
        must call finalize() to get the resulting objects after all objects have
        been added.

        Args:
            reader: The data to add. Accepts a `bytes`-like value or any file-like
                object with a `read(n)` method.

        Returns:
            The number of bytes read.
        """
        if isinstance(reader, (bytes, bytearray, memoryview)):
            reader = BytesIO(bytes(reader))
        return await super().add(BytesReader(reader))


class BytesReader(Reader):
    """Adapts any file-like object to the Reader trait.

    This allows you to upload data from any source that supports the
    standard Python binary read interface (files, BytesIO, etc.).

    Example:
        # From bytes
        reader = BytesReader(BytesIO(b"hello"))

        # From file
        with open("data.bin", "rb") as f:
            reader = BytesReader(f)
    """

    def __init__(self, stream: BinaryIO, chunk_size: int = (1 << 20)):
        """Create a BytesReader from a file-like object.

        Args:
            stream: Any object with a read(n) method returning bytes.
            chunk_size: Size of chunks to read (default 1MiB).
        """
        self._stream = stream
        self._chunk_size = chunk_size

    async def read(self) -> bytes:
        """Read the next chunk of data."""
        return self._stream.read(self._chunk_size)
