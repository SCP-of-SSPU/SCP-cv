import { createWebHashHistory, createWebHistory, type RouterHistory } from 'vue-router';

export type ClientBuildTarget = 'web' | 'app';
export type ClientPlatform = 'web' | 'electron' | 'android';
export type ClientLifecycleState = 'active' | 'inactive';
export type ClientHistoryKind = 'history' | 'hash';
export type BackAction = 'dismiss-layer' | 'router-back' | 'exit-client';

export interface PlatformFile {
  readonly name: string;
  readonly mimeType: string;
  readonly size: number;
  readonly data: Blob;
}

export interface SaveFileRequest {
  readonly suggestedName: string;
  readonly mimeType: string;
  readonly data: Blob;
}

/**
 * 原生壳能力的最小共享边界。业务页面只能依赖此接口，不直接访问 Electron、
 * Capacitor、Node.js 或 Android API。具体实现会在对应平台任务中接入。
 */
export interface PlatformAdapter {
  readonly platform: ClientPlatform;
  readonly isPackaged: boolean;
  onBackRequested(handler: () => boolean | Promise<boolean>): () => void;
  onLifecycleChanged(handler: (state: ClientLifecycleState) => void): () => void;
  pickFile(accept?: readonly string[]): Promise<PlatformFile | null>;
  saveFile(request: SaveFileRequest): Promise<boolean>;
  clearSession(): Promise<void>;
}

export function getClientBuildTarget(mode = import.meta.env.MODE): ClientBuildTarget {
  return mode === 'app' ? 'app' : 'web';
}

export function getClientHistoryKind(target: ClientBuildTarget): ClientHistoryKind {
  return target === 'app' ? 'hash' : 'history';
}

export function resolveBackAction(input: {
  readonly hasDismissibleLayer: boolean;
  readonly canGoBack: boolean;
}): BackAction {
  if (input.hasDismissibleLayer) return 'dismiss-layer';
  return input.canGoBack ? 'router-back' : 'exit-client';
}

/** Web 使用 history 与服务器 fallback；本地 Electron/Capacitor 资源使用 hash。 */
export function createClientHistory(
  target: ClientBuildTarget = getClientBuildTarget(),
): RouterHistory {
  return getClientHistoryKind(target) === 'hash' ? createWebHashHistory() : createWebHistory();
}
