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
    val obj = sdk.upload(ByteArrayInputStream("hello from upload()!".toByteArray()))
    sdk.pinObject(obj)
    var elapsed = System.currentTimeMillis() - start
    println("Uploaded and pinned ${obj.size()} bytes with upload() in ${elapsed}ms")

    val data = ByteArrayOutputStream()
    start = System.currentTimeMillis()
    sdk.download(data, obj)
    elapsed = System.currentTimeMillis() - start
    println("Downloaded with download(): \"${String(data.toByteArray())}\" in ${elapsed}ms")

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
    elapsed = System.currentTimeMillis() - start
    println("Upload finished ${objects.size} objects in ${elapsed}ms")

    // Pin each object to the indexer
    for (obj in objects) {
        sdk.pinObject(obj)
        println("Pinned object ${obj.id()}")
    }

    start = System.currentTimeMillis()
    val lastObj = objects.last()
    println("Downloading object ${lastObj.id()} ${lastObj.size()} bytes")
    val buffer = ByteArrayOutputStream()
    sdk.download(buffer, lastObj, DownloadOptions())
    elapsed = System.currentTimeMillis() - start
    println("Downloaded object ${lastObj.id()} with ${buffer.size()} bytes in ${elapsed}ms")
}
