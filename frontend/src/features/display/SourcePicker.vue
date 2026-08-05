<script setup lang="ts">
/**
 * 显示控制页左侧「切换源」面板：
 *   - 顶部搜索 + 类型筛选 Pill；
 *   - List/Detail 风格列表，点击行直接打开到当前窗口；
 *   - 折叠的「上传并打开」区域：创建临时源并立即打开，结束后由后端清理。
 */
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import {
  NButton,
  NCard,
  NFormItem,
  NInput,
  NProgress,
  NSpin,
  NTabs,
  NTabPane,
  NTag,
} from 'naive-ui';

import FIcon from '@/design-system/FIcon.vue';
import { useToast } from '@/composables/useToast';
import { useBackgroundAudioStore } from '@/stores/backgroundAudio';
import { useSessionStore } from '@/stores/sessions';
import { useSourceStore, type SourceCategory } from '@/stores/sources';
import type { MediaSourceItem } from '@/services/api';
import SourceThumbnail from '../sources/SourceThumbnail.vue';
import { sourceCategoryLabel } from '../sources/sourcePresentation';

const props = defineProps<{ windowId: number }>();
const emit = defineEmits<{ (event: 'opened'): void }>();

const { t } = useI18n();
const sourceStore = useSourceStore();
const backgroundAudioStore = useBackgroundAudioStore();
const sessionStore = useSessionStore();
const toast = useToast();

const filterValue = ref<SourceCategory>('all');
const searchKeyword = ref('');
const expanded = ref(false);
const fileToUpload = ref<File | null>(null);
const fileDisplayName = ref('');
const uploadProgress = ref(0);
const uploading = ref(false);
const switchingSourceId = ref<number | null>(null);
const uploadError = ref('');
const fileInputRef = ref<HTMLInputElement | null>(null);

const filteredSources = computed<MediaSourceItem[]>(() => {
  const keyword = searchKeyword.value.trim().toLowerCase();
  return sourceStore.sources.filter((source) => {
    if (source.source_type === 'audio') return false;
    if (filterValue.value !== 'all' && sourceStore.resolveCategory(source.source_type) !== filterValue.value) {
      return false;
    }
    if (!keyword) return true;
    const hay = `${source.name} ${source.uri ?? ''} ${source.original_filename ?? ''}`.toLowerCase();
    return hay.includes(keyword);
  });
});
async function selectSource(source: MediaSourceItem): Promise<void> {
  if (!source.is_available || switchingSourceId.value !== null) {
    if (!source.is_available) toast.warning(t('sourcePicker.offline'), t('sourcePicker.offlineHint'));
    return;
  }
  switchingSourceId.value = source.id;
  try {
    await sessionStore.openSource(props.windowId, source.id, true);
    toast.success(t('sourcePicker.openedOk', { name: source.name }));
    emit('opened');
  } catch (error) {
    toast.error(t('sourcePicker.openFail'), error instanceof Error ? error.message : t('common.retry'));
  } finally {
    switchingSourceId.value = null;
  }
}

function isCurrentSource(source: MediaSourceItem): boolean {
  return sessionStore.byWindowId(props.windowId)?.source_id === source.id;
}

function onFileSelect(event: Event): void {
  const target = event.target as HTMLInputElement;
  fileToUpload.value = target.files?.[0] ?? null;
}

async function uploadAndOpen(): Promise<void> {
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
      isTemporary: true,
      onProgress: (percent) => {
        uploadProgress.value = percent;
      },
    });
    if (result.source_type === 'audio') {
      await backgroundAudioStore.playSource(result.id);
      toast.success(t('backgroundAudio.playingOk', { name: result.name }));
    } else {
      await sessionStore.openSource(props.windowId, result.id, true);
      toast.success(t('sourcePicker.uploadedOpened'), t('sourcePicker.sourceNameDetail', { name: result.name }));
      emit('opened');
    }
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

    <ul class="source-picker__list">
      <li v-if="filteredSources.length === 0" class="source-picker__empty">
        {{ t('sourcePicker.empty') }}
      </li>
      <li
        v-for="source in filteredSources"
        :key="source.id"
        class="source-picker__item"
        :class="{
          'source-picker__item--unavailable': !source.is_available,
          'source-picker__item--active': isCurrentSource(source),
          'source-picker__item--switching': switchingSourceId === source.id,
        }"
      >
        <button
          type="button"
          class="source-picker__item-button"
          :disabled="!source.is_available || switchingSourceId !== null"
          :aria-current="isCurrentSource(source) ? 'true' : undefined"
          @click="selectSource(source)"
        >
          <SourceThumbnail :source="source" />
          <div class="source-picker__meta">
            <p class="source-picker__name">{{ source.name }}</p>
            <p class="source-picker__sub">
              <n-tag v-if="isCurrentSource(source)" type="success" size="small" round>{{ t('sourcePicker.onAir') }}</n-tag>
              <n-tag :type="source.is_available ? 'default' : 'error'" size="small" round>
                {{ source.is_available ? sourceCategoryLabel(source) : t('sourcePicker.offline') }}
              </n-tag>
            </p>
          </div>
          <n-spin v-if="switchingSourceId === source.id" :size="18" />
        </button>
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
              accept=".pdf,.pptx,.ppt,.pps,.ppsx,.pptm,.ppsm,.pot,.potx,.potm,.odp,.mp4,.mkv,.avi,.mov,.wmv,.flv,.webm,.m4v,.mp3,.wav,.flac,.aac,.ogg,.wma,.m4a,.png,.jpg,.jpeg,.gif,.bmp,.webp,.svg"
              @change="onFileSelect" />
            <span>{{ fileToUpload ? fileToUpload.name : t('sourcePicker.noFile') }}</span>
            <n-button @click="() => fileInputRef?.click()">
              {{ t('sourcePicker.chooseFile') }}
            </n-button>
          </label>
        </n-form-item>
        <n-alert type="info" :title="t('sourcePicker.pdfSuggestion')" :closable="false" />
        <n-form-item :label="t('sourcePicker.displayName')" :feedback="t('sourcePicker.displayNameHint')">
          <n-input v-model:value="fileDisplayName" :placeholder="t('sourcePicker.displayNamePlaceholder')" />
        </n-form-item>
        <p v-if="uploadError" class="source-picker__upload-error">{{ uploadError }}</p>
        <n-progress v-if="uploading" type="line" :percentage="uploadProgress" />

        <div class="source-picker__upload-actions">
          <n-button type="primary" block :disabled="uploading || !fileToUpload" :loading="uploading"
            @click="uploadAndOpen">
            {{ t('sourcePicker.uploadOpen') }}
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
  border-radius: var(--borderRadiusMedium);
  border: 1px solid var(--colorNeutralStroke2);
  background: var(--colorNeutralBackground1);
  overflow: hidden;
}

.source-picker__item-button {
  width: 100%;
  display: flex;
  align-items: center;
  gap: var(--spacingHorizontalS);
  padding: var(--spacingVerticalS) var(--spacingHorizontalM);
  border: 0;
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.source-picker__item:hover:not(.source-picker__item--unavailable) {
  background: var(--colorBrandBackground2);
  border-color: var(--colorBrandStroke1);
}

.source-picker__item:has(.source-picker__item-button:focus-visible) {
  outline: none;
  border-color: var(--colorBrandBackground);
  box-shadow: 0 0 0 2px var(--colorBrandBackground2);
}

.source-picker__item--unavailable {
  background: var(--colorNeutralBackground3);
  opacity: 0.7;
}

.source-picker__item--unavailable .source-picker__item-button {
  cursor: not-allowed;
}

.source-picker__item--active {
  border-color: var(--colorStatusSuccessForeground1);
  box-shadow: inset 3px 0 0 var(--colorStatusSuccessForeground1);
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
