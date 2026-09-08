import type { PlatformAdapter, PlatformFile } from './index';

export interface DownloadResponse {
  readonly ok: boolean;
  readonly status?: number;
  readonly headers: Headers;
  blob(): Promise<Blob>;
}

export async function pickUploadFile(
  adapter: Pick<PlatformAdapter, 'pickFile'>,
  accept: readonly string[] = [],
): Promise<PlatformFile | null> {
  return adapter.pickFile(accept);
}

export async function saveResponseFile(
  adapter: Pick<PlatformAdapter, 'saveFile'>,
  response: DownloadResponse,
  suggestedName: string,
): Promise<boolean> {
  if (!response.ok) {
    throw new Error(`下载失败：HTTP ${response.status ?? 'unknown'}`);
  }
  const data = await response.blob();
  return adapter.saveFile({
    suggestedName,
    mimeType: response.headers.get('Content-Type') || data.type || 'application/octet-stream',
    data,
  });
}
