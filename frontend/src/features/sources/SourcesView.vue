<script setup lang="ts">
/**
 * 媒体源管理：
 *   - 桌面：左侧类型 NavList + 右侧 DetailList；
 *   - 移动：顶部类型 Pills（横滑） + 卡片列表 + 右下 FAB（添加源 Sheet）。
 *
 * 行末菜单只保留：打开到窗口 1/2/3/4、编辑、下载（仅文件型）、删除。
 */
import { computed, h, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import {
  NAlert,
  NButton,
  NCard,
  NDropdown,
  NEmpty,
  NInput,
  NModal,
  NSkeleton,
  NTabs,
  NTabPane,
  NTag,
  type DropdownOption,
} from 'naive-ui';

import FIcon from '@/design-system/FIcon.vue';
import AddSourceDrawer from './AddSourceDrawer.vue';
import EditSourceDrawer from './EditSourceDrawer.vue';
import SourceThumbnail from './SourceThumbnail.vue';
import { sourceCategoryLabel, sourceCategoryTone } from './sourcePresentation';
import { useBreakpoint } from '@/composables/useBreakpoint';
import { useDialog } from '@/composables/useDialog';
import { useToast } from '@/composables/useToast';
import { useBackgroundAudioStore } from '@/stores/backgroundAudio';
import { useSessionStore } from '@/stores/sessions';
import { useSourceStore, type SourceCategory } from '@/stores/sources';
import { api, type MediaFolderItem, type MediaSourceItem } from '@/services/api';
import { formatBytes, formatRelativeTime } from '@/design-system/utils';

const { t } = useI18n();
const sourceStore = useSourceStore();
const backgroundAudioStore = useBackgroundAudioStore();
const sessionStore = useSessionStore();
const dialog = useDialog();
const toast = useToast();
const { isMobile } = useBreakpoint();

const isLoading = ref(false);
const drawerOpen = ref(false);
const editDrawerOpen = ref(false);
const editingSource = ref<MediaSourceItem | null>(null);
const newFolderDialogOpen = ref(false);
const newFolderName = ref('');
const creatingFolder = ref(false);

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
  { value: 'audio', label: t('sources.cat.audioLabel'), emptyTitle: t('sources.cat.audioEmptyTitle'), emptyHint: t('sources.cat.audioEmptyHint') },
  { value: 'image', label: t('sources.cat.imageLabel'), emptyTitle: t('sources.cat.imageEmptyTitle'), emptyHint: t('sources.cat.imageEmptyHint') },
  { value: 'web', label: t('sources.cat.webLabel'), emptyTitle: t('sources.cat.webEmptyTitle'), emptyHint: t('sources.cat.webEmptyHint') },
  { value: 'stream', label: t('sources.cat.streamLabel'), emptyTitle: t('sources.cat.streamEmptyTitle'), emptyHint: t('sources.cat.streamEmptyHint') },
]);

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
  if (!source.is_available) {
    toast.warning(t('sources.offline'), t('sources.unavailableCard'));
    return;
  }
  try {
    await sessionStore.openSource(windowId, source.id, true);
    toast.success(t('sources.openedOk', { id: windowId, name: source.name }));
  } catch (error) {
    toast.error(t('sources.openFail'), error instanceof Error ? error.message : t('common.retry'));
  }
}

async function playAsBackgroundAudio(source: MediaSourceItem): Promise<void> {
  try {
    await backgroundAudioStore.playSource(source.id);
    toast.success(t('sources.backgroundAudioPlayOk', { name: source.name }));
  } catch (error) {
    toast.error(t('sources.backgroundAudioFail'), error instanceof Error ? error.message : t('common.retry'));
  }
}

async function addToBackgroundAudio(source: MediaSourceItem): Promise<void> {
  try {
    await backgroundAudioStore.addSource(source.id);
    toast.success(t('sources.backgroundAudioAddOk'));
  } catch (error) {
    toast.error(t('sources.backgroundAudioFail'), error instanceof Error ? error.message : t('common.retry'));
  }
}

function downloadSource(source: MediaSourceItem): void {
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

function renderIcon(name: string) {
  return () => h(FIcon, { name, size: 18 });
}

function buildRowMenu(source: MediaSourceItem): DropdownOption[] {
  const isFileBased = !!source.file_size && source.file_size > 0;
  const openOptions: DropdownOption[] = source.source_type === 'audio'
    ? [
      {
        label: t('sources.playAsBackgroundAudio'),
        key: 'play-background-audio',
        icon: renderIcon('play_24_regular'),
        props: { onClick: () => playAsBackgroundAudio(source) },
      },
      {
        label: t('sources.addToBackgroundAudio'),
        key: 'add-background-audio',
        icon: renderIcon('music_note_2_24_regular'),
        props: { onClick: () => addToBackgroundAudio(source) },
      },
    ]
    : [
      {
        type: 'group',
        label: t('sources.openToWindow'),
        key: 'open-group',
        disabled: !source.is_available,
        children: [1, 2, 3, 4].map((windowId) => ({
          label: t('sources.window', { id: windowId }),
          key: `open-${windowId}`,
          icon: renderIcon('open_24_regular'),
          props: { onClick: () => openToWindow(source, windowId) },
        })),
      },
    ];
  return [
    ...openOptions,
    { type: 'divider', key: 'divider-1' },
    {
      label: t('common.edit'),
      key: 'edit',
      icon: renderIcon('edit_24_regular'),
      props: { onClick: () => startEdit(source) },
    },
    {
      label: t('sources.moveToFolder'),
      key: 'move-to',
      icon: renderIcon('folder_24_regular'),
      children: buildMoveToFolderOptions(source),
    },
    {
      label: t('sources.download'),
      key: 'download',
      icon: renderIcon('arrow_download_24_regular'),
      disabled: !isFileBased,
      props: { onClick: () => isFileBased && downloadSource(source) },
    },
    {
      label: t('sources.deleteSource'),
      key: 'delete',
      icon: renderIcon('delete_24_regular'),
      props: {
        onClick: () => deleteSource(source),
        style: 'color: var(--colorStatusDangerForeground1);',
      },
    },
  ];
}

function activeWindowLabel(sourceId: number): string {
  const windows = sessionStore.sessions
    .filter((session) => session.source_id === sourceId)
    .map((session) => session.window_id)
    .sort((left, right) => left - right)
    .join('、');
  return windows ? t('sources.onAirWindows', { windows }) : '';
}

function setCategory(value: SourceCategory): void {
  sourceStore.setCategory(value);
}

function handleMenuSelect(_key: string, option: DropdownOption): void {
  const handler = (option.props as { onClick?: () => void } | undefined)?.onClick;
  handler?.();
}

const totalCaption = computed(() => {
  const count = sourceStore.filtered.length;
  const totalBytes = sourceStore.filtered.reduce((acc, item) => acc + (item.file_size || 0), 0);
  if (totalBytes <= 0) return t('sources.countOnly', { n: count });
  return t('sources.countWithSize', { n: count, size: formatBytes(totalBytes) });
});

const searchModel = computed({
  get: () => sourceStore.searchKeyword,
  set: (value: string) => sourceStore.setSearchKeyword(value),
});

const categoryModel = computed({
  get: () => sourceStore.category,
  set: (value: string) => setCategory(value as SourceCategory),
});

// ═══════════════════ 文件夹管理 ═══════════════════

const breadcrumbs = computed(() => sourceStore.folderBreadcrumbs);
const childFolders = computed(() => sourceStore.childFolders);

async function navigateToFolder(folderId: number | null): Promise<void> {
  isLoading.value = true;
  try {
    sourceStore.setCurrentFolder(folderId);
    await sourceStore.refresh();
  } catch (error) {
    toast.error(t('sources.folderFail'), error instanceof Error ? error.message : t('common.retry'));
  } finally {
    isLoading.value = false;
  }
}

async function createFolder(): Promise<void> {
  const name = newFolderName.value.trim();
  if (!name) return;
  creatingFolder.value = true;
  try {
    await sourceStore.createFolder(name, sourceStore.currentFolderId);
    toast.success(t('sources.folderCreatedOk'));
    newFolderName.value = '';
    newFolderDialogOpen.value = false;
  } catch (error) {
    toast.error(t('sources.folderFail'), error instanceof Error ? error.message : t('common.retry'));
  } finally {
    creatingFolder.value = false;
  }
}

async function renameFolder(folder: MediaFolderItem): Promise<void> {
  // 使用简单的 prompt 对话框重命名
  const newName = window.prompt(t('sources.renameFolder'), folder.name);
  if (newName === null || newName.trim() === folder.name) return;
  try {
    await sourceStore.renameFolder(folder.id, newName.trim());
    toast.success(t('sources.folderRenamedOk'));
  } catch (error) {
    toast.error(t('sources.folderFail'), error instanceof Error ? error.message : t('common.retry'));
  }
}

async function deleteFolderConfirm(folder: MediaFolderItem): Promise<void> {
  const confirmed = await dialog.danger({
    title: t('sources.deleteFolderTitle', { name: folder.name }),
    description: t('sources.deleteFolderDesc'),
    confirmLabel: t('sources.deleteFolderOk'),
  });
  if (!confirmed) return;
  try {
    await sourceStore.deleteFolder(folder.id);
    toast.success(t('sources.folderDeletedOk'));
  } catch (error) {
    toast.error(t('sources.folderFail'), error instanceof Error ? error.message : t('common.retry'));
  }
}

function buildFolderMenu(folder: MediaFolderItem): DropdownOption[] {
  return [
    {
      label: t('sources.renameFolder'),
      key: 'rename-folder',
      icon: renderIcon('edit_24_regular'),
      props: { onClick: () => renameFolder(folder) },
    },
    {
      label: t('sources.deleteFolder'),
      key: 'delete-folder',
      icon: renderIcon('delete_24_regular'),
      props: {
        onClick: () => deleteFolderConfirm(folder),
        style: 'color: var(--colorStatusDangerForeground1);',
      },
    },
  ];
}

/** 构建可移动到的文件夹列表（排除源当前所在文件夹）。 */
function buildMoveToFolderOptions(source: MediaSourceItem): DropdownOption[] {
  const allFolders = sourceStore.folders;
  const options: DropdownOption[] = [
    {
      label: t('sources.moveToRoot'),
      key: 'move-root',
      icon: renderIcon('folder_24_regular'),
      disabled: source.folder_id === null,
      props: { onClick: () => moveSourceToFolder(source, null) },
    },
  ];
  for (const folder of allFolders) {
    if (folder.id === source.folder_id) continue;
    options.push({
      label: folder.name,
      key: `move-${folder.id}`,
      icon: renderIcon('folder_24_regular'),
      props: { onClick: () => moveSourceToFolder(source, folder.id) },
    });
  }
  return options;
}

async function moveSourceToFolder(source: MediaSourceItem, folderId: number | null): Promise<void> {
  try {
    await sourceStore.moveSource(source.id, folderId);
    const folderName = sourceStore.folders.find((folder) => folder.id === folderId)?.name;
    toast.success(folderId === null
      ? t('sources.movedRootOk')
      : t('sources.movedOk', { name: folderName ?? '' }));
    await refresh();
  } catch (error) {
    toast.error(t('sources.moveFail'), error instanceof Error ? error.message : t('common.retry'));
  }
}
</script>

<template>
  <div class="sources-view">
    <header class="sources-view__toolbar">
      <div class="sources-view__heading">
        <h2 class="sources-view__title">{{ t('sources.title') }}</h2>
        <p class="sources-view__caption">{{ totalCaption }}</p>
      </div>
      <div class="sources-view__actions">
        <n-input
          v-model:value="searchModel"
          :placeholder="t('sources.searchPlaceholder')"
          :aria-label="t('sources.searchPlaceholder')"
          clearable
        >
          <template #prefix>
            <FIcon name="search_20_regular" />
          </template>
        </n-input>
        <n-button :loading="isLoading" :aria-label="t('sources.refreshAria')" @click="refresh">
          <template #icon><FIcon name="arrow_clockwise_20_regular" /></template>
        </n-button>
        <n-button type="primary" @click="drawerOpen = true">
          <template #icon><FIcon name="add_24_regular" /></template>
          {{ t('sources.addSource') }}
        </n-button>
      </div>
    </header>

    <div v-if="isMobile" class="sources-view__mobile-pills">
      <n-tabs v-model:value="categoryModel" type="segment" :aria-label="t('sources.sourceTypeAria')">
        <n-tab-pane v-for="def in CATEGORY_DEFS" :key="def.value" :name="def.value" :tab="`${def.label} (${sourceStore.countByCategory[def.value]})`" />
      </n-tabs>
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
        <!-- 文件夹面包屑 + 新建文件夹 -->
        <div class="sources-view__folder-bar">
          <nav class="sources-view__breadcrumb" :aria-label="t('sources.folderBreadcrumbAria')">
            <button type="button" class="sources-view__breadcrumb-item"
              :class="{ 'sources-view__breadcrumb-item--active': sourceStore.currentFolderId === null }"
              @click="navigateToFolder(null)">
              <FIcon name="home_24_regular" :size="16" />
              <span>{{ t('sources.folderRoot') }}</span>
            </button>
            <template v-for="crumb in breadcrumbs" :key="crumb.id">
              <FIcon name="chevron_right_24_regular" :size="14" class="sources-view__breadcrumb-sep" />
              <button type="button" class="sources-view__breadcrumb-item"
                :class="{ 'sources-view__breadcrumb-item--active': crumb.id === sourceStore.currentFolderId }"
                @click="navigateToFolder(crumb.id)">
                {{ crumb.name }}
              </button>
            </template>
          </nav>
          <n-button size="small" quaternary :aria-label="t('sources.newFolder')" @click="newFolderDialogOpen = true">
            <template #icon><FIcon name="add_24_regular" /></template>
            {{ t('sources.newFolderOkShort') }}
          </n-button>
        </div>

        <!-- 子文件夹列表 -->
        <div v-if="childFolders.length > 0" class="sources-view__folders">
          <div v-for="folder in childFolders" :key="folder.id" class="sources-view__folder-card" role="button"
            tabindex="0" @click="navigateToFolder(folder.id)" @keyup.enter="navigateToFolder(folder.id)">
            <FIcon name="folder_24_regular" :size="28" />
            <span class="sources-view__folder-name">{{ folder.name }}</span>
            <n-dropdown trigger="click" placement="bottom-end" :options="buildFolderMenu(folder)"
              @select="handleMenuSelect" @click.stop>
              <n-button quaternary circle size="tiny" :aria-label="t('common.edit')">
                <template #icon><FIcon name="more_horizontal_20_regular" :size="16" /></template>
              </n-button>
            </n-dropdown>
          </div>
        </div>
        <n-card content-style="padding:0">
          <template v-if="isLoading && sourceStore.filtered.length === 0">
            <div class="sources-view__skeletons">
              <div v-for="line in 6" :key="line" class="sources-view__skeleton-row">
                <n-skeleton text width="40%" />
                <n-skeleton text width="20%" />
                <n-skeleton text width="15%" />
                <n-skeleton text width="15%" />
              </div>
            </div>
          </template>

          <template v-else-if="sourceStore.filtered.length === 0">
            <n-empty :description="sourceStore.searchKeyword.trim() ? t('sources.searchEmpty') : activeCategoryDef.emptyHint">
              <template #icon>
                <FIcon name="library_24_regular" />
              </template>
              <template #extra>
                <n-button type="primary" @click="drawerOpen = true">
                  <template #icon><FIcon name="add_24_regular" /></template>
                  {{ t('sources.addSource') }}
                </n-button>
              </template>
            </n-empty>
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
                        <n-tag v-if="activeWindowLabel(source.id)" type="success" round size="small" class="sources-view__on-air">
                          {{ activeWindowLabel(source.id) }}
                        </n-tag>
                        <p v-if="source.uri" class="sources-view__uri">{{ source.uri }}</p>
                      </div>
                    </div>
                  </td>
                  <td>
                    <n-tag :type="sourceCategoryTone(source)" round size="small">{{ sourceCategoryLabel(source) }}</n-tag>
                    <n-tag v-if="!source.is_available" type="error" round size="small" class="sources-view__chip">
                      {{ t('sources.offline') }}
                    </n-tag>
                  </td>
                  <td class="sources-view__col--num">{{ source.file_size ? formatBytes(source.file_size) : t('common.none') }}</td>
                  <td>{{ formatRelativeTime(source.created_at) }}</td>
                  <td class="sources-view__col--actions">
                    <n-dropdown
                      trigger="click"
                      placement="bottom-end"
                      :options="buildRowMenu(source)"
                      @select="handleMenuSelect"
                    >
                      <n-button quaternary circle :aria-label="t('sources.rowActionsAria', { name: source.name })">
                        <template #icon><FIcon name="more_horizontal_20_regular" /></template>
                      </n-button>
                    </n-dropdown>
                  </td>
                </tr>
              </tbody>
            </table>
          </template>

          <template v-else>
            <div class="sources-view__cards">
              <n-card v-for="source in sourceStore.filtered" :key="source.id" size="small">
                <template #header>
                  <div class="sources-view__card-title">
                    <SourceThumbnail :source="source" />
                    <span>{{ source.name }}</span>
                  </div>
                </template>
                <template #header-extra>
                  <n-dropdown
                    trigger="click"
                    placement="bottom-end"
                    :options="buildRowMenu(source)"
                    @select="handleMenuSelect"
                  >
                    <n-button quaternary circle :aria-label="t('sources.rowActionsAria', { name: source.name })">
                      <template #icon><FIcon name="more_horizontal_24_regular" /></template>
                    </n-button>
                  </n-dropdown>
                </template>
                <div class="sources-view__card-meta">
                  <n-tag :type="sourceCategoryTone(source)" round size="small">{{ sourceCategoryLabel(source) }}</n-tag>
                  <n-tag v-if="activeWindowLabel(source.id)" type="success" round size="small">
                    {{ activeWindowLabel(source.id) }}
                  </n-tag>
                  <span v-if="source.file_size">{{ formatBytes(source.file_size) }}</span>
                  <span>{{ formatRelativeTime(source.created_at) }}</span>
                </div>
                <n-alert v-if="!source.is_available" type="error" :closable="false">
                  {{ t('sources.unavailableCard') }}
                </n-alert>
              </n-card>
            </div>
          </template>
        </n-card>
      </section>
    </div>

    <!-- 新建文件夹对话框 -->
    <n-modal v-model:show="newFolderDialogOpen" preset="dialog" :title="t('sources.newFolder')"
      :positive-text="t('sources.newFolderOk')" :negative-text="t('common.cancel')"
      :loading="creatingFolder" @positive-click="createFolder">
      <n-input v-model:value="newFolderName" :placeholder="t('sources.newFolderPlaceholder')"
        :aria-label="t('sources.newFolderName')" @keyup.enter="createFolder" />
    </n-modal>

    <AddSourceDrawer v-model:open="drawerOpen" :folderId="sourceStore.currentFolderId" @added="refresh" />
    <EditSourceDrawer v-model:open="editDrawerOpen" :source="editingSource" @updated="refresh" />
  </div>
</template>

<style scoped src="./SourcesView.css"></style>
