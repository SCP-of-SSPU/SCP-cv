import { isAbsolute, relative, resolve, sep } from 'node:path';

export const APP_SCHEME = 'app';
export const APP_HOST = 'scp-cv';
export const APP_ORIGIN = `${APP_SCHEME}://${APP_HOST}`;

export const PACKAGED_CSP = [
  "default-src 'self'",
  "script-src 'self'",
  "style-src 'self' 'unsafe-inline'",
  "connect-src https: wss: http://127.0.0.1:* http://localhost:*",
  "img-src 'self' data: blob: https:",
  "media-src 'self' blob: https:",
  "font-src 'self' data:",
  "object-src 'none'",
  "base-uri 'none'",
  "frame-src 'none'",
  "form-action 'self' https:",
].join('; ');

export interface StoredServerProfile {
  origin: string;
  displayName: string;
  allowInsecureDevelopment?: boolean;
}

export function normalizeStoredServerProfile(profile: StoredServerProfile): StoredServerProfile {
  if (!profile || typeof profile.origin !== 'string' || typeof profile.displayName !== 'string') {
    throw new Error('播放主机配置格式无效。');
  }
  const url = new URL(profile.origin.trim());
  const isLoopback = ['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname);
  const allowHttp = Boolean(profile.allowInsecureDevelopment && isLoopback);
  if (url.protocol !== 'https:' && !(url.protocol === 'http:' && allowHttp)) {
    throw new Error('远程播放主机必须使用 HTTPS。');
  }
  if (url.username || url.password || url.pathname !== '/' || url.search || url.hash) {
    throw new Error('播放主机地址只能包含 scheme、host 和 port。');
  }
  return {
    origin: url.origin,
    displayName: profile.displayName.trim().slice(0, 100) || url.host,
    allowInsecureDevelopment: allowHttp,
  };
}

export function safeResolveAppAsset(root: string, requestUrl: string): string {
  // URL 会在暴露 pathname 前折叠编码后的点段，因此必须先拒绝原始编码点段。
  if (/%2e/i.test(requestUrl)) throw new Error('应用资源路径无效。');
  const url = new URL(requestUrl);
  if (url.protocol !== `${APP_SCHEME}:` || url.hostname !== APP_HOST || url.username || url.password) {
    throw new Error('不受信任的应用资源地址。');
  }
  const pathname = decodeURIComponent(url.pathname);
  if (pathname.includes('\\') || pathname.includes('\0')) throw new Error('应用资源路径无效。');
  const relativePath = pathname === '/' || pathname === '' ? 'index.html' : pathname.replace(/^\/+/, '');
  const assetPath = resolve(root, relativePath);
  const boundary = relative(root, assetPath);
  if (boundary.startsWith(`..${sep}`) || boundary === '..' || isAbsolute(boundary)) {
    throw new Error('应用资源路径越界。');
  }
  return assetPath;
}

export function isTrustedRendererUrl(rendererUrl: string, developmentUrl = ''): boolean {
  try {
    const url = new URL(rendererUrl);
    if (url.protocol === `${APP_SCHEME}:` && url.hostname === APP_HOST) return true;
    if (!developmentUrl) return false;
    const allowed = new URL(developmentUrl);
    const isLoopback = ['127.0.0.1', 'localhost', '[::1]'].includes(allowed.hostname);
    return isLoopback && url.origin === allowed.origin;
  } catch {
    return false;
  }
}

export function validateDevelopmentUrl(rawUrl: string): string {
  if (!rawUrl) return '';
  const url = new URL(rawUrl);
  const isLoopback = ['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname);
  if (!isLoopback || !['http:', 'https:'].includes(url.protocol) || url.username || url.password) {
    throw new Error('Electron 开发地址必须是无凭据的本机 HTTP(S) 地址。');
  }
  return url.href;
}
