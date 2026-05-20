<script setup lang="ts">
/**
 * 添加源 Drawer / Sheet：仅暴露「上传文件」「网页」两个 Tab。
 * 设计稿 §4.4：两颗按钮分别表达「上传但不保存」与「上传并保存」。
 */
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import {
  FButton,
  FDrawer,
  FField,
  FIcon,
  FInput,
  FMessageBar,
  FProgress,
  FSwitch,
  FTabs,
} from '@/design-system';
import type { FTabsItem } from '@/design-system';
import { useToast } from '@/composables/useToast';
import { useSourceStore } from '@/stores/sources';

const props = defineProps<{ open: boolean }>();
const emit = defineEmits<{
  (event: 'update:open', value: boolean): void;
  (event: 'added'): void;
}>();

const { t } = useI18n();
const sourceStore = useSourceStore();
const toast = useToast();

type TabId = 'file' | 'web';

const activeTab = ref<TabId>('file');
const tabs = computed<FTabsItem<TabId>[]>(() => [
  { label: t('sources.add.tabFile'), value: 'file', icon: 'arrow_upload_24_regular' },
  { label: t('sources.add.tabWeb'), value: 'web', icon: 'link_24_regular' },
]);

const fileToUpload = ref<File | null>(null);
const fileDisplayName = ref('');
const webUrl = ref('');
const webName = ref('');
// 网页源默认开启「预热」：播放器启动时提前加载 QWebEngineView，
// 切换到该网页时可复用已加载视图，减少首屏白屏时间。
const webPreheatEnabled = ref(true);
const uploadProgress = ref(0);
const uploading = ref(false);
const errorMessage = ref('');

const fileLabel = computed(() => fileToUpload.value?.name ?? t('sources.add.noFile'));
const fileSize = computed(() => {
  if (!fileToUpload.value) return '';
  const bytes = fileToUpload.value.size;
  const units = ['B', 'KB', 'MB', 'GB'];
  let value = bytes;
  let unitIdx = 0;
  while (value >= 1024 && unitIdx < units.length - 1) {
    value /= 1024;
    unitIdx += 1;
  }
  return `${value.toFixed(unitIdx === 0 ? 0 : 1)} ${units[unitIdx]}`;
});

function close(): void {
  emit('update:open', false);
}

function reset(): void {
  fileToUpload.value = null;
  fileDisplayName.value = '';
  webUrl.value = '';
  webName.value = '';
  webPreheatEnabled.value = true;
  uploadProgress.value = 0;
  uploading.value = false;
  errorMessage.value = '';
  activeTab.value = 'file';
}

const fileInputEl = ref<HTMLInputElement | null>(null);

function onFileSelect(event: Event): void {
  const target = event.target as HTMLInputElement;
  fileToUpload.value = target.files?.[0] ?? null;
}

function triggerFilePicker(): void {
  fileInputEl.value?.click();
}

async function uploadFile(persist: boolean): Promise<void> {
  if (!fileToUpload.value) {
    errorMessage.value = t('sources.add.pickFileFirst');
    return;
  }
  uploading.value = true;
  uploadProgress.value = 0;
  errorMessage.value = '';
  try {
    const result = await sourceStore.upload(fileToUpload.value, {
      name: fileDisplayName.value.trim() || undefined,
      isTemporary: !persist,
      onProgress: (percent) => {
        uploadProgress.value = percent;
      },
    });
    toast.success(persist ? t('sources.add.uploadedSaved') : t('sources.add.uploadedNoSave'), t('sources.add.sourceNameDetail', { name: result.name }));
    emit('added');
    reset();
    close();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : t('sources.add.uploadFail');
  } finally {
    uploading.value = false;
  }
}

async function addWebSource(): Promise<void> {
  const url = webUrl.value.trim();
  if (!url) {
    errorMessage.value = t('sources.add.urlRequired');
    return;
  }
  uploading.value = true;
  errorMessage.value = '';
  try {
    await sourceStore.addWebSource(url, webName.value.trim() || undefined, webPreheatEnabled.value);
    toast.success(t('sources.add.webAddedOk'));
    emit('added');
    reset();
    close();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : t('sources.add.webAddFail');
  } finally {
    uploading.value = false;
  }
}
</script>

<template>
  <FDrawer :open="open" :title="t('sources.add.title')" :description="t('sources.add.desc')" :primary-label="t('common.add')"
    :hide-default-actions="true" :width="480" @update:open="(value) => emit('update:open', value)">
    <FTabs v-model="activeTab" :items="tabs" appearance="line" :aria-label="t('sources.add.typeAria')" />

    <template v-if="activeTab === 'file'">
      <FField :label="t('sources.add.file')" required :hint="t('sources.add.fileHint')">
        <label class="add-source__file">
          <input ref="fileInputEl" type="file" class="visually-hidden" :disabled="uploading" @change="onFileSelect" />
          <span class="add-source__file-info">
            <FIcon name="arrow_upload_24_regular" />
            <span>{{ fileLabel }}</span>
            <span v-if="fileSize" class="add-source__file-size">{{ fileSize }}</span>
          </span>
          <FButton appearance="secondary" type="button" @click="triggerFilePicker">
            {{ t('sources.add.chooseFile') }}
          </FButton>
        </label>
      </FField>
      <FField :label="t('sources.add.displayName')" :hint="t('sources.add.displayNameHint')">
        <FInput v-model="fileDisplayName" :placeholder="t('sources.add.displayNamePlaceholder')" />
      </FField>

      <FProgress v-if="uploading" :value="uploadProgress" show-label />
    </template>

    <template v-if="activeTab === 'web'">
      <FField :label="t('sources.add.url')" required :hint="t('sources.add.urlHint')">
        <FInput v-model="webUrl" placeholder="https://" type="url" :aria-label="t('sources.add.url')" />
      </FField>
      <FField :label="t('sources.add.webName')" :hint="t('sources.add.webNameHint')">
        <FInput v-model="webName" :placeholder="t('sources.add.webNamePlaceholder')" />
      </FField>
      <FField :label="t('sources.add.preheat')" :hint="t('sources.add.preheatHint')">
        <FSwitch v-model="webPreheatEnabled" :label="t('sources.add.preheatSwitch')" />
      </FField>
    </template>

    <FMessageBar v-if="errorMessage" tone="error" :title="t('sources.add.cantComplete')">
      {{ errorMessage }}
    </FMessageBar>

    <template #actions="{ cancel }">
      <FButton appearance="secondary" :disabled="uploading" @click="cancel">{{ t('common.cancel') }}</FButton>
      <template v-if="activeTab === 'file'">
        <FButton appearance="secondary" :disabled="uploading || !fileToUpload"
          :loading="uploading && uploadProgress < 100" @click="() => uploadFile(false)">
          {{ t('sources.add.uploadNoSave') }}
        </FButton>
        <FButton appearance="primary" :disabled="uploading || !fileToUpload" :loading="uploading"
          @click="() => uploadFile(true)">
          {{ t('sources.add.uploadSave') }}
        </FButton>
      </template>
      <FButton v-else appearance="primary" :disabled="uploading" :loading="uploading" @click="addWebSource">
        {{ t('sources.add.addWeb') }}
      </FButton>
    </template>
  </FDrawer>
</template>

<style scoped>
.add-source__file {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-m);
  padding: var(--spacing-m);
  border: 1px dashed var(--colorNeutralStroke1);
  border-radius: var(--borderRadiusMedium);
  cursor: pointer;
  background: var(--colorNeutralBackground2);
}

.add-source__file:hover {
  border-color: var(--colorBrandStroke1);
}

.add-source__file-info {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-s);
  color: var(--colorNeutralForeground2);
  flex: 1 1 auto;
  min-width: 0;
}

.add-source__file-size {
  color: var(--colorNeutralForeground3);
  font-size: var(--fontSizeBase200);
}

@media (max-width: 767px) {
  .add-source__file {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
