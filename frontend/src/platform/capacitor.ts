import { App } from '@capacitor/app';
import { Capacitor, CapacitorCookies } from '@capacitor/core';
import { Directory, Filesystem } from '@capacitor/filesystem';

import type {
  ClientLifecycleState,
  PlatformAdapter,
  PlatformFile,
  SaveFileRequest,
} from './index';

const MAX_BASE64_SAVE_BYTES = 32 * 1024 * 1024;

export function sanitizeDownloadName(name: string): string {
  const sanitized = name.trim()
    .replace(/^(?:\.\.[\\/])+/, '')
    .replace(/[\\/:*?"<>|\u0000-\u001f]/g, '_')
    .replace(/^\.+/, '');
  if (!sanitized || sanitized.length > 180) throw new Error('下载文件名无效。');
  return sanitized;
}

export async function blobToBase64(blob: Blob): Promise<string> {
  if (blob.size > MAX_BASE64_SAVE_BYTES) {
    throw new Error('Android 下载文件超过 32 MiB；请改用网页下载或较小的文件。');
  }
  const bytes = new Uint8Array(await blob.arrayBuffer());
  let binary = '';
  const chunkSize = 0x8000;
  for (let offset = 0; offset < bytes.length; offset += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + chunkSize));
  }
  return btoa(binary);
}

function pickHtmlFile(accept: readonly string[]): Promise<PlatformFile | null> {
  return new Promise((resolve) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = accept.join(',');
    input.hidden = true;
    let settled = false;
    const finish = (file: File | null) => {
      if (settled) return;
      settled = true;
      window.removeEventListener('focus', onFocus);
      input.remove();
      resolve(file
        ? { name: file.name, mimeType: file.type || 'application/octet-stream', size: file.size, data: file }
        : null);
    };
    const onFocus = () => window.setTimeout(() => finish(input.files?.[0] ?? null), 0);
    input.addEventListener('change', () => finish(input.files?.[0] ?? null), { once: true });
    window.addEventListener('focus', onFocus, { once: true });
    document.body.append(input);
    input.click();
  });
}

function bindAsyncListener<T>(
  registration: Promise<{ remove(): Promise<void> }>,
  onReady?: (handle: { remove(): Promise<void> }) => void,
): () => void {
  let disposed = false;
  let handle: { remove(): Promise<void> } | null = null;
  void registration.then(async (created) => {
    if (disposed) await created.remove();
    else {
      handle = created;
      onReady?.(created);
    }
  });
  return () => {
    disposed = true;
    if (handle) void handle.remove();
  };
}

export function createCapacitorPlatformAdapter(): PlatformAdapter {
  if (!Capacitor.isNativePlatform() || Capacitor.getPlatform() !== 'android') {
    throw new Error('Capacitor Android 原生桥不可用。');
  }
  return {
    platform: 'android',
    isPackaged: true,
    onBackRequested(handler) {
      return bindAsyncListener(App.addListener('backButton', async () => {
        const handled = await handler();
        if (!handled) await App.exitApp();
      }));
    },
    onLifecycleChanged(handler) {
      return bindAsyncListener(App.addListener('appStateChange', ({ isActive }) => {
        handler(isActive ? 'active' : 'inactive');
      }));
    },
    pickFile(accept = []) {
      return pickHtmlFile(accept);
    },
    async saveFile(request: SaveFileRequest): Promise<boolean> {
      const permission = await Filesystem.checkPermissions();
      if (permission.publicStorage === 'prompt' || permission.publicStorage === 'prompt-with-rationale') {
        const requested = await Filesystem.requestPermissions();
        if (requested.publicStorage === 'denied') throw new Error('未授予文件保存权限。');
      } else if (permission.publicStorage === 'denied') {
        throw new Error('未授予文件保存权限。');
      }
      await Filesystem.writeFile({
        path: `SCP-cv/${sanitizeDownloadName(request.suggestedName)}`,
        data: await blobToBase64(request.data),
        directory: Directory.Documents,
        recursive: true,
      });
      return true;
    },
    async clearSession(): Promise<void> {
      await CapacitorCookies.clearAllCookies();
    },
  };
}

export type { ClientLifecycleState };
