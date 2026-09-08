export type ClientConnectionStatus =
  | 'disconnected'
  | 'connecting'
  | 'unauthenticated'
  | 'connected'
  | 'stale'
  | 'reconnecting'
  | 'error';

export interface ServerProfile {
  readonly origin: string;
  readonly displayName: string;
  readonly allowInsecureDevelopment?: boolean;
}

export const SERVER_PROFILE_STORAGE_KEY = 'scp-cv.server-profile';

export function loadStoredServerProfile(
  storage: Pick<Storage, 'getItem'> = window.localStorage,
): ServerProfile | null {
  const raw = storage.getItem(SERVER_PROFILE_STORAGE_KEY);
  if (!raw) return null;
  try {
    return normalizeServerProfile(JSON.parse(raw) as ServerProfile);
  } catch {
    return null;
  }
}

export function saveServerProfile(
  profile: ServerProfile,
  storage: Pick<Storage, 'setItem'> = window.localStorage,
): void {
  storage.setItem(SERVER_PROFILE_STORAGE_KEY, JSON.stringify(normalizeServerProfile(profile)));
}

export interface ConnectionCoordinatorDependencies {
  closeEvents?(): void;
  clearSession?(): Promise<void>;
  clearStores?(): void;
  saveProfile?(profile: ServerProfile): Promise<void>;
  refreshSnapshot?(): Promise<void>;
  openEvents?(): void;
  scheduleReconnect?(callback: () => void | Promise<void>): unknown;
}

export class OfflineCommandError extends Error {
  constructor() {
    super('控制端当前离线，操作未发送且不会自动重放。');
    this.name = 'OfflineCommandError';
  }
}

export class StaleConnectionResponseError extends Error {
  constructor() {
    super('响应属于已切换的播放主机，已丢弃。');
    this.name = 'StaleConnectionResponseError';
  }
}

export function normalizeServerProfile(profile: ServerProfile): ServerProfile {
  const rawOrigin = profile.origin.trim();
  const url = new URL(rawOrigin);
  const isLoopback = ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname);
  const allowHttp = Boolean(profile.allowInsecureDevelopment && isLoopback);
  if (url.protocol !== 'https:' && !(url.protocol === 'http:' && allowHttp)) {
    throw new Error('播放主机必须使用受信 HTTPS；仅显式开发模式允许本机 HTTP。');
  }
  if (url.username || url.password) {
    throw new Error('播放主机地址不得包含用户名或密码。');
  }
  if ((url.pathname && url.pathname !== '/') || url.search || url.hash) {
    throw new Error('播放主机地址只能包含 scheme、host 和 port。');
  }
  return {
    origin: url.origin,
    displayName: profile.displayName.trim() || url.host,
    allowInsecureDevelopment: allowHttp,
  };
}

export class ClientConnectionCoordinator {
  private generation = 0;
  private reconnectScheduled = false;
  private dependencies: ConnectionCoordinatorDependencies;
  private currentProfile: ServerProfile | null = null;

  status: ClientConnectionStatus = 'disconnected';

  constructor(dependencies: ConnectionCoordinatorDependencies = {}) {
    this.dependencies = dependencies;
  }

  get profile(): ServerProfile | null {
    return this.currentProfile;
  }

  captureGeneration(): number {
    return this.generation;
  }

  restoreProfile(profile: ServerProfile): number {
    this.currentProfile = normalizeServerProfile(profile);
    this.generation += 1;
    this.status = 'disconnected';
    return this.generation;
  }

  async switchServer(
    profile: ServerProfile,
    dependencies: ConnectionCoordinatorDependencies = this.dependencies,
  ): Promise<number> {
    const normalized = normalizeServerProfile(profile);
    this.generation += 1;
    this.status = 'disconnected';
    this.reconnectScheduled = false;
    dependencies.closeEvents?.();
    await dependencies.clearSession?.();
    dependencies.clearStores?.();
    this.currentProfile = normalized;
    await dependencies.saveProfile?.(normalized);
    return this.generation;
  }

  applyIfCurrent(generation: number, apply: () => void): boolean {
    if (generation !== this.generation) return false;
    apply();
    return true;
  }

  applyEventIfCurrent(generation: number, apply: () => void): boolean {
    return this.applyIfCurrent(generation, apply);
  }

  markConnecting(): void {
    this.status = 'connecting';
  }

  markConnected(): void {
    this.status = 'connected';
    this.reconnectScheduled = false;
  }

  markDisconnected(): void {
    this.status = 'disconnected';
    this.reconnectScheduled = false;
  }

  markReconnecting(): void {
    this.status = 'reconnecting';
  }

  handleEventError(): void {
    this.status = 'reconnecting';
    if (this.reconnectScheduled) return;
    this.reconnectScheduled = true;
    const generation = this.captureGeneration();
    const reconnect = async (): Promise<void> => {
      this.reconnectScheduled = false;
      if (generation !== this.generation) return;
      try {
        await this.dependencies.refreshSnapshot?.();
        if (generation !== this.generation) return;
        this.dependencies.openEvents?.();
      } catch {
        if (generation === this.generation) this.status = 'error';
      }
    };
    if (this.dependencies.scheduleReconnect) {
      this.dependencies.scheduleReconnect(reconnect);
    } else {
      window.setTimeout(() => void reconnect(), 2000);
    }
  }

  async executeCommand<T>(command: () => Promise<T>): Promise<T> {
    if (this.status !== 'connected') throw new OfflineCommandError();
    return command();
  }
}

export const clientConnection = new ClientConnectionCoordinator();
