/**
 * Idiomatic Node.js wrappers for the Sia SDK.
 *
 * This module provides convenience classes that make the SDK feel native
 * to Node.js developers, wrapping the low-level Reader/Writer traits with
 * standard Buffer support.
 */

import { Builder as _Builder } from "./sia_storage_ffi.js";

const DEFAULT_UPLOAD_OPTIONS = { max_inflight: 10, data_shards: 10, parity_shards: 20, progress_callback: undefined };
const DEFAULT_DOWNLOAD_OPTIONS = { max_inflight: 10, offset: 0n, length: undefined };

class BufferReader {
  #buffer;
  #offset;
  #chunkSize;

  constructor(buffer, chunkSize = 65536) {
    this.#buffer = buffer;
    this.#offset = 0;
    this.#chunkSize = chunkSize;
  }

  async read() {
    if (this.#offset >= this.#buffer.length) {
      return new Uint8Array(0);
    }
    const end = Math.min(this.#offset + this.#chunkSize, this.#buffer.length);
    const chunk = this.#buffer.subarray(this.#offset, end);
    this.#offset = end;
    return chunk;
  }
}

class BufferWriter {
  #chunks;

  constructor() {
    this.#chunks = [];
  }

  async write(data) {
    if (data.length > 0) {
      this.#chunks.push(data.slice());
    }
  }

  toBuffer() {
    return Buffer.concat(this.#chunks);
  }
}

export class Builder {
  #inner;

  /**
   * Creates a new SDK builder with the provided indexer URL.
   *
   * After creating the builder, call connected() to attempt to connect
   * using an existing app key, or request_connection() to request a new
   * connection.
   */
  constructor(indexer_url, app_meta) {
    this.#inner = new _Builder(indexer_url, app_meta);
  }

  async request_connection() {
    await this.#inner.request_connection();
    return this;
  }

  response_url() {
    return this.#inner.response_url();
  }

  async wait_for_approval() {
    await this.#inner.wait_for_approval();
    return this;
  }

  /**
   * Registers the application with the indexer using the provided mnemonic.
   * Returns an SDK instance that can be used to interact with the indexer.
   */
  async register(mnemonic) {
    return new SDK(await this.#inner.register(mnemonic));
  }

  /**
   * Attempts to connect using the provided app key.
   * Returns an SDK instance if valid, otherwise undefined.
   */
  async connected(app_key) {
    const result = await this.#inner.connected(app_key);
    return result ? new SDK(result) : undefined;
  }
}

export class SDK {
  #inner;

  /** @internal Use Builder.register() or Builder.connected() */
  constructor(inner) {
    this.#inner = inner;
  }

  /**
   * Uploads data to the Sia network and pins it to the indexer.
   *
   * @param {Buffer|Uint8Array} data - The data to upload.
   * @param {UploadOptions} [options] - Optional upload options.
   * @returns {Promise<PinnedObject>}
   */
  async upload(data, options) {
    return this.#inner.upload(new BufferReader(data), options ?? DEFAULT_UPLOAD_OPTIONS);
  }

  /**
   * Downloads an object and returns its contents as a Buffer.
   *
   * @param {PinnedObject} obj - The object to download.
   * @param {DownloadOptions} [options] - Optional download options.
   * @returns {Promise<Buffer>}
   */
  async download(obj, options) {
    const w = new BufferWriter();
    await this.#inner.download(w, obj, options ?? DEFAULT_DOWNLOAD_OPTIONS);
    return w.toBuffer();
  }

  /**
   * Creates a new packed upload for efficient multi-object uploads.
   *
   * @param {UploadOptions} [options] - Optional upload options.
   * @returns {Promise<PackedUpload>}
   */
  async upload_packed(options) {
    return new PackedUpload(await this.#inner.upload_packed(options ?? DEFAULT_UPLOAD_OPTIONS));
  }

  app_key() { return this.#inner.app_key(); }
  account() { return this.#inner.account(); }
  delete_object(key) { return this.#inner.delete_object(key); }
  hosts() { return this.#inner.hosts(); }
  object(key) { return this.#inner.object(key); }
  object_events(cursor, limit) { return this.#inner.object_events(cursor, limit); }
  pin_object(obj) { return this.#inner.pin_object(obj); }
  prune_slabs() { return this.#inner.prune_slabs(); }
  share_object(obj, valid_until) { return this.#inner.share_object(obj, valid_until); }
  shared_object(shared_url) { return this.#inner.shared_object(shared_url); }
  slab(slab_id) { return this.#inner.slab(slab_id); }
  update_object_metadata(obj) { return this.#inner.update_object_metadata(obj); }
}

export class PackedUpload {
  #inner;

  /** @internal Use SDK.upload_packed() */
  constructor(inner) {
    this.#inner = inner;
  }

  /**
   * Adds a new object to the upload.
   *
   * @param {Buffer|Uint8Array} data - The data to add.
   * @returns {Promise<bigint|number>} The number of bytes read.
   */
  async add(data) {
    return this.#inner.add(new BufferReader(data));
  }

  finalize() { return this.#inner.finalize(); }
  cancel() { return this.#inner.cancel(); }
  remaining() { return this.#inner.remaining(); }
  length() { return this.#inner.length(); }
  slabs() { return this.#inner.slabs(); }
}
