<script setup lang="ts">
/**
 * 媒体源缩略图。
 * 优先使用后端返回的真实预览；缺失或加载失败时回退到源类型图标。
 */
import { computed, ref, watch } from 'vue';
import { NTooltip } from 'naive-ui';

import FIcon from '@/design-system/FIcon.vue';
import { buildBackendUrl, type MediaSourceItem } from '@/services/api';
import { sourceCategoryIcon } from './sourcePresentation';

const props = withDefaults(defineProps<{
  source: MediaSourceItem;
  size?: 'compact' | 'comfortable' | 'stage';
  imageUrl?: string;
}>(), {
  size: 'compact',
  imageUrl: '',
});

const loadFailed = ref(false);
const rawPreviewUrl = computed(() => props.imageUrl || props.source.thumbnail_url || props.source.preview_url || '');
const previewUrl = computed(() => (rawPreviewUrl.value ? buildBackendUrl(rawPreviewUrl.value) : ''));
const previewKind = computed(() => props.source.preview_kind || 'icon');
const fallbackIcon = computed(() => sourceCategoryIcon(props.source));
const canRenderPreview = computed(() => !!previewUrl.value && previewKind.value !== 'icon' && !loadFailed.value);

watch(rawPreviewUrl, () => {
  loadFailed.value = false;
});

function markFailed(): void {
  loadFailed.value = true;
}
</script>

<template>
  <n-tooltip placement="top">
    <template #trigger>
      <span class="source-thumbnail" :class="[
        `source-thumbnail--${size}`,
        { 'source-thumbnail--media': canRenderPreview },
      ]">
        <img v-if="canRenderPreview && previewKind === 'image'" :src="previewUrl" :alt="source.name" loading="lazy"
          @error="markFailed" />
        <video v-else-if="canRenderPreview && previewKind === 'video'" :src="`${previewUrl}#t=0.1`" muted playsinline
          preload="metadata" aria-hidden="true" @error="markFailed" />
        <FIcon v-else class="source-thumbnail__icon" :name="fallbackIcon" />
      </span>
    </template>
    {{ source.preview_label || source.name }}
  </n-tooltip>
</template>

<style scoped>
.source-thumbnail {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--borderRadiusSmall);
  background: var(--colorNeutralBackground2);
  overflow: hidden;
  box-shadow: inset 0 0 0 1px var(--colorNeutralStroke2);
}

.source-thumbnail--compact {
  width: 40px;
  height: 30px;
}

.source-thumbnail--comfortable {
  width: 48px;
  height: 36px;
}

.source-thumbnail--stage {
  width: min(100%, 320px);
  aspect-ratio: 16 / 9;
  border-radius: var(--borderRadiusMedium);
}

.source-thumbnail--stage .source-thumbnail__icon {
  font-size: 3rem;
}

.source-thumbnail--media {
  background: var(--colorNeutralBackgroundInverted, #000);
}

.source-thumbnail img,
.source-thumbnail video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  pointer-events: none;
}

.source-thumbnail__icon {
  font-size: 1.375rem;
  color: var(--colorNeutralForeground2);
}
</style>
