// swift-tools-version: 6.0
import Foundation
import PackageDescription

// Set SIA_STORAGE_SDK_USE_LOCAL_XCFRAMEWORK=1 to use a locally-built XCFramework.
let useLocalBinary = ProcessInfo.processInfo.environment["SIA_STORAGE_SDK_USE_LOCAL_XCFRAMEWORK"] == "1"

let binaryTarget: Target = useLocalBinary
    ? .binaryTarget(
        name: "SiaStorageSDKFFI",
        path: "build/SiaStorageSDKFFI.xcframework"
    )
    : .binaryTarget(
        name: "SiaStorageSDKFFI",
        url: "https://github.com/SiaFoundation/indexd-sdk/releases/download/v0.1.0/SiaStorageSDKFFI-0.1.0.xcframework.zip",
        checksum: "bba1b626e36a2eea1d0c0b9557ca04b3d7c0652ab84f8f4b72337fd8faef3bc6"
    )

let package = Package(
    name: "SiaStorageSDK",
    platforms: [
        .iOS(.v16),
        .macOS(.v14)
    ],
    products: [
        .library(name: "SiaStorageSDK", targets: ["SiaStorageSDK"])
    ],
    targets: [
        binaryTarget,
        .target(
            name: "SiaStorageSDK",
            dependencies: ["SiaStorageSDKFFI"],
            path: "swift/Sources/SiaStorageSDK",
            swiftSettings: [
                .swiftLanguageMode(.v5)
            ],
            linkerSettings: [
                .linkedFramework("Security"),
                .linkedFramework("SystemConfiguration")
            ]
        )
    ]
)
