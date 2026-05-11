<script setup lang="ts">
/**
 * 预案预览抽屉：列出四窗口配置；
 * 桌面 480 px 右侧 Drawer，移动端自动改全屏 Sheet。
 */
import { computed, ref } from 'vue';

import {
  FButton,
  FCard,
  FDrawer,
  FIcon,
  FTag,
} from '@/design-system';
import type { TagTone } from '@/design-system';
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

const scenarioStore = useScenarioStore();
const sourceStore = useSourceStore();
const runtime = useRuntimeStore();
const dialog = useDialog();
const toast = useToast();
const isActivating = ref(false);
const isPinning = ref(false);

const meta = computed(() => {
  if (!props.scenario) return '';
  const segments: string[] = [];
  segments.push(props.scenario.big_screen_mode_state === 'unset' ? '保持大屏模式' : props.scenario.big_screen_mode_label || '大屏');
  segments.push(props.scenario.volume_state === 'unset' ? '保持系统音量' : `系统音量 ${props.scenario.volume_level}`);
  segments.push(`更新于 ${formatRelativeTime(props.scenario.updated_at)}`);
  return segments.join(' · ');
});

const orderedTargets = computed<ScenarioTargetItem[]>(() => {
  if (!props.scenario) return [];
  // 双屏：W1 W2 W3 W4；单屏（big-right 隐藏）：W1 W3 W4
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
  if (isSingle && windowId === 1) return '大屏';
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

function targetTone(target: ScenarioTargetItem): TagTone {
  if (target.source_state === 'unset') return 'subtle';
  if (target.source_state === 'empty') return 'neutral';
  return 'success';
}

function targetLabel(target: ScenarioTargetItem): string {
  if (target.source_state === 'unset') return '保持当前';
  if (target.source_state === 'empty') return '黑屏';
  return target.source_name || '已设置';
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
    toast.success('预案已调用', `已应用「${props.scenario.name}」到所有窗口`);
  } catch (error) {
    toast.error('调用预案失败', error instanceof Error ? error.message : '请稍后重试');
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
    toast.success(next.sort_order > 0 ? '预案已置顶' : '预案已取消置顶');
  } catch (error) {
    toast.error(wasPinned ? '取消置顶失败' : '置顶失败', error instanceof Error ? error.message : '请稍后重试');
  } finally {
    isPinning.value = false;
  }
}

async function remove(): Promise<void> {
  if (!props.scenario) return;
  const confirmed = await dialog.danger({
    title: `删除预案「${props.scenario.name}」？`,
    description: '此操作不可恢复，预案中四窗口配置会被一并移除。',
    confirmLabel: '删除预案',
  });
  if (!confirmed) return;
  try {
    await scenarioStore.remove(props.scenario.id);
    toast.success('预案已删除');
    emit('after-delete');
    emit('update:open', false);
  } catch (error) {
    toast.error('删除失败', error instanceof Error ? error.message : '请稍后重试');
  }
}

function edit(): void {
  if (!props.scenario) return;
  emit('edit', props.scenario);
}

const isPinned = computed(() => Boolean(props.scenario && props.scenario.sort_order > 0));

const isSingleScreenMode = computed(() => props.scenario?.big_screen_mode === 'single');

const currentBigScreenSnapshotMode = computed(() => runtime.runtime?.big_screen_mode ?? 'single');
void currentBigScreenSnapshotMode; // 保留以备未来在预览中显示模式差异提示
</script>

<template>
  <FDrawer :open="open" :title="scenario?.name ?? '预案预览'" :description="meta" :primary-label="'激活'"
    :secondary-label="'关闭'" :width="520" :hide-default-actions="true"
    @update:open="(value) => emit('update:open', value)">
    <div class="scenario-preview__matrix" :class="{ 'scenario-preview__matrix--single': isSingleScreenMode }">
      <FCard v-for="target in orderedTargets" :key="target.window_id" padding="compact">
        <template #eyebrow>{{ windowLabel(target.window_id, isSingleScreenMode) }}</template>
        <template #title>
          <FTag :tone="targetTone(target)" :icon="targetIcon(target)">
            {{ targetLabel(target) }}
          </FTag>
        </template>
        <p v-if="target.source_state === 'set' && target.source_name" class="scenario-preview__source">
          {{ target.source_name }}
        </p>
        <p v-else-if="target.source_state === 'empty'" class="scenario-preview__hint">
          切换到本预案时，该窗口黑屏。
        </p>
        <p v-else class="scenario-preview__hint">
          切换到本预案时，该窗口保留当前内容。
        </p>
        <p v-if="target.source_state === 'set'" class="scenario-preview__settings">
          自动播放 {{ target.autoplay ? '开' : '关' }} · 续播 {{ target.resume ? '是' : '否' }}
        </p>
      </FCard>
    </div>

    <template #actions="{ cancel }">
      <FButton appearance="secondary" @click="cancel">关闭</FButton>
      <FButton appearance="subtle" :icon-start="isPinned ? 'pin_off_24_regular' : 'pin_24_regular'" :loading="isPinning"
        @click="pinToggle">
        {{ isPinned ? '取消置顶' : '置顶' }}
      </FButton>
      <FButton appearance="danger" icon-start="delete_24_regular" @click="remove">
        删除
      </FButton>
      <FButton appearance="secondary" icon-start="edit_24_regular" @click="edit">
        编辑
      </FButton>
      <FButton appearance="primary" icon-start="play_24_regular" :loading="isActivating" @click="activate">
        激活
      </FButton>
    </template>
  </FDrawer>
</template>

<style scoped>
.scenario-preview__matrix {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--spacing-m);
}

.scenario-preview__matrix--single {
  grid-template-columns: 1fr;
}

.scenario-preview__matrix--single :deep(.f-card):first-child {
  grid-column: span 1;
}

.scenario-preview__source {
  margin: 0;
  font-weight: 600;
}

.scenario-preview__hint {
  margin: 0;
  color: var(--color-text-tertiary);
  font-size: var(--type-caption1-size);
}

.scenario-preview__settings {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--type-caption1-size);
}

@media (max-width: 767px) {
  .scenario-preview__matrix {
    grid-template-columns: 1fr;
  }
}
</style>
