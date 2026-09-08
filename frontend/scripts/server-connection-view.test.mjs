import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

import { deriveConnectionLayerSummary } from '../src/features/settings/serverConnectionState.ts';

const sourceRoot = fileURLToPath(new URL('../src/', import.meta.url));

test('控制链路在线不能伪装 PlayerWorker 在线', () => {
  assert.deepEqual(deriveConnectionLayerSummary('connected', [
    { player_online: false },
    { player_online: false },
  ]), {
    control: 'connected',
    player: 'offline',
    onlinePlayerCount: 0,
  });
  assert.deepEqual(deriveConnectionLayerSummary('closed', [
    { player_online: true },
  ]), {
    control: 'offline',
    player: 'online',
    onlinePlayerCount: 1,
  });
});

test('连接页为公开 focus 路由且登录页和设置页都有入口', () => {
  const router = readFileSync(`${sourceRoot}/router/index.ts`, 'utf8');
  const login = readFileSync(`${sourceRoot}/features/auth/LoginView.vue`, 'utf8');
  const runtimeSettings = readFileSync(`${sourceRoot}/features/settings/tabs/RuntimeSettingsTab.vue`, 'utf8');

  assert.match(router, /path:\s*'\/connect'[\s\S]*?public:\s*true[\s\S]*?focus:\s*true/);
  assert.match(login, /to="\/connect"/);
  assert.match(runtimeSettings, /router\.push\('\/connect'\)/);
});

test('连接页通过 runtime.switchServer 切换代次并重新探测认证状态', () => {
  const view = readFileSync(`${sourceRoot}/features/settings/ServerConnectionView.vue`, 'utf8');
  const locale = readFileSync(`${sourceRoot}/locales/zh-CN/core.ts`, 'utf8');
  assert.match(view, /await runtime\.switchServer\(/);
  assert.match(view, /await auth\.probeCurrentServer\(\)/);
  assert.match(locale, /SSE 在线不能代替播放器在线/);
});
