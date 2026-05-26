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
  NButton,
  NCard,
  NFormItem,
  NInput,
  NProgress,
  NSelect,
  NSpin,
  NTabs,
  NTabPane,
  NTag,
} from 'naive-ui';

import FIcon from '@/design-system/FIcon.vue';
import { useDialog } from '@/composables/useDialog';
import { useToast } from '@/composables/useToast';
import { useSessionStore } from '@/stores/sessions';
import { useSourceStore, type SourceCategory } from '@/stores/sources';
import type { MediaSourceItem, PptBackend } from '@/services/api';
import SourceThumbnail from '../sources/SourceThumbnail.vue';
import { sourceCategoryLabel } from '../sources/sourcePresentation';

const props = defineProps<{ windowId: number }>();

const { t } = useI18n();
const sourceStore = useSourceStore();
const sessionStore = useSessionStore();
const toast = useToast();
const dialog = useDialog();

const filterValue = ref<SourceCategory>('all');
const searchKeyword = ref('');
const expanded = ref(false);
const fileToUpload = ref<File | null>(null);
const fileDisplayName = ref('');
const filePptBackend = ref<PptBackend>('libreoffice');
const pptOpenBackend = ref<PptBackend | 'source-default'>('source-default');
const uploadProgress = ref(0);
const uploading = ref(false);
const uploadError = ref('');
const fileInputRef = ref<HTMLInputElement | null>(null);

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
const isPptUpload = computed(() => /\.(pptx?|ppsx?)$/i.test(fileToUpload.value?.name ?? ''));
const hasPptSources = computed(() => sourceStore.sources.some((source) => source.source_type === 'ppt'));
const pptBackendOptions = computed(() => [
  { label: t('sourcePicker.pptBackendDefault'), value: 'source-default' },
  { label: t('sources.pptBackend.libreoffice'), value: 'libreoffice' },
  { label: t('sources.pptBackend.powerpoint'), value: 'powerpoint' },
]);
const pptBackendStrictOptions = computed(() => [
  { label: t('sources.pptBackend.libreoffice'), value: 'libreoffice' },
  { label: t('sources.pptBackend.powerpoint'), value: 'powerpoint' },
]);

async function selectSource(source: MediaSourceItem): Promise<void> {
  try {
    const selectedBackend = source.source_type === 'ppt' && pptOpenBackend.value !== 'source-default'
      ? pptOpenBackend.value
      : undefined;
    if (selectedBackend && selectedBackend !== source.ppt_backend) {
      const confirmed = await dialog.confirm({
        title: t('sourcePicker.switchPptBackendTitle'),
        description: t('sourcePicker.switchPptBackendDesc', { backend: selectedBackend === 'libreoffice' ? t('sources.pptBackend.libreoffice') : t('sources.pptBackend.powerpoint') }),
        confirmLabel: t('sourcePicker.switchPptBackendConfirm'),
        cancelLabel: t('common.cancel'),
      });
      if (!confirmed) return;
    }
    await sessionStore.openSource(props.windowId, source.id, true, selectedBackend);
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
      pptBackend: isPptUpload.value ? filePptBackend.value : undefined,
      onProgress: (percent) => {
        uploadProgress.value = percent;
      },
    });
    await sessionStore.openSource(props.windowId, result.id, true, result.source_type === 'ppt' ? result.ppt_backend : undefined);
    toast.success(persist ? t('sourcePicker.uploadedOpenedSave') : t('sourcePicker.uploadedOpenedNoSave'), t('sourcePicker.sourceNameDetail', { name: result.name }));
    fileToUpload.value = null;
    fileDisplayName.value = '';
    filePptBackend.value = 'libreoffice';
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
  <n-card class="source-picker" :title="t('sourcePicker.title')" size="small">
    <template #header-extra>
      <span class="source-picker__count">{{ totalLabel }}</span>
    </template>

    <n-input
      v-model:value="searchKeyword"
      :placeholder="t('sourcePicker.searchPlaceholder')"
      :aria-label="t('sourcePicker.searchAria')"
      clearable
    >
      <template #prefix>
        <FIcon name="search_20_regular" />
      </template>
    </n-input>

    <n-tabs v-model:value="filterValue" type="segment" :aria-label="t('sourcePicker.filterAria')">
      <n-tab-pane name="all" :tab="t('sourcePicker.filter.all')" />
      <n-tab-pane name="ppt" :tab="t('sourcePicker.filter.ppt')" />
      <n-tab-pane name="video" :tab="t('sourcePicker.filter.video')" />
      <n-tab-pane name="image" :tab="t('sourcePicker.filter.image')" />
      <n-tab-pane name="web" :tab="t('sourcePicker.filter.web')" />
      <n-tab-pane name="stream" :tab="t('sourcePicker.filter.stream')" />
    </n-tabs>

    <n-form-item v-if="hasPptSources" :label="t('sourcePicker.pptBackend')" :feedback="t('sourcePicker.pptBackendHint')">
      <n-select v-model:value="pptOpenBackend" :options="pptBackendOptions" size="small" />
    </n-form-item>

    <ul class="source-picker__list">
      <li v-if="filteredSources.length === 0" class="source-picker__empty">
        {{ t('sourcePicker.empty') }}
      </li>
      <li
        v-for="source in filteredSources"
        :key="source.id"
        class="source-picker__item"
        :class="{ 'source-picker__item--unavailable': !source.is_available }"
        @click="selectSource(source)"
      >
        <SourceThumbnail :source="source" />
        <div class="source-picker__meta">
          <p class="source-picker__name">{{ source.name }}</p>
          <p class="source-picker__sub">
            <n-tag :type="source.is_available ? 'default' : 'error'" size="small" round>
              {{ source.is_available ? sourceCategoryLabel(source) : t('sourcePicker.offline') }}
            </n-tag>
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
        <n-form-item :label="t('sourcePicker.file')" required :feedback="t('sourcePicker.fileHint')">
          <label class="source-picker__file">
            <input ref="fileInputRef" type="file" class="visually-hidden" :disabled="uploading"
              @change="onFileSelect" />
            <span>{{ fileToUpload ? fileToUpload.name : t('sourcePicker.noFile') }}</span>
            <n-button @click="() => fileInputRef?.click()">
              {{ t('sourcePicker.chooseFile') }}
            </n-button>
          </label>
        </n-form-item>
        <n-form-item :label="t('sourcePicker.displayName')" :feedback="t('sourcePicker.displayNameHint')">
          <n-input v-model:value="fileDisplayName" :placeholder="t('sourcePicker.displayNamePlaceholder')" />
        </n-form-item>
        <n-form-item v-if="isPptUpload" :label="t('sources.pptBackend.label')" :feedback="t('sources.pptBackend.importHint')">
          <n-select v-model:value="filePptBackend" :options="pptBackendStrictOptions" />
        </n-form-item>
        <p v-if="uploadError" class="source-picker__upload-error">{{ uploadError }}</p>
        <n-progress v-if="uploading" type="line" :percentage="uploadProgress" />

        <div class="source-picker__upload-actions">
          <n-button block :disabled="uploading || !fileToUpload"
            :loading="uploading && uploadProgress < 100" @click="() => uploadAndOpen(false)">
            {{ t('sourcePicker.uploadNoSave') }}
          </n-button>
          <n-button type="primary" block :disabled="uploading || !fileToUpload" :loading="uploading"
            @click="() => uploadAndOpen(true)">
            {{ t('sourcePicker.uploadSave') }}
          </n-button>
        </div>
      </div>
    </details>

    <p v-if="uploading && !expanded" class="source-picker__upload-state">
      <n-spin :size="16" /> {{ t('sourcePicker.uploading') }}
    </p>
  </n-card>
</template>

<style scoped>
.source-picker {
  height: 100%;
}

.source-picker__count {
  font-size: var(--fontSizeBase200);
  color: var(--colorNeutralForeground3);
}

.source-picker__list {
  list-style: none;
  margin: var(--spacingVerticalM) 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--spacingVerticalXS);
  max-height: 420px;
  overflow-y: auto;
}

.source-picker__empty {
  padding: var(--spacingVerticalL);
  text-align: center;
  color: var(--colorNeutralForeground3);
  font-size: var(--fontSizeBase200);
}

.source-picker__item {
  display: flex;
  align-items: center;
  gap: var(--spacingHorizontalS);
  padding: var(--spacingVerticalS) var(--spacingHorizontalM);
  border-radius: var(--borderRadiusMedium);
  border: 1px solid var(--colorNeutralStroke2);
  background: var(--colorNeutralBackground1);
  cursor: pointer;
}

.source-picker__item:hover {
  background: var(--colorBrandBackground2);
  border-color: var(--colorBrandStroke1);
}

.source-picker__item:focus-visible {
  outline: none;
  border-color: var(--colorBrandBackground);
}

.source-picker__item--unavailable {
  background: var(--colorNeutralBackground3);
  cursor: not-allowed;
  opacity: 0.7;
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
  gap: var(--spacingHorizontalS);
  flex-wrap: wrap;
  color: var(--colorNeutralForeground2);
  font-size: var(--fontSizeBase200);
}

.source-picker__upload {
  border-top: 1px solid var(--colorNeutralStroke2);
  padding-top: var(--spacingVerticalS);
  margin-top: var(--spacingVerticalM);
}

.source-picker__upload-summary {
  display: inline-flex;
  align-items: center;
  gap: var(--spacingHorizontalS);
  cursor: pointer;
  font-weight: 600;
  color: var(--colorNeutralForeground2);
}

.source-picker__upload-body {
  margin-top: var(--spacingVerticalS);
  display: flex;
  flex-direction: column;
  gap: var(--spacingVerticalS);
}

.source-picker__file {
  display: flex;
  align-items: center;
  gap: var(--spacingHorizontalS);
  padding: var(--spacingVerticalS) var(--spacingHorizontalM);
  border: 1px dashed var(--colorNeutralStroke1);
  border-radius: var(--borderRadiusMedium);
  background: var(--colorNeutralBackground2);
}

.source-picker__file:hover {
  border-color: var(--colorBrandStroke1);
  background: var(--colorNeutralBackground1);
}

.source-picker__file > span {
  flex: 1 1 auto;
  color: var(--colorNeutralForeground2);
  font-size: var(--fontSizeBase200);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.source-picker__upload-actions {
  display: flex;
  gap: var(--spacingHorizontalS);
}

.source-picker__upload-error {
  margin: 0;
  color: var(--colorStatusDangerForeground1);
  font-size: var(--fontSizeBase200);
}

.source-picker__upload-state {
  display: inline-flex;
  align-items: center;
  gap: var(--spacingHorizontalS);
  margin: var(--spacingVerticalS) 0 0;
  font-size: var(--fontSizeBase200);
  color: var(--colorNeutralForeground2);
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
