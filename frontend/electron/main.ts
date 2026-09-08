import { readFile, writeFile } from 'node:fs/promises';
import { readFileSync } from 'node:fs';
import { basename, extname, join } from 'node:path';

import {
  app,
  BrowserWindow,
  dialog,
  ipcMain,
  protocol,
  session,
  type IpcMainInvokeEvent,
} from 'electron';

import { IPC } from './channels.js';
import {
  APP_HOST,
  APP_ORIGIN,
  APP_SCHEME,
  PACKAGED_CSP,
  isTrustedRendererUrl,
  normalizeStoredServerProfile,
  safeResolveAppAsset,
  validateDevelopmentUrl,
  type StoredServerProfile,
} from './security.js';

protocol.registerSchemesAsPrivileged([
  {
    scheme: APP_SCHEME,
    privileges: {
      standard: true,
      secure: true,
      supportFetchAPI: true,
      corsEnabled: true,
      stream: true,
    },
  },
]);

const developmentUrl = validateDevelopmentUrl(process.env.SCP_CV_ELECTRON_DEV_URL?.trim() ?? '');
const controlPartition = 'persist:scp-cv-control';
const MAX_BRIDGE_FILE_BYTES = 256 * 1024 * 1024;
let mainWindow: BrowserWindow | null = null;

function assertTrustedCaller(event: IpcMainInvokeEvent): void {
  const senderUrl = event.senderFrame?.url ?? '';
  if (!isTrustedRendererUrl(senderUrl, developmentUrl)) {
    throw new Error('拒绝来自非应用页面的原生能力调用。');
  }
}

function contentType(path: string): string {
  switch (extname(path).toLowerCase()) {
    case '.html': return 'text/html; charset=utf-8';
    case '.js': return 'text/javascript; charset=utf-8';
    case '.css': return 'text/css; charset=utf-8';
    case '.json': return 'application/json; charset=utf-8';
    case '.svg': return 'image/svg+xml';
    case '.png': return 'image/png';
    case '.jpg':
    case '.jpeg': return 'image/jpeg';
    case '.woff2': return 'font/woff2';
    default: return 'application/octet-stream';
  }
}

function registerAppProtocol(): void {
  const rendererRoot = join(app.getAppPath(), 'dist-app');
  // 渲染窗口使用持久化 partition；协议处理器必须注册到同一个 session，
  // 仅注册默认 session 会导致打包客户端导航到 app:// 时得到空白页。
  session.fromPartition(controlPartition).protocol.handle(APP_SCHEME, async (request) => {
    try {
      const assetPath = safeResolveAppAsset(rendererRoot, request.url);
      return new Response(readFileSync(assetPath), {
        headers: {
          'Content-Type': contentType(assetPath),
          'Content-Security-Policy': PACKAGED_CSP,
          'X-Content-Type-Options': 'nosniff',
        },
      });
    } catch (error) {
      console.error('app protocol resource failure', request.url, error);
      return new Response('Not found', {
        status: 404,
        headers: { 'Content-Security-Policy': PACKAGED_CSP },
      });
    }
  });
}

function setupSessionSecurity(): void {
  const controlSession = session.fromPartition(controlPartition);
  controlSession.setPermissionCheckHandler(() => false);
  controlSession.setPermissionRequestHandler((_webContents, _permission, callback) => callback(false));
  controlSession.webRequest.onHeadersReceived((details, callback) => {
    if (developmentUrl && new URL(details.url).origin === new URL(developmentUrl).origin) {
      callback({ responseHeaders: details.responseHeaders });
      return;
    }
    callback({
      responseHeaders: {
        ...details.responseHeaders,
        'Content-Security-Policy': [PACKAGED_CSP],
        'X-Content-Type-Options': ['nosniff'],
      },
    });
  });
}

function setupIpc(): void {
  ipcMain.handle(IPC.pickFile, async (event, accept: unknown) => {
    assertTrustedCaller(event);
    if (!Array.isArray(accept) || accept.length > 32 || accept.some((item) => typeof item !== 'string' || item.length > 128)) {
      throw new Error('文件类型过滤器无效。');
    }
    const result = await dialog.showOpenDialog(mainWindow!, {
      properties: ['openFile'],
      filters: accept.length ? [{ name: '允许的文件', extensions: accept.flatMap(extensionFromAccept).filter(Boolean) }] : undefined,
    });
    if (result.canceled || !result.filePaths[0]) return null;
    const bytes = await readFile(result.filePaths[0]);
    if (bytes.byteLength > MAX_BRIDGE_FILE_BYTES) throw new Error('所选文件超过 256 MiB 原生桥接上限。');
    return { name: basename(result.filePaths[0]), mimeType: '', bytes };
  });

  ipcMain.handle(IPC.saveFile, async (event, request: unknown) => {
    assertTrustedCaller(event);
    if (!request || typeof request !== 'object') throw new Error('保存请求无效。');
    const { suggestedName, bytes } = request as { suggestedName?: unknown; bytes?: unknown };
    if (typeof suggestedName !== 'string' || basename(suggestedName) !== suggestedName || suggestedName.length > 240) {
      throw new Error('建议文件名无效。');
    }
    if (!(bytes instanceof Uint8Array) || bytes.byteLength > MAX_BRIDGE_FILE_BYTES) {
      throw new Error('保存内容无效或超过 256 MiB。');
    }
    const result = await dialog.showSaveDialog(mainWindow!, { defaultPath: suggestedName });
    if (result.canceled || !result.filePath) return false;
    await writeFile(result.filePath, bytes);
    return true;
  });

  ipcMain.handle(IPC.clearSession, async (event) => {
    assertTrustedCaller(event);
    await event.sender.session.clearStorageData({ storages: ['cookies'] });
  });

  ipcMain.handle(IPC.loadServerProfile, async (event) => {
    assertTrustedCaller(event);
    try {
      const raw = await readFile(join(app.getPath('userData'), 'server-profile.json'), 'utf8');
      return normalizeStoredServerProfile(JSON.parse(raw) as StoredServerProfile);
    } catch {
      return null;
    }
  });

  ipcMain.handle(IPC.saveServerProfile, async (event, profile: StoredServerProfile) => {
    assertTrustedCaller(event);
    const normalized = normalizeStoredServerProfile(profile);
    await writeFile(join(app.getPath('userData'), 'server-profile.json'), `${JSON.stringify(normalized, null, 2)}\n`, { encoding: 'utf8', mode: 0o600 });
    return normalized;
  });
}

function extensionFromAccept(value: string): string[] {
  const extension = value.trim().replace(/^\./, '');
  return /^[a-zA-Z0-9]+$/.test(extension) ? [extension] : [];
}

function createWindow(): BrowserWindow {
  const window = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 360,
    minHeight: 640,
    show: false,
    autoHideMenuBar: true,
    webPreferences: {
      partition: controlPartition,
      preload: join(import.meta.dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      webSecurity: true,
      allowRunningInsecureContent: false,
    },
  });
  window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  window.webContents.on('will-navigate', (event, url) => {
    if (!isTrustedRendererUrl(url, developmentUrl)) event.preventDefault();
  });
  window.webContents.on('did-fail-load', (_event, errorCode, errorDescription, validatedURL) => {
    console.error('renderer load failure', errorCode, errorDescription, validatedURL);
  });
  window.webContents.on('did-finish-load', () => console.error('renderer load finished', window.webContents.getURL()));
  window.on('focus', () => window.webContents.send(IPC.lifecycle, 'active'));
  window.on('blur', () => window.webContents.send(IPC.lifecycle, 'inactive'));
  window.once('ready-to-show', () => window.show());
  window.on('closed', () => { mainWindow = null; });
  void window.loadURL(developmentUrl || `${APP_ORIGIN}/`);
  return window;
}

app.whenReady().then(async () => {
  registerAppProtocol();
  setupSessionSecurity();
  setupIpc();
  mainWindow = createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) mainWindow = createWindow();
  });
});

app.on('window-all-closed', () => app.quit());
