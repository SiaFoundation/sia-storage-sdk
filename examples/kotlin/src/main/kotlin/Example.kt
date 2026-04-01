import kotlinx.coroutines.runBlocking
import sia.indexd.*
import java.io.ByteArrayInputStream

class PrintLogger : Logger {
    override fun debug(msg: String) = println("DEBUG $msg")
    override fun info(msg: String) = println("INFO $msg")
    override fun warn(msg: String) = println("WARN $msg")
    override fun error(msg: String) = println("ERROR $msg")
}

fun main() = runBlocking {
    setLogger(PrintLogger(), "debug")

    val appId = ByteArray(32) { 0x01 }

    val builder = Builder("https://app.sia.storage", AppMeta(
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
    println("App registered ${appKey.export()}")

    println("Connected to indexd")

    var start = System.currentTimeMillis()
    val upload = sdk.uploadPacked(UploadOptions())

    for (i in 0 until 10) {
        val data = "hello, world $i!"
        val reader = StreamReader(ByteArrayInputStream(data.toByteArray()))
        val size = upload.add(reader)
        val rem = upload.remaining()
        println("upload $i added $size bytes ($rem remaining)")
    }

    val objects = upload.finalize()
    var elapsed = System.currentTimeMillis() - start
    println("Upload finished ${objects.size} objects in ${elapsed}ms")

    // Pin each object to the indexer
    for (obj in objects) {
        sdk.pinObject(obj)
        println("Pinned object ${obj.id()}")
    }

    start = System.currentTimeMillis()
    val lastObj = objects.last()
    println("Downloading object ${lastObj.id()} ${lastObj.size()} bytes")
    val downloaded = sdk.downloadBytes(lastObj)
    elapsed = System.currentTimeMillis() - start
    println("Downloaded object ${lastObj.id()} with ${downloaded.size} bytes in ${elapsed}ms")

    // Convenience functions for simple cases
    println("\nConvenience function examples...")

    val obj = sdk.uploadBytes("hello from uploadBytes!".toByteArray())
    println("Uploaded ${obj.size()} bytes with uploadBytes()")

    val data = sdk.downloadBytes(obj)
    println("Downloaded with downloadBytes(): \"${String(data)}\"")
}
