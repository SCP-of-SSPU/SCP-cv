/*
 * 播放会话 Store：每个窗口（1-4）的源、状态、音量、循环。
 * 与 SSE 推送强联动：runtime.connectEvents 会调用 applyRemoteSessions 把
 * 服务端推送的最新快照写入本 store，所有 UI 直接订阅。
 */
import { defineStore } from 'pinia';

import { api, type SessionSnapshot } from '@/services/api';

interface SessionState {
  /** 后端返回的四个窗口会话；首次启动前为空数组。 */
  sessions: SessionSnapshot[];
}

export const useSessionStore = defineStore('sessions', {
  state: (): SessionState => ({
    sessions: [],
  }),
  getters: {
    /** 按 window_id 提供 O(1) 查询。 */
    byWindowId(state): (windowId: number) => SessionSnapshot | undefined {
      const cache = new Map<number, SessionSnapshot>();
      state.sessions.forEach((session) => cache.set(session.window_id, session));
      return (windowId: number) => cache.get(windowId);
    },
    /** 用于 NavPane / 移动端 SegmentedControl 等场景的窗口选择列表。 */
    windowIds(state): number[] {
      return state.sessions.map((session) => session.window_id).sort((a, b) => a - b);
    },
  },
  actions: {
    /** 拉取最新四窗口快照，常用于初始化和兜底重试。 */
    async refresh(): Promise<void> {
      const payload = await api.listSessions();
      this.applyRemoteSessions(payload.sessions);
    },
    /** SSE 推送或 REST 返回时统一入口。 */
    applyRemoteSessions(sessions: SessionSnapshot[]): void {
      this.sessions = sessions;
    },
    async openSource(windowId: number, sourceId: number, autoplay = true): Promise<void> {
      const payload = await api.openSource(windowId, sourceId, autoplay);
      this.applyRemoteSessions(payload.sessions);
    },
    async closeSource(windowId: number): Promise<void> {
      const payload = await api.closeSource(windowId);
      this.applyRemoteSessions(payload.sessions);
    },
    async control(windowId: number, action: string): Promise<void> {
      const payload = await api.controlPlayback(windowId, action);
      this.applyRemoteSessions(payload.sessions);
    },
    async navigate(windowId: number, action: string, targetIndex = 0, positionMs = 0): Promise<void> {
      const payload = await api.navigateContent(windowId, action, targetIndex, positionMs);
      this.applyRemoteSessions(payload.sessions);
    },
    async controlPptMedia(windowId: number, action: string, mediaId: string, mediaIndex: number): Promise<void> {
      const payload = await api.controlPptMedia(windowId, action, mediaId, mediaIndex);
      this.applyRemoteSessions(payload.sessions);
    },
    async setLoop(windowId: number, enabled: boolean): Promise<void> {
      const payload = await api.setLoop(windowId, enabled);
      this.applyRemoteSessions(payload.sessions);
    },
    async setWindowVolume(windowId: number, volume: number): Promise<void> {
      const payload = await api.setWindowVolume(windowId, volume);
      this.applyRemoteSessions(payload.sessions);
    },
    async setWindowMute(windowId: number, muted: boolean): Promise<void> {
      const payload = await api.setWindowMute(windowId, muted);
      this.applyRemoteSessions(payload.sessions);
    },
    async resetAll(): Promise<void> {
      const payload = await api.resetAllSessions();
      this.applyRemoteSessions(payload.sessions);
    },
    async showWindowIds(): Promise<void> {
      const payload = await api.showWindowIds();
      this.applyRemoteSessions(payload.sessions);
    },
    async shutdownSystem(): Promise<{ detail?: string }> {
      const payload = await api.shutdownSystem();
      this.applyRemoteSessions(payload.sessions);
      return { detail: payload.detail };
    },
  },
});
