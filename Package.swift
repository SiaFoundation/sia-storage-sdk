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
        url: "https://github.com/SiaFoundation/sia-storage-sdk/releases/download/v0.4.1/SiaStorageSDKFFI-0.4.1.xcframework.zip",
        checksum: "8326daa482e3c7e8599622b030cfb5d2cf303069be566c96483ba26941e6aa7d"
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
