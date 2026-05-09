import type { TagTone } from '@/design-system';
import type { MediaSourceItem } from '@/services/api';
import { SOURCE_TYPE_TO_CATEGORY, type SourceCategory } from '@/stores/sources';

/** 将后端 source_type 聚合成前端可视大类。 */
export function resolveSourceCategory(source: MediaSourceItem): SourceCategory {
  return SOURCE_TYPE_TO_CATEGORY[source.source_type] ?? 'all';
}

/** 媒体源类型标签文案，保持 SourcesView 与 SourcePicker 一致。 */
export function sourceCategoryLabel(source: MediaSourceItem): string {
  switch (resolveSourceCategory(source)) {
    case 'ppt':
      return 'PPT';
    case 'video':
      return '视频';
    case 'image':
      return '图片';
    case 'web':
      return '网页';
    case 'stream':
      return '直播';
    default:
      return '其它';
  }
}

/** 媒体源类型图标，供缩略图缺失或源不可预览时回退。 */
export function sourceCategoryIcon(source: MediaSourceItem): string {
  switch (resolveSourceCategory(source)) {
    case 'ppt':
      return 'document_24_regular';
    case 'video':
      return 'video_24_regular';
    case 'image':
      return 'image_24_regular';
    case 'web':
      return 'globe_24_regular';
    case 'stream':
      return 'live_24_regular';
    default:
      return 'document_24_regular';
  }
}

/** 媒体源类型标签色彩，直播源额外体现在线状态。 */
export function sourceCategoryTone(source: MediaSourceItem): TagTone {
  switch (resolveSourceCategory(source)) {
    case 'ppt':
      return 'info';
    case 'video':
      return 'success';
    case 'image':
    case 'web':
      return 'subtle';
    case 'stream':
      return source.is_available ? 'warning' : 'error';
    default:
      return 'subtle';
  }
}
