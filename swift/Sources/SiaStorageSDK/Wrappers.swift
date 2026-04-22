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
public final class BytesReader: Reader, @unchecked Sendable {
    private let data: Data?
    private var offset: Int = 0
    private let stream: InputStream?
    private let chunkSize: Int

    public init(data: Data, chunkSize: Int = 1 << 20) {
        self.data = data
        self.stream = nil
        self.chunkSize = chunkSize
    }

    public init(stream: InputStream, chunkSize: Int = 1 << 20) {
        self.data = nil
        self.stream = stream
        self.chunkSize = chunkSize
        if stream.streamStatus == .notOpen {
            stream.open()
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
        if bytesRead <= 0 {
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
}

/**
 * Convenience readers for the streaming `Download` handle.
 *
 * `Download` conforms to `AsyncSequence`, so you can iterate over the chunks
 * with `for try await`:
 *
 * ```swift
 * let d = try sdk.download(object: obj)
 * for try await chunk in d {
 *     process(chunk)
 * }
 * ```
 *
 * Or drain into a single buffer / writer:
 *
 * ```swift
 * let d = try sdk.download(object: obj)
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
     * let d = try sdk.download(object: obj)
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
                if written < 0 {
                    throw stream.streamError ?? NSError(domain: NSPOSIXErrorDomain, code: Int(EIO))
                }
                if written == 0 { break }
                total += UInt64(written)
                remaining = remaining.suffix(from: remaining.startIndex + written)
            }
        }
        return total
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
}
