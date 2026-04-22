import kotlinx.coroutines.runBlocking
import sia.indexd.*
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.util.Base64

class PrintLogger : Logger {
    override fun debug(msg: String) = println("DEBUG $msg")
    override fun info(msg: String) = println("INFO $msg")
    override fun warn(msg: String) = println("WARNING $msg")
    override fun error(msg: String) = println("ERROR $msg")
}

val onUpload = progressCallback { p ->
    println("  uploaded slab ${p.slabIndex} shard ${p.shardIndex} " +
            "(${p.shardSize} bytes) to ${p.hostKey} in ${p.elapsedMs}ms")
}

val onDownload = progressCallback { p ->
    println("  downloaded slab ${p.slabIndex} shard ${p.shardIndex} " +
            "(${p.shardSize} bytes) from ${p.hostKey} in ${p.elapsedMs}ms")
}

fun main() = runBlocking {
    setLogger(PrintLogger(), "debug")

    val appId = ByteArray(32) { 0x01 }

    val builder = Builder("https://sia.storage", AppMeta(
        id = appId,
        name = "kotlin example",
        description = "an example app",
        serviceUrl = "https://example.com",
        logoUrl = null,
        callbackUrl = null,
    ))

    builder.requestConnection()

    println("Please approve connection ${builder.responseUrl()}")
    builder.waitForApproval()

    print("Enter mnemonic (or leave empty to generate new): ")
    var mnemonic = readlnOrNull()?.trim() ?: ""
    if (mnemonic.isEmpty()) {
        mnemonic = generateRecoveryPhrase()
        println("mnemonic: $mnemonic")
    }

    val sdk = builder.register(mnemonic)

    val appKey = sdk.appKey()
    println("App registered: ${Base64.getEncoder().encodeToString(appKey.export())}")

    println("Connected to indexer")

    var start = System.currentTimeMillis()
    val obj = sdk.upload(
        PinnedObject(),
        ByteArrayInputStream("hello from upload()!".toByteArray()),
        UploadOptions(shardUploaded = onUpload),
    )
    sdk.pinObject(obj)
    var elapsed = (System.currentTimeMillis() - start) / 1000.0
    println("Uploaded and pinned ${obj.size()} bytes with upload() in %.2fs".format(elapsed))

    start = System.currentTimeMillis()
    val d = sdk.download(obj, DownloadOptions(shardDownloaded = onDownload))
    val data = d.readAll()
    elapsed = (System.currentTimeMillis() - start) / 1000.0
    println("Downloaded with download(): \"${String(data)}\" in %.2fs".format(elapsed))

    println("\nUpload Packing Example...")

    start = System.currentTimeMillis()
    val upload = sdk.uploadPacked(UploadOptions())

    for (i in 0 until 10) {
        val payload = "hello, world $i!"
        val size = upload.add(ByteArrayInputStream(payload.toByteArray()))
        val rem = upload.remaining()
        println("upload $i added $size bytes ($rem remaining)")
    }

    val objects = upload.finalize()
    elapsed = (System.currentTimeMillis() - start) / 1000.0
    println("Upload finished ${objects.size} objects in %.2fs".format(elapsed))

    // Pin each object to the indexer
    for (obj in objects) {
        sdk.pinObject(obj)
        println("Pinned object ${obj.id()}")
    }

    start = System.currentTimeMillis()
    val lastObj = objects.last()
    println("Downloading object ${lastObj.id()} ${lastObj.size()} bytes")
    val buffer = ByteArrayOutputStream()
    val d2 = sdk.download(lastObj, DownloadOptions())
    val total = d2.writeTo(buffer)
    elapsed = (System.currentTimeMillis() - start) / 1000.0
    println("Downloaded object ${lastObj.id()} with $total bytes in %.2fs".format(elapsed))
}
