<script setup lang="ts">
/**
 * 添加源 Drawer / Sheet：仅暴露「上传文件」「网页」两个 Tab。
 * 两颗按钮分别表达「上传但不保存」与「上传并保存」。
 */
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import {
  NAlert,
  NButton,
  NDrawer,
  NDrawerContent,
  NFormItem,
  NInput,
  NProgress,
  NSelect,
  NSwitch,
  NTabs,
  NTabPane,
} from 'naive-ui';

import FIcon from '@/design-system/FIcon.vue';
import { useToast } from '@/composables/useToast';
import { useSourceStore } from '@/stores/sources';
import type { PptBackend } from '@/services/api';

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

const fileToUpload = ref<File | null>(null);
const fileDisplayName = ref('');
const filePptBackend = ref<PptBackend>('libreoffice');
const webUrl = ref('');
const webName = ref('');
const webPreheatEnabled = ref(true);
const uploadProgress = ref(0);
const uploading = ref(false);
const errorMessage = ref('');

const fileLabel = computed(() => fileToUpload.value?.name ?? t('sources.add.noFile'));
const isPptFile = computed(() => /\.(pptx?|ppsx?)$/i.test(fileToUpload.value?.name ?? ''));
const pptBackendOptions = computed(() => [
  { label: t('sources.pptBackend.libreoffice'), value: 'libreoffice' },
  { label: t('sources.pptBackend.powerpoint'), value: 'powerpoint' },
]);
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

const isOpen = computed({
  get: () => props.open,
  set: (value: boolean) => emit('update:open', value),
});

function close(): void {
  emit('update:open', false);
}

function reset(): void {
  fileToUpload.value = null;
  fileDisplayName.value = '';
  filePptBackend.value = 'libreoffice';
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
      pptBackend: isPptFile.value ? filePptBackend.value : undefined,
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
  <n-drawer v-model:show="isOpen" :width="480" placement="right">
    <n-drawer-content :title="t('sources.add.title')" closable>
      <p class="add-source__desc">{{ t('sources.add.desc') }}</p>

      <n-tabs v-model:value="activeTab" type="line" :aria-label="t('sources.add.typeAria')">
        <n-tab-pane name="file" :tab="t('sources.add.tabFile')">
          <n-form-item :label="t('sources.add.file')" required :feedback="t('sources.add.fileHint')">
            <label class="add-source__file">
              <input ref="fileInputEl" type="file" class="visually-hidden" :disabled="uploading" @change="onFileSelect" />
              <span class="add-source__file-info">
                <FIcon name="arrow_upload_24_regular" />
                <span>{{ fileLabel }}</span>
                <span v-if="fileSize" class="add-source__file-size">{{ fileSize }}</span>
              </span>
              <n-button @click="triggerFilePicker">{{ t('sources.add.chooseFile') }}</n-button>
            </label>
          </n-form-item>
          <n-form-item :label="t('sources.add.displayName')" :feedback="t('sources.add.displayNameHint')">
            <n-input v-model:value="fileDisplayName" :placeholder="t('sources.add.displayNamePlaceholder')" />
          </n-form-item>
          <n-form-item v-if="isPptFile" :label="t('sources.pptBackend.label')" :feedback="t('sources.pptBackend.importHint')">
            <n-select v-model:value="filePptBackend" :options="pptBackendOptions" />
          </n-form-item>

          <n-progress v-if="uploading" type="line" :percentage="uploadProgress" />
        </n-tab-pane>

        <n-tab-pane name="web" :tab="t('sources.add.tabWeb')">
          <n-form-item :label="t('sources.add.url')" required :feedback="t('sources.add.urlHint')">
            <n-input v-model:value="webUrl" placeholder="https://" :aria-label="t('sources.add.url')" />
          </n-form-item>
          <n-form-item :label="t('sources.add.webName')" :feedback="t('sources.add.webNameHint')">
            <n-input v-model:value="webName" :placeholder="t('sources.add.webNamePlaceholder')" />
          </n-form-item>
          <n-form-item :label="t('sources.add.preheat')" :feedback="t('sources.add.preheatHint')">
            <n-switch v-model:value="webPreheatEnabled">
              <template #checked>{{ t('sources.add.preheatSwitch') }}</template>
              <template #unchecked>{{ t('sources.add.preheatSwitch') }}</template>
            </n-switch>
          </n-form-item>
        </n-tab-pane>
      </n-tabs>

      <n-alert v-if="errorMessage" type="error" :title="t('sources.add.cantComplete')">
        {{ errorMessage }}
      </n-alert>

      <template #footer>
        <div class="add-source__actions">
          <n-button :disabled="uploading" @click="close">{{ t('common.cancel') }}</n-button>
          <template v-if="activeTab === 'file'">
            <n-button :disabled="uploading || !fileToUpload"
              :loading="uploading && uploadProgress < 100" @click="() => uploadFile(false)">
              {{ t('sources.add.uploadNoSave') }}
            </n-button>
            <n-button type="primary" :disabled="uploading || !fileToUpload" :loading="uploading"
              @click="() => uploadFile(true)">
              {{ t('sources.add.uploadSave') }}
            </n-button>
          </template>
          <n-button v-else type="primary" :disabled="uploading" :loading="uploading" @click="addWebSource">
            {{ t('sources.add.addWeb') }}
          </n-button>
        </div>
      </template>
    </n-drawer-content>
  </n-drawer>
</template>

<style scoped>
.add-source__desc {
  margin: 0 0 var(--spacingVerticalM);
  color: var(--colorNeutralForeground2);
  font-size: var(--fontSizeBase200);
}

.add-source__file {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacingHorizontalM);
  padding: var(--spacingVerticalM);
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
  gap: var(--spacingHorizontalS);
  color: var(--colorNeutralForeground2);
  flex: 1 1 auto;
  min-width: 0;
}

.add-source__file-size {
  color: var(--colorNeutralForeground3);
  font-size: var(--fontSizeBase200);
}

.add-source__actions {
  display: inline-flex;
  align-items: center;
  gap: var(--spacingHorizontalS);
  justify-content: flex-end;
  width: 100%;
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

@media (max-width: 767px) {
  .add-source__file {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
