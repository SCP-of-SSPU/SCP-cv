<script setup lang="ts">
/**
 * 预案管理：列表 + 预览 Drawer + 编辑 Drawer。
 *   - 默认形态仅 Sub-Toolbar + 列表；
 *   - 卡片整体可点开预览；
 *   - 新建 / 编辑 / 从当前状态生成 共用同一编辑表单。
 */
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import {
  NButton,
  NCard,
  NEmpty,
  NSkeleton,
  NTag,
} from 'naive-ui';

import FIcon from '@/design-system/FIcon.vue';
import ScenarioEditDrawer from './ScenarioEditDrawer.vue';
import ScenarioPreviewDrawer from './ScenarioPreviewDrawer.vue';
import { createEmptyDraft, type ScenarioDraft } from './scenarioModel';
import { useToast } from '@/composables/useToast';
import { useRuntimeStore } from '@/stores/runtime';
import { useScenarioStore } from '@/stores/scenarios';
import { useSessionStore } from '@/stores/sessions';
import { formatRelativeTime } from '@/design-system/utils';
import type { ScenarioItem } from '@/services/api';

const { t } = useI18n();
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
    toast.error(t('scenarios.loadFail'), error instanceof Error ? error.message : t('common.retry'));
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
  previewScenarioId.value = null;
  void refresh();
}

function onSaved(scenario: ScenarioItem): void {
  toast.success(t('scenarios.saved'));
  editingScenario.value = null;
  prefillDraft.value = undefined;
  editOpen.value = false;
  previewScenarioId.value = scenario.id;
  previewOpen.value = true;
}

async function activateScenario(scenario: ScenarioItem): Promise<void> {
  pendingActivateId.value = scenario.id;
  try {
    await scenarioStore.activate(scenario.id);
    toast.success(t('scenarios.activatedOk'), t('scenarios.activatedDetail', { name: scenario.name }));
  } catch (error) {
    toast.error(t('scenarios.activateFail'), error instanceof Error ? error.message : t('common.retry'));
  } finally {
    pendingActivateId.value = null;
  }
}

async function togglePin(scenario: ScenarioItem): Promise<void> {
  const wasPinned = scenario.sort_order > 0;
  pendingPinId.value = scenario.id;
  try {
    const next = await scenarioStore.pin(scenario.id);
    toast.success(next.sort_order > 0 ? t('scenarios.pinnedOk') : t('scenarios.unpinnedOk'));
  } catch (error) {
    toast.error(wasPinned ? t('scenarios.unpinFail') : t('scenarios.pinFail'), error instanceof Error ? error.message : t('common.retry'));
  } finally {
    pendingPinId.value = null;
  }
}
</script>

<template>
  <div class="scenarios-view">
    <header class="scenarios-view__toolbar">
      <div class="scenarios-view__heading">
        <h2 class="scenarios-view__title">{{ t('scenarios.title') }}</h2>
        <p class="scenarios-view__caption">{{ t('scenarios.caption') }}</p>
      </div>
      <div class="scenarios-view__actions">
        <n-button :loading="isLoading" :aria-label="t('scenarios.refreshAria')" @click="refresh">
          <template #icon><FIcon name="arrow_clockwise_20_regular" /></template>
        </n-button>
        <n-button @click="captureFromCurrent">
          <template #icon><FIcon name="document_24_regular" /></template>
          {{ t('scenarios.captureFromState') }}
        </n-button>
        <n-button type="primary" @click="openCreate">
          <template #icon><FIcon name="add_24_regular" /></template>
          {{ t('scenarios.create') }}
        </n-button>
      </div>
    </header>

    <section class="scenarios-view__grid">
      <template v-if="isLoading && sortedScenarios.length === 0">
        <n-card v-for="i in 4" :key="i" size="small">
          <n-skeleton text width="50%" />
          <n-skeleton text width="80%" />
          <n-skeleton text width="35%" />
        </n-card>
      </template>

      <template v-else-if="sortedScenarios.length === 0">
        <n-empty :description="t('scenarios.emptyDesc')">
          <template #icon>
            <FIcon name="layer_24_regular" />
          </template>
          <template #extra>
            <n-button type="primary" @click="openCreate">
              <template #icon><FIcon name="add_24_regular" /></template>
              {{ t('scenarios.create') }}
            </n-button>
            <n-button tertiary @click="captureFromCurrent">
              <template #icon><FIcon name="document_24_regular" /></template>
              {{ t('scenarios.captureFromState') }}
            </n-button>
          </template>
        </n-empty>
      </template>

      <template v-else>
        <n-card
          v-for="scenario in sortedScenarios"
          :key="scenario.id"
          size="small"
          hoverable
          :class="{ 'scenarios-view__card--pinned': scenario.sort_order > 0 }"
          @click="openPreview(scenario)"
        >
          <template #header>
            <div class="scenarios-view__card-header">
              <span v-if="scenario.sort_order > 0" class="scenarios-view__pinned">
                <FIcon name="pin_24_filled" /> {{ t('scenarios.pinned') }}
              </span>
              <span v-else class="scenarios-view__eyebrow">{{ t('scenarios.label') }}</span>
              <h3 class="scenarios-view__card-title">{{ scenario.name }}</h3>
            </div>
          </template>
          <template #header-extra>
            <div class="scenarios-view__card-actions" @click.stop>
              <n-button
                quaternary
                size="small"
                :aria-label="scenario.sort_order > 0 ? t('scenarios.unpinAria') : t('scenarios.pinAria')"
                :loading="pendingPinId === scenario.id"
                @click="togglePin(scenario)"
              >
                <template #icon>
                  <FIcon :name="scenario.sort_order > 0 ? 'pin_off_24_regular' : 'pin_24_regular'" />
                </template>
              </n-button>
              <n-button
                type="primary"
                size="small"
                :loading="pendingActivateId === scenario.id"
                @click="activateScenario(scenario)"
              >
                <template #icon><FIcon name="play_24_regular" /></template>
                {{ t('scenarios.activate') }}
              </n-button>
            </div>
          </template>

          <p class="scenarios-view__meta">
            <n-tag :type="scenario.big_screen_mode_state === 'unset' ? 'default' : 'info'" size="small" round>
              {{ scenario.big_screen_mode_state === 'unset' ? t('scenarios.keepScreenMode') : scenario.big_screen_mode_label }}
            </n-tag>
            <n-tag :type="scenario.volume_state === 'unset' ? 'default' : 'info'" size="small" round>
              {{ scenario.volume_state === 'unset' ? t('scenarios.keepVolume') : t('scenarios.volumeValue', { n: scenario.volume_level }) }}
            </n-tag>
          </p>
          <p v-if="scenario.description" class="scenarios-view__desc">{{ scenario.description }}</p>
          <p class="scenarios-view__updated">{{ t('scenarios.updatedAt', { time: formatRelativeTime(scenario.updated_at) }) }}</p>
        </n-card>
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
  gap: var(--spacingVerticalL);
  max-width: 1280px;
}

.scenarios-view__toolbar {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--spacingHorizontalL);
  padding: var(--spacingVerticalM) 0;
  flex-wrap: wrap;
  border-bottom: 1px solid var(--colorNeutralStrokeDivider);
}

.scenarios-view__heading {
  display: flex;
  flex-direction: column;
  gap: var(--spacingVerticalXS);
}

.scenarios-view__title {
  margin: 0;
  font-size: var(--fontSizeHero700);
  line-height: var(--lineHeightHero700);
  font-weight: 600;
}

.scenarios-view__caption {
  margin: 0;
  color: var(--colorNeutralForeground3);
  font-size: var(--fontSizeBase200);
}

.scenarios-view__actions {
  display: inline-flex;
  align-items: center;
  gap: var(--spacingHorizontalS);
  flex-wrap: wrap;
}

.scenarios-view__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: var(--spacingHorizontalL);
}

.scenarios-view__grid > .n-empty {
  grid-column: 1 / -1;
  justify-self: center;
  align-self: center;
  padding: var(--spacingVerticalXXL) var(--spacingHorizontalL);
}

.scenarios-view__grid:has(.n-empty) {
  min-height: 50vh;
}

.scenarios-view__card--pinned {
  border-left: 4px solid var(--colorBrandBackground);
}

.scenarios-view__card-header {
  display: flex;
  flex-direction: column;
  gap: var(--spacingVerticalXS);
}

.scenarios-view__card-title {
  margin: 0;
  font-size: var(--fontSizeBase400);
  font-weight: 600;
}

.scenarios-view__eyebrow {
  font-size: var(--fontSizeBase200);
  color: var(--colorNeutralForeground3);
}

.scenarios-view__pinned {
  display: inline-flex;
  align-items: center;
  gap: var(--spacingHorizontalXS);
  color: var(--colorBrandForeground1);
  font-size: var(--fontSizeBase200);
}

.scenarios-view__card-actions {
  display: inline-flex;
  align-items: center;
  gap: var(--spacingHorizontalXS);
}

.scenarios-view__meta {
  margin: var(--spacingVerticalS) 0 0;
  display: inline-flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--spacingHorizontalXS);
}

.scenarios-view__desc {
  margin: var(--spacingVerticalS) 0 0;
  color: var(--colorNeutralForeground2);
  font-size: var(--fontSizeBase200);
  line-height: var(--lineHeightBase300);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.scenarios-view__updated {
  margin: var(--spacingVerticalS) 0 0;
  color: var(--colorNeutralForeground3);
  font-size: var(--fontSizeBase200);
}

@media (max-width: 767px) {
  .scenarios-view__toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .scenarios-view__grid {
    grid-template-columns: 1fr;
  }
}
</style>
