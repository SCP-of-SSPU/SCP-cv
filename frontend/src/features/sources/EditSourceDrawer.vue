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
  NAlert,
  NButton,
  NDrawer,
  NDrawerContent,
  NFormItem,
  NInput,
  NSelect,
  NSwitch,
} from 'naive-ui';

import { useToast } from '@/composables/useToast';
import { useSourceStore } from '@/stores/sources';
import type { MediaSourceItem, MediaSourceUpdate, PptBackend } from '@/services/api';

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
const draftPptBackend = ref<PptBackend>('libreoffice');
const saving = ref(false);
const errorMessage = ref('');

const isWebSource = computed(() => props.source?.source_type === 'web');
const isPptSource = computed(() => props.source?.source_type === 'ppt');
const pptBackendOptions = computed(() => [
  { label: t('sources.pptBackend.libreoffice'), value: 'libreoffice' },
  { label: t('sources.pptBackend.powerpoint'), value: 'powerpoint' },
  { label: t('sources.pptBackend.wps'), value: 'wps' },
]);

const isOpen = computed({
  get: () => props.open,
  set: (value: boolean) => emit('update:open', value),
});

watch(
  () => [props.open, props.source?.id] as const,
  ([isOpenVal, sourceId]) => {
    if (!isOpenVal || sourceId === undefined) return;
    const source = props.source!;
    draftName.value = source.name ?? '';
    draftUri.value = source.uri ?? '';
    draftPreheatEnabled.value = source.preheat_enabled ?? source.keep_alive ?? true;
    draftPptBackend.value = source.ppt_backend ?? 'libreoffice';
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
  if (isPptSource.value && draftPptBackend.value !== props.source.ppt_backend) {
    patch.ppt_backend = draftPptBackend.value;
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

function close(): void {
  emit('update:open', false);
}
</script>

<template>
  <n-drawer v-model:show="isOpen" :width="480" placement="right">
    <n-drawer-content :title="t('sources.editDrawer.title')" closable>
      <p v-if="source" class="edit-source__desc">{{ t('sources.editDrawer.desc', { name: source.name }) }}</p>

      <template v-if="source">
        <n-form-item :label="t('sources.editDrawer.displayName')" required :feedback="t('sources.editDrawer.displayNameHint')">
          <n-input v-model:value="draftName" :placeholder="t('sources.editDrawer.displayNamePlaceholder')" :disabled="saving" />
        </n-form-item>

        <template v-if="isWebSource">
          <n-form-item :label="t('sources.editDrawer.url')" required :feedback="t('sources.editDrawer.urlHint')">
            <n-input v-model:value="draftUri" placeholder="https://" :disabled="saving" :aria-label="t('sources.editDrawer.url')" />
          </n-form-item>
          <n-form-item :label="t('sources.editDrawer.preheat')" :feedback="t('sources.editDrawer.preheatHint')">
            <n-switch v-model:value="draftPreheatEnabled" :disabled="saving">
              <template #checked>{{ t('sources.editDrawer.preheatSwitch') }}</template>
              <template #unchecked>{{ t('sources.editDrawer.preheatSwitch') }}</template>
            </n-switch>
          </n-form-item>
        </template>

        <template v-if="isPptSource">
          <n-form-item :label="t('sources.pptBackend.label')" :feedback="t('sources.pptBackend.editHint')">
            <n-select v-model:value="draftPptBackend" :options="pptBackendOptions" :disabled="saving" />
          </n-form-item>
        </template>

        <n-alert v-if="!isWebSource && !isPptSource" type="info" :closable="false">
          {{ t('sources.editDrawer.nonWebInfo') }}
        </n-alert>
      </template>

      <n-alert v-if="errorMessage" type="error" :title="t('sources.editDrawer.cantSave')">
        {{ errorMessage }}
      </n-alert>

      <template #footer>
        <div class="edit-source__actions">
          <n-button :disabled="saving" @click="close">{{ t('common.cancel') }}</n-button>
          <n-button type="primary" :loading="saving" :disabled="!source || saving" @click="save">
            {{ t('sources.editDrawer.saveChanges') }}
          </n-button>
        </div>
      </template>
    </n-drawer-content>
  </n-drawer>
</template>

<style scoped>
.edit-source__desc {
  margin: 0 0 var(--spacingVerticalM);
  color: var(--colorNeutralForeground2);
  font-size: var(--fontSizeBase200);
}

.edit-source__actions {
  display: inline-flex;
  align-items: center;
  gap: var(--spacingHorizontalS);
  justify-content: flex-end;
  width: 100%;
}
</style>
