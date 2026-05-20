<script setup lang="ts">
/**
 * 显示控制页左侧「切换源」面板：
 *   - 顶部搜索 + 类型筛选 Pill；
 *   - List/Detail 风格列表，点击行直接打开到当前窗口；
 *   - 折叠的「上传并打开」区域：上传但不保存 / 上传并保存。
 */
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

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

const { t } = useI18n();
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

const filterTabs = computed<FTabsItem<SourceCategory>[]>(() => [
  { label: t('sourcePicker.filter.all'), value: 'all' },
  { label: t('sourcePicker.filter.ppt'), value: 'ppt' },
  { label: t('sourcePicker.filter.video'), value: 'video' },
  { label: t('sourcePicker.filter.image'), value: 'image' },
  { label: t('sourcePicker.filter.web'), value: 'web' },
  { label: t('sourcePicker.filter.stream'), value: 'stream' },
]);

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
    toast.success(t('sourcePicker.openedOk', { name: source.name }));
  } catch (error) {
    toast.error(t('sourcePicker.openFail'), error instanceof Error ? error.message : t('common.retry'));
  }
}

function onFileSelect(event: Event): void {
  const target = event.target as HTMLInputElement;
  fileToUpload.value = target.files?.[0] ?? null;
}

async function uploadAndOpen(persist: boolean): Promise<void> {
  if (!fileToUpload.value) {
    uploadError.value = t('sourcePicker.pickFileFirst');
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
    toast.success(persist ? t('sourcePicker.uploadedOpenedSave') : t('sourcePicker.uploadedOpenedNoSave'), t('sourcePicker.sourceNameDetail', { name: result.name }));
    fileToUpload.value = null;
    fileDisplayName.value = '';
    if (fileInputRef.value) fileInputRef.value.value = '';
  } catch (error) {
    uploadError.value = error instanceof Error ? error.message : t('sourcePicker.uploadFail');
  } finally {
    uploading.value = false;
    uploadProgress.value = 0;
  }
}

const totalLabel = computed(() => t('sourcePicker.count', { n: filteredSources.value.length }));
</script>

<template>
  <FCard padding="compact" class="source-picker">
    <template #title>
      <span>{{ t('sourcePicker.title') }}</span>
    </template>
    <template #actions>
      <span class="source-picker__count">{{ totalLabel }}</span>
    </template>

    <FInput v-model="searchKeyword" :placeholder="t('sourcePicker.searchPlaceholder')" :aria-label="t('sourcePicker.searchAria')" clearable>
      <template #prefix>
        <FIcon name="search_20_regular" />
      </template>
    </FInput>

    <FTabs v-model="filterValue" :items="filterTabs" appearance="pill" full-width :aria-label="t('sourcePicker.filterAria')" />

    <ul class="source-picker__list">
      <li v-if="filteredSources.length === 0" class="source-picker__empty">
        {{ t('sourcePicker.empty') }}
      </li>
      <li v-for="source in filteredSources" :key="source.id" class="source-picker__item"
        :class="{ 'source-picker__item--unavailable': !source.is_available }" @click="selectSource(source)">
        <SourceThumbnail :source="source" />
        <div class="source-picker__meta">
          <p class="source-picker__name">{{ source.name }}</p>
          <p class="source-picker__sub">
            <FTag :tone="source.is_available ? 'subtle' : 'error'">
              {{ source.is_available ? sourceCategoryLabel(source) : t('sourcePicker.offline') }}
            </FTag>
          </p>
        </div>
      </li>
    </ul>

    <details class="source-picker__upload" :open="expanded"
      @toggle="expanded = ($event.target as HTMLDetailsElement).open">
      <summary class="source-picker__upload-summary">
        <FIcon name="arrow_upload_24_regular" />
        <span>{{ t('sourcePicker.uploadAndOpen') }}</span>
      </summary>
      <div class="source-picker__upload-body">
        <FField :label="t('sourcePicker.file')" required :hint="t('sourcePicker.fileHint')">
          <label class="source-picker__file">
            <input ref="fileInputRef" type="file" class="visually-hidden" :disabled="uploading"
              @change="onFileSelect" />
            <span>{{ fileToUpload ? fileToUpload.name : t('sourcePicker.noFile') }}</span>
            <FButton appearance="secondary" type="button" @click="() => fileInputRef?.click()">
              {{ t('sourcePicker.chooseFile') }}
            </FButton>
          </label>
        </FField>
        <FField :label="t('sourcePicker.displayName')" :hint="t('sourcePicker.displayNameHint')">
          <FInput v-model="fileDisplayName" :placeholder="t('sourcePicker.displayNamePlaceholder')" />
        </FField>
        <p v-if="uploadError" class="source-picker__upload-error">{{ uploadError }}</p>
        <FProgress v-if="uploading" :value="uploadProgress" show-label />

        <div class="source-picker__upload-actions">
          <FButton appearance="secondary" full-width :disabled="uploading || !fileToUpload"
            :loading="uploading && uploadProgress < 100" @click="() => uploadAndOpen(false)">
            {{ t('sourcePicker.uploadNoSave') }}
          </FButton>
          <FButton appearance="primary" full-width :disabled="uploading || !fileToUpload" :loading="uploading"
            @click="() => uploadAndOpen(true)">
            {{ t('sourcePicker.uploadSave') }}
          </FButton>
        </div>
      </div>
    </details>

    <p v-if="uploading && !expanded" class="source-picker__upload-state">
      <FSpinner :size="16" /> {{ t('sourcePicker.uploading') }}
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
