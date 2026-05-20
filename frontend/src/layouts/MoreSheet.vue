<script setup lang="ts">
/**
 * 移动端「更多」 Sheet：列出二级入口。
 * 设计稿 §7.2：tabbar 「更多」 弹出底部 Sheet。
 */
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';

import EmergencyMenu from './EmergencyMenu.vue';
import { FButton, FCard, FDrawer, FIcon, FSegmented, FSwitch } from '@/design-system';
import { useDialog } from '@/composables/useDialog';
import { useToast } from '@/composables/useToast';
import { useRuntimeStore } from '@/stores/runtime';

const props = defineProps<{ open: boolean }>();
const emit = defineEmits<{ (event: 'update:open', value: boolean): void }>();

const { t } = useI18n();
const router = useRouter();
const runtime = useRuntimeStore();
const dialog = useDialog();
const toast = useToast();

const screenMode = computed({
  get: () => runtime.runtime?.big_screen_mode ?? 'single',
  set: async (mode: 'single' | 'double') => {
    try {
      await runtime.setBigScreenMode(mode);
      toast.success(mode === 'double' ? t('more.switchedDouble') : t('more.switchedSingle'));
    } catch (error) {
      toast.error(t('more.switchFail'), error instanceof Error ? error.message : t('common.retry'));
    }
  },
});

const muteToggle = computed({
  get: () => runtime.systemVolume.muted,
  set: async (next: boolean) => {
    try {
      await runtime.setSystemVolume(runtime.systemVolume.level, next);
    } catch (error) {
      toast.error(t('more.muteFail'), error instanceof Error ? error.message : t('common.retry'));
    }
  },
});

function close(): void {
  emit('update:open', false);
}

function navigate(path: string): void {
  close();
  void router.push(path);
}

async function onAboutHelp(): Promise<void> {
  close();
  // 直接进设置「开发」分组，免单独的「关于」页。
  await router.push('/settings');
}

void props;
void EmergencyMenu;
void dialog; // 当前 Sheet 不直接调用，但保留依赖以便未来在更多里加确认。
void FIcon;
</script>

<template>
  <FDrawer
    :open="open"
    :title="t('more.title')"
    :description="t('more.desc')"
    :primary-label="t('common.close')"
    :secondary-label="t('common.back')"
    :hide-default-actions="true"
    @update:open="(value) => emit('update:open', value)"
  >
    <FCard padding="compact">
      <template #title>{{ t('more.screenMode') }}</template>
      <FSegmented
        v-model="screenMode"
        :options="[
          { label: t('screen.single'), value: 'single' },
          { label: t('screen.double'), value: 'double' },
        ]"
        full-width
      />
      <p class="more-sheet__hint">
        {{ t('more.screenHint') }}
      </p>
    </FCard>

    <FCard padding="compact">
      <template #title>{{ t('more.systemMute') }}</template>
      <FSwitch v-model="muteToggle" :label="t('more.enableSystemMute')" />
    </FCard>

    <FCard padding="compact">
      <template #title>{{ t('more.settings') }}</template>
      <FButton appearance="subtle" full-width icon-start="settings_24_regular" @click="navigate('/settings')">
        {{ t('more.openSettings') }}
      </FButton>
      <FButton appearance="subtle" full-width icon-start="info_24_regular" @click="onAboutHelp">
        {{ t('more.aboutHelp') }}
      </FButton>
    </FCard>
  </FDrawer>
</template>

<style scoped>
.more-sheet__hint {
  margin: 0;
  color: var(--color-text-tertiary);
  font-size: var(--type-caption1-size);
}
</style>
