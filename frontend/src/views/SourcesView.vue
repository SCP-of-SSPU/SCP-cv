<script setup lang="ts">
import { computed, ref } from 'vue';

import { api, formatBytes, type MediaSourceItem } from '@/services/api';
import { useAppStore } from '@/stores/app';

const appStore = useAppStore();
const localPath = ref('');
const localName = ref('');
const webUrl = ref('');
const webName = ref('');
const uploadName = ref('');
const uploadFile = ref<File | null>(null);
const uploadInputKey = ref(0);
const uploadProgress = ref(0);
const isTemporaryUpload = ref(false);
const isUploading = ref(false);
const isAddingLocal = ref(false);
const isAddingWeb = ref(false);
const newFolderName = ref('');
const sourceTypeFilter = ref('');

const visibleSources = computed(() => (
  sourceTypeFilter.value
    ? appStore.sources.filter((source) => source.source_type === sourceTypeFilter.value)
    : appStore.sources
));
const sourceTypes = computed(() => Array.from(new Set(appStore.sources.map((source) => source.source_type))).sort());
const folderName = computed(() => {
  if (appStore.selectedFolderId === null) return '全部源';
  if (appStore.selectedFolderId === -1) return '根目录';
  return appStore.sourceFoldersById.get(appStore.selectedFolderId) || '文件夹';
});

async function runAction(action: () => Promise<void>): Promise<void> {
  try {
    await action();
  } catch (error) {
    appStore.notify(error instanceof Error ? error.message : '操作失败', true);
  }
}

function onFileSelected(event: Event): void {
  const input = event.target as HTMLInputElement;
  uploadFile.value = input.files?.[0] || null;
}

function activeFolderForWrite(): number | null {
  if (appStore.selectedFolderId === null || appStore.selectedFolderId === -1) return null;
  return appStore.selectedFolderId;
}

async function createFolder(): Promise<void> {
  if (!newFolderName.value.trim()) {
    appStore.notify('请输入文件夹名称', true);
    return;
  }
  await api.createFolder({ name: newFolderName.value.trim() });
  newFolderName.value = '';
  await appStore.refreshFolders();
  appStore.notify('文件夹已创建');
}

async function deleteFolder(folderId: number): Promise<void> {
  if (!window.confirm('删除文件夹后，其中媒体源会回到根目录。继续吗？')) return;
  await api.deleteFolder(folderId);
  if (appStore.selectedFolderId === folderId) appStore.selectedFolderId = null;
  await Promise.all([appStore.refreshFolders(), appStore.refreshSources()]);
  appStore.notify('文件夹已删除');
}

async function uploadSource(): Promise<void> {
  if (!uploadFile.value) {
    appStore.notify('请先选择文件', true);
    return;
  }
  const formData = new FormData();
  formData.append('file', uploadFile.value);
  if (uploadName.value) formData.append('name', uploadName.value);
  const folderId = activeFolderForWrite();
  if (folderId !== null) formData.append('folder_id', String(folderId));
  if (isTemporaryUpload.value) formData.append('is_temporary', 'true');
  isUploading.value = true;
  uploadProgress.value = 0;
  try {
    await api.uploadSource(formData, {
      onProgress: (percent: number) => {
        uploadProgress.value = percent;
      },
    });
    uploadFile.value = null;
    uploadName.value = '';
    isTemporaryUpload.value = false;
    uploadInputKey.value += 1;
    await appStore.refreshSources();
    appStore.notify('文件已上传');
  } finally {
    isUploading.value = false;
  }
}

async function addLocalSource(): Promise<void> {
  isAddingLocal.value = true;
  try {
    await api.addLocalSource({ path: localPath.value, name: localName.value, folder_id: activeFolderForWrite() });
    localPath.value = '';
    localName.value = '';
    await appStore.refreshSources();
    appStore.notify('本地源已添加');
  } finally {
    isAddingLocal.value = false;
  }
}

async function addWebSource(): Promise<void> {
  isAddingWeb.value = true;
  try {
    await api.addWebSource({ url: webUrl.value, name: webName.value, folder_id: activeFolderForWrite() });
    webUrl.value = '';
    webName.value = '';
    await appStore.refreshSources();
    appStore.notify('网页源已添加');
  } finally {
    isAddingWeb.value = false;
  }
}

async function moveSource(source: MediaSourceItem, folderId: number | null): Promise<void> {
  await api.moveSource(source.id, folderId === -1 ? null : folderId);
  await appStore.refreshSources();
  appStore.notify('媒体源已移动');
}

async function deleteSource(sourceId: number): Promise<void> {
  if (!window.confirm('确定删除该媒体源吗？')) return;
  await api.deleteSource(sourceId);
  await appStore.refreshSources();
  appStore.notify('媒体源已删除');
}
</script>

<template>
  <section class="source-shell">
    <aside class="panel source-rail">
      <span class="eyebrow">Source Vault</span>
      <h2>媒体库</h2>
      <button type="button" :class="{ active: appStore.selectedFolderId === null }" @click="runAction(() => appStore.selectFolder(null))">全部源</button>
      <button type="button" :class="{ active: appStore.selectedFolderId === -1 }" @click="runAction(() => appStore.selectFolder(-1))">根目录</button>
      <button
        v-for="folder in appStore.folders"
        :key="folder.id"
        type="button"
        :class="{ active: appStore.selectedFolderId === folder.id }"
        @click="runAction(() => appStore.selectFolder(folder.id))"
      >
        {{ folder.name }}
      </button>
      <div class="inline-form source-rail__new">
        <input v-model="newFolderName" placeholder="新文件夹" @keyup.enter="runAction(createFolder)" />
        <button type="button" @click="runAction(createFolder)">新建</button>
      </div>
      <button v-if="appStore.selectedFolderId && appStore.selectedFolderId > 0" type="button" class="danger" @click="runAction(() => deleteFolder(Number(appStore.selectedFolderId)))">删除当前文件夹</button>
    </aside>

    <main>
      <section class="grid three">
        <article class="panel">
          <h2>上传文件</h2>
          <input :key="uploadInputKey" type="file" :disabled="isUploading" @change="onFileSelected" />
          <input v-model="uploadName" placeholder="显示名称（可选）" :disabled="isUploading" />
          <label class="checkbox-line"><input v-model="isTemporaryUpload" type="checkbox" :disabled="isUploading" /> 临时源</label>
          <div v-if="isUploading" class="upload-progress" role="progressbar" :aria-valuenow="uploadProgress" aria-valuemin="0" aria-valuemax="100">
            <span :style="{ width: `${uploadProgress}%` }"></span>
            <strong>{{ uploadProgress }}%</strong>
          </div>
          <button type="button" :disabled="isUploading || !uploadFile" @click="runAction(uploadSource)">{{ isUploading ? '上传中...' : `上传到 ${folderName}` }}</button>
        </article>

        <article class="panel">
          <h2>本地路径</h2>
          <input v-model="localPath" placeholder="本地文件绝对路径" :disabled="isAddingLocal" />
          <input v-model="localName" placeholder="显示名称（可选）" :disabled="isAddingLocal" />
          <button type="button" :disabled="isAddingLocal || !localPath.trim()" @click="runAction(addLocalSource)">{{ isAddingLocal ? '添加中...' : '添加本地源' }}</button>
        </article>

        <article class="panel">
          <h2>网页源</h2>
          <input v-model="webUrl" placeholder="192.168.1.10:3000 或 https://example.com" :disabled="isAddingWeb" />
          <input v-model="webName" placeholder="显示名称（可选）" :disabled="isAddingWeb" />
          <button type="button" :disabled="isAddingWeb || !webUrl.trim()" @click="runAction(addWebSource)">{{ isAddingWeb ? '添加中...' : '添加网页源' }}</button>
        </article>
      </section>

      <section class="panel">
        <div class="panel__header">
          <div>
            <span class="eyebrow">{{ folderName }}</span>
            <h2>媒体源</h2>
          </div>
          <div class="row-actions">
            <select v-model="sourceTypeFilter" aria-label="源类型筛选">
              <option value="">全部类型</option>
              <option v-for="sourceType in sourceTypes" :key="sourceType" :value="sourceType">{{ sourceType }}</option>
            </select>
            <button type="button" @click="runAction(appStore.refreshSources)">刷新</button>
          </div>
        </div>
        <ul class="source-list">
          <li v-for="source in visibleSources" :key="source.id" class="source-card source-card--rich">
            <div>
              <span class="chip" :class="{ 'chip--accent': source.is_available }">{{ source.source_type }}</span>
              <strong>{{ source.name }}</strong>
              <small>{{ source.uri }}</small>
              <small>{{ formatBytes(source.file_size) }} · {{ source.original_filename || '无文件名' }} · {{ source.is_temporary ? '临时' : '持久' }}</small>
            </div>
            <div class="row-actions">
              <button type="button" :disabled="!source.is_available" @click="runAction(() => appStore.openSource(source.id))">打开</button>
              <a class="button-link" :href="api.downloadSourceUrl(source.id)">下载</a>
              <select :value="source.folder_id ?? -1" aria-label="移动到文件夹" @change="runAction(() => moveSource(source, Number(($event.target as HTMLSelectElement).value)))">
                <option :value="-1">根目录</option>
                <option v-for="folder in appStore.folders" :key="folder.id" :value="folder.id">{{ folder.name }}</option>
              </select>
              <button type="button" class="danger" @click="runAction(() => deleteSource(source.id))">删除</button>
            </div>
          </li>
        </ul>
      </section>
    </main>
  </section>
</template>
