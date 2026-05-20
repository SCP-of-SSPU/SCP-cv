<script setup lang="ts">
/**
 * 媒体源管理：
 *   - 桌面：左侧类型 NavList + 右侧 DetailList；
 *   - 移动：顶部类型 Pills（横滑） + 卡片列表 + 右下 FAB（添加源 Sheet）。
 *
 * 设计稿 §4.4：
 *   - 不再展示「文件夹」与「临时源」UI；
 *   - 行末菜单只保留：打开到窗口 1/2/3/4、下载（仅文件型）、删除。
 */
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import {
  FButton,
  FCard,
  FEmpty,
  FIcon,
  FInput,
  FMenu,
  FMessageBar,
  FSkeleton,
  FTabs,
  FTag,
} from '@/design-system';
import type { FTabsItem, FMenuGroup } from '@/design-system';
import AddSourceDrawer from './AddSourceDrawer.vue';
import EditSourceDrawer from './EditSourceDrawer.vue';
import SourceThumbnail from './SourceThumbnail.vue';
import { sourceCategoryLabel, sourceCategoryTone } from './sourcePresentation';
import { useBreakpoint } from '@/composables/useBreakpoint';
import { useDialog } from '@/composables/useDialog';
import { useToast } from '@/composables/useToast';
import { useSessionStore } from '@/stores/sessions';
import { useSourceStore, type SourceCategory } from '@/stores/sources';
import { api, type MediaSourceItem } from '@/services/api';
import { formatBytes, formatRelativeTime } from '@/design-system/utils';

const { t } = useI18n();
const sourceStore = useSourceStore();
const sessionStore = useSessionStore();
const dialog = useDialog();
const toast = useToast();
const { isMobile } = useBreakpoint();

const isLoading = ref(false);
const drawerOpen = ref(false);
const editDrawerOpen = ref(false);
const editingSource = ref<MediaSourceItem | null>(null);

function startEdit(source: MediaSourceItem): void {
  editingSource.value = source;
  editDrawerOpen.value = true;
}

interface CategoryDef {
  value: SourceCategory;
  label: string;
  emptyTitle: string;
  emptyHint: string;
}

const CATEGORY_DEFS = computed<CategoryDef[]>(() => [
  { value: 'all', label: t('sources.cat.allLabel'), emptyTitle: t('sources.cat.allEmptyTitle'), emptyHint: t('sources.cat.allEmptyHint') },
  { value: 'ppt', label: t('sources.cat.pptLabel'), emptyTitle: t('sources.cat.pptEmptyTitle'), emptyHint: t('sources.cat.pptEmptyHint') },
  { value: 'video', label: t('sources.cat.videoLabel'), emptyTitle: t('sources.cat.videoEmptyTitle'), emptyHint: t('sources.cat.videoEmptyHint') },
  { value: 'image', label: t('sources.cat.imageLabel'), emptyTitle: t('sources.cat.imageEmptyTitle'), emptyHint: t('sources.cat.imageEmptyHint') },
  { value: 'web', label: t('sources.cat.webLabel'), emptyTitle: t('sources.cat.webEmptyTitle'), emptyHint: t('sources.cat.webEmptyHint') },
  { value: 'stream', label: t('sources.cat.streamLabel'), emptyTitle: t('sources.cat.streamEmptyTitle'), emptyHint: t('sources.cat.streamEmptyHint') },
]);

const navItems = computed<FTabsItem[]>(() =>
  CATEGORY_DEFS.value.map((def) => ({
    label: def.label,
    value: def.value,
    badge: sourceStore.countByCategory[def.value],
  })),
);

const activeCategoryDef = computed(
  () => CATEGORY_DEFS.value.find((def) => def.value === sourceStore.category) ?? CATEGORY_DEFS.value[0],
);

async function refresh(): Promise<void> {
  isLoading.value = true;
  try {
    await sourceStore.refresh();
  } catch (error) {
    toast.error(t('sources.loadFail'), error instanceof Error ? error.message : t('common.retry'));
  } finally {
    isLoading.value = false;
  }
}

async function openToWindow(source: MediaSourceItem, windowId: number): Promise<void> {
  try {
    await sessionStore.openSource(windowId, source.id, true);
    toast.success(t('sources.openedOk', { id: windowId, name: source.name }));
  } catch (error) {
    toast.error(t('sources.openFail'), error instanceof Error ? error.message : t('common.retry'));
  }
}

function downloadSource(source: MediaSourceItem): void {
  // 文件型源走后端 download 接口；非文件源（web、stream）跳过菜单已禁用
  const url = api.downloadSourceUrl(source.id);
  window.open(url, '_blank');
}

async function deleteSource(source: MediaSourceItem): Promise<void> {
  const confirmed = await dialog.danger({
    title: t('sources.deleteTitle', { name: source.name }),
    description: t('sources.deleteDesc'),
    confirmLabel: t('sources.deleteSource'),
  });
  if (!confirmed) return;
  try {
    await sourceStore.deleteSource(source.id);
    toast.success(t('sources.deletedOk'));
  } catch (error) {
    toast.error(t('sources.deleteFail'), error instanceof Error ? error.message : t('common.retry'));
  }
}

function buildRowMenu(source: MediaSourceItem): FMenuGroup[] {
  const isFileBased = !!source.file_size && source.file_size > 0;
  return [
    {
      label: t('sources.openToWindow'),
      items: [1, 2, 3, 4].map((windowId) => ({
        label: t('sources.window', { id: windowId }),
        icon: 'open_24_regular',
        onTrigger: () => openToWindow(source, windowId),
      })),
    },
    {
      items: [
        {
          label: t('common.edit'),
          icon: 'edit_24_regular',
          onTrigger: () => startEdit(source),
        },
        {
          label: t('sources.download'),
          icon: 'arrow_download_24_regular',
          disabled: !isFileBased,
          hint: isFileBased ? undefined : t('sources.downloadDisabledHint'),
          onTrigger: () => downloadSource(source),
        },
        {
          label: t('sources.deleteSource'),
          icon: 'delete_24_regular',
          danger: true,
          onTrigger: () => deleteSource(source),
        },
      ],
    },
  ];
}

function setCategory(value: SourceCategory): void {
  sourceStore.setCategory(value);
}

const totalCaption = computed(() => {
  const count = sourceStore.filtered.length;
  const totalBytes = sourceStore.filtered.reduce((acc, item) => acc + (item.file_size || 0), 0);
  if (totalBytes <= 0) return t('sources.countOnly', { n: count });
  return t('sources.countWithSize', { n: count, size: formatBytes(totalBytes) });
});
</script>

<template>
  <div class="sources-view">
    <header class="sources-view__toolbar">
      <div class="sources-view__heading">
        <h2 class="sources-view__title">{{ t('sources.title') }}</h2>
        <p class="sources-view__caption">{{ totalCaption }}</p>
      </div>
      <div class="sources-view__actions">
        <FInput :model-value="sourceStore.searchKeyword" :placeholder="t('sources.searchPlaceholder')" :aria-label="t('sources.searchPlaceholder')"
          clearable @update:modelValue="sourceStore.setSearchKeyword">
          <template #prefix>
            <FIcon name="search_20_regular" />
          </template>
        </FInput>
        <FButton appearance="secondary" icon-start="arrow_clockwise_20_regular" icon-only :aria-label="t('sources.refreshAria')"
          :loading="isLoading" @click="refresh" />
        <FButton appearance="primary" icon-start="add_24_regular" @click="drawerOpen = true">
          {{ t('sources.addSource') }}
        </FButton>
      </div>
    </header>

    <div v-if="isMobile" class="sources-view__mobile-pills">
      <FTabs :model-value="sourceStore.category" :items="navItems" appearance="pill" full-width :aria-label="t('sources.sourceTypeAria')"
        @update:modelValue="(value) => setCategory(value as SourceCategory)" />
    </div>

    <div class="sources-view__layout" :class="{ 'sources-view__layout--mobile': isMobile }">
      <aside v-if="!isMobile" class="sources-view__nav" :aria-label="t('sources.sourceFilterAria')">
        <button v-for="def in CATEGORY_DEFS" :key="def.value" type="button" class="sources-view__nav-item"
          :class="{ 'sources-view__nav-item--active': sourceStore.category === def.value }"
          @click="setCategory(def.value)">
          <span class="sources-view__nav-label">{{ def.label }}</span>
          <span class="sources-view__nav-badge">{{ sourceStore.countByCategory[def.value] }}</span>
        </button>
      </aside>

      <section class="sources-view__main">
        <FCard padding="none">
          <template v-if="isLoading && sourceStore.filtered.length === 0">
            <div class="sources-view__skeletons">
              <div v-for="line in 6" :key="line" class="sources-view__skeleton-row">
                <FSkeleton shape="text" width="40%" />
                <FSkeleton shape="text" width="20%" />
                <FSkeleton shape="text" width="15%" />
                <FSkeleton shape="text" width="15%" />
              </div>
            </div>
          </template>

          <template v-else-if="sourceStore.filtered.length === 0">
            <FEmpty :title="activeCategoryDef.emptyTitle" :description="activeCategoryDef.emptyHint"
              icon="library_24_regular">
              <template #actions>
                <FButton appearance="primary" icon-start="add_24_regular" @click="drawerOpen = true">
                  {{ t('sources.addSource') }}
                </FButton>
              </template>
            </FEmpty>
          </template>

          <template v-else-if="!isMobile">
            <table class="sources-view__table">
              <thead>
                <tr>
                  <th scope="col">{{ t('sources.colName') }}</th>
                  <th scope="col">{{ t('sources.colType') }}</th>
                  <th scope="col" class="sources-view__col--num">{{ t('sources.colSize') }}</th>
                  <th scope="col">{{ t('sources.colUpdated') }}</th>
                  <th scope="col" class="sources-view__col--actions">{{ t('sources.colActions') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="source in sourceStore.filtered" :key="source.id">
                  <td>
                    <div class="sources-view__name-cell">
                      <SourceThumbnail :source="source" size="comfortable" />
                      <div>
                        <p class="sources-view__name">{{ source.name }}</p>
                        <p v-if="source.uri" class="sources-view__uri">{{ source.uri }}</p>
                      </div>
                    </div>
                  </td>
                  <td>
                    <FTag :tone="sourceCategoryTone(source)">{{ sourceCategoryLabel(source) }}</FTag>
                    <FTag v-if="!source.is_available" tone="error" class="sources-view__chip">
                      {{ t('sources.offline') }}
                    </FTag>
                  </td>
                  <td class="sources-view__col--num">{{ source.file_size ? formatBytes(source.file_size) : t('common.none') }}</td>
                  <td>{{ formatRelativeTime(source.created_at) }}</td>
                  <td class="sources-view__col--actions">
                    <FMenu :groups="buildRowMenu(source)" trigger-icon="more_horizontal_20_regular" />
                  </td>
                </tr>
              </tbody>
            </table>
          </template>

          <template v-else>
            <div class="sources-view__cards">
              <FCard v-for="source in sourceStore.filtered" :key="source.id" padding="compact">
                <template #title>
                  <div class="sources-view__card-title">
                    <SourceThumbnail :source="source" />
                    <span>{{ source.name }}</span>
                  </div>
                </template>
                <template #actions>
                  <FMenu :groups="buildRowMenu(source)" trigger-icon="more_horizontal_24_regular" />
                </template>
                <div class="sources-view__card-meta">
                  <FTag :tone="sourceCategoryTone(source)">{{ sourceCategoryLabel(source) }}</FTag>
                  <span v-if="source.file_size">{{ formatBytes(source.file_size) }}</span>
                  <span>{{ formatRelativeTime(source.created_at) }}</span>
                </div>
                <FMessageBar v-if="!source.is_available" tone="error" :dismissible="false">
                  {{ t('sources.unavailableCard') }}
                </FMessageBar>
              </FCard>
            </div>
          </template>
        </FCard>
      </section>
    </div>

    <AddSourceDrawer v-model:open="drawerOpen" @added="refresh" />
    <EditSourceDrawer v-model:open="editDrawerOpen" :source="editingSource" @updated="refresh" />
  </div>
</template>

<style scoped src="./SourcesView.css"></style>
