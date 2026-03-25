// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "SiaStorageExample",
    platforms: [
        .iOS(.v16),
        .macOS(.v14)
    ],
    dependencies: [
        // Reference the SiaStorageSDK package at the repo root
        .package(path: "../../"),
    ],
    targets: [
        .executableTarget(
            name: "SiaStorageExample",
            dependencies: [
                .product(name: "SiaStorageSDK", package: "indexd-sdk"),
            ],
            path: "Sources"
        )
    ]
)
