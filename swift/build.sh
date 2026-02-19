#!/usr/bin/env bash
set -euo pipefail

# Build XCFramework and Swift package for IndexdSDK
#
# Prerequisites:
#   rustup target add aarch64-apple-ios aarch64-apple-ios-sim x86_64-apple-ios \
#                     aarch64-apple-darwin x86_64-apple-darwin
#
# Usage:
#   SIA_SDK_RS_PATH=/path/to/sia-sdk-rs ./swift/build.sh

if [ -z "${SIA_SDK_RS_PATH:-}" ]; then
    echo "Error: SIA_SDK_RS_PATH must be set to the path of the sia-sdk-rs repository"
    exit 1
fi

SWIFT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SWIFT_DIR/.." && pwd)"

CRATE="indexd_ffi"
LIB="libindexd_ffi"
FFI_MODULE="IndexdSDKFFI"
SWIFT_MODULE="IndexdSDK"

BUILD_DIR="$REPO_ROOT/build"
GEN_DIR="$REPO_ROOT/build/generated"

cd "$SIA_SDK_RS_PATH"

# Build all Apple targets
for target in aarch64-apple-ios aarch64-apple-ios-sim x86_64-apple-ios aarch64-apple-darwin x86_64-apple-darwin; do
    cargo build -p "$CRATE" --release --target "$target"
done

# Build host dylib for uniffi-bindgen
cargo build -p "$CRATE" --release

# Generate Swift bindings
mkdir -p "$GEN_DIR"
cargo run -p "$CRATE" --bin uniffi-bindgen -- \
    generate --library "target/release/${LIB}.dylib" \
    --language swift \
    --out-dir "$GEN_DIR" \
    --config "$SWIFT_DIR/uniffi.toml"

# Create fat binaries
mkdir -p "$BUILD_DIR"/{ios-device,ios-simulator,macos}/Headers

cp "target/aarch64-apple-ios/release/${LIB}.a" "$BUILD_DIR/ios-device/"

lipo -create \
    "target/aarch64-apple-ios-sim/release/${LIB}.a" \
    "target/x86_64-apple-ios/release/${LIB}.a" \
    -output "$BUILD_DIR/ios-simulator/${LIB}.a"

lipo -create \
    "target/aarch64-apple-darwin/release/${LIB}.a" \
    "target/x86_64-apple-darwin/release/${LIB}.a" \
    -output "$BUILD_DIR/macos/${LIB}.a"

# Stage headers
for platform in ios-device ios-simulator macos; do
    cp "$GEN_DIR/${FFI_MODULE}.h" "$BUILD_DIR/$platform/Headers/"
    cp "$GEN_DIR/${FFI_MODULE}.modulemap" "$BUILD_DIR/$platform/Headers/module.modulemap"
done

# Create XCFramework
rm -rf "$BUILD_DIR/${FFI_MODULE}.xcframework"
xcodebuild -create-xcframework \
    -library "$BUILD_DIR/ios-device/${LIB}.a" \
    -headers "$BUILD_DIR/ios-device/Headers" \
    -library "$BUILD_DIR/ios-simulator/${LIB}.a" \
    -headers "$BUILD_DIR/ios-simulator/Headers" \
    -library "$BUILD_DIR/macos/${LIB}.a" \
    -headers "$BUILD_DIR/macos/Headers" \
    -output "$BUILD_DIR/${FFI_MODULE}.xcframework"

# Copy generated Swift source
mkdir -p "$REPO_ROOT/swift/Sources/$SWIFT_MODULE"
cp "$GEN_DIR/${SWIFT_MODULE}.swift" "$REPO_ROOT/swift/Sources/$SWIFT_MODULE/$SWIFT_MODULE.swift"

echo "Swift source updated at: $REPO_ROOT/swift/Sources/$SWIFT_MODULE"

# Distribution zip with checksum
rm -f "$BUILD_DIR/${FFI_MODULE}.xcframework.zip"
(cd "$BUILD_DIR" && zip -rq "${FFI_MODULE}.xcframework.zip" "${FFI_MODULE}.xcframework")
CHECKSUM=$(swift package compute-checksum "$BUILD_DIR/${FFI_MODULE}.xcframework.zip")

echo ""
echo "=== Build Complete ==="
echo "XCFramework: $BUILD_DIR/${FFI_MODULE}.xcframework"
echo "Distribution zip: $BUILD_DIR/${FFI_MODULE}.xcframework.zip"
echo "Checksum: $CHECKSUM"
echo ""
echo "To use locally:"
echo "  INDEXD_SDK_USE_LOCAL_XCFRAMEWORK=1 swift build"
