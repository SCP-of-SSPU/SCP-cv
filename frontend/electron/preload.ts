import { contextBridge, ipcRenderer } from 'electron';

import { IPC } from './channels.js';
import type { StoredServerProfile } from './security.js';

type LifecycleState = 'active' | 'inactive';

function validateAccept(accept: unknown): string[] {
  if (!Array.isArray(accept) || accept.length > 32 || accept.some((item) => typeof item !== 'string' || item.length > 128)) {
    throw new Error('文件类型过滤器无效。');
  }
  return [...accept];
}

const bridge = Object.freeze({
  platform: 'electron' as const,
  pickFile: (accept: readonly string[] = []) => ipcRenderer.invoke(IPC.pickFile, validateAccept(accept)),
  saveFile: (request: { suggestedName: string; mimeType: string; bytes: Uint8Array }) => {
    if (!request || typeof request.suggestedName !== 'string' || !(request.bytes instanceof Uint8Array)) {
      throw new Error('保存请求无效。');
    }
    return ipcRenderer.invoke(IPC.saveFile, request);
  },
  clearSession: () => ipcRenderer.invoke(IPC.clearSession),
  loadServerProfile: () => ipcRenderer.invoke(IPC.loadServerProfile),
  saveServerProfile: (profile: StoredServerProfile) => ipcRenderer.invoke(IPC.saveServerProfile, profile),
  onLifecycleChanged: (listener: (state: LifecycleState) => void) => {
    const wrapped = (_event: Electron.IpcRendererEvent, state: LifecycleState) => listener(state);
    ipcRenderer.on(IPC.lifecycle, wrapped);
    return () => ipcRenderer.removeListener(IPC.lifecycle, wrapped);
  },
  onBackRequested: (listener: () => void) => {
    const wrapped = () => listener();
    ipcRenderer.on(IPC.backRequested, wrapped);
    return () => ipcRenderer.removeListener(IPC.backRequested, wrapped);
  },
});

contextBridge.exposeInMainWorld('scpCvElectron', bridge);
