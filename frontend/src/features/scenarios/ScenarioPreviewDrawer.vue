<script setup lang="ts">
/**
 * 预案预览抽屉：列出四窗口配置；
 * 桌面 480 px 右侧 Drawer，移动端自动改全屏 Sheet。
 */
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import {
  NButton,
  NCard,
  NDrawer,
  NDrawerContent,
  NTag,
} from 'naive-ui';

import FIcon from '@/design-system/FIcon.vue';
import { useDialog } from '@/composables/useDialog';
import { useToast } from '@/composables/useToast';
import { useRuntimeStore } from '@/stores/runtime';
import { useScenarioStore } from '@/stores/scenarios';
import { useSourceStore } from '@/stores/sources';
import { formatRelativeTime } from '@/design-system/utils';
import type { ScenarioItem, ScenarioTargetItem } from '@/services/api';

interface ScenarioPreviewDrawerProps {
  open: boolean;
  scenario: ScenarioItem | null;
}

const props = defineProps<ScenarioPreviewDrawerProps>();
const emit = defineEmits<{
  (event: 'update:open', value: boolean): void;
  (event: 'edit', scenario: ScenarioItem): void;
  (event: 'after-delete'): void;
}>();

const { t } = useI18n();
const scenarioStore = useScenarioStore();
const sourceStore = useSourceStore();
const runtime = useRuntimeStore();
const dialog = useDialog();
const toast = useToast();
const isActivating = ref(false);
const isPinning = ref(false);

type NTagType = 'default' | 'primary' | 'info' | 'success' | 'warning' | 'error';

const isOpen = computed({
  get: () => props.open,
  set: (value: boolean) => emit('update:open', value),
});

const meta = computed(() => {
  if (!props.scenario) return '';
  const segments: string[] = [];
  segments.push(props.scenario.big_screen_mode_state === 'unset' ? t('scenarios.preview.keepScreen') : props.scenario.big_screen_mode_label || t('scenarios.preview.bigScreen'));
  segments.push(props.scenario.volume_state === 'unset' ? t('scenarios.preview.keepVolume') : t('scenarios.preview.systemVolume', { n: props.scenario.volume_level }));
  segments.push(t('scenarios.preview.updatedAt', { time: formatRelativeTime(props.scenario.updated_at) }));
  return segments.join(' · ');
});

const orderedTargets = computed<ScenarioTargetItem[]>(() => {
  if (!props.scenario) return [];
  const relevantWindowIds =
    props.scenario.big_screen_mode === 'single' && props.scenario.big_screen_mode_state !== 'unset'
      ? [1, 3, 4]
      : [1, 2, 3, 4];
  const map = new Map<number, ScenarioTargetItem>();
  props.scenario.targets.forEach((target) => map.set(target.window_id, target));
  return relevantWindowIds.map((wid) => map.get(wid) ?? ({
    window_id: wid,
    source_state: 'unset',
    source_id: null,
    source_name: '',
    autoplay: false,
    resume: false,
  } satisfies ScenarioTargetItem));
});

function windowLabel(windowId: number, isSingle: boolean): string {
  if (isSingle && windowId === 1) return t('scenarios.preview.winBig');
  switch (windowId) {
    case 1:
      return t('scenarios.preview.winBigLeft');
    case 2:
      return t('scenarios.preview.winBigRight');
    case 3:
      return t('scenarios.preview.winTvLeft');
    case 4:
      return t('scenarios.preview.winTvRight');
    default:
      return t('scenarios.preview.winFallback', { id: windowId });
  }
}

function targetTone(target: ScenarioTargetItem): NTagType {
  if (target.source_state === 'unset') return 'default';
  if (target.source_state === 'empty') return 'default';
  return 'success';
}

function targetLabel(target: ScenarioTargetItem): string {
  if (target.source_state === 'unset') return t('scenarios.preview.keepCurrent');
  if (target.source_state === 'empty') return t('scenarios.preview.blackout');
  return target.source_name || t('scenarios.preview.set');
}

function targetIcon(target: ScenarioTargetItem): string {
  if (target.source_state === 'unset') return 'arrow_repeat_all_off_24_regular';
  if (target.source_state === 'empty') return 'tv_24_regular';
  if (!target.source_id) return 'document_24_regular';
  const source = sourceStore.sources.find((s) => s.id === target.source_id);
  if (!source) return 'document_24_regular';
  const cat = sourceStore.resolveCategory(source.source_type);
  switch (cat) {
    case 'ppt':
      return 'document_24_regular';
    case 'video':
      return 'video_24_regular';
    case 'image':
      return 'image_24_regular';
    case 'web':
      return 'globe_24_regular';
    case 'stream':
      return 'live_24_regular';
    default:
      return 'document_24_regular';
  }
}

async function activate(): Promise<void> {
  if (!props.scenario) return;
  isActivating.value = true;
  try {
    await scenarioStore.activate(props.scenario.id);
    toast.success(t('scenarios.activatedOk'), t('scenarios.activatedDetail', { name: props.scenario.name }));
  } catch (error) {
    toast.error(t('scenarios.activateFail'), error instanceof Error ? error.message : t('common.retry'));
  } finally {
    isActivating.value = false;
  }
}

async function pinToggle(): Promise<void> {
  if (!props.scenario) return;
  const wasPinned = props.scenario.sort_order > 0;
  isPinning.value = true;
  try {
    const next = await scenarioStore.pin(props.scenario.id);
    toast.success(next.sort_order > 0 ? t('scenarios.pinnedOk') : t('scenarios.unpinnedOk'));
  } catch (error) {
    toast.error(wasPinned ? t('scenarios.unpinFail') : t('scenarios.pinFail'), error instanceof Error ? error.message : t('common.retry'));
  } finally {
    isPinning.value = false;
  }
}

async function remove(): Promise<void> {
  if (!props.scenario) return;
  const confirmed = await dialog.danger({
    title: t('scenarios.preview.deleteTitle', { name: props.scenario.name }),
    description: t('scenarios.preview.deleteDesc'),
    confirmLabel: t('scenarios.preview.deleteConfirm'),
  });
  if (!confirmed) return;
  try {
    await scenarioStore.remove(props.scenario.id);
    toast.success(t('scenarios.preview.deletedOk'));
    emit('after-delete');
    emit('update:open', false);
  } catch (error) {
    toast.error(t('scenarios.preview.deleteFail'), error instanceof Error ? error.message : t('common.retry'));
  }
}

function edit(): void {
  if (!props.scenario) return;
  emit('edit', props.scenario);
}

function close(): void {
  emit('update:open', false);
}

const isPinned = computed(() => Boolean(props.scenario && props.scenario.sort_order > 0));
const isSingleScreenMode = computed(() => props.scenario?.big_screen_mode === 'single');

void runtime;
</script>

<template>
  <n-drawer v-model:show="isOpen" :width="520" placement="right">
    <n-drawer-content :title="scenario?.name ?? t('scenarios.preview.title')" closable>
      <p class="scenario-preview__meta">{{ meta }}</p>

      <div class="scenario-preview__matrix" :class="{ 'scenario-preview__matrix--single': isSingleScreenMode }">
        <n-card v-for="target in orderedTargets" :key="target.window_id" size="small">
          <template #header>
            <div>
              <span class="scenario-preview__eyebrow">{{ windowLabel(target.window_id, isSingleScreenMode) }}</span>
              <div class="scenario-preview__target-tag">
                <n-tag :type="targetTone(target)" size="small" round>
                  <template #icon>
                    <FIcon :name="targetIcon(target)" />
                  </template>
                  {{ targetLabel(target) }}
                </n-tag>
              </div>
            </div>
          </template>
          <p v-if="target.source_state === 'set' && target.source_name" class="scenario-preview__source">
            {{ target.source_name }}
          </p>
          <p v-else-if="target.source_state === 'empty'" class="scenario-preview__hint">
            {{ t('scenarios.preview.blackoutHint') }}
          </p>
          <p v-else class="scenario-preview__hint">
            {{ t('scenarios.preview.keepHint') }}
          </p>
          <p v-if="target.source_state === 'set'" class="scenario-preview__settings">
            {{ t('scenarios.preview.sourceLine', { autoplay: target.autoplay ? t('scenarios.preview.on') : t('scenarios.preview.off'), resume: target.resume ? t('scenarios.preview.yes') : t('scenarios.preview.no') }) }}
          </p>
        </n-card>
      </div>

      <template #footer>
        <div class="scenario-preview__actions">
          <n-button @click="close">{{ t('common.close') }}</n-button>
          <n-button tertiary :loading="isPinning" @click="pinToggle">
            <template #icon>
              <FIcon :name="isPinned ? 'pin_off_24_regular' : 'pin_24_regular'" />
            </template>
            {{ isPinned ? t('scenarios.preview.unpin') : t('scenarios.preview.pin') }}
          </n-button>
          <n-button type="error" @click="remove">
            <template #icon><FIcon name="delete_24_regular" /></template>
            {{ t('common.delete') }}
          </n-button>
          <n-button @click="edit">
            <template #icon><FIcon name="edit_24_regular" /></template>
            {{ t('common.edit') }}
          </n-button>
          <n-button type="primary" :loading="isActivating" @click="activate">
            <template #icon><FIcon name="play_24_regular" /></template>
            {{ t('scenarios.preview.activate') }}
          </n-button>
        </div>
      </template>
    </n-drawer-content>
  </n-drawer>
</template>

<style scoped>
.scenario-preview__meta {
  margin: 0 0 var(--spacingVerticalM);
  color: var(--colorNeutralForeground2);
  font-size: var(--fontSizeBase200);
}

.scenario-preview__matrix {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--spacingHorizontalM);
}

.scenario-preview__matrix--single {
  grid-template-columns: 1fr;
}

.scenario-preview__eyebrow {
  font-size: var(--fontSizeBase200);
  color: var(--colorNeutralForeground3);
}

.scenario-preview__target-tag {
  margin-top: var(--spacingVerticalXS);
}

.scenario-preview__source {
  margin: 0;
  font-weight: 600;
}

.scenario-preview__hint {
  margin: 0;
  color: var(--colorNeutralForeground3);
  font-size: var(--fontSizeBase200);
}

.scenario-preview__settings {
  margin: var(--spacingVerticalXS) 0 0;
  color: var(--colorNeutralForeground2);
  font-size: var(--fontSizeBase200);
}

.scenario-preview__actions {
  display: inline-flex;
  align-items: center;
  gap: var(--spacingHorizontalS);
  justify-content: flex-end;
  width: 100%;
  flex-wrap: wrap;
}

@media (max-width: 767px) {
  .scenario-preview__matrix {
    grid-template-columns: 1fr;
  }
}
</style>
