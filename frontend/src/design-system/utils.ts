/*
 * 设计系统通用辅助函数。
 * 仅放纯逻辑工具（class 拼接、id 生成、防抖）；任何视觉值必须来自 token，不在此处硬编码。
 */

/**
 * 拼接 className，过滤 falsy 项。
 * @param classNames 任意数量的 class 片段；undefined / false / null / '' 会被忽略
 * @return 去重后的 class 字符串
 */
export function cls(...classNames: Array<string | false | null | undefined>): string {
  const seen = new Set<string>();
  for (const item of classNames) {
    if (!item) continue;
    for (const token of item.split(/\s+/)) {
      if (token) seen.add(token);
    }
  }
  return Array.from(seen).join(' ');
}

let nextLocalId = 1;
/**
 * 生成稳定的本地 id，用于 aria-controls / aria-describedby 等关联属性。
 * @param prefix 前缀，便于调试时识别用途
 * @return 形如 `${prefix}-${n}` 的字符串
 */
export function useLocalId(prefix: string): string {
  return `${prefix}-${nextLocalId++}`;
}

/**
 * 简单防抖：返回新函数，延时段内重复调用会刷新计时器。
 * @param fn 原函数
 * @param waitMs 延时毫秒
 * @return 防抖包装后的函数
 */
export function debounce<TArgs extends unknown[]>(
  fn: (...args: TArgs) => void,
  waitMs: number,
): (...args: TArgs) => void {
  let timer: number | null = null;
  return (...args: TArgs) => {
    if (timer !== null) window.clearTimeout(timer);
    timer = window.setTimeout(() => {
      timer = null;
      fn(...args);
    }, waitMs);
  };
}

/**
 * 简单节流：在 leading 边缘立即触发，trailing 也保留一次最后状态。
 * @param fn 原函数
 * @param intervalMs 触发间隔
 * @return 节流包装后的函数
 */
export function throttle<TArgs extends unknown[]>(
  fn: (...args: TArgs) => void,
  intervalMs: number,
): (...args: TArgs) => void {
  let lastInvoke = 0;
  let trailingTimer: number | null = null;
  let trailingArgs: TArgs | null = null;
  return (...args: TArgs) => {
    const now = Date.now();
    const remain = intervalMs - (now - lastInvoke);
    trailingArgs = args;
    if (remain <= 0) {
      lastInvoke = now;
      trailingArgs = null;
      fn(...args);
    } else if (trailingTimer === null) {
      trailingTimer = window.setTimeout(() => {
        lastInvoke = Date.now();
        trailingTimer = null;
        if (trailingArgs) fn(...trailingArgs);
      }, remain);
    }
  };
}

/**
 * 格式化时长（毫秒 → mm:ss / hh:mm:ss）。
 * @param milliseconds 时长，单位 ms
 * @return 文本，最少两段（mm:ss）；超过 1 小时显示 hh:mm:ss
 */
export function formatDuration(milliseconds: number): string {
  const totalSeconds = Math.max(0, Math.floor(milliseconds / 1000));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const pad = (n: number): string => String(n).padStart(2, '0');
  if (hours > 0) return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
  return `${pad(minutes)}:${pad(seconds)}`;
}

/**
 * 把字节数格式化为人类可读字符串。
 * @param bytes 字节数
 * @return 例如 "1.4 MB"；0 / 缺省返回 "0 B"
 */
export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const unitIndex = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    units.length - 1,
  );
  const value = bytes / 1024 ** unitIndex;
  return `${value.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

/**
 * 把 ISO 时间转为相对时间（仅本地化中文）。
 * @param isoText ISO 时间字符串；空值返回 ""
 * @return 形如「刚刚」「3 分钟前」「2 天前」「2026-04-21 13:42」
 */
export function formatRelativeTime(isoText: string): string {
  if (!isoText) return '';
  const targetMs = Date.parse(isoText);
  if (Number.isNaN(targetMs)) return isoText;
  const diffSec = (Date.now() - targetMs) / 1000;
  if (diffSec < 30) return '刚刚';
  if (diffSec < 60 * 60) return `${Math.floor(diffSec / 60)} 分钟前`;
  if (diffSec < 60 * 60 * 24) return `${Math.floor(diffSec / 3600)} 小时前`;
  if (diffSec < 60 * 60 * 24 * 7) return `${Math.floor(diffSec / 86400)} 天前`;
  const date = new Date(targetMs);
  const pad = (n: number): string => String(n).padStart(2, '0');
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ` +
    `${pad(date.getHours())}:${pad(date.getMinutes())}`
  );
}
