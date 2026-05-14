<script setup lang="ts">
/*
 * PPT 专注页幻灯片缩略图栏：展示全部页面并提供快速跳页入口。
 */
import { nextTick, watch, type ComponentPublicInstance } from 'vue';

import { FIcon } from '@/design-system';

interface PptSlideRailItem {
  pageIndex: number;
  imageUrl: string;
  hasMedia: boolean;
}

interface PptSlideRailProps {
  items: PptSlideRailItem[];
  currentPage: number;
  totalPages: number;
}

const props = defineProps<PptSlideRailProps>();
const emit = defineEmits<{
  jump: [pageIndex: number];
}>();

const itemRefs = new Map<number, HTMLElement>();

watch(
  () => [props.currentPage, props.items.length] as const,
  () => scrollCurrentSlideIntoView(),
  { immediate: true, flush: 'post' },
);

function setItemRef(
  pageIndex: number,
  element: Element | ComponentPublicInstance | null,
): void {
  if (element instanceof HTMLElement) {
    itemRefs.set(pageIndex, element);
    return;
  }
  itemRefs.delete(pageIndex);
}

function scrollCurrentSlideIntoView(): void {
  void nextTick(() => {
    const activeItem = itemRefs.get(props.currentPage);
    activeItem?.scrollIntoView({ block: 'nearest', inline: 'nearest' });
  });
}

function requestJump(pageIndex: number): void {
  emit('jump', pageIndex);
}
</script>

<template>
  <aside class="ppt-slide-rail" aria-label="PPT 页面缩略图">
    <header class="ppt-slide-rail__header">
      <span class="ppt-slide-rail__title">页面</span>
      <span class="ppt-slide-rail__count">{{ currentPage }}/{{ totalPages || items.length }}</span>
    </header>

    <div class="ppt-slide-rail__list" role="list">
      <button
        v-for="item in items"
        :key="item.pageIndex"
        :ref="(element) => setItemRef(item.pageIndex, element)"
        type="button"
        class="ppt-slide-rail__item"
        :class="{ 'ppt-slide-rail__item--active': item.pageIndex === currentPage }"
        :aria-current="item.pageIndex === currentPage ? 'page' : undefined"
        :aria-label="`跳转到第 ${item.pageIndex} 页`"
        @click="requestJump(item.pageIndex)"
      >
        <span class="ppt-slide-rail__thumb">
          <img v-if="item.imageUrl" :src="item.imageUrl" :alt="`第 ${item.pageIndex} 页预览`" />
          <span v-else class="ppt-slide-rail__fallback">
            <FIcon name="document_24_regular" />
          </span>
        </span>
        <span class="ppt-slide-rail__meta">
          <span class="ppt-slide-rail__page">{{ item.pageIndex }}</span>
          <span v-if="item.hasMedia" class="ppt-slide-rail__media" aria-label="该页包含媒体" />
        </span>
      </button>

      <p v-if="items.length === 0" class="ppt-slide-rail__empty">暂无页面预览</p>
    </div>
  </aside>
</template>

<style scoped src="./PptSlideRail.css"></style>
