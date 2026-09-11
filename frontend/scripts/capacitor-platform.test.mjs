import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

import { blobToBase64, sanitizeDownloadName } from '../src/platform/capacitor.ts';
import { resumeClientConnection } from '../src/platform/lifecycleState.ts';

const frontendRoot = fileURLToPath(new URL('../', import.meta.url));

test('Capacitor 正式配置固定安全本地 origin、WebView 111 和必要插件', () => {
  const config = readFileSync(join(frontendRoot, 'capacitor.config.ts'), 'utf8');
  assert.match(config, /webDir:\s*'dist-app'/);
  assert.match(config, /hostname:\s*'localhost'/);
  assert.match(config, /androidScheme:\s*'https'/);
  assert.match(config, /cleartext:\s*false/);
  assert.match(config, /allowMixedContent:\s*false/);
  assert.match(config, /minWebViewVersion:\s*111/);
  assert.match(config, /CapacitorHttp:[\s\S]*?enabled:\s*false/);
  assert.doesNotMatch(config, /server:\s*\{[\s\S]*?url:/);
});

test('Android 原生返回键必须交给已注册的 JS backButton 监听器', () => {
  const config = readFileSync(join(frontendRoot, 'capacitor.config.ts'), 'utf8');
  assert.doesNotMatch(config, /disableBackButtonHandler:\s*true/);
});

test('Android Manifest 拒绝明文并仅允许应用私有 FileProvider 范围', () => {
  const manifest = readFileSync(join(frontendRoot, 'android/app/src/main/AndroidManifest.xml'), 'utf8');
  const paths = readFileSync(join(frontendRoot, 'android/app/src/main/res/xml/file_paths.xml'), 'utf8');
  assert.match(manifest, /usesCleartextTraffic="false"/);
  assert.match(manifest, /networkSecurityConfig="@xml\/network_security_config"/);
  assert.doesNotMatch(paths, /<external-path\b/);
});

test('Android 前台恢复先验会话和全量状态，再建立单一 SSE', async () => {
  const order = [];
  const authenticated = await resumeClientConnection({
    hasServerProfile: () => true,
    disconnectEvents: () => order.push('disconnect'),
    probeSession: async () => { order.push('probe'); return true; },
    refreshSnapshot: async () => { order.push('snapshot'); },
    connectEvents: () => order.push('events'),
  });
  assert.equal(authenticated, true);
  assert.deepEqual(order, ['disconnect', 'probe', 'snapshot', 'events']);
});

test('Android 下载文件名与 base64 桥有明确边界', async () => {
  assert.equal(sanitizeDownloadName('../report?.pdf'), 'report_.pdf');
  assert.equal(await blobToBase64(new Blob(['SCP-cv'])), 'U0NQLWN2');
  await assert.rejects(blobToBase64(new Blob([new Uint8Array(32 * 1024 * 1024 + 1)])), /32 MiB/);
});
