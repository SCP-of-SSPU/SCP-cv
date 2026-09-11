import assert from 'node:assert/strict';
import test from 'node:test';

import {
  ClientConnectionCoordinator,
  OfflineCommandError,
  loadStoredServerProfile,
  normalizeServerProfile,
} from '../src/platform/connection.ts';
import { resolveCsrfToken } from '../src/platform/csrf.ts';

test('multipart 上传优先使用登录流程缓存的 CSRF token', () => {
  assert.equal(resolveCsrfToken('cached-token', 'cookie-token'), 'cached-token');
  assert.equal(resolveCsrfToken('', 'cookie-token'), 'cookie-token');
  assert.equal(resolveCsrfToken('', ''), '');
});

test('服务器配置只接受 HTTPS origin 或显式本机 HTTP 开发地址', () => {
  assert.equal(normalizeServerProfile({ origin: 'https://host.test/', displayName: '' }).origin, 'https://host.test');
  assert.equal(
    normalizeServerProfile({
      origin: 'http://127.0.0.1:18000',
      displayName: '本机',
      allowInsecureDevelopment: true,
    }).origin,
    'http://127.0.0.1:18000',
  );
  assert.throws(() => normalizeServerProfile({ origin: 'http://host.test', displayName: '不安全' }));
  assert.throws(() => normalizeServerProfile({ origin: 'https://user:pass@host.test', displayName: '凭据' }));
  assert.throws(() => normalizeServerProfile({ origin: 'https://host.test/api', displayName: '路径' }));
  assert.equal(loadStoredServerProfile({ getItem: () => '{invalid' }), null);
});

test('切换播放主机递增 generation 并清理旧 SSE、会话和业务状态', async () => {
  const calls = [];
  const coordinator = new ClientConnectionCoordinator({
    closeEvents: () => calls.push('close-events'),
    clearSession: async () => calls.push('clear-session'),
    clearStores: () => calls.push('clear-stores'),
    saveProfile: async (profile) => calls.push(`save:${profile.origin}`),
  });
  const before = coordinator.captureGeneration();

  const after = await coordinator.switchServer({
    origin: 'https://control.example.test',
    displayName: '测试主机',
  });

  assert.equal(after, before + 1);
  assert.equal(coordinator.captureGeneration(), after);
  assert.deepEqual(calls, [
    'close-events',
    'clear-session',
    'clear-stores',
    'save:https://control.example.test',
  ]);
});

test('切主机后的迟到请求和旧 SSE 事件不能写入新主机状态', async () => {
  const coordinator = new ClientConnectionCoordinator();
  const staleGeneration = coordinator.captureGeneration();
  let applied = 0;

  await coordinator.switchServer({ origin: 'https://new.example.test', displayName: '新主机' });

  assert.equal(coordinator.applyIfCurrent(staleGeneration, () => { applied += 1; }), false);
  assert.equal(coordinator.applyEventIfCurrent(staleGeneration, () => { applied += 1; }), false);
  assert.equal(applied, 0);
  assert.equal(coordinator.applyIfCurrent(coordinator.captureGeneration(), () => { applied += 1; }), true);
  assert.equal(applied, 1);
});

test('SSE 断线只安排一次重连，并在重建单一连接前拉取全量快照', async () => {
  const order = [];
  const scheduled = [];
  const coordinator = new ClientConnectionCoordinator({
    scheduleReconnect: (callback) => {
      scheduled.push(callback);
      return scheduled.length;
    },
    refreshSnapshot: async () => order.push('snapshot'),
    openEvents: () => order.push('open-events'),
  });
  coordinator.markConnected();

  coordinator.handleEventError();
  coordinator.handleEventError();

  assert.equal(scheduled.length, 1, '多个 error 不得建立并行重连定时器');
  assert.equal(coordinator.status, 'reconnecting');
  await scheduled[0]();
  assert.deepEqual(order, ['snapshot', 'open-events']);
});

test('离线控制立即拒绝且不缓存待联网重放', async () => {
  const coordinator = new ClientConnectionCoordinator();
  let invocations = 0;

  await assert.rejects(
    coordinator.executeCommand(async () => { invocations += 1; }),
    OfflineCommandError,
  );
  assert.equal(invocations, 0);

  coordinator.markConnected();
  await coordinator.executeCommand(async () => { invocations += 1; });
  assert.equal(invocations, 1);

  coordinator.markDisconnected();
  coordinator.markConnected();
  assert.equal(invocations, 1, '恢复连接不能重放离线期间拒绝的操作');
});
