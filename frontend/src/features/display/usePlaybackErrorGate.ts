import { computed, onBeforeUnmount, ref, watch } from 'vue';
import type { ComputedRef } from 'vue';

import type { SessionSnapshot } from '@/services/api';
import type { SourceCategory } from '@/stores/sources';

const STREAM_ERROR_CONFIRM_MS = 5000;

interface PlaybackErrorGateOptions {
  session: () => SessionSnapshot;
  category: () => SourceCategory;
}

/**
 * 延迟确认直播源错误，避免首帧握手或 SSE 抖动把瞬时 error 直接展示给操作员。
 * @param options 当前播放会话与源大类读取函数
 * @return 错误条展示状态与手动关闭动作
 */
export function usePlaybackErrorGate(options: PlaybackErrorGateOptions): {
  showErrorBar: ComputedRef<boolean>;
  dismissErrorBar: () => void;
} {
  const dismissedErrorKey = ref('');
  const streamErrorConfirmed = ref(false);
  let confirmTimer: number | null = null;

  const currentErrorKey = computed(() => {
    const session = options.session();
    return `${session.window_id}::${session.source_id ?? 0}::${session.source_type}::${session.playback_state}::${session.error_message || ''}`;
  });

  function clearConfirmTimer(): void {
    if (confirmTimer !== null) {
      window.clearTimeout(confirmTimer);
      confirmTimer = null;
    }
  }

  watch(
    () => [currentErrorKey.value, options.category()] as const,
    ([, category]) => {
      const session = options.session();
      clearConfirmTimer();
      streamErrorConfirmed.value = false;
      if (session.playback_state !== 'error') {
        dismissedErrorKey.value = '';
        return;
      }
      if (category !== 'stream') {
        streamErrorConfirmed.value = true;
        return;
      }
      confirmTimer = window.setTimeout(() => {
        streamErrorConfirmed.value = true;
        confirmTimer = null;
      }, STREAM_ERROR_CONFIRM_MS);
    },
    { immediate: true },
  );

  onBeforeUnmount(clearConfirmTimer);

  const showErrorBar = computed(() => {
    const session = options.session();
    if (session.playback_state !== 'error') return false;
    if (dismissedErrorKey.value === currentErrorKey.value) return false;
    return options.category() === 'stream' ? streamErrorConfirmed.value : true;
  });

  function dismissErrorBar(): void {
    dismissedErrorKey.value = currentErrorKey.value;
  }

  return { showErrorBar, dismissErrorBar };
}
