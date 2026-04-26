<script setup lang="ts">
import { ref } from 'vue';

import { api } from '@/services/api';
import { useAppStore } from '@/stores/app';

const appStore = useAppStore();
const localPath = ref('');
const localName = ref('');
const webUrl = ref('');
const webName = ref('');
const uploadName = ref('');
const uploadFile = ref<File | null>(null);

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

async function uploadSource(): Promise<void> {
  if (!uploadFile.value) {
    appStore.notify('请先选择文件', true);
    return;
  }
  const formData = new FormData();
  formData.append('file', uploadFile.value);
  if (uploadName.value) formData.append('name', uploadName.value);
  await api.uploadSource(formData);
  uploadFile.value = null;
  uploadName.value = '';
  await appStore.refreshSources();
  appStore.notify('文件已上传');
}

async function addLocalSource(): Promise<void> {
  await api.addLocalSource({ path: localPath.value, name: localName.value });
  localPath.value = '';
  localName.value = '';
  await appStore.refreshSources();
  appStore.notify('本地源已添加');
}

async function addWebSource(): Promise<void> {
  await api.addWebSource({ url: webUrl.value, name: webName.value });
  webUrl.value = '';
  webName.value = '';
  await appStore.refreshSources();
  appStore.notify('网页源已添加');
}

async function deleteSource(sourceId: number): Promise<void> {
  if (!window.confirm('确定删除该媒体源吗？')) return;
  await api.deleteSource(sourceId);
  await appStore.refreshSources();
  appStore.notify('媒体源已删除');
}
</script>

<template>
  <section class="grid two">
    <article class="panel">
      <h2>上传文件</h2>
      <input type="file" @change="onFileSelected" />
      <input v-model="uploadName" placeholder="显示名称（可选）" />
      <button type="button" @click="runAction(uploadSource)">上传</button>
    </article>
    <article class="panel">
      <h2>添加本地路径</h2>
      <input v-model="localPath" placeholder="本地文件绝对路径" />
      <input v-model="localName" placeholder="显示名称（可选）" />
      <button type="button" @click="runAction(addLocalSource)">添加</button>
    </article>
    <article class="panel">
      <h2>添加网页</h2>
      <input v-model="webUrl" placeholder="https://example.com" />
      <input v-model="webName" placeholder="显示名称（可选）" />
      <button type="button" @click="runAction(addWebSource)">添加</button>
    </article>
  </section>

  <section class="panel">
    <div class="panel__header">
      <h2>所有媒体源</h2>
      <button type="button" @click="runAction(appStore.refreshSources)">刷新</button>
    </div>
    <ul class="source-list">
      <li v-for="source in appStore.sources" :key="source.id" class="source-card">
        <div>
          <span class="chip">{{ source.source_type }}</span>
          <strong>{{ source.name }}</strong>
          <small>{{ source.uri }}</small>
        </div>
        <div class="row-actions">
          <button type="button" :disabled="!source.is_available" @click="runAction(() => appStore.openSource(source.id))">打开</button>
          <button type="button" class="danger" @click="runAction(() => deleteSource(source.id))">删除</button>
        </div>
      </li>
    </ul>
  </section>
</template>
