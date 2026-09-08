// Electron sandboxed preload 只允许通过受限的 CommonJS require 取得 Electron API；
// 不使用 ESM import，否则打包后 Chromium 会在 sandbox wrapper 中拒绝执行脚本。
const { contextBridge, ipcRenderer } = require('electron') as typeof import('electron');

const IPC = Object.freeze({
  pickFile: 'scp-cv:file:pick',
  saveFile: 'scp-cv:file:save',
  clearSession: 'scp-cv:session:clear',
  loadServerProfile: 'scp-cv:server-profile:load',
  saveServerProfile: 'scp-cv:server-profile:save',
  lifecycle: 'scp-cv:lifecycle',
  backRequested: 'scp-cv:back-requested',
});

type StoredServerProfile = {
  origin: string;
  displayName: string;
  allowInsecureDevelopment?: boolean;
};

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
