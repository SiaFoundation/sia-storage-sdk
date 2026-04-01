# SiaStorageSDK for Node.js

Node.js bindings for Sia Storage, built with Rust and UniFFI.

## Requirements

- Node.js 20+
- ESM modules (`"type": "module"` in package.json)

## Installation

```bash
npm install sia-storage-sdk
```

## Example

```javascript
import { generate_recovery_phrase, Builder } from "sia-storage-sdk";

// Create a builder and connect
const builder = new Builder("https://app.sia.storage", {
  id: new Uint8Array(32).fill(0x01),
  name: "My App",
  description: "App description",
  service_url: "https://myapp.com",
  logo_url: undefined,
  callback_url: undefined,
});
await builder.request_connection();
await builder.wait_for_approval();

// Register with a recovery phrase
const mnemonic = generate_recovery_phrase();
const sdk = await builder.register(mnemonic);

// Upload data
const obj = await sdk.upload(Buffer.from("hello, world!"));

// Download data
const data = await sdk.download(obj);
```

For custom streaming, implement the `Reader` and `Writer` interfaces
and use the raw FFI SDK directly.

A complete working example is available in [examples/node/](../examples/node/).

## Local Development

```sh
# Install uniffi-bindgen-node-js (first time only)
cargo install --git https://github.com/SiaFoundation/uniffi-bindgen-node-js --rev cafa761cc510e48c51ed6e45b400429f59f8f53e

# Build native library, generate bindings, and assemble the package
./node/build.sh

# Run the example
cd examples/node && npm install && node example.mjs
```

## License

MIT License - see [LICENSE](../LICENSE) for details.
