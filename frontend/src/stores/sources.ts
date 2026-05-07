/*
 * 媒体源 Store：列表、按类型筛选、上传、删除。
 *
 * 设计稿 §4.4：
 *   - 不再支持「文件夹」概念；
 *   - 直播源聚合 srt_stream / rtsp_stream / custom_stream 三种 source_type；
 *   - UI 只暴露「上传文件 / 网页」两种添加入口；
 *   - 不再向 UI 展示「音频源」。后端 SourceType 仍保留 audio 作为兼容枚举，
 *     但 store 在写入前会把 audio 源过滤掉，使其不出现在列表 / 选择器 / 预案下拉中；
 *     已存在的 audio 会话回退用「视频」分支控制条，避免 UI 崩坏。
 */
import { defineStore } from 'pinia';

import { api, type MediaSourceItem, type MediaSourceUpdate, type UploadOptions } from '@/services/api';

/** UI 可视的源大类；与后端 source_type 不一一映射，直播由前端聚合。 */
export type SourceCategory = 'all' | 'ppt' | 'video' | 'image' | 'web' | 'stream';

/**
 * 后端真实 source_type 字段映射到前端大类的策略。
 * 注意：`audio` 没有独立 UI 大类，统一并入 `video` 分支以确保已存在的 audio 会话
 *      仍能套用「视频/音频控制」UI；列表层面会在 sources getter 之外把 audio 源过滤掉。
 */
const SOURCE_TYPE_TO_CATEGORY: Record<string, SourceCategory> = {
  ppt: 'ppt',
  video: 'video',
  image: 'image',
  audio: 'video',
  web: 'web',
  srt_stream: 'stream',
  rtsp_stream: 'stream',
  custom_stream: 'stream',
};

/**
 * 判断后端返回的源是否对 UI 可见。
 * 设计稿要求不再展示音频源；audio source_type 直接被过滤掉。
 * @param source 后端返回的媒体源
 * @return 是否纳入 store 展示列表
 */
function isVisibleSource(source: MediaSourceItem): boolean {
  return source.source_type !== 'audio';
}

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
        web: 0,
        stream: 0,
      };
      for (const source of state.sources) {
        const category = SOURCE_TYPE_TO_CATEGORY[source.source_type];
        if (category && category !== 'all') result[category] += 1;
      }
      return result;
    },
    /**
     * 当前 Tab + 搜索过滤后的列表，按显示名称首字母升序排列，
     * 中文走 `localeCompare('zh-Hans-CN')` 自动按拼音首字母分组，
     * 英文则按字母顺序，确保大量源时操作员能快速定位。
     */
    filtered(state): MediaSourceItem[] {
      const keyword = state.searchKeyword.trim().toLowerCase();
      const matched = state.sources.filter((source) => {
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
      // 优先使用 `co-pinyin` collation 按汉语拼音首字母对中文排序，与英文混排；
      // 不支持该 collation 的运行时（部分 Node / 旧 Chromium）会自动 fallback 到 'zh-Hans-CN'。
      const collator = new Intl.Collator(['zh-Hans-CN-u-co-pinyin', 'zh-Hans-CN'], { numeric: true, sensitivity: 'base' });
      return [...matched].sort((a, b) => collator.compare(a.name ?? '', b.name ?? ''));
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
      // 设计稿外延：UI 不再展示音频源；后端如返回 audio 类型源也一并过滤。
      this.sources = payload.sources.filter(isVisibleSource);
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
      // 同时过滤 audio：即便用户上传了 .mp3，UI 也不展示。
      if (!options.isTemporary && isVisibleSource(payload.source)) {
        this.sources = [payload.source, ...this.sources];
      }
      return payload.source;
    },
    /**
     * 添加网页/URL 源。
     * @param url 网页地址或 ip:port
     * @param name 显示名称；省略时后端用 URL 截前 80 字符作名称
     * @param keepAlive 启动时是否预热并保持后台活跃（默认 true）
     */
    async addWebSource(url: string, name?: string, keepAlive: boolean = true): Promise<MediaSourceItem> {
      const payload = await api.addWebSource({ url, name, keep_alive: keepAlive });
      // 网页源不会是 audio，直接前置即可。
      this.sources = [payload.source, ...this.sources];
      return payload.source;
    },
    /**
     * 更新已存在源的可编辑字段。
     * @param sourceId 源主键
     * @param patch 仅传入需要修改的字段；未传字段保持后端原值
     */
    async updateSource(sourceId: number, patch: MediaSourceUpdate): Promise<MediaSourceItem> {
      const payload = await api.updateSource(sourceId, patch);
      this.sources = this.sources.map((item) => (item.id === sourceId ? payload.source : item));
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
