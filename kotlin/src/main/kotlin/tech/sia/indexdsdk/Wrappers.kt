/**
 * Idiomatic Kotlin wrappers for the Sia SDK.
 *
 * This module provides convenience classes and extension functions that make the SDK
 * feel native to Kotlin developers, wrapping the low-level Reader/Writer
 * traits with standard Java/Kotlin I/O support.
 */
package tech.sia.indexdsdk

import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.InputStream
import java.io.OutputStream

/**
 * Adapts an [InputStream] to the [Reader] trait.
 *
 * This allows you to upload data from any source that supports the standard
 * Java/Kotlin InputStream interface (files, ByteArrayInputStream, etc.).
 *
 * Example:
 * ```kotlin
 * // From bytes
 * val reader = StreamReader(ByteArrayInputStream(data))
 *
 * // From file
 * val reader = StreamReader(FileInputStream("data.bin"))
 * ```
 */
class StreamReader(
    private val stream: InputStream,
    private val chunkSize: Int = 65536,
) : Reader {
    override suspend fun read(): ByteArray {
        val buffer = ByteArray(chunkSize)
        val bytesRead = stream.read(buffer)
        return if (bytesRead <= 0) ByteArray(0) else buffer.copyOf(bytesRead)
    }
}

/**
 * Adapts an [OutputStream] to the [Writer] trait.
 *
 * This allows you to download data to any destination that supports the
 * standard Java/Kotlin OutputStream interface (files, ByteArrayOutputStream, etc.).
 *
 * Example:
 * ```kotlin
 * // To ByteArrayOutputStream
 * val buffer = ByteArrayOutputStream()
 * val writer = StreamWriter(buffer)
 *
 * // To file
 * val writer = StreamWriter(FileOutputStream("output.bin"))
 * ```
 */
class StreamWriter(
    private val stream: OutputStream,
) : Writer {
    override suspend fun write(data: ByteArray) {
        if (data.isNotEmpty()) {
            stream.write(data)
        }
    }
}

/**
 * Upload bytes directly to the Sia network.
 *
 * Example:
 * ```kotlin
 * val obj = sdk.uploadBytes("hello, world!".toByteArray())
 * ```
 */
suspend fun Sdk.uploadBytes(
    data: ByteArray,
    options: UploadOptions = UploadOptions(),
): PinnedObject = upload(StreamReader(ByteArrayInputStream(data)), options)

/**
 * Download an object and return its contents as bytes.
 *
 * Example:
 * ```kotlin
 * val data = sdk.downloadBytes(obj)
 * ```
 */
suspend fun Sdk.downloadBytes(
    obj: PinnedObject,
    options: DownloadOptions = DownloadOptions(),
): ByteArray {
    val buffer = ByteArrayOutputStream()
    download(StreamWriter(buffer), obj, options)
    return buffer.toByteArray()
}
