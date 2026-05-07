/*
 * 预案表单状态模型：
 *   - 列表 / 预览 / 编辑覆盖大卡片共享同一组数据结构；
 *   - 三态 source_state（unset 保持 / empty 黑屏 / set 切换）严格对应后端字段。
 */
import type { ScenarioItem, ScenarioPayload } from '@/services/api';

export type ScenarioWindowMode = 'unset' | 'empty' | 'set';

export interface ScenarioWindowDraft {
  windowId: number;
  sourceState: ScenarioWindowMode;
  sourceId: number | null;
  autoplay: boolean;
  resume: boolean;
}

export interface ScenarioDraft {
  /** 编辑时 id 不为 null。 */
  id: number | null;
  name: string;
  description: string;
  bigScreenModeState: ScenarioWindowMode;
  bigScreenMode: 'single' | 'double';
  volumeState: ScenarioWindowMode;
  volumeLevel: number;
  windows: ScenarioWindowDraft[];
}

const DEFAULT_WINDOWS: ScenarioWindowDraft[] = [1, 2, 3, 4].map((windowId) => ({
  windowId,
  sourceState: 'unset',
  sourceId: null,
  autoplay: false,
  resume: false,
}));

/**
 * 创建一份「全部保持」的空白草稿：常用于新建预案。
 * @return ScenarioDraft 全字段初始值
 */
export function createEmptyDraft(): ScenarioDraft {
  return {
    id: null,
    name: '',
    description: '',
    bigScreenModeState: 'unset',
    bigScreenMode: 'single',
    volumeState: 'unset',
    volumeLevel: 100,
    windows: DEFAULT_WINDOWS.map((win) => ({ ...win })),
  };
}

/**
 * 把后端 ScenarioItem 反序列化为编辑草稿。
 * @param item 后端列表项或详情
 * @return ScenarioDraft
 */
export function fromScenarioItem(item: ScenarioItem): ScenarioDraft {
  const targets = new Map<number, ScenarioWindowDraft>();
  for (const target of item.targets) {
    targets.set(target.window_id, {
      windowId: target.window_id,
      sourceState: target.source_state,
      sourceId: target.source_id,
      autoplay: target.autoplay,
      resume: target.resume,
    });
  }
  return {
    id: item.id,
    name: item.name,
    description: item.description ?? '',
    bigScreenModeState: item.big_screen_mode_state,
    bigScreenMode: item.big_screen_mode,
    volumeState: item.volume_state,
    volumeLevel: item.volume_level,
    windows: [1, 2, 3, 4].map((windowId) => targets.get(windowId) ?? {
      windowId,
      sourceState: 'unset',
      sourceId: null,
      autoplay: false,
      resume: false,
    }),
  };
}

/**
 * 把草稿序列化为后端 PATCH/POST 负载。
 * 设计稿 §4.5.3：从当前状态生成与新建公用同一 endpoint。
 * @param draft 编辑草稿
 * @return ScenarioPayload
 */
export function toScenarioPayload(draft: ScenarioDraft): ScenarioPayload {
  return {
    name: draft.name.trim(),
    description: draft.description.trim() || undefined,
    big_screen_mode_state: draft.bigScreenModeState,
    big_screen_mode: draft.bigScreenMode,
    volume_state: draft.volumeState,
    volume_level: draft.volumeLevel,
    targets: draft.windows.map((win) => ({
      window_id: win.windowId,
      source_state: win.sourceState,
      source_id: win.sourceState === 'set' ? win.sourceId ?? undefined : undefined,
      autoplay: win.autoplay,
      resume: win.resume,
    })),
  };
}

/**
 * 校验预案名是否合法（设计稿 §4.5.3）。
 * @param name 预案名称
 * @return 错误说明文案；通过返回空字符串
 */
export function validateName(name: string): string {
  const trimmed = name.trim();
  if (!trimmed) return '预案名称不能为空，请输入 1–32 个字符。';
  if (trimmed.length > 32) return '预案名称过长（≤ 32 字符）。';
  return '';
}
