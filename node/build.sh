#!/usr/bin/env bash
set -euo pipefail

# Build Node.js package for SiaStorageSDK
#
# Prerequisites:
#   cargo install --git https://github.com/SiaFoundation/uniffi-bindgen-node-js --rev cafa761cc510e48c51ed6e45b400429f59f8f53e
#
# Usage:
#   ./node/build.sh

BUNDLED_PREBUILDS=false
while [ $# -gt 0 ]; do
    case "$1" in
        --bundled-prebuilds) BUNDLED_PREBUILDS=true; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

NODE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$NODE_DIR/.." && pwd)"

PACKAGE="sia-storage-sdk"
CRATE="sia_storage_ffi"
LIB="libsia_storage_ffi"
OUT_DIR="$NODE_DIR/generated"

cd "$REPO_ROOT"

# Clean previous build
rm -rf "$OUT_DIR"

# Build the native library
cargo build --release

# Determine library extension
case "$(uname -s)" in
    Darwin) EXT="dylib" ;;
    MINGW*|MSYS*|CYGWIN*) EXT="dll"; LIB="sia_storage_ffi" ;;
    *) EXT="so" ;;
esac

LIB_PATH="target/release/${LIB}.${EXT}"

# Locate uniffi-bindgen-node-js
BINDGEN="${UNIFFI_BINDGEN_NODE_JS:-$(command -v uniffi-bindgen-node-js 2>/dev/null || true)}"
if [ -z "$BINDGEN" ]; then
    echo "uniffi-bindgen-node-js not found. Install with:"
    echo "  cargo install --git https://github.com/SiaFoundation/uniffi-bindgen-node-js --rev cafa761cc510e48c51ed6e45b400429f59f8f53e"
    exit 1
fi

# Generate Node.js bindings
BINDGEN_ARGS=("$LIB_PATH" --crate-name "$CRATE" --out-dir "$OUT_DIR" --package-name "$PACKAGE")
if [ "$BUNDLED_PREBUILDS" = true ]; then
    BINDGEN_ARGS+=(--bundled-prebuilds)
fi
"$BINDGEN" generate "${BINDGEN_ARGS[@]}"

# Copy native library into the package
if [ "$BUNDLED_PREBUILDS" = false ]; then
    cp "$LIB_PATH" "$OUT_DIR/"
fi

# Copy hand-written wrappers and generate index files
cp "$NODE_DIR/wrappers.js" "$OUT_DIR/wrappers.js"
cp "$NODE_DIR/wrappers.d.ts" "$OUT_DIR/wrappers.d.ts"

# Wrapper classes override the generated Builder, SDK, and PackedUpload
INDEX='export { Builder, SDK, PackedUpload } from "./wrappers.js";
export * from "./sia_storage_ffi.js";'
echo "$INDEX" > "$OUT_DIR/index.js"
echo "$INDEX" > "$OUT_DIR/index.d.ts"

# Install dependencies
cd "$OUT_DIR"
npm install

echo "Node.js package built at $OUT_DIR"
