# Re-export all public API from the native UniFFI module
from sia_storage.sia_storage.sia_storage_ffi import (
    # Functions
    generate_recovery_phrase,
    validate_recovery_phrase,
    set_logger,
    encoded_size,
    uniffi_set_event_loop,
    # Classes/Objects
    AppKey,
    PinnedObject,
    # Records
    Account,
    App,
    AppMeta,
    Host,
    NetAddress,
    ObjectEvent,
    ObjectsCursor,
    PinnedSector,
    PinnedSlab,
    SealedObject,
    ShardProgress,
    Slab,
    UploadOptions,
    DownloadOptions,
    # Enums
    AddressProtocol,
    # Errors
    Error,
    ConnectError,
    UploadError,
    DownloadError,
    AppKeyError,
    SeedError,
    BuilderError,
    ObjectError,
    IoError,
    # Base classes for implementing custom traits
    Logger,
    Reader,
    ProgressCallback,
)

# Idiomatic Python wrappers for common operations
from sia_storage.wrappers import (
    Builder,
    BytesReader,
    Download,
    PackedUpload,
    Sdk,
)

# Aliases for common naming conventions
SDK = Sdk
IOError = IoError

__all__ = [
    # Functions
    "generate_recovery_phrase",
    "validate_recovery_phrase",
    "set_logger",
    "encoded_size",
    "uniffi_set_event_loop",
    # Classes/Objects
    "SDK",
    "Builder",
    "AppKey",
    "PinnedObject",
    "PackedUpload",
    "Download",
    "BytesReader",
    # Records
    "Account",
    "App",
    "AppMeta",
    "Host",
    "NetAddress",
    "ObjectEvent",
    "ObjectsCursor",
    "PinnedSector",
    "PinnedSlab",
    "SealedObject",
    "ShardProgress",
    "Slab",
    "UploadOptions",
    "DownloadOptions",
    # Enums
    "AddressProtocol",
    # Errors
    "Error",
    "ConnectError",
    "UploadError",
    "DownloadError",
    "AppKeyError",
    "SeedError",
    "BuilderError",
    "ObjectError",
    "IOError",  # alias
    # Base classes for implementing custom traits
    "Logger",
    "Reader",
    "ProgressCallback",
]
