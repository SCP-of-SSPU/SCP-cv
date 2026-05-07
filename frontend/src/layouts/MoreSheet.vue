<script setup lang="ts">
/**
 * 移动端「更多」 Sheet：列出二级入口。
 * 设计稿 §7.2：tabbar 「更多」 弹出底部 Sheet。
 */
import { computed } from 'vue';
import { useRouter } from 'vue-router';

import EmergencyMenu from './EmergencyMenu.vue';
import { FButton, FCard, FDrawer, FIcon, FSegmented, FSwitch } from '@/design-system';
import { useDialog } from '@/composables/useDialog';
import { useToast } from '@/composables/useToast';
import { useRuntimeStore } from '@/stores/runtime';

const props = defineProps<{ open: boolean }>();
const emit = defineEmits<{ (event: 'update:open', value: boolean): void }>();

const router = useRouter();
const runtime = useRuntimeStore();
const dialog = useDialog();
const toast = useToast();

const screenMode = computed({
  get: () => runtime.runtime?.big_screen_mode ?? 'single',
  set: async (mode: 'single' | 'double') => {
    try {
      await runtime.setBigScreenMode(mode);
      toast.success(mode === 'double' ? '已切换为双屏' : '已切换为单屏');
    } catch (error) {
      toast.error('切换失败', error instanceof Error ? error.message : '请稍后重试');
    }
  },
});

const muteToggle = computed({
  get: () => runtime.systemVolume.muted,
  set: async (next: boolean) => {
    try {
      await runtime.setSystemVolume(runtime.systemVolume.level, next);
    } catch (error) {
      toast.error('系统静音切换失败', error instanceof Error ? error.message : '请稍后重试');
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
    title="更多"
    description="次级入口与全局设置"
    :primary-label="'关闭'"
    :secondary-label="'返回'"
    :hide-default-actions="true"
    @update:open="(value) => emit('update:open', value)"
  >
    <FCard padding="compact">
      <template #title>大屏模式</template>
      <FSegmented
        v-model="screenMode"
        :options="[
          { label: '单屏', value: 'single' },
          { label: '双屏', value: 'double' },
        ]"
        full-width
      />
      <p class="more-sheet__hint">
        切换会立即生效；单屏模式下窗口 2 自动静音。
      </p>
    </FCard>

    <FCard padding="compact">
      <template #title>系统静音</template>
      <FSwitch v-model="muteToggle" label="启用系统静音" />
    </FCard>

    <FCard padding="compact">
      <template #title>设置</template>
      <FButton appearance="subtle" full-width icon-start="settings_24_regular" @click="navigate('/settings')">
        打开设置中心
      </FButton>
      <FButton appearance="subtle" full-width icon-start="info_24_regular" @click="onAboutHelp">
        关于与帮助
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
