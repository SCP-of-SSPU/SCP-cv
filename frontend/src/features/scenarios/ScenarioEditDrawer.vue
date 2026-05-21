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
import { useI18n } from 'vue-i18n';

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

const { t } = useI18n();
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
    const groupLabel = cat === 'ppt' ? t('sources.typeLabel.ppt')
      : cat === 'video' ? t('sources.typeLabel.video')
        : cat === 'image' ? t('sources.typeLabel.image')
          : cat === 'web' ? t('sources.typeLabel.web')
            : cat === 'stream' ? t('sources.typeLabel.stream') : t('sources.typeLabel.other');
    if (!groups.has(groupLabel)) groups.set(groupLabel, []);
    groups.get(groupLabel)!.push(source);
  }
  const options: FComboboxOption<number>[] = [];
  for (const [groupLabel, list] of groups.entries()) {
    // group 头是分类标题、不是真实源；标记 disabled 防止用户点中后把 source_id 设成 -1，
    // 旧实现会让前端校验通过却被后端 _resolve_source(-1) 拒绝，最终表现为「无法保存预案」。
    options.push({ label: groupLabel, value: -1, group: groupLabel, disabled: true });
    for (const item of list) {
      options.push({
        label: item.name || item.original_filename || item.uri || t('scenarios.edit.sourceFallback', { id: item.id }),
        value: item.id,
        hint: item.is_available ? undefined : t('scenarios.edit.unavailable'),
      });
    }
  }
  return options;
});

const screenSegmentOptions = computed<FSegmentedOption<ScenarioWindowMode>[]>(() => [
  { label: t('scenarios.edit.keep'), value: 'unset' },
  { label: t('scenarios.edit.single'), value: 'empty' as ScenarioWindowMode },
  { label: t('scenarios.edit.double'), value: 'set' as ScenarioWindowMode },
]);

const volumeSegmentOptions = computed<FSegmentedOption<ScenarioWindowMode>[]>(() => [
  { label: t('scenarios.edit.keep'), value: 'unset' },
  { label: t('scenarios.edit.set'), value: 'set' },
]);

const sourceSegmentOptions = computed<FSegmentedOption<ScenarioWindowMode>[]>(() => [
  { label: t('scenarios.edit.keep'), value: 'unset' },
  { label: t('scenarios.edit.blackout'), value: 'empty' },
  { label: t('scenarios.edit.switch'), value: 'set' },
]);

const visibleWindows = computed<ScenarioWindowDraft[]>(() => {
  // 顶部「大屏模式：单屏」时合并 W1/W2 为「大屏」，但实际仍写 W1。
  if (draft.value.bigScreenModeState !== 'unset' && draft.value.bigScreenMode === 'single') {
    return draft.value.windows.filter((win) => win.windowId !== 2);
  }
  return draft.value.windows;
});

function windowLabel(windowId: number): string {
  if (draft.value.bigScreenModeState !== 'unset' && draft.value.bigScreenMode === 'single' && windowId === 1) {
    return t('scenarios.edit.winBig');
  }
  switch (windowId) {
    case 1:
      return t('scenarios.edit.winBigLeft');
    case 2:
      return t('scenarios.edit.winBigRight');
    case 3:
      return t('scenarios.edit.winTvLeft');
    case 4:
      return t('scenarios.edit.winTvRight');
    default:
      return t('scenarios.edit.winFallback', { id: windowId });
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
    // 「切换」窗口必须绑定真实存在的源（id ≥ 1）；
    // 旧实现仅用 `!window.sourceId` 判定，会放过 -1 这种 group 占位值，
    // 导致后端 _resolve_source(-1) 抛错让用户感觉「无法保存」。
    if (window.sourceState === 'set' && (window.sourceId === null || window.sourceId === undefined || window.sourceId < 1)) {
      errorMessage.value = t('scenarios.edit.requireSource', { label: windowLabel(window.windowId) });
      return;
    }
  }

  saving.value = true;
  try {
    const payload = toScenarioPayload(draft.value);
    const saved = draft.value.id
      ? await scenarioStore.update(draft.value.id, payload)
      : await scenarioStore.create(payload);
    toast.success(draft.value.id ? t('scenarios.edit.updated') : t('scenarios.edit.created'));
    emit('saved', saved);
    emit('update:open', false);
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : t('scenarios.edit.saveFail');
  } finally {
    saving.value = false;
  }
}

function close(): void {
  emit('update:open', false);
}
</script>

<template>
  <FDrawer :open="open" :title="scenario ? t('scenarios.edit.titleEdit') : t('scenarios.edit.titleCreate')" :description="t('scenarios.edit.desc')" :primary-label="t('scenarios.edit.save')"
    :hide-default-actions="true" :width="520" @update:open="(value) => emit('update:open', value)">
    <FCard padding="compact">
      <template #title>{{ t('scenarios.edit.basic') }}</template>
      <FField :label="t('scenarios.edit.name')" required>
        <FInput v-model="draft.name" :placeholder="t('scenarios.edit.namePlaceholder')" />
      </FField>
      <FField :label="t('scenarios.edit.remark')" :hint="t('scenarios.edit.remarkHint')">
        <FTextarea v-model="draft.description" :rows="2" :placeholder="t('scenarios.edit.remarkPlaceholder')" />
      </FField>
      <FField :label="t('scenarios.edit.bigScreenMode')" :hint="t('scenarios.edit.bigScreenHint')">
        <FSegmented v-model="bigScreenSegmentValue" :options="screenSegmentOptions" full-width />
      </FField>
      <FField :label="t('scenarios.edit.systemVolume')" :hint="t('scenarios.edit.systemVolumeHint')">
        <FSegmented v-model="draft.volumeState" :options="volumeSegmentOptions" full-width />
        <FSlider v-if="draft.volumeState === 'set'" v-model="draft.volumeLevel" :min="0" :max="100" show-value
          :aria-label="t('scenarios.edit.systemVolumeAria')" />
      </FField>
    </FCard>

    <FCard padding="compact">
      <template #title>{{ t('scenarios.edit.windowsConfig') }}</template>
      <div class="scenario-edit__windows">
        <FCard v-for="window in visibleWindows" :key="window.windowId" padding="compact" variant="subtle">
          <template #eyebrow>{{ windowLabel(window.windowId) }}</template>
          <template #title>{{ t('scenarios.edit.window', { id: window.windowId }) }}</template>
          <FSegmented v-model="window.sourceState" :options="sourceSegmentOptions" full-width />
          <p v-if="window.sourceState === 'unset'" class="scenario-edit__hint">
            {{ t('scenarios.edit.keepHint') }}
          </p>
          <p v-else-if="window.sourceState === 'empty'" class="scenario-edit__hint">
            {{ t('scenarios.edit.blackoutHint') }}
          </p>
          <template v-else>
            <FField :label="t('scenarios.edit.sourceSelect')" required>
              <FCombobox v-model="window.sourceId" :options="sourceOptionsByCategory" :placeholder="t('scenarios.edit.sourcePlaceholder')" searchable />
            </FField>
            <FSwitch v-model="window.autoplay" :label="t('scenarios.edit.autoplay')" size="compact" />
            <FSwitch v-if="showLoopToggle(window)" v-model="window.resume" :label="t('scenarios.edit.resume')" size="compact" />
            <p v-if="window.sourceState === 'set' && !isVolumeEditable(window)" class="scenario-edit__hint">
              {{ t('scenarios.edit.noVolumeHint') }}
            </p>
          </template>
        </FCard>
      </div>
    </FCard>

    <FMessageBar v-if="errorMessage" tone="error" :title="t('scenarios.edit.cantSave')">
      {{ errorMessage }}
    </FMessageBar>

    <template #actions>
      <FButton appearance="secondary" :disabled="saving" @click="close">{{ t('common.cancel') }}</FButton>
      <FButton appearance="primary" :loading="saving" @click="save">{{ t('scenarios.edit.save') }}</FButton>
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
  color: var(--colorNeutralForeground3);
  font-size: var(--fontSizeBase200);
}

@media (min-width: 768px) {
  .scenario-edit__windows {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
