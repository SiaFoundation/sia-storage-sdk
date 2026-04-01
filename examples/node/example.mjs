import * as readline from "node:readline/promises";
import { stdin as input, stdout as output } from "node:process";

import {
  generate_recovery_phrase,
  set_logger,
  Builder,
} from "sia-storage-sdk";

// Set up logging
set_logger(
  {
    debug(msg) { console.log("DEBUG", msg); },
    info(msg) { console.log("INFO", msg); },
    warn(msg) { console.log("WARNING", msg); },
    error(msg) { console.log("ERROR", msg); },
  },
  "debug",
);

async function main() {
  const appId = new Uint8Array(32).fill(0x01);

  const builder = new Builder("https://app.sia.storage", {
    id: appId,
    name: "node example",
    description: "an example app",
    service_url: "https://example.com",
    logo_url: undefined,
    callback_url: undefined,
  });
  await builder.request_connection();

  console.log(`Please approve connection ${builder.response_url()}`);
  await builder.wait_for_approval();

  const rl = readline.createInterface({ input, output });
  let mnemonic = await rl.question(
    "Enter mnemonic (or leave empty to generate new): ",
  );
  rl.close();

  if (!mnemonic) {
    mnemonic = generate_recovery_phrase();
    console.log("mnemonic:", mnemonic);
  }

  const sdk = await builder.register(mnemonic);

  // Store the app key for later use
  const appKey = sdk.app_key();
  console.log(
    "App registered:",
    Buffer.from(appKey.export()).toString("base64"),
  );

  console.log("Connected to indexer");

  let start = Date.now();
  const obj = await sdk.upload(Buffer.from("hello from upload()!"));
  console.log(`Uploaded ${obj.size()} bytes with upload() in ${Date.now() - start}ms`);

  start = Date.now();
  const data = await sdk.download(obj);
  console.log(`Downloaded with download(): ${JSON.stringify(data.toString())} in ${Date.now() - start}ms`);

  console.log("\nUpload Packing Example...");

  start = Date.now();
  const upload = await sdk.upload_packed();

  for (let i = 0; i < 10; i++) {
    const size = await upload.add(Buffer.from(`hello, world ${i}!`));
    const rem = upload.remaining();
    console.log(`upload ${i} added ${size} bytes (${rem} remaining)`);
  }

  const objects = await upload.finalize();
  let elapsed = Date.now() - start;
  console.log(`Upload finished ${objects.length} objects in ${elapsed}ms`);

  start = Date.now();
  const lastObj = objects[objects.length - 1];
  console.log(`Downloading object ${lastObj.id()} ${lastObj.size()} bytes`);
  const downloaded = await sdk.download(lastObj);
  elapsed = Date.now() - start;
  console.log(
    `Downloaded object ${lastObj.id()} with ${downloaded.length} bytes in ${elapsed}ms`,
  );
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
