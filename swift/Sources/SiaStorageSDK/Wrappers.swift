/**
 * Idiomatic Swift wrappers for the Sia SDK.
 *
 * This module provides convenience classes and extensions that make the SDK
 * feel native to Swift developers: a `Reader` adapter for both `Data` and
 * `InputStream` sources, and convenience methods on the streaming `Download`
 * handle for draining into `Data` or writing into an `OutputStream`.
 */

import Foundation

/**
 * Wraps a plain closure as a `ProgressCallback`.
 *
 * Example:
 * ```swift
 * try await sdk.upload(
 *     object: PinnedObject(),
 *     data: payload,
 *     options: UploadOptions(shardUploaded: progressCallback { p in
 *         print("uploaded shard \(p.shardIndex) in \(p.elapsedMs)ms")
 *     })
 * )
 * ```
 */
public func progressCallback(
    _ fn: @escaping @Sendable (ShardProgress) -> Void
) -> ProgressCallback {
    return ClosureProgressCallback(fn)
}

private final class ClosureProgressCallback: ProgressCallback, @unchecked Sendable {
    private let fn: @Sendable (ShardProgress) -> Void
    init(_ fn: @escaping @Sendable (ShardProgress) -> Void) { self.fn = fn }
    func progress(progress: ShardProgress) { fn(progress) }
}

/**
 * Adapts a `Data` value or `InputStream` to the `Reader` protocol.
 *
 * Example:
 * ```swift
 * // From bytes
 * let reader = BytesReader(data: "hello".data(using: .utf8)!)
 *
 * // From a file
 * let reader = BytesReader(stream: InputStream(fileAtPath: "data.bin")!)
 * ```
 */
/// Read calls are made sequentially by the SDK; this type is not safe
/// for concurrent reads from multiple tasks.
public final class BytesReader: Reader, @unchecked Sendable {
    private let data: Data?
    private var offset: Int = 0
    private let stream: InputStream?
    private let chunkSize: Int
    private let ownsStream: Bool

    public init(data: Data, chunkSize: Int = 1 << 20) {
        self.data = data
        self.stream = nil
        self.chunkSize = chunkSize
        self.ownsStream = false
    }

    public init(stream: InputStream, chunkSize: Int = 1 << 20) {
        self.data = nil
        self.stream = stream
        self.chunkSize = chunkSize
        if stream.streamStatus == .notOpen {
            stream.open()
            self.ownsStream = true
        } else {
            self.ownsStream = false
        }
    }

    deinit {
        if ownsStream, let stream = stream,
           stream.streamStatus != .closed {
            stream.close()
        }
    }

    public func read() async throws -> Data {
        if let data = data {
            if offset >= data.count {
                return Data()
            }
            let end = min(offset + chunkSize, data.count)
            let chunk = data[offset..<end]
            offset = end
            return Data(chunk)
        }
        guard let stream = stream else { return Data() }
        var buffer = [UInt8](repeating: 0, count: chunkSize)
        let bytesRead = buffer.withUnsafeMutableBufferPointer { ptr in
            stream.read(ptr.baseAddress!, maxLength: chunkSize)
        }
        if bytesRead < 0 {
            let err = stream.streamError
                ?? NSError(domain: NSPOSIXErrorDomain, code: Int(EIO))
            if ownsStream { stream.close() }
            throw err
        }
        if bytesRead == 0 {
            if ownsStream { stream.close() }
            return Data()
        }
        return Data(buffer.prefix(bytesRead))
    }
}

/**
 * Upload data to the Sia network.
 *
 * Pass `PinnedObject()` for a new upload. To resume a previous upload,
 * pass the object returned from the earlier call. Appending data changes
 * the object's ID, so any existing references must be updated and the
 * object must be re-pinned afterward.
 *
 * Example:
 * ```swift
 * let obj = try await sdk.upload(object: PinnedObject(), data: "hello".data(using: .utf8)!)
 * ```
 */
extension Sdk {
    public func upload(
        object: PinnedObject,
        data: Data,
        options: UploadOptions = UploadOptions()
    ) async throws -> PinnedObject {
        return try await upload(object: object, r: BytesReader(data: data), options: options)
    }

    public func upload(
        object: PinnedObject,
        stream: InputStream,
        options: UploadOptions = UploadOptions()
    ) async throws -> PinnedObject {
        return try await upload(object: object, r: BytesReader(stream: stream), options: options)
    }

    /**
     * Upload the file at `url` to the Sia network.
     *
     * Prefer this to the `Data` and `InputStream` overloads for files on disk:
     * the read stays on the Rust runtime instead of crossing the FFI boundary
     * once per chunk.
     *
     * Example:
     * ```swift
     * let obj = try await sdk.upload(
     *     object: PinnedObject(),
     *     file: URL(fileURLWithPath: "data.bin")
     * )
     * ```
     */
    public func upload(
        object: PinnedObject,
        file url: URL,
        options: UploadOptions = UploadOptions()
    ) async throws -> PinnedObject {
        return try await uploadPath(object: object, path: url.path, options: options)
    }

    /**
     * Create a new packed upload using the default options.
     *
     * Example:
     * ```swift
     * let upload = try await sdk.uploadPacked()
     * ```
     */
    public func uploadPacked() async throws -> PackedUpload {
        return try await uploadPacked(options: PackedUploadOptions())
    }

    /**
     * Create a sharing key that never expires.
     *
     * Attach objects to it with `shareObject(key:object:)` and hand out
     * `key.seed()` so recipients can connect with `SharedSdk.connect`.
     *
     * Example:
     * ```swift
     * let key = try await sdk.createSharingKey(description: "holiday photos")
     * try await sdk.shareObject(key: key, object: obj)
     * ```
     */
    public func createSharingKey(description: String) async throws -> SharingKey {
        return try await createSharingKey(description: description, expiresAt: nil)
    }

    /**
     * List the account's sharing keys, most recently created first.
     *
     * Example:
     * ```swift
     * for record in try await sdk.sharingKeys() {
     *     print("\(record.description): \(record.stats.objectCount) objects")
     * }
     * ```
     */
    public func sharingKeys() async throws -> [KeyRecord] {
        return try await sharingKeys(offset: 0, limit: 100)
    }

    /**
     * List and decrypt the objects attached to a sharing key.
     *
     * Example:
     * ```swift
     * let objects = try await sdk.sharedObjects(key: key)
     * ```
     */
    public func sharedObjects(key: SharingKey) async throws -> [PinnedObject] {
        return try await sharedObjects(key: key, offset: 0, limit: 100)
    }
}

/**
 * Convenience readers for the read-only `SharedSdk`.
 *
 * Example:
 * ```swift
 * let shared = try await SharedSdk.connect(indexerUrl: "https://sia.storage", seed: key.seed())
 * let objects = try await shared.objects()
 * let data = try await shared.download(object: objects[0]).readAll()
 * ```
 */
extension SharedSdk {
    /**
     * List and decrypt a page of the objects the key grants access to.
     *
     * Example:
     * ```swift
     * let objects = try await shared.objects()
     * ```
     */
    public func objects() async throws -> [PinnedObject] {
        return try await objects(offset: 0, limit: 100)
    }

    /**
     * Stream a shared object's data using the default download options.
     *
     * Example:
     * ```swift
     * let d = try shared.download(object: obj)
     * let data = try await d.readAll()
     * ```
     */
    public func download(object: PinnedObject) throws -> Download {
        return try download(object: object, options: DownloadOptions())
    }
}

/**
 * Convenience readers for the streaming `Download` handle.
 *
 * `Download` conforms to `AsyncSequence`, so you can iterate over the chunks
 * with `for try await`:
 *
 * ```swift
 * let d = try sdk.download(object: obj, options: DownloadOptions())
 * for try await chunk in d {
 *     process(chunk)
 * }
 * ```
 *
 * Or drain into a single buffer / writer:
 *
 * ```swift
 * let d = try sdk.download(object: obj, options: DownloadOptions())
 * let data = try await d.readAll()
 * ```
 *
 * Call `await d.cancel()` to abort an in-flight download early.
 */
extension Download: AsyncSequence {
    public typealias Element = Data

    public struct AsyncIterator: AsyncIteratorProtocol {
        let download: Download
        public mutating func next() async throws -> Data? {
            let chunk = try await download.read()
            return chunk.isEmpty ? nil : chunk
        }
    }

    public func makeAsyncIterator() -> AsyncIterator {
        AsyncIterator(download: self)
    }
}

extension Download {
    public func readAll() async throws -> Data {
        var buffer = Data()
        while true {
            let chunk = try await read()
            if chunk.isEmpty { break }
            buffer.append(chunk)
        }
        return buffer
    }

    /**
     * Streams the remaining data to an `OutputStream` and returns the total
     * bytes written. The stream is opened if it is not already open.
     *
     * Example:
     * ```swift
     * let out = OutputStream.toMemory()
     * let d = try sdk.download(object: obj, options: DownloadOptions())
     * let total = try await d.write(to: out)
     * ```
     */
    public func write(to stream: OutputStream) async throws -> UInt64 {
        if stream.streamStatus == .notOpen {
            stream.open()
        }
        var total: UInt64 = 0
        while true {
            let chunk = try await read()
            if chunk.isEmpty { break }
            var remaining = chunk
            while !remaining.isEmpty {
                let written = remaining.withUnsafeBytes { raw -> Int in
                    guard let base = raw.baseAddress else { return 0 }
                    return stream.write(base.assumingMemoryBound(to: UInt8.self), maxLength: raw.count)
                }
                if written <= 0 {
                    throw stream.streamError ?? NSError(domain: NSPOSIXErrorDomain, code: Int(EIO))
                }
                total += UInt64(written)
                remaining = remaining.suffix(from: remaining.startIndex + written)
            }
        }
        return total
    }

    /**
     * Writes the whole download to `url`, creating or truncating the file, and
     * returns the number of bytes written.
     *
     * Prefer this to `readAll()` or `write(to:)` when the destination is a
     * local file: the data never crosses the FFI boundary.
     *
     * Example:
     * ```swift
     * let d = try sdk.download(object: obj, options: DownloadOptions())
     * let total = try await d.write(to: URL(fileURLWithPath: "out.bin"))
     * ```
     */
    public func write(to url: URL) async throws -> UInt64 {
        return try await writeToPath(path: url.path)
    }
}

/**
 * Add data to a packed upload.
 *
 * Example:
 * ```swift
 * let size = try await upload.add(data: "hello".data(using: .utf8)!)
 * ```
 */
extension PackedUpload {
    public func add(data: Data) async throws -> UInt64 {
        return try await add(reader: BytesReader(data: data))
    }

    public func add(stream: InputStream) async throws -> UInt64 {
        return try await add(reader: BytesReader(stream: stream))
    }

    /**
     * Add the file at `url` to the packed upload.
     *
     * Prefer this to the `Data` and `InputStream` overloads for files on disk:
     * the read stays on the Rust runtime instead of crossing the FFI boundary
     * once per chunk.
     *
     * Example:
     * ```swift
     * let size = try await upload.add(file: URL(fileURLWithPath: "data.bin"))
     * ```
     */
    public func add(file url: URL) async throws -> UInt64 {
        return try await addPath(path: url.path)
    }
}
