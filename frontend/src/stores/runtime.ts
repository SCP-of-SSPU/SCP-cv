/*
 * Runtime / 大屏模式 / 系统音量 / SSE 连接状态。
 *
 * 设计稿 §3 + §4.1：TitleBar 与仪表盘需要长时可见这些信息。
 * 拆出本 store 让多个布局层共享同一份状态，避免轮询接口。
 */
import { defineStore } from 'pinia';

import { api, type RuntimeSnapshot, type SessionSnapshot, buildBackendUrl } from '@/services/api';
import { useSessionStore } from './sessions';

interface SystemVolumeState {
  level: number;
  muted: boolean;
  systemSynced: boolean;
  backend: string;
}

interface RuntimeState {
  /** 后端运行态：单/双屏 + 静音窗口列表。 */
  runtime: RuntimeSnapshot | null;
  /** 系统音量。 */
  systemVolume: SystemVolumeState;
  /** SSE 连接状态：connecting / connected / reconnecting / closed。 */
  sseStatus: 'connecting' | 'connected' | 'reconnecting' | 'closed';
  /** SSE 上次更新时间（用于诊断展示）。 */
  sseLastUpdate: number;
  /** 内部 EventSource 引用，避免重复建连。 */
  _eventSource: EventSource | null;
  _reconnectTimer: number | null;
}

const SSE_RECONNECT_INTERVAL_MS = 2000;

export const useRuntimeStore = defineStore('runtime', {
  state: (): RuntimeState => ({
    runtime: null,
    systemVolume: {
      level: 100,
      muted: false,
      systemSynced: false,
      backend: 'runtime_state',
    },
    sseStatus: 'closed',
    sseLastUpdate: 0,
    _eventSource: null,
    _reconnectTimer: null,
  }),
  getters: {
    /** 当前是否处于双屏模式；仪表盘、Nav、预案预览均会用到。 */
    isDoubleScreen: (state): boolean => state.runtime?.big_screen_mode === 'double',
    /** 大屏模式中文标签。 */
    bigScreenLabel: (state): string => (state.runtime?.big_screen_mode === 'double' ? '双屏' : '单屏'),
  },
  actions: {
    /** 拉取最新 runtime 快照。 */
    async refresh(): Promise<void> {
      const payload = await api.getRuntime();
      this.runtime = payload.runtime;
    },
    /** 拉取系统音量。 */
    async refreshSystemVolume(): Promise<void> {
      const payload = await api.getSystemVolume();
      this.applyVolume(payload.volume);
    },
    applyVolume(volume: { level: number; muted: boolean; system_synced: boolean; backend: string }): void {
      this.systemVolume = {
        level: volume.level,
        muted: volume.muted,
        systemSynced: volume.system_synced,
        backend: volume.backend,
      };
    },
    /** 切换大屏模式：会同步刷新 sessions（后端 PATCH 返回最新会话快照）。 */
    async setBigScreenMode(mode: 'single' | 'double'): Promise<void> {
      const payload = await api.setRuntimeMode(mode);
      this.runtime = payload.runtime;
      useSessionStore().applyRemoteSessions(payload.sessions);
    },
    /** 设置系统音量；后端可能返回未同步标记（无 Windows Core Audio 时）。 */
    async setSystemVolume(level: number, muted?: boolean): Promise<void> {
      const payload = await api.setSystemVolume(level, muted);
      this.applyVolume(payload.volume);
    },
    /**
     * 建立 SSE 长连接：监听 `playback_state` 事件，刷新会话快照。
     * 自动重连：连接关闭后 2 s 重试一次，期间 sseStatus = 'reconnecting'。
     */
    connectEvents(): void {
      this.disconnectEvents();
      this.sseStatus = 'connecting';
      const source = new EventSource(buildBackendUrl('/api/events/'));
      this._eventSource = source;

      source.onopen = (): void => {
        this.sseStatus = 'connected';
        this.sseLastUpdate = Date.now();
      };

      source.onerror = (): void => {
        this.sseStatus = 'reconnecting';
        // 服务器异常时按 fallback 抓一次 sessions，避免页面状态长时间漂移。
        void useSessionStore().refresh().catch(() => undefined);
        if (source.readyState === EventSource.CLOSED && this._reconnectTimer === null) {
          this._reconnectTimer = window.setTimeout(() => {
            this._reconnectTimer = null;
            this.connectEvents();
          }, SSE_RECONNECT_INTERVAL_MS);
        }
      };

      source.addEventListener('playback_state', (event: MessageEvent): void => {
        try {
          const payload = JSON.parse(event.data) as { sessions?: SessionSnapshot[] };
          if (Array.isArray(payload.sessions)) {
            useSessionStore().applyRemoteSessions(payload.sessions);
          }
          this.sseLastUpdate = Date.now();
        } catch {
          // 解析失败时不影响连接；调用方页面会通过 `refresh` 兜底。
        }
      });
    },
    /** 主动断开并清理定时器。 */
    disconnectEvents(): void {
      if (this._eventSource) {
        this._eventSource.close();
        this._eventSource = null;
      }
      if (this._reconnectTimer !== null) {
        window.clearTimeout(this._reconnectTimer);
        this._reconnectTimer = null;
      }
      this.sseStatus = 'closed';
    },
  },
});
