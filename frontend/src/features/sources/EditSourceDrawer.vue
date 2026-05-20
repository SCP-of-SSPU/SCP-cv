<script setup lang="ts">
/*
 * 媒体源「编辑」抽屉。
 * 仅暴露安全可改写的字段：
 *   - 显示名称（所有源类型可编辑）；
 *   - URL（仅网页源；本地文件 / 流类型禁止改 URI 以防误改文件路径）；
 *   - 预热（仅网页源参与播放器启动预加载）。
 *
 * 使用 PATCH /api/sources/{id}/，仅传递发生变更的字段，避免误覆盖后端持久值。
 */
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';

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

const { t } = useI18n();
const sourceStore = useSourceStore();
const toast = useToast();

const draftName = ref('');
const draftUri = ref('');
const draftPreheatEnabled = ref(true);
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
    draftPreheatEnabled.value = source.preheat_enabled ?? source.keep_alive ?? true;
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
    const currentPreheat = props.source.preheat_enabled ?? props.source.keep_alive ?? true;
    if (draftPreheatEnabled.value !== currentPreheat) {
      patch.preheat_enabled = draftPreheatEnabled.value;
    }
  }
  return Object.keys(patch).length > 0 ? patch : null;
}

async function save(): Promise<void> {
  if (!props.source) return;
  errorMessage.value = '';
  if (!draftName.value.trim()) {
    errorMessage.value = t('sources.editDrawer.nameEmpty');
    return;
  }
  const patch = buildPatch();
  if (!patch) {
    toast.info(t('sources.editDrawer.noChange'));
    emit('update:open', false);
    return;
  }
  saving.value = true;
  try {
    const updated = await sourceStore.updateSource(props.source.id, patch);
    toast.success(t('sources.editDrawer.updatedOk'), updated.name);
    emit('updated', updated);
    emit('update:open', false);
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : t('sources.editDrawer.saveFail');
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <FDrawer
    :open="open"
    :title="t('sources.editDrawer.title')"
    :description="source ? t('sources.editDrawer.desc', { name: source.name }) : ''"
    :width="480"
    hide-default-actions
    @update:open="(value) => emit('update:open', value)"
  >
    <template v-if="source">
      <FField :label="t('sources.editDrawer.displayName')" required :hint="t('sources.editDrawer.displayNameHint')">
        <FInput v-model="draftName" :placeholder="t('sources.editDrawer.displayNamePlaceholder')" :disabled="saving" />
      </FField>

      <template v-if="isWebSource">
        <FField :label="t('sources.editDrawer.url')" required :hint="t('sources.editDrawer.urlHint')">
          <FInput v-model="draftUri" placeholder="https://" :disabled="saving" :aria-label="t('sources.editDrawer.url')" />
        </FField>
        <FField
          :label="t('sources.editDrawer.preheat')"
          :hint="t('sources.editDrawer.preheatHint')"
        >
          <FSwitch v-model="draftPreheatEnabled" :label="t('sources.editDrawer.preheatSwitch')" :disabled="saving" />
        </FField>
      </template>

      <FMessageBar v-if="!isWebSource" tone="info" :dismissible="false">
        {{ t('sources.editDrawer.nonWebInfo') }}
      </FMessageBar>
    </template>

    <FMessageBar v-if="errorMessage" tone="error" :title="t('sources.editDrawer.cantSave')">
      {{ errorMessage }}
    </FMessageBar>

    <template #actions="{ cancel }">
      <FButton appearance="secondary" :disabled="saving" @click="cancel">{{ t('common.cancel') }}</FButton>
      <FButton appearance="primary" :loading="saving" :disabled="!source || saving" @click="save">
        {{ t('sources.editDrawer.saveChanges') }}
      </FButton>
    </template>
  </FDrawer>
</template>
