import { defineStore } from 'pinia';

import {
  api,
  buildBackendUrl,
  type DeviceItem,
  type DisplayTargetItem,
  type MediaFolderItem,
  type MediaSourceItem,
  type RuntimeSnapshot,
  type ScenarioItem,
  type SessionSnapshot,
} from '@/services/api';

interface AppState {
  activeWindowId: number;
  selectedFolderId: number | null;
  sources: MediaSourceItem[];
  folders: MediaFolderItem[];
  sessions: SessionSnapshot[];
  runtime: RuntimeSnapshot | null;
  scenarios: ScenarioItem[];
  displays: DisplayTargetItem[];
  devices: DeviceItem[];
  systemVolumeLevel: number;
  systemMuted: boolean;
  systemVolumeBackend: string;
  connectionStatus: string;
  message: string;
  isError: boolean;
  eventSource: EventSource | null;
  eventReconnectTimer: number | null;
}

export const useAppStore = defineStore('app', {
  state: (): AppState => ({
    activeWindowId: 1,
    selectedFolderId: null,
    sources: [],
    folders: [],
    sessions: [],
    runtime: null,
    scenarios: [],
    displays: [],
    devices: [],
    systemVolumeLevel: 100,
    systemMuted: false,
    systemVolumeBackend: 'runtime_state',
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
    sourceFoldersById: (state) => new Map(state.folders.map((folder) => [folder.id, folder.name])),
    bigScreenModeLabel: (state) => (state.runtime?.big_screen_mode === 'double' ? '双屏' : '单屏'),
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
      const bootstrapTasks = await Promise.allSettled([
        this.refreshFolders(),
        this.refreshSources(),
        this.refreshSessions(),
        this.refreshRuntime(),
        this.refreshSystemVolume(),
        this.refreshScenarios(),
        this.refreshDisplays(),
        this.refreshDevices(),
      ]);
      const failedTask = bootstrapTasks.find((task) => task.status === 'rejected');
      if (failedTask && failedTask.status === 'rejected') {
        this.notify(failedTask.reason instanceof Error ? failedTask.reason.message : '部分状态加载失败', true);
      }
      this.connectEvents();
    },
    async refreshFolders(): Promise<void> {
      const payload = await api.listFolders();
      this.folders = payload.folders;
    },
    async refreshSources(): Promise<void> {
      const payload = await api.listSources('', this.selectedFolderId);
      this.sources = payload.sources;
    },
    async refreshSessions(): Promise<void> {
      const payload = await api.listSessions();
      this.applySessions(payload.sessions);
    },
    async refreshRuntime(): Promise<void> {
      const payload = await api.getRuntime();
      this.runtime = payload.runtime;
    },
    async refreshSystemVolume(): Promise<void> {
      const payload = await api.getSystemVolume();
      this.systemVolumeLevel = payload.volume.level;
      this.systemMuted = payload.volume.muted;
      this.systemVolumeBackend = payload.volume.backend;
    },
    async refreshScenarios(): Promise<void> {
      const payload = await api.listScenarios();
      this.scenarios = payload.scenarios;
    },
    async refreshDisplays(): Promise<void> {
      const payload = await api.listDisplays();
      this.displays = payload.targets;
    },
    async refreshDevices(): Promise<void> {
      const payload = await api.listDevices();
      this.devices = payload.devices;
    },
    async selectFolder(folderId: number | null): Promise<void> {
      this.selectedFolderId = folderId;
      await this.refreshSources();
    },
    connectEvents(): void {
      if (this.eventSource) this.eventSource.close();
      if (this.eventReconnectTimer !== null) {
        window.clearTimeout(this.eventReconnectTimer);
        this.eventReconnectTimer = null;
      }
      const source = new EventSource(buildBackendUrl('/api/events/'));
      this.eventSource = source;
      source.onopen = () => {
        this.connectionStatus = 'SSE: 已连接';
      };
      source.onerror = () => {
        this.connectionStatus = 'SSE: 重连中';
        void this.refreshSessions().catch(() => undefined);
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
    async resetAllSessions(): Promise<void> {
      const payload = await api.resetAllSessions();
      this.applySessions(payload.sessions);
      this.notify('已将所有窗口重置为待机');
    },
    async shutdownSystem(): Promise<void> {
      const payload = await api.shutdownSystem();
      this.applySessions(payload.sessions);
      this.connectionStatus = 'SSE: 系统关闭中';
      this.notify(payload.detail || '系统关闭请求已发送');
      if (this.eventSource) {
        this.eventSource.close();
        this.eventSource = null;
      }
    },
    async toggleLoop(): Promise<void> {
      const enabled = !(this.activeSession?.loop_enabled || false);
      const payload = await api.setLoop(this.activeWindowId, enabled);
      this.applySessions(payload.sessions);
      this.notify(enabled ? '循环播放已开启' : '循环播放已关闭');
    },
    async setWindowVolume(volume: number): Promise<void> {
      const payload = await api.setWindowVolume(this.activeWindowId, volume);
      this.applySessions(payload.sessions);
    },
    async setWindowMute(muted: boolean): Promise<void> {
      const payload = await api.setWindowMute(this.activeWindowId, muted);
      this.applySessions(payload.sessions);
    },
    async setBigScreenMode(bigScreenMode: 'single' | 'double'): Promise<void> {
      const payload = await api.setRuntimeMode(bigScreenMode);
      this.runtime = payload.runtime;
      this.applySessions(payload.sessions);
      this.notify(bigScreenMode === 'double' ? '已切换为双屏' : '已切换为单屏');
    },
    async setSystemVolume(level: number, muted?: boolean): Promise<void> {
      const payload = await api.setSystemVolume(level, muted);
      this.systemVolumeLevel = payload.volume.level;
      this.systemMuted = payload.volume.muted;
      this.systemVolumeBackend = payload.volume.backend;
      this.notify(payload.volume.system_synced ? `系统音量已设为 ${payload.volume.level}` : `音量状态已保存为 ${payload.volume.level}`);
    },
    async toggleDevice(deviceType: string): Promise<void> {
      await api.toggleDevice(deviceType);
      this.notify('电源切换指令已发送');
    },
    async powerDevice(deviceType: string, action: 'on' | 'off'): Promise<void> {
      await api.powerDevice(deviceType, action);
      this.notify(action === 'on' ? '开机指令已发送' : '关机指令已发送');
    },
    async showWindowIds(): Promise<void> {
      const payload = await api.showWindowIds();
      this.applySessions(payload.sessions);
      this.notify('已触发窗口 ID 显示');
    },
  },
});
