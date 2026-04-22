# Sia Storage SDK for Kotlin

Kotlin bindings for Sia Storage, built with Rust and UniFFI.

## Requirements

- JDK 17+
- Kotlin 2.1.0+

## Installation

### Gradle (Maven Central)

Add to your `build.gradle.kts`:

```kotlin
dependencies {
    implementation("tech.sia:siastoragesdk:0.3.0")
}
```

## Example

```kotlin
import kotlinx.coroutines.runBlocking
import sia.indexd.*
import java.io.ByteArrayInputStream

fun main() = runBlocking {
    setLogger(PrintLogger(), "debug")

    val appId = ByteArray(32) { 0x01 }

    val builder = Builder("https://sia.storage", AppMeta(
        id = appId,
        name = "My App",
        description = "App description",
        serviceUrl = "https://myapp.com",
        logoUrl = null,
        callbackUrl = null,
    ))

    builder.requestConnection()

    // Wait for user approval
    println("Please approve connection ${builder.responseUrl()}")
    builder.waitForApproval()

    // Register with a recovery phrase
    val mnemonic = generateRecoveryPhrase()
    val sdk = builder.register(mnemonic)

    // Upload data
    val upload = sdk.uploadPacked(UploadOptions())
    val reader = StreamReader(ByteArrayInputStream("hello, world!".toByteArray()))
    upload.add(reader)
    val objects = upload.finalize()

    // Download data
    val data = sdk.downloadBytes(objects.last())
}
```

`PrintLogger` is a user-defined class that implements the SDK's `Logger` interface.
`StreamReader` is provided by the SDK to adapt any `InputStream` to the `Reader` interface.

A complete working example is available in [examples/kotlin/](../examples/kotlin/).

## Local Development

```sh
# Build the Rust library
cargo build --release

# Generate Kotlin bindings
cargo run --release --bin uniffi-bindgen generate \
  --library target/release/libsia_storage_ffi.so \
  --language kotlin \
  --out-dir bindings \
  --config kotlin/uniffi.toml \
  --no-format

# Copy bindings and native library into the Kotlin project
cp bindings/sia/indexd/sia_storage_ffi.kt kotlin/src/main/kotlin/sia/indexd/
mkdir -p kotlin/src/main/resources/linux-x86-64
cp target/release/libsia_storage_ffi.so kotlin/src/main/resources/linux-x86-64/

# Build the SDK
cd kotlin && gradle build -x test

# Run the example
cd ../examples/kotlin && gradle run
```

## License

MIT License - see [LICENSE](../LICENSE) for details.
