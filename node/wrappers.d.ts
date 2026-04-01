import {
  AppKey,
  AppMeta,
  Account,
  DownloadOptions,
  Host,
  ObjectEvent,
  ObjectsCursor,
  PinnedObject,
  PinnedSlab,
  UploadOptions,
} from "./sia_storage_ffi.js";

export declare class Builder {
  constructor(indexer_url: string, app_meta: AppMeta);
  request_connection(): Promise<Builder>;
  response_url(): string;
  wait_for_approval(): Promise<Builder>;
  register(mnemonic: string): Promise<SDK>;
  connected(app_key: AppKey): Promise<SDK | undefined>;
}

export declare class SDK {
  upload(data: Buffer | Uint8Array, options?: UploadOptions): Promise<PinnedObject>;
  download(obj: PinnedObject, options?: DownloadOptions): Promise<Buffer>;
  upload_packed(options?: UploadOptions): Promise<PackedUpload>;
  app_key(): AppKey;
  account(): Promise<Account>;
  delete_object(key: string): Promise<void>;
  hosts(): Promise<Array<Host>>;
  object(key: string): Promise<PinnedObject>;
  object_events(cursor: ObjectsCursor | undefined, limit: number): Promise<Array<ObjectEvent>>;
  pin_object(obj: PinnedObject): Promise<void>;
  prune_slabs(): Promise<void>;
  share_object(obj: PinnedObject, valid_until: Date): string;
  shared_object(shared_url: string): Promise<PinnedObject>;
  slab(slab_id: string): Promise<PinnedSlab>;
  update_object_metadata(obj: PinnedObject): Promise<void>;
}

export declare class PackedUpload {
  add(data: Buffer | Uint8Array): Promise<bigint | number>;
  finalize(): Promise<Array<PinnedObject>>;
  cancel(): Promise<void>;
  remaining(): bigint | number;
  length(): bigint | number;
  slabs(): bigint | number;
}
