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
        url: "https://github.com/SiaFoundation/sia-storage-sdk/releases/download/v0.1.0/SiaStorageSDKFFI-0.1.0.xcframework.zip",
        checksum: "ae2e6c6d35104aeb5e85b71ad86e842573d3f880594a45b4327c8ea6414291bb"
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
