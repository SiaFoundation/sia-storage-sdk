/**
 * Idiomatic Swift wrappers for the Sia SDK.
 *
 * This module provides convenience classes and extensions that make the SDK
 * feel native to Swift developers, wrapping the low-level Reader/Writer
 * protocols with standard Swift Data support.
 */

import Foundation

/**
 * Adapts a `Data` value to the `Reader` protocol.
 *
 * This allows you to upload data from any `Data` source.
 *
 * Example:
 * ```swift
 * let reader = BytesReader(data: "hello".data(using: .utf8)!)
 * ```
 */
public final class BytesReader: Reader, @unchecked Sendable {
    private let data: Data
    private var offset: Int = 0
    private let chunkSize: Int

    public init(data: Data, chunkSize: Int = 1 << 20) {
        self.data = data
        self.chunkSize = chunkSize
    }

    public func read() async throws -> Data {
        if offset >= data.count {
            return Data()
        }

        let end = min(offset + chunkSize, data.count)
        let chunk = data[offset..<end]
        offset = end
        return Data(chunk)
    }
}

/**
 * Adapts a mutable buffer to the `Writer` protocol.
 *
 * This allows you to download data into an in-memory buffer.
 *
 * Example:
 * ```swift
 * let writer = BytesWriter()
 * // ... download into writer ...
 * let data = writer.getData()
 * ```
 */
public final class BytesWriter: Writer, @unchecked Sendable {
    private var buffer = Data()

    public init() {}

    public func write(data: Data) async throws {
        if !data.isEmpty {
            buffer.append(data)
        }
    }

    public func getData() -> Data {
        return buffer
    }
}

/**
 * Upload data to the Sia network.
 *
 * Example:
 * ```swift
 * let obj = try await sdk.upload(data: "hello, world!".data(using: .utf8)!)
 * ```
 */
extension Sdk {
    public func upload(
        data: Data,
        options: UploadOptions = UploadOptions()
    ) async throws -> PinnedObject {
        return try await upload(object: PinnedObject(), r: BytesReader(data: data), options: options)
    }

    /**
     * Download an object and return its contents as `Data`.
     *
     * Example:
     * ```swift
     * let data = try await sdk.download(object: obj)
     * ```
     */
    public func download(
        object: PinnedObject,
        options: DownloadOptions = DownloadOptions()
    ) async throws -> Data {
        let writer = BytesWriter()
        try await download(w: writer, object: object, options: options)
        return writer.getData()
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
}
