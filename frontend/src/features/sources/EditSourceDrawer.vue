<script setup lang="ts">
/*
 * 媒体源「编辑」抽屉。
 * 仅暴露安全可改写的字段：
 *   - 显示名称（所有源类型可编辑）；
 *   - URL（仅网页源；本地文件 / 流类型禁止改 URI 以防误改文件路径）；
 *   - 保持活跃（仅网页源参与播放器启动预热）。
 *
 * 使用 PATCH /api/sources/{id}/，仅传递发生变更的字段，避免误覆盖后端持久值。
 */
import { computed, ref, watch } from 'vue';

import {
  FButton,
  FDrawer,
  FField,
  FInput,
  FMessageBar,
  FSwitch,
} from '@/design-system';
import { useToast } from '@/composables/useToast';
import { useSourceStore } from '@/stores/sources';
import type { MediaSourceItem, MediaSourceUpdate } from '@/services/api';

const props = defineProps<{
  open: boolean;
  source: MediaSourceItem | null;
}>();

const emit = defineEmits<{
  (event: 'update:open', value: boolean): void;
  (event: 'updated', source: MediaSourceItem): void;
}>();

const sourceStore = useSourceStore();
const toast = useToast();

const draftName = ref('');
const draftUri = ref('');
const draftKeepAlive = ref(true);
const saving = ref(false);
const errorMessage = ref('');

const isWebSource = computed(() => props.source?.source_type === 'web');

watch(
  () => [props.open, props.source?.id] as const,
  ([isOpen, sourceId]) => {
    if (!isOpen || sourceId === undefined) return;
    const source = props.source!;
    draftName.value = source.name ?? '';
    draftUri.value = source.uri ?? '';
    draftKeepAlive.value = source.keep_alive ?? true;
    errorMessage.value = '';
  },
  { immediate: true },
);

function buildPatch(): MediaSourceUpdate | null {
  if (!props.source) return null;
  const patch: MediaSourceUpdate = {};
  const trimmedName = draftName.value.trim();
  if (trimmedName && trimmedName !== props.source.name) {
    patch.name = trimmedName;
  }
  if (isWebSource.value) {
    const trimmedUri = draftUri.value.trim();
    if (trimmedUri && trimmedUri !== props.source.uri) {
      patch.uri = trimmedUri;
    }
    if (draftKeepAlive.value !== props.source.keep_alive) {
      patch.keep_alive = draftKeepAlive.value;
    }
  }
  return Object.keys(patch).length > 0 ? patch : null;
}

async function save(): Promise<void> {
  if (!props.source) return;
  errorMessage.value = '';
  if (!draftName.value.trim()) {
    errorMessage.value = '显示名称不能为空';
    return;
  }
  const patch = buildPatch();
  if (!patch) {
    toast.info('未修改任何字段');
    emit('update:open', false);
    return;
  }
  saving.value = true;
  try {
    const updated = await sourceStore.updateSource(props.source.id, patch);
    toast.success('媒体源已更新', updated.name);
    emit('updated', updated);
    emit('update:open', false);
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '保存失败，请稍后重试';
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <FDrawer
    :open="open"
    title="编辑媒体源"
    :description="source ? `修改「${source.name}」的可编辑字段` : ''"
    :width="480"
    hide-default-actions
    @update:open="(value) => emit('update:open', value)"
  >
    <template v-if="source">
      <FField label="显示名称" required hint="操作员在源列表与切换面板中看到的名称">
        <FInput v-model="draftName" placeholder="例如：早会 PPT" :disabled="saving" />
      </FField>

      <template v-if="isWebSource">
        <FField label="URL 或 ip:port" required hint="支持 http/https、ip:port、file:// 协议">
          <FInput v-model="draftUri" placeholder="https://" :disabled="saving" />
        </FField>
        <FField
          label="保持活跃"
          hint="开启后系统启动时自动加载该网页并在后台保持，切换到此源时无需再次首屏加载。"
        >
          <FSwitch v-model="draftKeepAlive" label="启用预热与后台活跃" :disabled="saving" />
        </FField>
      </template>

      <FMessageBar v-if="!isWebSource" tone="info" :dismissible="false">
        非网页源仅允许编辑显示名称；如需更换文件，请删除后重新上传。
      </FMessageBar>
    </template>

    <FMessageBar v-if="errorMessage" tone="error" title="无法保存">
      {{ errorMessage }}
    </FMessageBar>

    <template #actions="{ cancel }">
      <FButton appearance="secondary" :disabled="saving" @click="cancel">取消</FButton>
      <FButton appearance="primary" :loading="saving" :disabled="!source || saving" @click="save">
        保存修改
      </FButton>
    </template>
  </FDrawer>
</template>
