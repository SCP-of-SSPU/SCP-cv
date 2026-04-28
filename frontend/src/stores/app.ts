import { defineStore } from 'pinia';

import { api, type DisplayTargetItem, type MediaSourceItem, type ScenarioItem, type SessionSnapshot } from '@/services/api';

interface AppState {
  activeWindowId: number;
  sources: MediaSourceItem[];
  sessions: SessionSnapshot[];
  scenarios: ScenarioItem[];
  displays: DisplayTargetItem[];
  connectionStatus: string;
  message: string;
  isError: boolean;
  eventSource: EventSource | null;
  eventReconnectTimer: number | null;
}

export const useAppStore = defineStore('app', {
  state: (): AppState => ({
    activeWindowId: 1,
    sources: [],
    sessions: [],
    scenarios: [],
    displays: [],
    connectionStatus: 'SSE: 连接中',
    message: '',
    isError: false,
    eventSource: null,
    eventReconnectTimer: null,
  }),
  getters: {
    activeSession: (state) => (
      state.sessions.find((session) => session.window_id === state.activeWindowId) || null
    ),
    availableSources: (state) => state.sources.filter((source) => source.is_available),
  },
  actions: {
    notify(message: string, isError = false): void {
      this.message = message;
      this.isError = isError;
      if (!isError) {
        window.setTimeout(() => {
          if (this.message === message) this.message = '';
        }, 3200);
      }
    },
    applySessions(sessions: SessionSnapshot[]): void {
      this.sessions = sessions;
    },
    async bootstrap(): Promise<void> {
      await Promise.all([this.refreshSources(), this.refreshSessions(), this.refreshScenarios(), this.refreshDisplays()]);
      this.connectEvents();
    },
    async refreshSources(): Promise<void> {
      const payload = await api.listSources();
      this.sources = payload.sources;
    },
    async refreshSessions(): Promise<void> {
      const payload = await api.listSessions();
      this.applySessions(payload.sessions);
    },
    async refreshScenarios(): Promise<void> {
      const payload = await api.listScenarios();
      this.scenarios = payload.scenarios;
    },
    async refreshDisplays(): Promise<void> {
      const payload = await api.listDisplays();
      this.displays = payload.targets;
    },
    connectEvents(): void {
      if (this.eventSource) this.eventSource.close();
      if (this.eventReconnectTimer !== null) {
        window.clearTimeout(this.eventReconnectTimer);
        this.eventReconnectTimer = null;
      }
      const source = new EventSource('/api/events/');
      this.eventSource = source;
      source.onopen = () => {
        this.connectionStatus = 'SSE: 已连接';
      };
      source.onerror = () => {
        this.connectionStatus = 'SSE: 重连中';
        if (source.readyState === EventSource.CLOSED && this.eventReconnectTimer === null) {
          this.eventReconnectTimer = window.setTimeout(() => {
            this.eventReconnectTimer = null;
            this.connectEvents();
          }, 2000);
        }
      };
      source.addEventListener('playback_state', (event) => {
        try {
          const payload = JSON.parse(event.data) as { sessions?: SessionSnapshot[] };
          if (Array.isArray(payload.sessions)) this.applySessions(payload.sessions);
        } catch (error) {
          this.notify('状态推送解析失败，请刷新页面重试', true);
        }
      });
    },
    async openSource(sourceId: number): Promise<void> {
      const payload = await api.openSource(this.activeWindowId, sourceId, true);
      this.applySessions(payload.sessions);
      this.notify('已打开媒体源');
    },
    async control(action: string): Promise<void> {
      const payload = await api.controlPlayback(this.activeWindowId, action);
      this.applySessions(payload.sessions);
    },
    async navigate(action: string, targetIndex = 0, positionMs = 0): Promise<void> {
      const payload = await api.navigateContent(this.activeWindowId, action, targetIndex, positionMs);
      this.applySessions(payload.sessions);
    },
    async closeActive(): Promise<void> {
      const payload = await api.closeSource(this.activeWindowId);
      this.applySessions(payload.sessions);
      this.notify('已关闭播放');
    },
    async toggleLoop(): Promise<void> {
      const enabled = !(this.activeSession?.loop_enabled || false);
      const payload = await api.setLoop(this.activeWindowId, enabled);
      this.applySessions(payload.sessions);
      this.notify(enabled ? '循环播放已开启' : '循环播放已关闭');
    },
    async showWindowIds(): Promise<void> {
      const payload = await api.showWindowIds();
      this.applySessions(payload.sessions);
      this.notify('已触发窗口 ID 显示');
    },
  },
});
