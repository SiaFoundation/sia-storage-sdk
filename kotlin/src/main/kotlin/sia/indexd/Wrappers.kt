/**
 * Idiomatic Kotlin wrappers for the Sia SDK.
 *
 * This module provides convenience classes and extension functions that make the SDK
 * feel native to Kotlin developers, wrapping the low-level Reader trait with
 * standard Java/Kotlin I/O support and exposing the streaming [Download] handle
 * with convenience readers for in-memory and [OutputStream] sinks.
 */
package sia.indexd

import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.InputStream
import java.io.OutputStream
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow

/**
 * Wraps a plain lambda as a [ProgressCallback].
 *
 * Example:
 * ```kotlin
 * sdk.upload(obj, stream, UploadOptions(shardUploaded = progressCallback { p ->
 *     println("uploaded shard ${p.shardIndex} in ${p.elapsedMs}ms")
 * }))
 * ```
 */
fun progressCallback(fn: (ShardProgress) -> Unit): ProgressCallback = object : ProgressCallback {
    override fun progress(progress: ShardProgress) = fn(progress)
}

/**
 * Adapts an [InputStream] to the [Reader] trait.
 *
 * This allows you to upload data from any source that supports the standard
 * Java/Kotlin InputStream interface (files, ByteArrayInputStream, etc.).
 *
 * Example:
 * ```kotlin
 * // From bytes
 * val reader = BytesReader(ByteArrayInputStream(data))
 *
 * // From file
 * val reader = BytesReader(FileInputStream("data.bin"))
 * ```
 */
class BytesReader(
    private val stream: InputStream,
    private val chunkSize: Int = 1 shl 20,
) : Reader {
    override suspend fun read(): ByteArray {
        val buffer = ByteArray(chunkSize)
        val bytesRead = stream.read(buffer)
        return if (bytesRead <= 0) ByteArray(0) else buffer.copyOf(bytesRead)
    }
}

/**
 * Upload data from an [InputStream] to the Sia network.
 *
 * Pass `PinnedObject()` for a new upload. To resume a previous upload,
 * pass the object returned from the earlier call. Appending data changes
 * the object's ID, so any existing references must be updated and the
 * object must be re-pinned afterward.
 *
 * Example:
 * ```kotlin
 * val obj = sdk.upload(PinnedObject(), ByteArrayInputStream("hello, world!".toByteArray()))
 * ```
 */
suspend fun Sdk.upload(
    obj: PinnedObject,
    r: InputStream,
    options: UploadOptions = UploadOptions(),
): PinnedObject = upload(obj, BytesReader(r), options)

/**
 * Upload an in-memory [ByteArray] to the Sia network.
 *
 * Example:
 * ```kotlin
 * val obj = sdk.upload(PinnedObject(), "hello, world!".toByteArray())
 * ```
 */
suspend fun Sdk.upload(
    obj: PinnedObject,
    data: ByteArray,
    options: UploadOptions = UploadOptions(),
): PinnedObject = upload(obj, BytesReader(ByteArrayInputStream(data)), options)

/**
 * Reads the entire remaining stream into memory and returns it.
 *
 * Example:
 * ```kotlin
 * val d = sdk.download(obj)
 * try { val bytes = d.readAll() } finally { d.close() }
 * ```
 */
suspend fun Download.readAll(): ByteArray {
    val out = ByteArrayOutputStream()
    while (true) {
        val chunk = read()
        if (chunk.isEmpty()) break
        out.write(chunk)
    }
    return out.toByteArray()
}

/**
 * Exposes the download as a cold [Flow] of chunks. Emission stops on EOF.
 *
 * Example:
 * ```kotlin
 * sdk.download(obj).use { d ->
 *     d.asFlow().collect { chunk -> process(chunk) }
 * }
 * ```
 */
fun Download.asFlow(): Flow<ByteArray> = flow {
    while (true) {
        val chunk = read()
        if (chunk.isEmpty()) break
        emit(chunk)
    }
}

/**
 * Streams the remaining data to an [OutputStream] and returns the total bytes written.
 *
 * Example:
 * ```kotlin
 * val buffer = ByteArrayOutputStream()
 * val d = sdk.download(obj)
 * try { d.writeTo(buffer) } finally { d.close() }
 * ```
 */
suspend fun Download.writeTo(w: OutputStream): Long {
    var total = 0L
    while (true) {
        val chunk = read()
        if (chunk.isEmpty()) break
        w.write(chunk)
        total += chunk.size
    }
    return total
}

/**
 * Add data from an [InputStream] to a packed upload.
 *
 * Example:
 * ```kotlin
 * val size = upload.add(ByteArrayInputStream(data))
 * ```
 */
suspend fun PackedUpload.add(
    reader: InputStream,
): ULong = add(BytesReader(reader))

/**
 * Add an in-memory [ByteArray] to a packed upload.
 *
 * Example:
 * ```kotlin
 * val size = upload.add("hello, world!".toByteArray())
 * ```
 */
suspend fun PackedUpload.add(
    data: ByteArray,
): ULong = add(BytesReader(ByteArrayInputStream(data)))
