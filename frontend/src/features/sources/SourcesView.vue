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
import type { FTabsItem, FMenuGroup, TagTone } from '@/design-system';
import AddSourceDrawer from './AddSourceDrawer.vue';
import EditSourceDrawer from './EditSourceDrawer.vue';
import { useBreakpoint } from '@/composables/useBreakpoint';
import { useDialog } from '@/composables/useDialog';
import { useToast } from '@/composables/useToast';
import { useSessionStore } from '@/stores/sessions';
import { useSourceStore, type SourceCategory } from '@/stores/sources';
import { api, type MediaSourceItem } from '@/services/api';
import { formatBytes, formatRelativeTime } from '@/design-system/utils';

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

const CATEGORY_DEFS: CategoryDef[] = [
  { value: 'all', label: '全部源', emptyTitle: '暂无媒体源', emptyHint: '上传文件或注册网页源后，可在这里浏览、打开到窗口或加入预案。' },
  { value: 'ppt', label: 'PPT 源', emptyTitle: '暂无 PPT 源', emptyHint: '上传 PPT 后，可在这里浏览、打开到窗口或加入预案。' },
  { value: 'video', label: '视频源', emptyTitle: '暂无视频源', emptyHint: '上传视频后，可在这里浏览、打开到窗口或加入预案。' },
  { value: 'image', label: '图片源', emptyTitle: '暂无图片源', emptyHint: '上传图片后，可在这里浏览、打开到窗口或加入预案。' },
  { value: 'web', label: '网页源', emptyTitle: '暂无网页源', emptyHint: '注册 URL 或 ip:port 网页后，可在这里浏览、打开到窗口或加入预案。' },
  { value: 'stream', label: '直播源', emptyTitle: '暂无直播源', emptyHint: '直播源由后端推流注入，离线超过 1 小时会自动清理。' },
];

const navItems = computed<FTabsItem[]>(() =>
  CATEGORY_DEFS.map((def) => ({
    label: def.label,
    value: def.value,
    badge: sourceStore.countByCategory[def.value],
  })),
);

const activeCategoryDef = computed(
  () => CATEGORY_DEFS.find((def) => def.value === sourceStore.category) ?? CATEGORY_DEFS[0],
);

async function refresh(): Promise<void> {
  isLoading.value = true;
  try {
    await sourceStore.refresh();
  } catch (error) {
    toast.error('媒体源列表加载失败', error instanceof Error ? error.message : '请稍后重试');
  } finally {
    isLoading.value = false;
  }
}

async function openToWindow(source: MediaSourceItem, windowId: number): Promise<void> {
  try {
    await sessionStore.openSource(windowId, source.id, true);
    toast.success(`已在窗口 ${windowId} 打开 ${source.name}`);
  } catch (error) {
    toast.error('打开到窗口失败', error instanceof Error ? error.message : '请稍后重试');
  }
}

function downloadSource(source: MediaSourceItem): void {
  // 文件型源走后端 download 接口；非文件源（web、stream）跳过菜单已禁用
  const url = api.downloadSourceUrl(source.id);
  window.open(url, '_blank');
}

async function deleteSource(source: MediaSourceItem): Promise<void> {
  const confirmed = await dialog.danger({
    title: `删除 ${source.name}？`,
    description: '该源会被永久移除；正在使用此源的窗口将停止播放。此操作不可恢复。',
    confirmLabel: '删除源',
  });
  if (!confirmed) return;
  try {
    await sourceStore.deleteSource(source.id);
    toast.success('源已删除');
  } catch (error) {
    toast.error('删除失败', error instanceof Error ? error.message : '请稍后重试');
  }
}

function buildRowMenu(source: MediaSourceItem): FMenuGroup[] {
  const isFileBased = !!source.file_size && source.file_size > 0;
  return [
    {
      label: '打开到窗口',
      items: [1, 2, 3, 4].map((windowId) => ({
        label: `窗口 ${windowId}`,
        icon: 'open_24_regular',
        onTrigger: () => openToWindow(source, windowId),
      })),
    },
    {
      items: [
        {
          label: '编辑',
          icon: 'edit_24_regular',
          onTrigger: () => startEdit(source),
        },
        {
          label: '下载',
          icon: 'arrow_download_24_regular',
          disabled: !isFileBased,
          hint: isFileBased ? undefined : '该源为非文件源，无法下载',
          onTrigger: () => downloadSource(source),
        },
        {
          label: '删除源',
          icon: 'delete_24_regular',
          danger: true,
          onTrigger: () => deleteSource(source),
        },
      ],
    },
  ];
}

function categoryToneOf(source: MediaSourceItem): TagTone {
  const cat = sourceStore.resolveCategory(source.source_type);
  switch (cat) {
    case 'ppt':
      return 'info';
    case 'video':
      return 'success';
    case 'image':
      return 'subtle';
    case 'web':
      return 'subtle';
    case 'stream':
      return source.is_available ? 'warning' : 'error';
    default:
      return 'subtle';
  }
}

function categoryLabel(source: MediaSourceItem): string {
  const cat = sourceStore.resolveCategory(source.source_type);
  switch (cat) {
    case 'ppt':
      return 'PPT';
    case 'video':
      return '视频';
    case 'image':
      return '图片';
    case 'web':
      return '网页';
    case 'stream':
      return '直播';
    default:
      return '其它';
  }
}

function categoryIcon(source: MediaSourceItem): string {
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

function setCategory(value: SourceCategory): void {
  sourceStore.setCategory(value);
}

const totalCaption = computed(() => {
  const count = sourceStore.filtered.length;
  const totalBytes = sourceStore.filtered.reduce((acc, item) => acc + (item.file_size || 0), 0);
  if (totalBytes <= 0) return `共 ${count} 项`;
  return `共 ${count} 项 · 占用 ${formatBytes(totalBytes)}`;
});
</script>

<template>
  <div class="sources-view">
    <header class="sources-view__toolbar">
      <div class="sources-view__heading">
        <h2 class="sources-view__title">媒体源</h2>
        <p class="sources-view__caption">{{ totalCaption }}</p>
      </div>
      <div class="sources-view__actions">
        <FInput :model-value="sourceStore.searchKeyword" placeholder="搜索源名称或 URL" aria-label="搜索源名称或 URL"
          @update:modelValue="sourceStore.setSearchKeyword">
          <template #prefix>
            <FIcon name="search_20_regular" />
          </template>
        </FInput>
        <FButton appearance="secondary" icon-start="arrow_clockwise_20_regular" icon-only aria-label="刷新源列表"
          :loading="isLoading" @click="refresh" />
        <FButton appearance="primary" icon-start="add_24_regular" @click="drawerOpen = true">
          添加源
        </FButton>
      </div>
    </header>

    <div v-if="isMobile" class="sources-view__mobile-pills">
      <FTabs :model-value="sourceStore.category" :items="navItems" appearance="pill" full-width aria-label="源类型"
        @update:modelValue="(value) => setCategory(value as SourceCategory)" />
    </div>

    <div class="sources-view__layout" :class="{ 'sources-view__layout--mobile': isMobile }">
      <aside v-if="!isMobile" class="sources-view__nav" aria-label="源类型筛选">
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
                  添加源
                </FButton>
              </template>
            </FEmpty>
          </template>

          <template v-else-if="!isMobile">
            <table class="sources-view__table">
              <thead>
                <tr>
                  <th scope="col">名称</th>
                  <th scope="col">类型</th>
                  <th scope="col" class="sources-view__col--num">大小</th>
                  <th scope="col">更新时间</th>
                  <th scope="col" class="sources-view__col--actions">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="source in sourceStore.filtered" :key="source.id">
                  <td>
                    <div class="sources-view__name-cell">
                      <FIcon class="sources-view__row-icon" :name="categoryIcon(source)" />
                      <div>
                        <p class="sources-view__name">{{ source.name }}</p>
                        <p v-if="source.uri" class="sources-view__uri">{{ source.uri }}</p>
                      </div>
                    </div>
                  </td>
                  <td>
                    <FTag :tone="categoryToneOf(source)">{{ categoryLabel(source) }}</FTag>
                    <FTag v-if="!source.is_available" tone="error" class="sources-view__chip">
                      离线
                    </FTag>
                  </td>
                  <td class="sources-view__col--num">{{ source.file_size ? formatBytes(source.file_size) : '—' }}</td>
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
                    <FIcon class="sources-view__row-icon" :name="categoryIcon(source)" />
                    <span>{{ source.name }}</span>
                  </div>
                </template>
                <template #actions>
                  <FMenu :groups="buildRowMenu(source)" trigger-icon="more_horizontal_24_regular" />
                </template>
                <div class="sources-view__card-meta">
                  <FTag :tone="categoryToneOf(source)">{{ categoryLabel(source) }}</FTag>
                  <span v-if="source.file_size">{{ formatBytes(source.file_size) }}</span>
                  <span>{{ formatRelativeTime(source.created_at) }}</span>
                </div>
                <FMessageBar v-if="!source.is_available" tone="error" :dismissible="false">
                  当前不可用，请检查源文件或推流状态。
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

<style scoped>
.sources-view {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-l);
}

/*
 * sticky toolbar 锚定到 .app-shell__content 滚动容器的 content-edge.top（已位于 AppShell
 * title-bar 之下并叠加 24 px 内容 padding），故 top 取 0 即"贴在内容区顶端"。
 * 历史值 56px 会让 toolbar 相对 scrollport 再下移 56 px，与下方 NavList 第一项产生
 * 视觉重叠，导致「全部源」按钮被遮挡。
 */
.sources-view__toolbar {
  position: sticky;
  top: 0;
  z-index: var(--z-sticky);
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--spacing-l);
  padding: var(--spacing-m) 0;
  background: var(--color-background-canvas);
  flex-wrap: wrap;
}

.sources-view__heading {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.sources-view__title {
  margin: 0;
  font-size: var(--type-title2-size);
  line-height: var(--type-title2-line);
  font-weight: 600;
}

.sources-view__caption {
  margin: 0;
  font-size: var(--type-caption1-size);
  color: var(--color-text-tertiary);
}

.sources-view__actions {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-s);
  flex-wrap: wrap;
  min-width: 320px;
}

.sources-view__actions :deep(.f-input) {
  width: 280px;
}

.sources-view__layout {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: var(--spacing-l);
  align-items: start;
}

.sources-view__layout--mobile {
  grid-template-columns: 1fr;
}

.sources-view__nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: var(--spacing-s);
  background: var(--color-background-card);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-large);
}

.sources-view__nav-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-s);
  padding: var(--spacing-s) var(--spacing-m);
  border-radius: var(--radius-medium);
  background: transparent;
  border: none;
  color: var(--color-text-secondary);
  font: inherit;
  cursor: pointer;
}

.sources-view__nav-item:hover {
  background: var(--color-background-subtle);
  color: var(--color-text-primary);
}

.sources-view__nav-item--active {
  background: var(--color-background-brand-selected);
  color: var(--color-text-brand);
  font-weight: 600;
}

.sources-view__nav-badge {
  min-width: 24px;
  text-align: center;
  font-size: var(--type-caption1-size);
  color: var(--color-text-tertiary);
}

.sources-view__nav-item--active .sources-view__nav-badge {
  color: var(--color-text-brand);
}

.sources-view__main {
  min-width: 0;
}

.sources-view__skeletons {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-s);
  padding: var(--spacing-l);
}

.sources-view__skeleton-row {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr;
  gap: var(--spacing-l);
}

.sources-view__table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--type-body1-size);
}

.sources-view__table th,
.sources-view__table td {
  text-align: left;
  padding: var(--spacing-m) var(--spacing-l);
  border-bottom: 1px solid var(--color-border-subtle);
  vertical-align: middle;
}

.sources-view__table th {
  background: var(--color-background-subtle);
  font-size: var(--type-caption1-size);
  font-weight: 600;
  color: var(--color-text-tertiary);
  position: sticky;
  top: 0;
  z-index: 1;
}

.sources-view__col--num {
  width: 110px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.sources-view__col--actions {
  width: 80px;
  text-align: right;
}

.sources-view__name-cell {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-s);
}

.sources-view__row-icon {
  width: 22px;
  height: 22px;
  color: var(--color-text-secondary);
}

.sources-view__name {
  margin: 0;
  font-weight: 600;
}

.sources-view__uri {
  margin: 0;
  font-size: var(--type-caption1-size);
  color: var(--color-text-tertiary);
  max-width: 320px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sources-view__chip {
  margin-left: var(--spacing-xs);
}

.sources-view__mobile-pills {
  position: sticky;
  top: 92px;
  z-index: var(--z-sticky);
  background: var(--color-background-canvas);
  padding: var(--spacing-xs) 0;
}

.sources-view__cards {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-s);
  padding: var(--spacing-s);
}

.sources-view__card-title {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-s);
}

.sources-view__card-meta {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-s);
  flex-wrap: wrap;
  color: var(--color-text-secondary);
  font-size: var(--type-caption1-size);
}

@media (max-width: 767px) {
  .sources-view__toolbar {
    top: 96px;
    flex-direction: column;
    align-items: stretch;
  }

  .sources-view__actions {
    flex-wrap: nowrap;
  }

  .sources-view__actions :deep(.f-input) {
    flex: 1 1 auto;
    width: auto;
    min-width: 0;
  }
}
</style>
