# SiaStorageSDK for Swift

Swift bindings for Sia Storage, built with Rust and UniFFI.

## Requirements

- iOS 16.0+ / macOS 14.0+
- Swift 6.0+
- Xcode 16.0+

## Installation

### Swift Package Manager

Add to your `Package.swift`:

```swift
dependencies: [
    .package(url: "https://github.com/SiaFoundation/sia-storage-sdk", from: "0.1.0")
]
```

Then add `SiaStorageSDK` to your target's dependencies:

```swift
.target(
    name: "YourTarget",
    dependencies: [
        .product(name: "SiaStorageSDK", package: "sia-storage-sdk")
    ]
)
```

Or in Xcode: File → Add Packages → enter the repository URL.

### CocoaPods

```ruby
pod 'SiaStorageSDK', '~> 0.1.0'
```

## Example

```swift
import SiaStorageSDK

// Set up logging
setLogger(logger: MyLogger(), level: "debug")

// Create a builder and connect
let builder = try await Builder(indexerUrl: "https://sia.storage", appMeta: AppMeta(
    id: appId,
    name: "My App",
    description: "App description",
    serviceUrl: "https://myapp.com",
    logoUrl: nil,
    callbackUrl: nil
))
    .requestConnection()

// Wait for user approval
let approvedBuilder = try await builder.waitForApproval()

// Register with a recovery phrase
let mnemonic = generateRecoveryPhrase()
let sdk = try await approvedBuilder.register(mnemonic: mnemonic)

// Upload data
let upload = await sdk.uploadPacked(options: UploadOptions())
let reader = BytesReader(data: myData)
try await upload.add(reader: reader)
let objects = try await upload.finalize()

// Download data
let writer = BytesWriter()
try await sdk.download(w: writer, object: objects[0], options: DownloadOptions())
```

`MyLogger`, `BytesReader`, and `BytesWriter` are user-defined types that conform to
the SDK's `Logger`, `Reader`, and `Writer` protocols.

A complete working example is available in [examples/swift/](../examples/swift/).

## Local Development

```sh
# Install Rust targets (first time only)
rustup target add aarch64-apple-ios aarch64-apple-ios-sim x86_64-apple-ios aarch64-apple-darwin x86_64-apple-darwin

# Build the XCFramework
./swift/build.sh

# Build the package locally
SIA_STORAGE_SDK_USE_LOCAL_XCFRAMEWORK=1 swift build

# Run the example
cd examples/swift
SIA_STORAGE_SDK_USE_LOCAL_XCFRAMEWORK=1 swift run
```

## License

MIT License - see [LICENSE](../LICENSE) for details.
