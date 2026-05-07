<script setup lang="ts">
/**
 * 添加源 Drawer / Sheet：仅暴露「上传文件」「网页」两个 Tab。
 * 设计稿 §4.4：两颗按钮分别表达「上传但不保存」与「上传并保存」。
 */
import { computed, ref } from 'vue';

import {
  FButton,
  FDrawer,
  FField,
  FIcon,
  FInput,
  FMessageBar,
  FProgress,
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

const sourceStore = useSourceStore();
const toast = useToast();

type TabId = 'file' | 'web';

const activeTab = ref<TabId>('file');
const tabs: FTabsItem<TabId>[] = [
  { label: '上传文件', value: 'file', icon: 'arrow_upload_24_regular' },
  { label: '网页', value: 'web', icon: 'link_24_regular' },
];

const fileToUpload = ref<File | null>(null);
const fileDisplayName = ref('');
const webUrl = ref('');
const webName = ref('');
const uploadProgress = ref(0);
const uploading = ref(false);
const errorMessage = ref('');

const fileLabel = computed(() => fileToUpload.value?.name ?? '尚未选择文件');
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
    errorMessage.value = '请先选择要上传的文件';
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
    toast.success(persist ? '已上传并保存' : '已上传，但不会写入媒体库', `源名称：${result.name}`);
    emit('added');
    reset();
    close();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '上传失败，请稍后重试';
  } finally {
    uploading.value = false;
  }
}

async function addWebSource(): Promise<void> {
  const url = webUrl.value.trim();
  if (!url) {
    errorMessage.value = '请输入 URL 或 ip:port';
    return;
  }
  uploading.value = true;
  errorMessage.value = '';
  try {
    await sourceStore.addWebSource(url, webName.value.trim() || undefined);
    toast.success('已添加网页源');
    emit('added');
    reset();
    close();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '注册网页源失败';
  } finally {
    uploading.value = false;
  }
}
</script>

<template>
  <FDrawer :open="open" title="添加媒体源" description="仅支持上传文件或注册网页 URL；直播源由推流端自动注入。" :primary-label="'添加'"
    :hide-default-actions="true" :width="480" @update:open="(value) => emit('update:open', value)">
    <FTabs v-model="activeTab" :items="tabs" appearance="line" aria-label="添加源类型" />

    <template v-if="activeTab === 'file'">
      <FField label="文件" required hint="支持 PPT / 视频 / 图片；单文件 ≤ 2 GB">
        <label class="add-source__file">
          <input ref="fileInputEl" type="file" class="visually-hidden" :disabled="uploading" @change="onFileSelect" />
          <span class="add-source__file-info">
            <FIcon name="arrow_upload_24_regular" />
            <span>{{ fileLabel }}</span>
            <span v-if="fileSize" class="add-source__file-size">{{ fileSize }}</span>
          </span>
          <FButton appearance="secondary" type="button" @click="triggerFilePicker">
            选择文件
          </FButton>
        </label>
      </FField>
      <FField label="显示名称" hint="可选；不填则使用文件名作为名称">
        <FInput v-model="fileDisplayName" placeholder="例如：早会 PPT" />
      </FField>

      <FProgress v-if="uploading" :value="uploadProgress" show-label />
    </template>

    <template v-if="activeTab === 'web'">
      <FField label="URL 或 ip:port" required hint="例如 https://example.com、192.168.1.10:8080">
        <FInput v-model="webUrl" placeholder="https://" type="url" />
      </FField>
      <FField label="显示名称" hint="可选；不填将使用 URL 作为名称">
        <FInput v-model="webName" placeholder="例如：直播首页" />
      </FField>
    </template>

    <FMessageBar v-if="errorMessage" tone="error" title="无法完成">
      {{ errorMessage }}
    </FMessageBar>

    <template #actions="{ cancel }">
      <FButton appearance="secondary" :disabled="uploading" @click="cancel">取消</FButton>
      <template v-if="activeTab === 'file'">
        <FButton appearance="secondary" :disabled="uploading || !fileToUpload"
          :loading="uploading && uploadProgress < 100" @click="() => uploadFile(false)">
          上传但不保存
        </FButton>
        <FButton appearance="primary" :disabled="uploading || !fileToUpload" :loading="uploading"
          @click="() => uploadFile(true)">
          上传并保存
        </FButton>
      </template>
      <FButton v-else appearance="primary" :disabled="uploading" :loading="uploading" @click="addWebSource">
        添加网页
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
  border: 1px dashed var(--color-border-default);
  border-radius: var(--radius-medium);
  cursor: pointer;
  background: var(--color-background-subtle);
}

.add-source__file:hover {
  border-color: var(--color-border-focus);
}

.add-source__file-info {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-s);
  color: var(--color-text-secondary);
  flex: 1 1 auto;
  min-width: 0;
}

.add-source__file-size {
  color: var(--color-text-tertiary);
  font-size: var(--type-caption1-size);
}

@media (max-width: 767px) {
  .add-source__file {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
