/*
 * 显示器目标 Store：列出可用显示器、为指定窗口选择显示器。
 * 设计稿 §4.6：设置 Tab「显示器」承载该交互。
 */
import { defineStore } from 'pinia';

import { api, type DisplayTargetItem, type SessionSnapshot } from '@/services/api';

import { useSessionStore } from './sessions';

interface DisplayState {
  targets: DisplayTargetItem[];
}

export const useDisplayStore = defineStore('displays', {
  state: (): DisplayState => ({
    targets: [],
  }),
  actions: {
    async refresh(): Promise<void> {
      const payload = await api.listDisplays();
      this.targets = payload.targets;
    },
    /**
     * 应用显示器配置到指定窗口。
     * @param windowId 目标窗口 1-4
     * @param displayMode 后端 PlaybackMode 字段（single）
     * @param targetLabel 显示器名称
     */
    async applyToWindow(
      windowId: number,
      displayMode: string,
      targetLabel: string,
    ): Promise<SessionSnapshot[]> {
      const payload = await api.selectDisplay({
        window_id: windowId,
        display_mode: displayMode,
        target_label: targetLabel,
      });
      useSessionStore().applyRemoteSessions(payload.sessions);
      return payload.sessions;
    },
  },
});
