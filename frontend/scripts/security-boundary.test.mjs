import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import test from 'node:test';

import { isTrustedRendererUrl, safeResolveAppAsset } from '../electron/security.ts';

test('Electron 外链与编码路径不能穿透受信边界', async () => {
  assert.equal(isTrustedRendererUrl('https://evil.example/'), false);
  assert.throws(() => safeResolveAppAsset(resolve('dist-app'), 'app://scp-cv/%2e%2e/secrets.txt'));

  const main = await readFile(new URL('../electron/main.ts', import.meta.url), 'utf8');
  assert.match(main, /setWindowOpenHandler\(\(\) => \(\{ action: 'deny' \}\)\)/);
  assert.match(main, /will-navigate[\s\S]*isTrustedRendererUrl[\s\S]*preventDefault/);
  assert.match(main, /setPermissionCheckHandler\(\(\) => false\)/);
});

test('原生桥仅允许受信页面且不暴露 Named Pipe 与 Office', async () => {
  const preload = await readFile(new URL('../electron/preload.ts', import.meta.url), 'utf8');
  const main = await readFile(new URL('../electron/main.ts', import.meta.url), 'utf8');
  assert.match(main, /assertTrustedCaller\(event\)/);
  assert.doesNotMatch(preload, /namedPipe|PowerPoint|Office|child_process/i);
  assert.match(main, /nodeIntegration: false/);
  assert.match(main, /contextIsolation: true/);
  assert.match(main, /sandbox: true/);
});
