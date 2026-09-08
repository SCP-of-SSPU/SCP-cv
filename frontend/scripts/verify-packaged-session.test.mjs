import assert from 'node:assert/strict';
import test from 'node:test';

import { resolvePackagedEndpoint, verifyPackagedSession } from './verify-packaged-session.mjs';

test('打包会话探针为 fetch 和 EventSource 使用同一 HTTPS origin 与 cookie jar', async () => {
  const requests = [];
  const fetchImpl = async (url, options = {}) => {
    requests.push({ url, options });
    const path = new URL(url).pathname;
    const payload = path.endsWith('/csrf/')
      ? { csrfToken: 'csrf-probe' }
      : path.endsWith('/me/')
        ? { user: { username: 'probe' } }
        : { detail: 'ok' };
    return { ok: true, status: 200, json: async () => payload };
  };
  let eventSourceCall;
  const eventSourceFactory = (url, options) => {
    eventSourceCall = { url, options };
    const source = { close() {} };
    queueMicrotask(() => source.onmessage?.({ type: 'playback_state', data: '{}' }));
    return source;
  };

  const result = await verifyPackagedSession({
    baseUrl: 'https://control.example.test/base/',
    username: 'probe',
    password: 'not-logged',
    fetchImpl,
    eventSourceFactory,
  });

  assert.equal(requests.length, 4);
  assert.ok(requests.every((request) => request.options.credentials === 'include'));
  assert.equal(requests[1].options.headers['X-CSRFToken'], 'csrf-probe');
  assert.equal(requests[3].options.headers['X-CSRFToken'], 'csrf-probe');
  assert.equal(new URL(eventSourceCall.url).origin, 'https://control.example.test');
  assert.equal(eventSourceCall.options.withCredentials, true);
  assert.equal(result.authenticatedUser, 'probe');
  assert.equal(result.eventType, 'playback_state');
});

test('服务器地址拒绝凭据 URL 和非本机明文 HTTP', () => {
  assert.throws(() => resolvePackagedEndpoint('https://user:pass@example.test', '/api/auth/me/'));
  assert.throws(() => resolvePackagedEndpoint('http://control.example.test', '/api/auth/me/'));
  assert.equal(
    resolvePackagedEndpoint('http://127.0.0.1:18000', '/api/auth/me/', { allowInsecureDevelopment: true }),
    'http://127.0.0.1:18000/api/auth/me/',
  );
});
