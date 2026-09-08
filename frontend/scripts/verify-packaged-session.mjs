const DEFAULT_TIMEOUT_MS = 5_000;

export function resolvePackagedEndpoint(baseUrl, path, { allowInsecureDevelopment = false } = {}) {
  const base = new URL(baseUrl);
  const isLoopback = ['127.0.0.1', 'localhost', '[::1]'].includes(base.hostname);
  if (base.protocol !== 'https:' && !(allowInsecureDevelopment && base.protocol === 'http:' && isLoopback)) {
    throw new Error('打包客户端只允许受信 HTTPS；仅显式开发探针可连接本机 HTTP。');
  }
  if (base.username || base.password) {
    throw new Error('服务器地址不得包含用户名或密码。');
  }

  return new URL(path.replace(/^\/+/, ''), `${base.href.replace(/\/+$/, '')}/`).href;
}

export async function verifyPackagedSession({
  baseUrl,
  username,
  password,
  fetchImpl = globalThis.fetch,
  eventSourceFactory = (url, options) => new EventSource(url, options),
  allowInsecureDevelopment = false,
  timeoutMs = DEFAULT_TIMEOUT_MS,
}) {
  if (typeof fetchImpl !== 'function') throw new Error('当前 renderer 没有可用的 fetch。');
  const endpoint = (path) => resolvePackagedEndpoint(baseUrl, path, { allowInsecureDevelopment });
  const csrfResponse = await fetchImpl(endpoint('/api/auth/csrf/'), { credentials: 'include' });
  const csrf = await readJson(csrfResponse, 'csrf');
  if (typeof csrf.csrfToken !== 'string' || !csrf.csrfToken) throw new Error('CSRF 响应缺少 csrfToken。');

  const unsafeHeaders = { 'Content-Type': 'application/json', 'X-CSRFToken': csrf.csrfToken };
  const loginResponse = await fetchImpl(endpoint('/api/auth/login/'), {
    method: 'POST',
    credentials: 'include',
    headers: unsafeHeaders,
    body: JSON.stringify({ username, password }),
  });
  await readJson(loginResponse, 'login');

  const meResponse = await fetchImpl(endpoint('/api/auth/me/'), { credentials: 'include' });
  const me = await readJson(meResponse, 'me');
  const event = await receiveAuthenticatedEvent(
    eventSourceFactory,
    endpoint('/api/events/'),
    timeoutMs,
  );

  const logoutResponse = await fetchImpl(endpoint('/api/auth/logout/'), {
    method: 'POST',
    credentials: 'include',
    headers: { 'X-CSRFToken': csrf.csrfToken },
  });
  await readJson(logoutResponse, 'logout');

  return {
    authenticatedUser: me.user?.username ?? '',
    eventType: event.type,
    sharedOrigin: new URL(baseUrl).origin,
    credentialsMode: 'include',
  };
}

async function readJson(response, stage) {
  if (!response?.ok) throw new Error(`${stage} 请求失败：HTTP ${response?.status ?? 'unknown'}`);
  return response.json();
}

function receiveAuthenticatedEvent(factory, url, timeoutMs) {
  return new Promise((resolve, reject) => {
    const source = factory(url, { withCredentials: true });
    const timeout = setTimeout(() => {
      source.close();
      reject(new Error(`SSE 探针在 ${timeoutMs}ms 内未收到事件。`));
    }, timeoutMs);
    const finish = (callback) => (event) => {
      clearTimeout(timeout);
      source.close();
      callback(event);
    };
    source.onmessage = finish((event) => resolve({ type: event.type || 'message', data: event.data }));
    source.onerror = finish(() => reject(new Error('SSE 探针连接失败。')));
  });
}
