/** 登录后缓存的 token 优先于 document.cookie，兼容 Electron 的安全 Cookie。 */
export function resolveCsrfToken(cachedToken: string, cookieToken: string): string {
  return cachedToken || cookieToken;
}
