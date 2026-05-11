<script setup lang="ts">
/**
 * 显示控制页左侧「切换源」面板：
 *   - 顶部搜索 + 类型筛选 Pill；
 *   - List/Detail 风格列表，点击行直接打开到当前窗口；
 *   - 折叠的「上传并打开」区域：上传但不保存 / 上传并保存。
 */
import { computed, ref } from 'vue';

import {
  FButton,
  FCard,
  FField,
  FIcon,
  FInput,
  FProgress,
  FSpinner,
  FTabs,
  FTag,
} from '@/design-system';
import type { FTabsItem } from '@/design-system';
import { useToast } from '@/composables/useToast';
import { useSessionStore } from '@/stores/sessions';
import { useSourceStore, type SourceCategory } from '@/stores/sources';
import type { MediaSourceItem } from '@/services/api';
import SourceThumbnail from '../sources/SourceThumbnail.vue';
import { sourceCategoryLabel } from '../sources/sourcePresentation';

const props = defineProps<{ windowId: number }>();

const sourceStore = useSourceStore();
const sessionStore = useSessionStore();
const toast = useToast();

const filterValue = ref<SourceCategory>('all');
const searchKeyword = ref('');
const expanded = ref(false);
const fileToUpload = ref<File | null>(null);
const fileDisplayName = ref('');
const uploadProgress = ref(0);
const uploading = ref(false);
const uploadError = ref('');
const fileInputRef = ref<HTMLInputElement | null>(null);

const filterTabs: FTabsItem<SourceCategory>[] = [
  { label: '全部', value: 'all' },
  { label: 'PPT', value: 'ppt' },
  { label: '视频', value: 'video' },
  { label: '图片', value: 'image' },
  { label: '网页', value: 'web' },
  { label: '直播', value: 'stream' },
];

const filteredSources = computed<MediaSourceItem[]>(() => {
  const keyword = searchKeyword.value.trim().toLowerCase();
  return sourceStore.sources.filter((source) => {
    if (filterValue.value !== 'all' && sourceStore.resolveCategory(source.source_type) !== filterValue.value) {
      return false;
    }
    if (!keyword) return true;
    const hay = `${source.name} ${source.uri ?? ''} ${source.original_filename ?? ''}`.toLowerCase();
    return hay.includes(keyword);
  });
});

async function selectSource(source: MediaSourceItem): Promise<void> {
  try {
    await sessionStore.openSource(props.windowId, source.id, true);
    toast.success(`已打开 ${source.name}`);
  } catch (error) {
    toast.error('打开源失败', error instanceof Error ? error.message : '请稍后重试');
  }
}

function onFileSelect(event: Event): void {
  const target = event.target as HTMLInputElement;
  fileToUpload.value = target.files?.[0] ?? null;
}

async function uploadAndOpen(persist: boolean): Promise<void> {
  if (!fileToUpload.value) {
    uploadError.value = '请先选择要上传的文件';
    return;
  }
  uploading.value = true;
  uploadProgress.value = 0;
  uploadError.value = '';
  try {
    const result = await sourceStore.upload(fileToUpload.value, {
      name: fileDisplayName.value.trim() || undefined,
      isTemporary: !persist,
      onProgress: (percent) => {
        uploadProgress.value = percent;
      },
    });
    await sessionStore.openSource(props.windowId, result.id, true);
    toast.success(persist ? '已上传并打开' : '已上传（未保存）并打开', `源名称：${result.name}`);
    fileToUpload.value = null;
    fileDisplayName.value = '';
    if (fileInputRef.value) fileInputRef.value.value = '';
  } catch (error) {
    uploadError.value = error instanceof Error ? error.message : '上传失败，请稍后重试';
  } finally {
    uploading.value = false;
    uploadProgress.value = 0;
  }
}

const totalLabel = computed(() => `共 ${filteredSources.value.length} 项`);
</script>

<template>
  <FCard padding="compact" class="source-picker">
    <template #title>
      <span>切换源</span>
    </template>
    <template #actions>
      <span class="source-picker__count">{{ totalLabel }}</span>
    </template>

    <FInput v-model="searchKeyword" placeholder="搜索源名称或 URL" aria-label="搜索源">
      <template #prefix>
        <FIcon name="search_20_regular" />
      </template>
    </FInput>

    <FTabs v-model="filterValue" :items="filterTabs" appearance="pill" full-width aria-label="源类型筛选" />

    <ul class="source-picker__list">
      <li v-if="filteredSources.length === 0" class="source-picker__empty">
        没有符合条件的源；请调整筛选或上传新源。
      </li>
      <li v-for="source in filteredSources" :key="source.id" class="source-picker__item"
        :class="{ 'source-picker__item--unavailable': !source.is_available }" @click="selectSource(source)">
        <SourceThumbnail :source="source" />
        <div class="source-picker__meta">
          <p class="source-picker__name">{{ source.name }}</p>
          <p class="source-picker__sub">
            <FTag :tone="source.is_available ? 'subtle' : 'error'">
              {{ source.is_available ? sourceCategoryLabel(source) : '离线' }}
            </FTag>
          </p>
        </div>
      </li>
    </ul>

    <details class="source-picker__upload" :open="expanded"
      @toggle="expanded = ($event.target as HTMLDetailsElement).open">
      <summary class="source-picker__upload-summary">
        <FIcon name="arrow_upload_24_regular" />
        <span>上传并打开</span>
      </summary>
      <div class="source-picker__upload-body">
        <FField label="文件" required hint="支持 PPT / 视频 / 图片">
          <label class="source-picker__file">
            <input ref="fileInputRef" type="file" class="visually-hidden" :disabled="uploading"
              @change="onFileSelect" />
            <span>{{ fileToUpload ? fileToUpload.name : '尚未选择文件' }}</span>
            <FButton appearance="secondary" type="button" @click="() => fileInputRef?.click()">
              选择
            </FButton>
          </label>
        </FField>
        <FField label="显示名称" hint="可选；不填则使用文件名">
          <FInput v-model="fileDisplayName" placeholder="例如：早会 PPT" />
        </FField>
        <p v-if="uploadError" class="source-picker__upload-error">{{ uploadError }}</p>
        <FProgress v-if="uploading" :value="uploadProgress" show-label />

        <div class="source-picker__upload-actions">
          <FButton appearance="secondary" full-width :disabled="uploading || !fileToUpload"
            :loading="uploading && uploadProgress < 100" @click="() => uploadAndOpen(false)">
            上传但不保存
          </FButton>
          <FButton appearance="primary" full-width :disabled="uploading || !fileToUpload" :loading="uploading"
            @click="() => uploadAndOpen(true)">
            上传并保存
          </FButton>
        </div>
      </div>
    </details>

    <p v-if="uploading && !expanded" class="source-picker__upload-state">
      <FSpinner :size="16" /> 正在上传…
    </p>
  </FCard>
</template>

<style scoped>
.source-picker {
  height: 100%;
}

.source-picker__count {
  font-size: var(--type-caption1-size);
  color: var(--color-text-tertiary);
}

.source-picker__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  max-height: 420px;
  overflow-y: auto;
}

.source-picker__empty {
  padding: var(--spacing-l);
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--type-caption1-size);
}

.source-picker__item {
  display: flex;
  align-items: center;
  gap: var(--spacing-s);
  padding: var(--spacing-s) var(--spacing-m);
  border-radius: var(--radius-medium);
  border: 1px solid var(--color-border-subtle);
  background: var(--color-background-card);
  cursor: pointer;
  box-shadow: var(--shadow-control);
  transition:
    background var(--motion-duration-medium) var(--motion-curve-ease),
    border-color var(--motion-duration-medium) var(--motion-curve-ease),
    box-shadow var(--motion-duration-medium) var(--motion-curve-ease),
    transform var(--motion-duration-medium) var(--motion-curve-ease);
}

.source-picker__item:hover {
  background: var(--color-background-brand-selected);
  border-color: var(--color-background-brand);
  box-shadow: var(--shadow-4), var(--halo-brand);
  transform: translateY(var(--motion-hover-lift));
}

.source-picker__item:focus-visible {
  outline: none;
  border-color: var(--color-background-brand);
  box-shadow: var(--shadow-focus);
}

.source-picker__item:active {
  transform: translateY(0) scale(var(--motion-press-scale));
  transition-duration: var(--motion-duration-fast);
}

.source-picker__item--unavailable {
  background: var(--color-background-disabled);
  cursor: not-allowed;
  opacity: 0.7;
  box-shadow: none;
}

.source-picker__item--unavailable:hover {
  transform: none;
  box-shadow: none;
  background: var(--color-background-disabled);
  border-color: var(--color-border-subtle);
}

.source-picker__meta {
  flex: 1 1 auto;
  min-width: 0;
}

.source-picker__name {
  margin: 0;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.source-picker__sub {
  margin: 2px 0 0;
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-s);
  flex-wrap: wrap;
  color: var(--color-text-secondary);
  font-size: var(--type-caption1-size);
}

.source-picker__upload {
  border-top: 1px solid var(--color-border-subtle);
  padding-top: var(--spacing-s);
}

.source-picker__upload-summary {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-s);
  cursor: pointer;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.source-picker__upload-body {
  margin-top: var(--spacing-s);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-s);
}

.source-picker__file {
  display: flex;
  align-items: center;
  gap: var(--spacing-s);
  padding: var(--spacing-s) var(--spacing-m);
  border: 1px dashed var(--color-border-default);
  border-radius: var(--radius-medium);
  background: var(--color-background-subtle);
  transition:
    border-color var(--motion-duration-medium) var(--motion-curve-ease),
    background var(--motion-duration-medium) var(--motion-curve-ease);
}

.source-picker__file:hover {
  border-color: var(--color-border-focus);
  background: var(--color-background-card);
}

.source-picker__file>span {
  flex: 1 1 auto;
  color: var(--color-text-secondary);
  font-size: var(--type-caption1-size);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.source-picker__upload-actions {
  display: flex;
  gap: var(--spacing-s);
}

.source-picker__upload-error {
  margin: 0;
  color: var(--color-text-error);
  font-size: var(--type-caption1-size);
}

.source-picker__upload-state {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-s);
  margin: 0;
  font-size: var(--type-caption1-size);
  color: var(--color-text-secondary);
}
</style>
