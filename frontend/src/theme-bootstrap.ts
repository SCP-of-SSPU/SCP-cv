try {
  const stored = window.localStorage.getItem('scp-cv-theme');
  const mode = stored === 'light' || stored === 'dark' ? stored : 'system';
  if (mode !== 'system') document.documentElement.setAttribute('data-theme', mode);
} catch {
  // 隐私模式或 localStorage 不可用时由 prefers-color-scheme 接管。
}
