<script setup lang="ts">
/**
 * 预案编辑覆盖大卡片：新建 / 编辑 / 从当前状态生成 三种入口共用。
 *  - 桌面：480 px 右侧 Drawer（移动端自动 → 全屏 Sheet）；
 *  - 移动端可视为单页可滚动表单。
 */
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import {
  NAlert,
  NButton,
  NCard,
  NDrawer,
  NDrawerContent,
  NFormItem,
  NInput,
  NRadio,
  NRadioGroup,
  NSelect,
  NSlider,
  NSwitch,
  type SelectGroupOption,
  type SelectOption,
} from 'naive-ui';

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
  scenario: ScenarioItem | null;
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

const isOpen = computed({
  get: () => props.open,
  set: (value: boolean) => emit('update:open', value),
});

watch(
  () => [props.open, props.scenario, props.prefillFromState] as const,
  ([isOpenVal, scenario, prefill]) => {
    if (!isOpenVal) return;
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

const sourceOptionsByCategory = computed<(SelectOption | SelectGroupOption)[]>(() => {
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
  const options: (SelectOption | SelectGroupOption)[] = [];
  for (const [groupLabel, list] of groups.entries()) {
    options.push({
      type: 'group',
      label: groupLabel,
      key: groupLabel,
      children: list.map((item) => ({
        label: item.name || item.original_filename || item.uri || t('scenarios.edit.sourceFallback', { id: item.id }),
        value: item.id,
        disabled: !item.is_available,
      })),
    });
  }
  return options;
});

const visibleWindows = computed<ScenarioWindowDraft[]>(() => {
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
  return cat === 'video';
}

function setBigScreenMode(value: ScenarioWindowMode): void {
  if (value === 'unset') {
    draft.value.bigScreenModeState = 'unset';
    return;
  }
  draft.value.bigScreenModeState = 'set';
  draft.value.bigScreenMode = value === 'empty' ? 'single' : 'double';
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
  <n-drawer v-model:show="isOpen" :width="520" placement="right">
    <n-drawer-content :title="scenario ? t('scenarios.edit.titleEdit') : t('scenarios.edit.titleCreate')" closable>
      <p class="scenario-edit__desc">{{ t('scenarios.edit.desc') }}</p>

      <n-card size="small" :title="t('scenarios.edit.basic')" class="scenario-edit__card">
        <n-form-item :label="t('scenarios.edit.name')" required>
          <n-input v-model:value="draft.name" :placeholder="t('scenarios.edit.namePlaceholder')" />
        </n-form-item>
        <n-form-item :label="t('scenarios.edit.remark')" :feedback="t('scenarios.edit.remarkHint')">
          <n-input v-model:value="draft.description" type="textarea" :rows="2" :placeholder="t('scenarios.edit.remarkPlaceholder')" />
        </n-form-item>
        <n-form-item :label="t('scenarios.edit.bigScreenMode')" :feedback="t('scenarios.edit.bigScreenHint')">
          <n-radio-group v-model:value="bigScreenSegmentValue">
            <n-radio value="unset">{{ t('scenarios.edit.keep') }}</n-radio>
            <n-radio value="empty">{{ t('scenarios.edit.single') }}</n-radio>
            <n-radio value="set">{{ t('scenarios.edit.double') }}</n-radio>
          </n-radio-group>
        </n-form-item>
        <n-form-item :label="t('scenarios.edit.systemVolume')" :feedback="t('scenarios.edit.systemVolumeHint')">
          <div class="scenario-edit__field-stack">
            <n-radio-group v-model:value="draft.volumeState">
              <n-radio value="unset">{{ t('scenarios.edit.keep') }}</n-radio>
              <n-radio value="set">{{ t('scenarios.edit.set') }}</n-radio>
            </n-radio-group>
            <n-slider v-if="draft.volumeState === 'set'" v-model:value="draft.volumeLevel" :min="0" :max="100"
              :aria-label="t('scenarios.edit.systemVolumeAria')" />
          </div>
        </n-form-item>
      </n-card>

      <n-card size="small" :title="t('scenarios.edit.windowsConfig')" class="scenario-edit__card">
        <div class="scenario-edit__windows">
          <n-card v-for="window in visibleWindows" :key="window.windowId" size="small" embedded>
            <template #header>
              <div>
                <span class="scenario-edit__eyebrow">{{ windowLabel(window.windowId) }}</span>
                <h4 class="scenario-edit__window-title">{{ t('scenarios.edit.window', { id: window.windowId }) }}</h4>
              </div>
            </template>
            <n-radio-group v-model:value="window.sourceState">
              <n-radio value="unset">{{ t('scenarios.edit.keep') }}</n-radio>
              <n-radio value="empty">{{ t('scenarios.edit.blackout') }}</n-radio>
              <n-radio value="set">{{ t('scenarios.edit.switch') }}</n-radio>
            </n-radio-group>
            <p v-if="window.sourceState === 'unset'" class="scenario-edit__hint">
              {{ t('scenarios.edit.keepHint') }}
            </p>
            <p v-else-if="window.sourceState === 'empty'" class="scenario-edit__hint">
              {{ t('scenarios.edit.blackoutHint') }}
            </p>
            <template v-else>
              <n-form-item :label="t('scenarios.edit.sourceSelect')" required>
                <n-select
                  v-model:value="window.sourceId"
                  :options="sourceOptionsByCategory"
                  :placeholder="t('scenarios.edit.sourcePlaceholder')"
                  filterable
                />
              </n-form-item>
              <div class="scenario-edit__switches">
                <div class="scenario-edit__switch">
                  <span>{{ t('scenarios.edit.autoplay') }}</span>
                  <n-switch v-model:value="window.autoplay" size="small" />
                </div>
                <div v-if="showLoopToggle(window)" class="scenario-edit__switch">
                  <span>{{ t('scenarios.edit.resume') }}</span>
                  <n-switch v-model:value="window.resume" size="small" />
                </div>
              </div>
              <p v-if="window.sourceState === 'set' && !isVolumeEditable(window)" class="scenario-edit__hint">
                {{ t('scenarios.edit.noVolumeHint') }}
              </p>
            </template>
          </n-card>
        </div>
      </n-card>

      <n-alert v-if="errorMessage" type="error" :title="t('scenarios.edit.cantSave')">
        {{ errorMessage }}
      </n-alert>

      <template #footer>
        <div class="scenario-edit__actions">
          <n-button :disabled="saving" @click="close">{{ t('common.cancel') }}</n-button>
          <n-button type="primary" :loading="saving" @click="save">{{ t('scenarios.edit.save') }}</n-button>
        </div>
      </template>
    </n-drawer-content>
  </n-drawer>
</template>

<style scoped>
.scenario-edit__desc {
  margin: 0 0 var(--spacingVerticalM);
  color: var(--colorNeutralForeground2);
  font-size: var(--fontSizeBase200);
}

.scenario-edit__card {
  margin-bottom: var(--spacingVerticalM);
}

.scenario-edit__field-stack {
  display: flex;
  flex-direction: column;
  gap: var(--spacingVerticalS);
  width: 100%;
}

.scenario-edit__windows {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--spacingVerticalM);
}

.scenario-edit__eyebrow {
  font-size: var(--fontSizeBase200);
  color: var(--colorNeutralForeground3);
}

.scenario-edit__window-title {
  margin: 0;
  font-size: var(--fontSizeBase300);
  font-weight: 600;
}

.scenario-edit__switches {
  display: flex;
  gap: var(--spacingHorizontalM);
  flex-wrap: wrap;
  margin-top: var(--spacingVerticalS);
}

.scenario-edit__switch {
  display: inline-flex;
  align-items: center;
  gap: var(--spacingHorizontalS);
}

.scenario-edit__hint {
  margin: var(--spacingVerticalXS) 0 0;
  color: var(--colorNeutralForeground3);
  font-size: var(--fontSizeBase200);
}

.scenario-edit__actions {
  display: inline-flex;
  align-items: center;
  gap: var(--spacingHorizontalS);
  justify-content: flex-end;
  width: 100%;
}

@media (min-width: 768px) {
  .scenario-edit__windows {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
