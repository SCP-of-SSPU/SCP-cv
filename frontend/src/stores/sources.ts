/*
 * 媒体源 Store：列表、按类型筛选、上传、删除。
 *
 * 设计稿 §4.4：
 *   - 不再支持「文件夹」概念；
 *   - 直播源聚合 srt_stream / rtsp_stream / custom_stream 三种 source_type；
 *   - UI 只暴露「上传文件 / 网页」两种添加入口。
 */
import { defineStore } from 'pinia';

import { api, type MediaSourceItem, type UploadOptions } from '@/services/api';

/** UI 可视的源大类；与后端 source_type 不一一映射，直播由前端聚合。 */
export type SourceCategory = 'all' | 'ppt' | 'video' | 'image' | 'audio' | 'web' | 'stream';

/** 后端真实 source_type 字段映射到前端大类的策略。 */
const SOURCE_TYPE_TO_CATEGORY: Record<string, SourceCategory> = {
  ppt: 'ppt',
  video: 'video',
  image: 'image',
  audio: 'audio',
  web: 'web',
  srt_stream: 'stream',
  rtsp_stream: 'stream',
  custom_stream: 'stream',
};

interface SourceState {
  sources: MediaSourceItem[];
  /** 当前选中的类型 Tab；默认 all。 */
  category: SourceCategory;
  /** 名称/URL 即时搜索关键字。 */
  searchKeyword: string;
}

export const useSourceStore = defineStore('sources', {
  state: (): SourceState => ({
    sources: [],
    category: 'all',
    searchKeyword: '',
  }),
  getters: {
    /** 类型计数：用于侧栏 NavList / Pills 数字徽章。 */
    countByCategory(state): Record<SourceCategory, number> {
      const result: Record<SourceCategory, number> = {
        all: state.sources.length,
        ppt: 0,
        video: 0,
        image: 0,
        audio: 0,
        web: 0,
        stream: 0,
      };
      for (const source of state.sources) {
        const category = SOURCE_TYPE_TO_CATEGORY[source.source_type];
        if (category && category !== 'all') result[category] += 1;
      }
      return result;
    },
    /** 当前 Tab + 搜索过滤后的列表，用于渲染 DetailList / 卡片列表。 */
    filtered(state): MediaSourceItem[] {
      const keyword = state.searchKeyword.trim().toLowerCase();
      return state.sources.filter((source) => {
        if (state.category !== 'all') {
          const cat = SOURCE_TYPE_TO_CATEGORY[source.source_type];
          if (cat !== state.category) return false;
        }
        if (!keyword) return true;
        const name = source.name?.toLowerCase() ?? '';
        const uri = source.uri?.toLowerCase() ?? '';
        const original = source.original_filename?.toLowerCase() ?? '';
        return name.includes(keyword) || uri.includes(keyword) || original.includes(keyword);
      });
    },
    /** 占用空间统计（仅文件型源）。 */
    totalBytes(state): number {
      return state.sources.reduce((acc, source) => acc + (source.file_size || 0), 0);
    },
  },
  actions: {
    setCategory(category: SourceCategory): void {
      this.category = category;
    },
    setSearchKeyword(keyword: string): void {
      this.searchKeyword = keyword;
    },
    async refresh(): Promise<void> {
      const payload = await api.listSources('', null);
      this.sources = payload.sources;
    },
    /** 上传源；支持「上传但不保存（is_temporary）」/「上传并保存」两种语义。 */
    async upload(file: File, options: { name?: string; isTemporary?: boolean; onProgress?: (percent: number) => void }): Promise<MediaSourceItem> {
      const formData = new FormData();
      formData.append('file', file);
      if (options.name) formData.append('name', options.name);
      if (options.isTemporary) formData.append('is_temporary', 'true');
      const uploadOptions: UploadOptions = options.onProgress ? { onProgress: options.onProgress } : {};
      const payload = await api.uploadSource(formData, uploadOptions);
      // 仅持久源加入列表；临时源不入列表（避免出现在管理页）。
      if (!options.isTemporary) {
        this.sources = [payload.source, ...this.sources];
      }
      return payload.source;
    },
    /** 添加网页/URL 源。 */
    async addWebSource(url: string, name?: string): Promise<MediaSourceItem> {
      const payload = await api.addWebSource({ url, name });
      this.sources = [payload.source, ...this.sources];
      return payload.source;
    },
    /** 删除源；删除当前类型时若列表为空 UI 会自动展示空态。 */
    async deleteSource(sourceId: number): Promise<void> {
      await api.deleteSource(sourceId);
      this.sources = this.sources.filter((source) => source.id !== sourceId);
    },
    /**
     * 把后端 source_type 字段映射到前端 UI 大类，便于在视图层判断。
     * @param sourceType 后端 source_type
     * @return 前端 UI 大类
     */
    resolveCategory(sourceType: string): SourceCategory {
      return SOURCE_TYPE_TO_CATEGORY[sourceType] ?? 'all';
    },
  },
});

export { SOURCE_TYPE_TO_CATEGORY };
