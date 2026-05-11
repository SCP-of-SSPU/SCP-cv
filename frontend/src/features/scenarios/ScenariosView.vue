<script setup lang="ts">
/**
 * 预案管理：列表 + 预览 Drawer + 编辑 Drawer。
 * 设计稿 §4.5：
 *   - 默认形态仅 Sub-Toolbar + 列表；
 *   - 卡片整体可点开预览；
 *   - 新建 / 编辑 / 从当前状态生成 共用同一编辑表单。
 */
import { computed, ref } from 'vue';

import {
  FButton,
  FCard,
  FEmpty,
  FIcon,
  FSkeleton,
  FTag,
} from '@/design-system';
import ScenarioEditDrawer from './ScenarioEditDrawer.vue';
import ScenarioPreviewDrawer from './ScenarioPreviewDrawer.vue';
import { createEmptyDraft, type ScenarioDraft } from './scenarioModel';
import { useToast } from '@/composables/useToast';
import { useRuntimeStore } from '@/stores/runtime';
import { useScenarioStore } from '@/stores/scenarios';
import { useSessionStore } from '@/stores/sessions';
import { formatRelativeTime } from '@/design-system/utils';
import type { ScenarioItem } from '@/services/api';

const scenarioStore = useScenarioStore();
const sessionStore = useSessionStore();
const runtime = useRuntimeStore();
const toast = useToast();

const previewOpen = ref(false);
const editOpen = ref(false);
const isLoading = ref(false);
const pendingActivateId = ref<number | null>(null);
const pendingPinId = ref<number | null>(null);

const previewScenarioId = ref<number | null>(null);
const editingScenario = ref<ScenarioItem | null>(null);
const prefillDraft = ref<ScenarioDraft | undefined>(undefined);

const sortedScenarios = computed(() => scenarioStore.sorted);
const previewScenario = computed<ScenarioItem | null>(() => {
  if (previewScenarioId.value === null) return null;
  return scenarioStore.scenarios.find((scenario) => scenario.id === previewScenarioId.value) ?? null;
});

async function refresh(): Promise<void> {
  isLoading.value = true;
  try {
    await scenarioStore.refresh();
  } catch (error) {
    toast.error('预案列表加载失败', error instanceof Error ? error.message : '请稍后重试');
  } finally {
    isLoading.value = false;
  }
}

function openPreview(scenario: ScenarioItem): void {
  previewScenarioId.value = scenario.id;
  previewOpen.value = true;
}

function openCreate(): void {
  editingScenario.value = null;
  prefillDraft.value = undefined;
  editOpen.value = true;
}

function openEdit(scenario: ScenarioItem): void {
  editingScenario.value = scenario;
  prefillDraft.value = undefined;
  previewOpen.value = false;
  editOpen.value = true;
}

function captureFromCurrent(): void {
  // 把当前 sessions / runtime 直接写到草稿，作为「从当前状态生成」入口。
  const draft: ScenarioDraft = createEmptyDraft();
  draft.name = '';
  draft.bigScreenModeState = 'set';
  draft.bigScreenMode = runtime.runtime?.big_screen_mode ?? 'single';
  draft.volumeState = 'set';
  draft.volumeLevel = runtime.systemVolume.level;

  draft.windows = draft.windows.map((win) => {
    const session = sessionStore.byWindowId(win.windowId);
    if (!session?.source_id) return { ...win, sourceState: 'unset' };
    return {
      ...win,
      sourceState: 'set',
      sourceId: session.source_id,
      autoplay: true,
      resume: false,
    };
  });

  editingScenario.value = null;
  prefillDraft.value = draft;
  editOpen.value = true;
}

function onAfterDelete(): void {
  // 删除后预览抽屉已自动关闭，这里再触发一次 refresh 防止漂移。
  previewScenarioId.value = null;
  void refresh();
}

function onSaved(scenario: ScenarioItem): void {
  toast.success('预案已保存');
  editingScenario.value = null;
  prefillDraft.value = undefined;
  editOpen.value = false;
  // 立即把刚保存的预案打开预览，便于继续微调或激活。
  previewScenarioId.value = scenario.id;
  previewOpen.value = true;
}

async function activateScenario(scenario: ScenarioItem): Promise<void> {
  pendingActivateId.value = scenario.id;
  try {
    await scenarioStore.activate(scenario.id);
    toast.success('预案已调用', `已应用「${scenario.name}」到所有窗口`);
  } catch (error) {
    toast.error('调用预案失败', error instanceof Error ? error.message : '请稍后重试');
  } finally {
    pendingActivateId.value = null;
  }
}

async function togglePin(scenario: ScenarioItem): Promise<void> {
  const wasPinned = scenario.sort_order > 0;
  pendingPinId.value = scenario.id;
  try {
    const next = await scenarioStore.pin(scenario.id);
    toast.success(next.sort_order > 0 ? '预案已置顶' : '预案已取消置顶');
  } catch (error) {
    toast.error(wasPinned ? '取消置顶失败' : '置顶失败', error instanceof Error ? error.message : '请稍后重试');
  } finally {
    pendingPinId.value = null;
  }
}

const activeId = computed(() => sessionStore.sessions[0]?.session_id ?? null);
void activeId; // 当前后端未提供「激活预案 id」字段；保留 hook
</script>

<template>
  <div class="scenarios-view">
    <header class="scenarios-view__toolbar">
      <div class="scenarios-view__heading">
        <h2 class="scenarios-view__title">预案</h2>
        <p class="scenarios-view__caption">浏览、调用、编辑预案；从当前状态可一键生成新预案。</p>
      </div>
      <div class="scenarios-view__actions">
        <FButton appearance="secondary" icon-start="arrow_clockwise_20_regular" icon-only aria-label="刷新预案列表"
          :loading="isLoading" @click="refresh" />
        <FButton appearance="secondary" icon-start="document_24_regular" @click="captureFromCurrent">
          从当前状态生成
        </FButton>
        <FButton appearance="primary" icon-start="add_24_regular" @click="openCreate">
          新建预案
        </FButton>
      </div>
    </header>

    <section class="scenarios-view__grid">
      <template v-if="isLoading && sortedScenarios.length === 0">
        <FCard v-for="i in 4" :key="i" padding="compact">
          <FSkeleton shape="text" width="50%" />
          <FSkeleton shape="text" width="80%" />
          <FSkeleton shape="text" width="35%" />
        </FCard>
      </template>

      <template v-else-if="sortedScenarios.length === 0">
        <FEmpty title="暂无预案" description="从当前播放状态生成预案，或手动创建第一个预案。" icon="layer_24_regular">
          <template #actions>
            <FButton appearance="primary" icon-start="add_24_regular" @click="openCreate">
              新建预案
            </FButton>
            <FButton appearance="subtle" icon-start="document_24_regular" @click="captureFromCurrent">
              从当前状态生成
            </FButton>
          </template>
        </FEmpty>
      </template>

      <template v-else>
        <FCard v-for="scenario in sortedScenarios" :key="scenario.id" padding="compact" interactive
          :class="{ 'scenarios-view__card--pinned': scenario.sort_order > 0 }" @click="openPreview(scenario)">
          <template #eyebrow>
            <span v-if="scenario.sort_order > 0" class="scenarios-view__pinned">
              <FIcon name="pin_24_filled" /> 置顶
            </span>
            <span v-else>预案</span>
          </template>
          <template #actions>
            <FButton appearance="transparent" size="compact" icon-only
              :icon-start="scenario.sort_order > 0 ? 'pin_off_24_regular' : 'pin_24_regular'"
              :aria-label="scenario.sort_order > 0 ? '取消置顶预案' : '置顶预案'"
              :loading="pendingPinId === scenario.id" @click.stop="togglePin(scenario)" />
            <FButton appearance="primary" size="compact" icon-start="play_24_regular"
              :loading="pendingActivateId === scenario.id" @click.stop="activateScenario(scenario)">
              调用
            </FButton>
          </template>
          <template #title>{{ scenario.name }}</template>
          <p class="scenarios-view__meta">
            <FTag :tone="scenario.big_screen_mode_state === 'unset' ? 'subtle' : 'info'">
              {{ scenario.big_screen_mode_state === 'unset' ? '保持大屏模式' : scenario.big_screen_mode_label }}
            </FTag>
            <FTag :tone="scenario.volume_state === 'unset' ? 'subtle' : 'info'">
              {{ scenario.volume_state === 'unset' ? '保持音量' : `音量 ${scenario.volume_level}` }}
            </FTag>
          </p>
          <p v-if="scenario.description" class="scenarios-view__desc">{{ scenario.description }}</p>
          <p class="scenarios-view__updated">更新于 {{ formatRelativeTime(scenario.updated_at) }}</p>
        </FCard>
      </template>
    </section>

    <ScenarioPreviewDrawer v-model:open="previewOpen" :scenario="previewScenario" @edit="openEdit"
      @after-delete="onAfterDelete" />
    <ScenarioEditDrawer v-model:open="editOpen" :scenario="editingScenario" :prefill-from-state="prefillDraft"
      @saved="onSaved" />
  </div>
</template>

<style scoped>
.scenarios-view {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-l);
  max-width: 1280px;
}

/*
 * sticky toolbar 锚定到 .app-shell__content 滚动容器的 content-edge.top；
 * 历史值 56px 会让 toolbar 在自身原位之外再向下偏移 56 px，与下方第一行卡片
 * 产生视觉重叠。改成 0 让 sticky 起点与自然位置一致。
 */
.scenarios-view__toolbar {
  position: sticky;
  top: 0;
  z-index: var(--z-sticky);
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--spacing-l);
  padding: var(--spacing-m) 0;
  background: color-mix(in srgb, var(--color-background-canvas) 92%, transparent);
  flex-wrap: wrap;
  -webkit-backdrop-filter: blur(12px);
  backdrop-filter: blur(12px);
}

.scenarios-view__heading {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.scenarios-view__title {
  margin: 0;
  font-size: var(--type-title2-size);
  line-height: var(--type-title2-line);
  font-weight: 600;
}

.scenarios-view__caption {
  margin: 0;
  color: var(--color-text-tertiary);
  font-size: var(--type-caption1-size);
}

.scenarios-view__actions {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-s);
  flex-wrap: wrap;
}

.scenarios-view__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: var(--spacing-l);
}

.scenarios-view__card--pinned {
  border-left: 4px solid var(--color-background-brand);
  box-shadow:
    var(--shadow-card-hover),
    inset 0 0 0 1px color-mix(in srgb, var(--color-background-brand) 16%, transparent);
}

.scenarios-view__pinned {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  color: var(--color-text-brand);
}

.scenarios-view__meta {
  margin: 0;
  display: inline-flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--spacing-xs);
}

.scenarios-view__desc {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--type-caption1-size);
  line-height: var(--type-body1-line);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.scenarios-view__updated {
  margin: 0;
  color: var(--color-text-tertiary);
  font-size: var(--type-caption1-size);
}

@media (max-width: 767px) {
  .scenarios-view__toolbar {
    top: 96px;
    flex-direction: column;
    align-items: stretch;
  }

  .scenarios-view__actions {
    justify-content: space-between;
  }

  .scenarios-view :deep(.f-card__header) {
    flex-direction: column;
  }

  .scenarios-view :deep(.f-card__actions) {
    width: 100%;
    justify-content: flex-end;
  }

  .scenarios-view__grid {
    grid-template-columns: 1fr;
  }
}
</style>
