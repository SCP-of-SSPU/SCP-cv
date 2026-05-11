/*
 * 预案 Store：列表、置顶、激活、新建/编辑/删除。
 * 设计稿 §4.5：列表 + 预览 Drawer + 编辑覆盖大卡共用。
 */
import { defineStore } from 'pinia';

import { api, type ScenarioItem, type ScenarioPayload } from '@/services/api';

import { useSessionStore } from './sessions';

interface ScenarioState {
  scenarios: ScenarioItem[];
}

export const useScenarioStore = defineStore('scenarios', {
  state: (): ScenarioState => ({
    scenarios: [],
  }),
  getters: {
    /** 置顶预案排在前；置顶组内以后置顶的更靠前。 */
    sorted(state): ScenarioItem[] {
      const list = [...state.scenarios];
      list.sort((a, b) => {
        const aPinned = a.sort_order > 0 ? 0 : 1;
        const bPinned = b.sort_order > 0 ? 0 : 1;
        if (aPinned !== bPinned) return aPinned - bPinned;
        if (aPinned === 0) return b.sort_order - a.sort_order || a.name.localeCompare(b.name, 'zh-Hans-CN');
        return a.name.localeCompare(b.name, 'zh-Hans-CN');
      });
      return list;
    },
  },
  actions: {
    async refresh(): Promise<void> {
      const payload = await api.listScenarios();
      this.scenarios = payload.scenarios;
    },
    async create(payload: ScenarioPayload): Promise<ScenarioItem> {
      const result = await api.createScenario(payload);
      this.scenarios = [result.scenario, ...this.scenarios];
      return result.scenario;
    },
    async update(scenarioId: number, payload: ScenarioPayload): Promise<ScenarioItem> {
      const result = await api.updateScenario(scenarioId, payload);
      this.scenarios = this.scenarios.map((item) => (item.id === scenarioId ? result.scenario : item));
      return result.scenario;
    },
    async remove(scenarioId: number): Promise<void> {
      await api.deleteScenario(scenarioId);
      this.scenarios = this.scenarios.filter((item) => item.id !== scenarioId);
    },
    async pin(scenarioId: number): Promise<ScenarioItem> {
      const result = await api.pinScenario(scenarioId);
      this.scenarios = this.scenarios.map((item) => (item.id === scenarioId ? result.scenario : item));
      return result.scenario;
    },
    async activate(scenarioId: number): Promise<void> {
      const payload = await api.activateScenario(scenarioId);
      // activate 会把当前播放快照写入 sessions，由 SessionStore 统一持有。
      useSessionStore().applyRemoteSessions(payload.sessions);
    },
  },
});
