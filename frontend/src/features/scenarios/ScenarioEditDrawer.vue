<script setup lang="ts">
/**
 * 预案编辑覆盖大卡片：新建 / 编辑 / 从当前状态生成 三种入口共用。
 *  - 桌面：480 px 右侧 Drawer（移动端自动 → 全屏 Sheet）；
 *  - 移动端可视为单页可滚动表单（设计稿 §4.5.4 中 md 断点形态）。
 *
 * 这里不使用「真覆盖式中卡」实现（与现有 Drawer 组件复用，便于响应式），
 * 视觉上等价于设计稿要求的「编辑覆盖大卡片」。
 */
import { computed, ref, watch } from 'vue';

import {
  FButton,
  FCard,
  FCombobox,
  FDrawer,
  FField,
  FInput,
  FMessageBar,
  FSegmented,
  FSlider,
  FSwitch,
  FTextarea,
} from '@/design-system';
import type { FComboboxOption, FSegmentedOption } from '@/design-system';
import { useToast } from '@/composables/useToast';
import { useScenarioStore } from '@/stores/scenarios';
import { useSourceStore } from '@/stores/sources';
import {
  createEmptyDraft,
  fromScenarioItem,
  toScenarioPayload,
  validateName,
  type ScenarioDraft,
  type ScenarioWindowDraft,
  type ScenarioWindowMode,
} from './scenarioModel';
import type { MediaSourceItem, ScenarioItem } from '@/services/api';

interface ScenarioEditDrawerProps {
  open: boolean;
  /** 入口数据来源：null（新建）、ScenarioItem（编辑）。 */
  scenario: ScenarioItem | null;
  /** 是否预填当前播放状态（「从当前状态生成」入口）。 */
  prefillFromState?: ScenarioDraft;
}

const props = withDefaults(defineProps<ScenarioEditDrawerProps>(), {
  prefillFromState: undefined,
});
const emit = defineEmits<{
  (event: 'update:open', value: boolean): void;
  (event: 'saved', scenario: ScenarioItem): void;
}>();

const sourceStore = useSourceStore();
const scenarioStore = useScenarioStore();
const toast = useToast();

const draft = ref<ScenarioDraft>(createEmptyDraft());
const errorMessage = ref('');
const saving = ref(false);

watch(
  () => [props.open, props.scenario, props.prefillFromState] as const,
  ([isOpen, scenario, prefill]) => {
    if (!isOpen) return;
    if (scenario) {
      draft.value = fromScenarioItem(scenario);
    } else if (prefill) {
      draft.value = JSON.parse(JSON.stringify(prefill));
    } else {
      draft.value = createEmptyDraft();
    }
    errorMessage.value = '';
  },
);

const sourceOptionsByCategory = computed<FComboboxOption<number>[]>(() => {
  const groups = new Map<string, MediaSourceItem[]>();
  for (const source of sourceStore.sources) {
    const cat = sourceStore.resolveCategory(source.source_type);
    const groupLabel = cat === 'ppt' ? 'PPT'
      : cat === 'video' ? '视频'
        : cat === 'image' ? '图片'
          : cat === 'web' ? '网页'
            : cat === 'stream' ? '直播' : '其它';
    if (!groups.has(groupLabel)) groups.set(groupLabel, []);
    groups.get(groupLabel)!.push(source);
  }
  const options: FComboboxOption<number>[] = [];
  for (const [groupLabel, list] of groups.entries()) {
    options.push({ label: groupLabel, value: -1, group: groupLabel });
    for (const item of list) {
      options.push({
        label: item.name || item.original_filename || item.uri || `源 ${item.id}`,
        value: item.id,
        hint: item.is_available ? undefined : '当前不可用',
      });
    }
  }
  return options;
});

const screenSegmentOptions: FSegmentedOption<ScenarioWindowMode>[] = [
  { label: '保持', value: 'unset' },
  { label: '单屏', value: 'empty' as ScenarioWindowMode },
  { label: '双屏', value: 'set' as ScenarioWindowMode },
];

const volumeSegmentOptions: FSegmentedOption<ScenarioWindowMode>[] = [
  { label: '保持', value: 'unset' },
  { label: '设置', value: 'set' },
];

const sourceSegmentOptions: FSegmentedOption<ScenarioWindowMode>[] = [
  { label: '保持', value: 'unset' },
  { label: '黑屏', value: 'empty' },
  { label: '切换', value: 'set' },
];

const visibleWindows = computed<ScenarioWindowDraft[]>(() => {
  // 顶部「大屏模式：单屏」时合并 W1/W2 为「大屏」，但实际仍写 W1。
  if (draft.value.bigScreenModeState !== 'unset' && draft.value.bigScreenMode === 'single') {
    return draft.value.windows.filter((win) => win.windowId !== 2);
  }
  return draft.value.windows;
});

function windowLabel(windowId: number): string {
  if (draft.value.bigScreenModeState !== 'unset' && draft.value.bigScreenMode === 'single' && windowId === 1) {
    return '大屏';
  }
  switch (windowId) {
    case 1:
      return '大屏左';
    case 2:
      return '大屏右';
    case 3:
      return 'TV 左';
    case 4:
      return 'TV 右';
    default:
      return `窗口 ${windowId}`;
  }
}

function isVolumeEditable(window: ScenarioWindowDraft): boolean {
  if (window.sourceState !== 'set' || !window.sourceId) return false;
  const source = sourceStore.sources.find((item) => item.id === window.sourceId);
  if (!source) return false;
  const cat = sourceStore.resolveCategory(source.source_type);
  return cat !== 'image' && cat !== 'web';
}

function showLoopToggle(window: ScenarioWindowDraft): boolean {
  if (window.sourceState !== 'set' || !window.sourceId) return false;
  const source = sourceStore.sources.find((item) => item.id === window.sourceId);
  if (!source) return false;
  const cat = sourceStore.resolveCategory(source.source_type);
  // 旧 audio 源被映射为 video 分支，因此只判断 video 即可覆盖音/视频两种情况。
  return cat === 'video';
}

function setBigScreenMode(value: ScenarioWindowMode): void {
  if (value === 'unset') {
    draft.value.bigScreenModeState = 'unset';
    return;
  }
  draft.value.bigScreenModeState = 'set';
  draft.value.bigScreenMode = value === 'empty' ? 'single' : 'double';
  // 单屏切回时 W2 自动重置为「保持」，避免下次切到双屏带遗留配置。
  if (draft.value.bigScreenMode === 'single') {
    const winTwo = draft.value.windows.find((win) => win.windowId === 2);
    if (winTwo) winTwo.sourceState = 'unset';
  }
}

const bigScreenSegmentValue = computed<ScenarioWindowMode>({
  get: (): ScenarioWindowMode => {
    if (draft.value.bigScreenModeState === 'unset') return 'unset';
    return draft.value.bigScreenMode === 'single' ? 'empty' : 'set';
  },
  set: (value: ScenarioWindowMode) => setBigScreenMode(value),
});

async function save(): Promise<void> {
  errorMessage.value = validateName(draft.value.name);
  if (errorMessage.value) return;

  for (const window of draft.value.windows) {
    if (window.sourceState === 'set' && !window.sourceId) {
      errorMessage.value = `${windowLabel(window.windowId)}：请选择「切换」时的源`;
      return;
    }
  }

  saving.value = true;
  try {
    const payload = toScenarioPayload(draft.value);
    const saved = draft.value.id
      ? await scenarioStore.update(draft.value.id, payload)
      : await scenarioStore.create(payload);
    toast.success(draft.value.id ? '预案已更新' : '预案已创建');
    emit('saved', saved);
    emit('update:open', false);
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '保存预案失败';
  } finally {
    saving.value = false;
  }
}

function close(): void {
  emit('update:open', false);
}
</script>

<template>
  <FDrawer :open="open" :title="scenario ? '编辑预案' : '新建预案'" description="名称必填；任意窗口选择「切换」时必须指定源。" :primary-label="'保存预案'"
    :hide-default-actions="true" :width="520" @update:open="(value) => emit('update:open', value)">
    <FCard padding="compact">
      <template #title>基础信息</template>
      <FField label="预案名称" required>
        <FInput v-model="draft.name" placeholder="例如：早会方案" />
      </FField>
      <FField label="备注" hint="可选；写明预案适用的场景或时间">
        <FTextarea v-model="draft.description" :rows="2" placeholder="例如：用于晨会现场，使用单屏 + 主屏 PPT" />
      </FField>
      <FField label="大屏模式" hint="保持表示不修改运行态；选择后将切换到对应模式">
        <FSegmented v-model="bigScreenSegmentValue" :options="screenSegmentOptions" full-width />
      </FField>
      <FField label="系统音量" hint="保持表示不修改系统音量；切换后按右侧值设定">
        <FSegmented v-model="draft.volumeState" :options="volumeSegmentOptions" full-width />
        <FSlider v-if="draft.volumeState === 'set'" v-model="draft.volumeLevel" :min="0" :max="100" show-value
          aria-label="系统音量值" />
      </FField>
    </FCard>

    <FCard padding="compact">
      <template #title>窗口配置</template>
      <div class="scenario-edit__windows">
        <FCard v-for="window in visibleWindows" :key="window.windowId" padding="compact" variant="subtle">
          <template #eyebrow>{{ windowLabel(window.windowId) }}</template>
          <template #title>窗口 {{ window.windowId }}</template>
          <FSegmented v-model="window.sourceState" :options="sourceSegmentOptions" full-width />
          <p v-if="window.sourceState === 'unset'" class="scenario-edit__hint">
            切换到本预案时，该窗口保留当前内容。
          </p>
          <p v-else-if="window.sourceState === 'empty'" class="scenario-edit__hint">
            切换到本预案时，该窗口黑屏。
          </p>
          <template v-else>
            <FField label="源选择" required>
              <FCombobox v-model="window.sourceId" :options="sourceOptionsByCategory" placeholder="选择源" searchable />
            </FField>
            <FSwitch v-model="window.autoplay" label="切换后自动播放" size="compact" />
            <FSwitch v-if="showLoopToggle(window)" v-model="window.resume" label="保留上次进度" size="compact" />
            <p v-if="window.sourceState === 'set' && !isVolumeEditable(window)" class="scenario-edit__hint">
              该源不支持音量控制（图片或网页源）。
            </p>
          </template>
        </FCard>
      </div>
    </FCard>

    <FMessageBar v-if="errorMessage" tone="error" title="无法保存">
      {{ errorMessage }}
    </FMessageBar>

    <template #actions>
      <FButton appearance="secondary" :disabled="saving" @click="close">取消</FButton>
      <FButton appearance="primary" :loading="saving" @click="save">保存预案</FButton>
    </template>
  </FDrawer>
</template>

<style scoped>
.scenario-edit__windows {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--spacing-m);
}

.scenario-edit__hint {
  margin: 0;
  color: var(--color-text-tertiary);
  font-size: var(--type-caption1-size);
}

@media (min-width: 768px) {
  .scenario-edit__windows {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
