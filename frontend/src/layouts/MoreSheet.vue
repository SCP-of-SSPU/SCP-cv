<script setup lang="ts">
/**
 * 移动端「更多」 Sheet：列出二级入口。
 * tabbar「更多」弹出底部 Sheet（DESIGN.md §2 Scale 适配下的移动端导航形态）。
 */
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import {
  NButton,
  NCard,
  NDrawer,
  NDrawerContent,
  NRadio,
  NRadioGroup,
  NSwitch,
} from 'naive-ui';

import EmergencyMenu from './EmergencyMenu.vue';
import FIcon from '@/design-system/FIcon.vue';
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
  set: async (mode: string) => {
    try {
      await runtime.setBigScreenMode(mode as 'single' | 'double');
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

const isOpen = computed({
  get: () => props.open,
  set: (value: boolean) => emit('update:open', value),
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
  await router.push('/settings');
}

void EmergencyMenu;
void dialog;
</script>

<template>
  <n-drawer v-model:show="isOpen" :width="360" placement="bottom" :height="480">
    <n-drawer-content :title="t('more.title')" closable>
      <p class="more-sheet__desc">{{ t('more.desc') }}</p>

      <n-card size="small" :title="t('more.screenMode')" class="more-sheet__card">
        <n-radio-group v-model:value="screenMode">
          <n-radio value="single">{{ t('screen.single') }}</n-radio>
          <n-radio value="double">{{ t('screen.double') }}</n-radio>
        </n-radio-group>
        <p class="more-sheet__hint">{{ t('more.screenHint') }}</p>
      </n-card>

      <n-card size="small" :title="t('more.systemMute')" class="more-sheet__card">
        <n-switch v-model:value="muteToggle">
          <template #checked>{{ t('more.enableSystemMute') }}</template>
          <template #unchecked>{{ t('more.enableSystemMute') }}</template>
        </n-switch>
      </n-card>

      <n-card size="small" :title="t('more.settings')" class="more-sheet__card">
        <n-button quaternary block @click="navigate('/background-audio')">
          <template #icon><FIcon name="music_note_2_24_regular" /></template>
          {{ t('more.openBackgroundAudio') }}
        </n-button>
        <n-button quaternary block @click="navigate('/settings')">
          <template #icon><FIcon name="settings_24_regular" /></template>
          {{ t('more.openSettings') }}
        </n-button>
        <n-button quaternary block @click="onAboutHelp">
          <template #icon><FIcon name="info_24_regular" /></template>
          {{ t('more.aboutHelp') }}
        </n-button>
      </n-card>
    </n-drawer-content>
  </n-drawer>
</template>

<style scoped>
.more-sheet__desc {
  margin: 0 0 var(--spacingVerticalM);
  color: var(--colorNeutralForeground2);
  font-size: var(--fontSizeBase200);
}
.more-sheet__card {
  margin-bottom: var(--spacingVerticalM);
}
.more-sheet__hint {
  margin: var(--spacingVerticalS) 0 0;
  color: var(--colorNeutralForeground3);
  font-size: var(--fontSizeBase200);
}
</style>
