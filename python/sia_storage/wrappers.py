"""Idiomatic Python wrappers for the Sia SDK.

This module provides convenience classes and functions that make the SDK
feel native to Python developers, wrapping the low-level Reader/Writer
traits with standard file-like object support.
"""

import asyncio
from typing import BinaryIO, Optional

from .sia_storage.sia_storage_ffi import (
    AppKey,
    AppMeta,
    Builder as _Builder,
    DownloadOptions,
    PackedUpload as _PackedUpload,
    PinnedObject,
    Reader,
    Sdk as _Sdk,
    UploadOptions,
    Writer,
    uniffi_set_event_loop,
)


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

    async def connected(self, app_key: AppKey) -> "Optional[Sdk]":
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

    async def register(self, mnemonic: str) -> "Sdk":
        """Registers the application with the indexer using the provided mnemonic.

        Once registered, returns an Sdk instance that can be used to interact
        with the indexer.

        Args:
            mnemonic: The user's mnemonic phrase used to derive the application key.
        """
        return Sdk._from_ffi(await super().register(mnemonic))


class Sdk(_Sdk):
    """The main SDK for interacting with the Sia decentralized storage network.

    Accepts standard Python file-like objects (BinaryIO) for upload and
    download operations.
    """

    def __init__(self, *args, **kwargs):
        raise ValueError("Use Builder.connected() or Builder.register() to create an SDK instance")

    @classmethod
    def _from_ffi(cls, inner: _Sdk):
        # exploits UniFFI's internals to wrap the class
        return cls._make_instance_(inner._uniffi_clone_pointer())

    async def upload(self, r: BinaryIO, options: Optional[UploadOptions] = None) -> PinnedObject:
        """Uploads data to the Sia network and pins it to the indexer.

        Args:
            r: A file-like object to read data from.
            options: The upload options to use for the upload.

        Returns:
            An object representing the uploaded data.
        """
        return await super().upload(BytesReader(r), options or UploadOptions())

    async def upload_packed(self, options: Optional[UploadOptions] = None) -> "PackedUpload":
        """Creates a new packed upload.

        This allows multiple objects to be packed together for more efficient
        uploads. The returned PackedUpload can be used to add objects to the
        upload, and then finalized to get the resulting objects.

        Args:
            options: The upload options to use for the upload.

        Returns:
            A PackedUpload that can be used to add objects and finalize the upload.
        """
        return PackedUpload._from_ffi(await super().upload_packed(options or UploadOptions()))

    async def download(self, w: BinaryIO, obj: PinnedObject, options: Optional[DownloadOptions] = None) -> None:
        """Initiates a download of the data referenced by the object.

        Args:
            w: A file-like object to write data to.
            obj: The pinned object to download.
            options: The download options to use for the download.
        """
        await super().download(BytesWriter(w), obj, options or DownloadOptions())


class PackedUpload(_PackedUpload):
    """A packed upload allows multiple objects to be uploaded together in a single upload.

    This can be more efficient than uploading each object separately if the size
    of the object is less than the minimum slab size.
    """

    def __init__(self, *args, **kwargs):
        raise ValueError("Use SDK.upload_packed() to create a PackedUpload instance")

    @classmethod
    def _from_ffi(cls, inner: _PackedUpload):
        return cls._make_instance_(inner._uniffi_clone_pointer())

    async def add(self, reader: BinaryIO) -> int:
        """Adds a new object to the upload.

        The data will be read until EOF and packed into the upload. The caller
        must call finalize() to get the resulting objects after all objects have
        been added.

        Args:
            reader: A file-like object to read data from.

        Returns:
            The number of bytes read.
        """
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


class BytesWriter(Writer):
    """Adapts any file-like object to the Writer trait.

    This allows you to download data to any destination that supports
    the standard Python binary write interface (files, BytesIO, etc.).

    Example:
        # To BytesIO
        buf = BytesIO()
        writer = BytesWriter(buf)

        # To file
        with open("output.bin", "wb") as f:
            writer = BytesWriter(f)
    """

    def __init__(self, stream: BinaryIO):
        """Create a BytesWriter from a file-like object.

        Args:
            stream: Any object with a write(data) method.
        """
        self._stream = stream

    async def write(self, data: bytes) -> None:
        """Write a chunk of data."""
        if len(data) > 0:
            self._stream.write(data)
