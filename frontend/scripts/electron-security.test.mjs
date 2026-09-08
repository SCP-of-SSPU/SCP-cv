import assert from 'node:assert/strict';
import { isAbsolute, resolve } from 'node:path';
import test from 'node:test';

import {
  PACKAGED_CSP,
  isTrustedRendererUrl,
  normalizeStoredServerProfile,
  safeResolveAppAsset,
  validateDevelopmentUrl,
} from '../electron/security.ts';

test('app 协议只解析打包根目录内资源', () => {
  const root = resolve('dist-app');
  assert.equal(safeResolveAppAsset(root, 'app://scp-cv/'), resolve(root, 'index.html'));
  assert.equal(safeResolveAppAsset(root, 'app://scp-cv/assets/app.js'), resolve(root, 'assets/app.js'));
  assert.throws(() => safeResolveAppAsset(root, 'app://other/index.html'));
  assert.throws(() => safeResolveAppAsset(root, 'https://scp-cv/index.html'));
  assert.throws(() => safeResolveAppAsset(root, 'app://scp-cv/%2e%2e/secret.txt'));
  assert.equal(isAbsolute(safeResolveAppAsset(root, 'app://scp-cv/index.html')), true);
});

test('打包 CSP 和渲染器信任边界禁止任意导航与原生对象', () => {
  assert.match(PACKAGED_CSP, /object-src 'none'/);
  assert.match(PACKAGED_CSP, /frame-src 'none'/);
  assert.doesNotMatch(PACKAGED_CSP, /script-src[^;]*'unsafe-eval'/);
  assert.equal(isTrustedRendererUrl('app://scp-cv/'), true);
  assert.equal(isTrustedRendererUrl('https://evil.example/'), false);
  assert.equal(isTrustedRendererUrl('http://127.0.0.1:5173/', 'http://127.0.0.1:5173/'), true);
  assert.equal(isTrustedRendererUrl('http://127.0.0.1:5174/', 'http://127.0.0.1:5173/'), false);
  assert.throws(() => validateDevelopmentUrl('https://remote.example/'));
});

test('Electron 主机配置只保存非敏感 HTTPS origin', () => {
  assert.deepEqual(normalizeStoredServerProfile({ origin: 'https://host.test/', displayName: ' 主机 ' }), {
    origin: 'https://host.test',
    displayName: '主机',
    allowInsecureDevelopment: false,
  });
  assert.throws(() => normalizeStoredServerProfile({ origin: 'https://user:pass@host.test', displayName: 'bad' }));
  assert.throws(() => normalizeStoredServerProfile({ origin: 'http://host.test', displayName: 'bad' }));
});

test('preload 不向 renderer 暴露 ipcRenderer 或任意文件 API', async () => {
  const { readFile } = await import('node:fs/promises');
  const preload = await readFile(new URL('../electron/preload.ts', import.meta.url), 'utf8');
  const exposed = preload.match(/const bridge = Object\.freeze\(\{([\s\S]*?)\n\}\);/)?.[1] ?? '';
  assert.doesNotMatch(exposed, /ipcRenderer\s*[:,]/);
  assert.doesNotMatch(exposed, /readFile|writeFile|namedPipe|powerpoint/i);
  assert.match(exposed, /pickFile/);
  assert.match(exposed, /saveFile/);
  assert.match(exposed, /clearSession/);
  assert.match(exposed, /loadServerProfile/);
});

test('切换主机通过 Electron 薄适配清理 Cookie 并保存非敏感配置', async () => {
  const { readFile } = await import('node:fs/promises');
  const runtime = await readFile(new URL('../src/stores/runtime.ts', import.meta.url), 'utf8');
  assert.match(runtime, /createElectronPlatformAdapter\(window\.scpCvElectron\)\.clearSession\(\)/);
  assert.match(runtime, /saveElectronServerProfile\(nextProfile, window\.scpCvElectron\)/);
});
