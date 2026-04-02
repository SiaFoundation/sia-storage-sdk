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
        url: "https://github.com/SiaFoundation/sia-storage-sdk/releases/download/v0.3.0/SiaStorageSDKFFI-0.3.0.xcframework.zip",
        checksum: "5ac3e380f76227cdbfabb9a0ece1fd21d9eac70a2e2bd8c80197fd7bf1bb8644"
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
