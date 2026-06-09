import { t } from '@/locales';

export interface MediaFolderItem {
  id: number;
  name: string;
  parent_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface MediaSourceItem {
  id: number;
  source_type: string;
  name: string;
  uri: string;
  is_available: boolean;
  stream_identifier: string;
  folder_id: number | null;
  original_filename: string;
  file_size: number;
  mime_type: string;
  is_temporary: boolean;
  expires_at: string | null;
  metadata: Record<string, unknown>;
  /**
   * 是否在播放器启动时预热媒体源。
   * keep_alive 是旧字段兼容别名，后续 UI 只展示 preheat_enabled。
   */
  preheat_enabled: boolean;
  keep_alive: boolean;
  preview_url: string;
  thumbnail_url: string;
  preview_kind: 'icon' | 'image' | 'video';
  preview_label: string;
  created_at: string;
}

/** PATCH /api/sources/{id}/ 可编辑字段子集。 */
export interface MediaSourceUpdate {
  name?: string;
  uri?: string;
  preheat_enabled?: boolean;
  keep_alive?: boolean;
}

export interface SessionSnapshot {
  window_id: number;
  session_id: number;
  source_id: number | null;
  source_name: string;
  source_type: string;
  source_type_label: string;
  source_uri: string;
  playback_state: string;
  playback_state_label: string;
  error_message: string;
  display_mode: string;
  display_mode_label: string;
  target_display_label: string;
  spliced_display_label: string;
  is_spliced: boolean;
  current_slide: number;
  total_slides: number;
  position_ms: number;
  duration_ms: number;
  pending_command: string;
  last_updated_at: string;
  volume: number;
  is_muted: boolean;
  loop_enabled: boolean;
}

export interface BackgroundAudioStateSnapshot {
  id: number;
  source_id: number | null;
  source_name: string;
  source_uri: string;
  source: MediaSourceItem | null;
  current_item_id: number | null;
  playback_state: string;
  playback_state_label: string;
  error_message: string;
  position_ms: number;
  duration_ms: number;
  volume: number;
  is_muted: boolean;
  loop_enabled: boolean;
  pending_command: string;
  updated_at: string;
}

export interface BackgroundAudioPlaylistItem {
  id: number;
  source_id: number;
  source_name: string;
  sort_order: number;
  created_at: string;
  source: MediaSourceItem;
}

export interface BackgroundAudioSnapshot {
  state: BackgroundAudioStateSnapshot;
  playlist: BackgroundAudioPlaylistItem[];
}

export interface BackgroundAudioPayload {
  success: boolean;
  background_audio: BackgroundAudioSnapshot;
}

export interface RuntimeSnapshot {
  big_screen_mode: 'single' | 'double';
  volume_level: number;
  muted_windows: number[];
}

export interface ScenarioTargetItem {
  window_id: number;
  source_state: 'unset' | 'empty' | 'set';
  source_id: number | null;
  source_name: string;
  autoplay: boolean;
  resume: boolean;
}

export interface ScenarioItem {
  id: number;
  name: string;
  description: string;
  sort_order: number;
  big_screen_mode_state: 'unset' | 'empty' | 'set';
  big_screen_mode: 'single' | 'double';
  big_screen_mode_label: string;
  volume_state: 'unset' | 'empty' | 'set';
  volume_level: number;
  targets: ScenarioTargetItem[];
  created_at: string;
  updated_at: string;
}

export interface DisplayTargetItem {
  index: number;
  name: string;
  width: number;
  height: number;
  x: number;
  y: number;
  is_primary: boolean;
}

export interface DeviceItem {
  name: string;
  device_type: 'splice_screen' | 'tv_left' | 'tv_right';
  device_type_label?: string;
  host?: string;
  port?: number;
  action?: string;
  detail?: string;
}

export interface PptMediaItem {
  id: string;
  media_index: number;
  media_type: string;
  name: string;
  target: string;
  shape_id: number;
}

export interface PptResourceItem {
  id: number;
  source_id: number;
  page_index: number;
  slide_image: string;
  next_slide_image: string;
  speaker_notes: string;
  has_media: boolean;
  media_items: PptMediaItem[];
  created_at: string;
}

export interface ApiStatePayload {
  success: boolean;
  sessions: SessionSnapshot[];
  background_audio?: BackgroundAudioSnapshot;
}

export interface PhysicalSmokeRequest {
  windows?: number[];
  source_ids?: Record<string, number>;
  settle_seconds?: number;
  timeout_seconds?: number;
  ppt_timeout_seconds?: number;
  stream_timeout_seconds?: number;
  total_timeout_seconds?: number;
  reset_after?: boolean;
}

export interface PhysicalSmokeStepResult {
  window_id: number;
  source_type: string;
  source_id: number;
  source_name: string;
  status: 'ok' | 'failed';
  open_elapsed: number;
  close_elapsed: number;
  error_message: string;
  open_error: string;
  close_error: string;
}

export interface PhysicalSmokeResult {
  success: boolean;
  started_at: string;
  finished_at: string;
  elapsed_seconds: number;
  total_timeout_seconds: number;
  windows: number[];
  source_ids: Record<string, number>;
  summary: { total: number; passed: number; failed: number };
  results: PhysicalSmokeStepResult[];
  reset: { status: 'ok' | 'failed' | 'skipped'; elapsed: number; error_message: string };
  sessions: SessionSnapshot[];
}

export interface UploadOptions {
  onProgress?: (percent: number) => void;
}

export interface ScenarioPayload {
  name: string;
  description?: string;
  big_screen_mode_state?: 'unset' | 'empty' | 'set';
  big_screen_mode?: 'single' | 'double';
  volume_state?: 'unset' | 'empty' | 'set';
  volume_level?: number;
  targets?: Array<{
    window_id: number;
    source_state: 'unset' | 'empty' | 'set';
    source_id?: number | null;
    autoplay?: boolean;
    resume?: boolean;
  }>;
}

interface ApiDetailPayload {
  detail?: string;
}

const REQUEST_TIMEOUT_MS = 10000;
const RUNTIME_MODE_TIMEOUT_MS = 120000;
export const PHYSICAL_SMOKE_TOTAL_TIMEOUT_SECONDS = 9 * 60;
const PHYSICAL_SMOKE_TIMEOUT_MS = (PHYSICAL_SMOKE_TOTAL_TIMEOUT_SECONDS + 60) * 1000;
const DEFAULT_BACKEND_PORT = '8000';

function resolveBackendBase(): string {
  // dev 模式下统一走 Vite 反向代理：相对路径 → 前端 origin → vite proxy → Django。
  // 这样请求与页面同 origin，浏览器不再发起跨 origin 预检，SameSite=Lax 的
  // csrftoken cookie 也能正常携带，避免登录失败。
  if (import.meta.env.DEV) return '';

  const configuredTarget = String(import.meta.env.VITE_BACKEND_TARGET || '').trim();
  if (configuredTarget) {
    // 显式配置优先，避免运行时偷偷改写导致 .env 中的地址失效。
    return configuredTarget.replace(/\/+$/, '');
  }

  const currentProtocol = window.location.protocol === 'https:' ? 'https:' : 'http:';
  const currentHost = window.location.hostname || '127.0.0.1';
  return `${currentProtocol}//${currentHost}:${DEFAULT_BACKEND_PORT}`;
}

export function buildBackendUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) return path;
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return resolveBackendBase() + normalizedPath;
}

function buildNonJsonError(statusCode: number, responseText: string): Error {
  const normalizedText = responseText.trim().replace(/\s+/g, ' ');
  const previewText = normalizedText.slice(0, 120) || t('api.emptyResponse');
  return new Error(t('api.nonJson', { code: statusCode, preview: previewText }));
}

function parseJsonText<T>(responseText: string, statusCode: number, contentType = ''): T & ApiDetailPayload {
  const trimmedText = responseText.trim();
  if (!trimmedText) return {} as T & ApiDetailPayload;
  if (contentType && !contentType.includes('application/json')) {
    throw buildNonJsonError(statusCode, trimmedText);
  }
  try {
    return JSON.parse(trimmedText) as T & ApiDetailPayload;
  } catch (error) {
    throw buildNonJsonError(statusCode, trimmedText);
  }
}

/**
 * 401 专用错误：路由守卫 / Pinia store 据此触发清状态 + 跳登录。
 */
export class UnauthorizedError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'UnauthorizedError';
  }
}

let unauthorizedHandler: (() => void) | null = null;

/**
 * 注册全局 401 回调（通常在 main.ts 启动时挂上）。
 * @param handler 401 触发时调用
 */
export function registerUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler;
}

/**
 * 从 document.cookie 中读取指定名称的值。
 * @param name cookie 名
 * @return 解码后的值；不存在返回空字符串
 */
function readCookie(name: string): string {
  if (typeof document === 'undefined') return '';
  const match = document.cookie.split('; ').find((row) => row.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.split('=').slice(1).join('=')) : '';
}

const UNSAFE_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);

async function fetchWithTimeout(url: string, init: RequestInit = {}, timeoutMs = REQUEST_TIMEOUT_MS): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } finally {
    window.clearTimeout(timeoutId);
  }
}

async function requestJson<T>(url: string, init: RequestInit = {}, timeoutMs = REQUEST_TIMEOUT_MS): Promise<T> {
  const absoluteUrl = buildBackendUrl(url);
  const method = (init.method || 'GET').toUpperCase();
  const csrfHeader: Record<string, string> = {};
  if (UNSAFE_METHODS.has(method)) {
    const token = readCookie('csrftoken');
    if (token) csrfHeader['X-CSRFToken'] = token;
  }
  const response = await fetchWithTimeout(absoluteUrl, {
    ...init,
    // Django session cookie 必须跟车，否则跨端口请求被识别为匿名用户。
    credentials: 'include',
    headers: {
      Accept: 'application/json',
      ...(init.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...csrfHeader,
      ...(init.headers || {}),
    },
  }, timeoutMs);
  const responseText = await response.text();
  const payload = parseJsonText<T>(responseText, response.status, response.headers.get('Content-Type') || '');
  if (response.status === 401) {
    unauthorizedHandler?.();
    throw new UnauthorizedError(payload.detail || t('api.requestFail', { status: 401 }));
  }
  if (!response.ok) {
    throw new Error(payload.detail || t('api.requestFail', { status: response.status }));
  }
  return payload;
}

function uploadFormData<T>(url: string, formData: FormData, options: UploadOptions = {}): Promise<T> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open('POST', buildBackendUrl(url));
    // 文件上传走 multipart：必须同样携带 session cookie + CSRF token，否则被拦截。
    request.withCredentials = true;
    const csrfToken = readCookie('csrftoken');
    if (csrfToken) request.setRequestHeader('X-CSRFToken', csrfToken);
    request.upload.onprogress = (event: ProgressEvent) => {
      if (!event.lengthComputable) return;
      options.onProgress?.(Math.min(99, Math.round((event.loaded / event.total) * 100)));
    };
    request.onload = () => {
      let payload: T & ApiDetailPayload;
      try {
        payload = parseJsonText<T>(request.responseText, request.status, request.getResponseHeader('Content-Type') || '');
      } catch (error) {
        reject(error instanceof Error ? error : new Error(t('api.parseFail')));
        return;
      }
      if (request.status === 401) {
        unauthorizedHandler?.();
        reject(new UnauthorizedError(payload.detail || t('api.requestFail', { status: 401 })));
        return;
      }
      if (request.status < 200 || request.status >= 300) {
        reject(new Error(payload.detail || t('api.requestFail', { status: request.status })));
        return;
      }
      options.onProgress?.(100);
      resolve(payload);
    };
    request.onerror = () => reject(new Error(t('api.uploadNetFail')));
    request.onabort = () => reject(new Error(t('api.uploadAborted')));
    request.send(formData);
  });
}

function sourceQuery(sourceType = '', folderId: number | null = null): string {
  const params = new URLSearchParams();
  if (sourceType) params.set('source_type', sourceType);
  if (folderId !== null) params.set('folder_id', String(folderId));
  const query = params.toString();
  return query ? `?${query}` : '';
}

export interface AuthUser {
  id: number;
  username: string;
  is_staff: boolean;
  is_superuser: boolean;
}

export const api = {
  // 鉴权：首次进入应用先触发 csrf cookie 下发；后续 login/logout/me 走同一会话。
  fetchCsrfToken: () => requestJson<{ csrfToken: string }>('/api/auth/csrf/'),
  login: (payload: { username: string; password: string }) =>
    requestJson<{ user: AuthUser }>('/api/auth/login/', { method: 'POST', body: JSON.stringify(payload) }),
  logout: () => requestJson<{ detail: string }>('/api/auth/logout/', { method: 'POST' }),
  fetchMe: () => requestJson<{ user: AuthUser }>('/api/auth/me/'),
  listFolders: () => requestJson<{ success: boolean; folders: MediaFolderItem[] }>('/api/folders/'),
  createFolder: (payload: { name: string; parent_id?: number | null }) => requestJson<{ success: boolean; folder: MediaFolderItem }>('/api/folders/', { method: 'POST', body: JSON.stringify(payload) }),
  updateFolder: (folderId: number, payload: { name?: string; parent_id?: number | null }) => requestJson<{ success: boolean; folder: MediaFolderItem }>(`/api/folders/${folderId}/`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteFolder: (folderId: number) => requestJson<{ success: boolean }>(`/api/folders/${folderId}/`, { method: 'DELETE' }),
  listSources: (sourceType = '', folderId: number | null = null) => requestJson<{ success: boolean; sources: MediaSourceItem[] }>(`/api/sources/${sourceQuery(sourceType, folderId)}`),
  uploadSource: (formData: FormData, options?: UploadOptions) => uploadFormData<{ success: boolean; source: MediaSourceItem }>('/api/sources/upload/', formData, options),
  addLocalSource: (payload: { path: string; name?: string; folder_id?: number | null }) => requestJson<{ success: boolean; source: MediaSourceItem }>('/api/sources/local/', { method: 'POST', body: JSON.stringify(payload) }),
  addWebSource: (payload: { url: string; name?: string; folder_id?: number | null; preheat_enabled?: boolean; keep_alive?: boolean }) => requestJson<{ success: boolean; source: MediaSourceItem }>('/api/sources/web/', { method: 'POST', body: JSON.stringify(payload) }),
  moveSource: (sourceId: number, folderId: number | null) => requestJson<{ success: boolean; source: MediaSourceItem }>(`/api/sources/${sourceId}/move/`, { method: 'PATCH', body: JSON.stringify({ folder_id: folderId }) }),
  updateSource: (sourceId: number, payload: MediaSourceUpdate) => requestJson<{ success: boolean; source: MediaSourceItem }>(`/api/sources/${sourceId}/`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteSource: (sourceId: number) => requestJson<{ success: boolean }>(`/api/sources/${sourceId}/`, { method: 'DELETE' }),
  downloadSourceUrl: (sourceId: number) => buildBackendUrl(`/api/sources/${sourceId}/download/`),
  listPptResources: (sourceId: number) => requestJson<{ success: boolean; resources: PptResourceItem[] }>(`/api/sources/${sourceId}/ppt-resources/`),
  listSessions: () => requestJson<ApiStatePayload>('/api/sessions/'),
  getRuntime: () => requestJson<{ success: boolean; runtime: RuntimeSnapshot }>('/api/runtime/'),
  setRuntimeMode: (bigScreenMode: 'single' | 'double') =>
    requestJson<ApiStatePayload & { runtime: RuntimeSnapshot }>('/api/runtime/', {
      method: 'PATCH',
      body: JSON.stringify({ big_screen_mode: bigScreenMode }),
    }, RUNTIME_MODE_TIMEOUT_MS),
  getSystemVolume: () => requestJson<{ success: boolean; volume: { level: number; muted: boolean; system_synced: boolean; backend: string } }>('/api/volume/'),
  setSystemVolume: (level: number, muted?: boolean) => requestJson<{ success: boolean; volume: { level: number; muted: boolean; system_synced: boolean; backend: string } }>('/api/volume/', { method: 'PATCH', body: JSON.stringify({ level, ...(muted === undefined ? {} : { muted }) }) }),
  getBackgroundAudio: () => requestJson<BackgroundAudioPayload>('/api/background-audio/'),
  addBackgroundAudioSource: (sourceId: number) => requestJson<BackgroundAudioPayload>('/api/background-audio/playlist/', { method: 'POST', body: JSON.stringify({ source_id: sourceId }) }),
  removeBackgroundAudioItem: (itemId: number) => requestJson<BackgroundAudioPayload>(`/api/background-audio/playlist/${itemId}/`, { method: 'DELETE' }),
  clearBackgroundAudioPlaylist: () => requestJson<BackgroundAudioPayload>('/api/background-audio/playlist/', { method: 'DELETE' }),
  playBackgroundAudioSource: (sourceId: number) => requestJson<BackgroundAudioPayload>('/api/background-audio/play-source/', { method: 'POST', body: JSON.stringify({ source_id: sourceId }) }),
  playBackgroundAudioItem: (itemId: number) => requestJson<BackgroundAudioPayload>(`/api/background-audio/playlist/${itemId}/play/`, { method: 'POST' }),
  controlBackgroundAudio: (action: 'play' | 'pause' | 'stop' | 'next' | 'prev' | 'seek', positionMs = 0) => requestJson<BackgroundAudioPayload>('/api/background-audio/control/', { method: 'POST', body: JSON.stringify({ action, position_ms: positionMs }) }),
  setBackgroundAudioVolume: (volume: number) => requestJson<BackgroundAudioPayload>('/api/background-audio/volume/', { method: 'PATCH', body: JSON.stringify({ volume }) }),
  setBackgroundAudioMute: (muted: boolean) => requestJson<BackgroundAudioPayload>('/api/background-audio/mute/', { method: 'PATCH', body: JSON.stringify({ muted }) }),
  setBackgroundAudioLoop: (enabled: boolean) => requestJson<BackgroundAudioPayload>('/api/background-audio/loop/', { method: 'PATCH', body: JSON.stringify({ enabled }) }),
  openSource: (windowId: number, sourceId: number, autoplay = true) => requestJson<ApiStatePayload>(`/api/playback/${windowId}/open/`, { method: 'POST', body: JSON.stringify({ source_id: sourceId, autoplay }) }),
  openSourceWithOptions: (windowId: number, payload: { source_id: number; autoplay?: boolean; target_slide?: number }) => requestJson<ApiStatePayload>(`/api/playback/${windowId}/open/`, { method: 'POST', body: JSON.stringify(payload) }),
  controlPlayback: (windowId: number, action: string) => requestJson<ApiStatePayload>(`/api/playback/${windowId}/control/`, { method: 'POST', body: JSON.stringify({ action }) }),
  navigateContent: (windowId: number, action: string, targetIndex = 0, positionMs = 0) => requestJson<ApiStatePayload>(`/api/playback/${windowId}/navigate/`, { method: 'POST', body: JSON.stringify({ action, target_index: targetIndex, position_ms: positionMs }) }),
  controlPptMedia: (windowId: number, action: string, mediaId: string, mediaIndex: number) => requestJson<ApiStatePayload>(`/api/playback/${windowId}/ppt-media/`, { method: 'POST', body: JSON.stringify({ action, media_id: mediaId, media_index: mediaIndex }) }),
  closeSource: (windowId: number) => requestJson<ApiStatePayload>(`/api/playback/${windowId}/close/`, { method: 'POST' }),
  resetAllSessions: () => requestJson<ApiStatePayload>('/api/playback/reset-all/', { method: 'POST' }),
  resetPptPlayback: () => requestJson<ApiStatePayload>('/api/playback/reset-ppt/', { method: 'POST' }),
  runPhysicalSmoke: (payload: PhysicalSmokeRequest = {}) => requestJson<PhysicalSmokeResult>('/api/playback/physical-smoke/', {
    method: 'POST',
    body: JSON.stringify({
      ...payload,
      total_timeout_seconds: payload.total_timeout_seconds ?? PHYSICAL_SMOKE_TOTAL_TIMEOUT_SECONDS,
    }),
  }, PHYSICAL_SMOKE_TIMEOUT_MS),
  shutdownSystem: () => requestJson<ApiStatePayload & { detail?: string }>('/api/system/shutdown/', { method: 'POST' }),
  setLoop: (windowId: number, enabled: boolean) => requestJson<ApiStatePayload>(`/api/playback/${windowId}/loop/`, { method: 'PATCH', body: JSON.stringify({ enabled }) }),
  setWindowVolume: (windowId: number, volume: number) => requestJson<ApiStatePayload>(`/api/playback/${windowId}/volume/`, { method: 'PATCH', body: JSON.stringify({ volume }) }),
  setWindowMute: (windowId: number, muted: boolean) => requestJson<ApiStatePayload>(`/api/playback/${windowId}/mute/`, { method: 'PATCH', body: JSON.stringify({ muted }) }),
  showWindowIds: () => requestJson<ApiStatePayload>('/api/playback/show-ids/', { method: 'POST' }),
  listDisplays: () => requestJson<{ success: boolean; targets: DisplayTargetItem[]; splice_label: string }>('/api/displays/'),
  selectDisplay: (payload: { window_id: number; display_mode: string; target_label: string }) => requestJson<ApiStatePayload>('/api/displays/select/', { method: 'POST', body: JSON.stringify(payload) }),
  listDevices: () => requestJson<{ success: boolean; devices: DeviceItem[] }>('/api/devices/'),
  toggleDevice: (deviceType: string) => requestJson<{ success: boolean; device: DeviceItem }>(`/api/devices/${deviceType}/toggle/`, { method: 'POST' }),
  powerDevice: (deviceType: string, action: 'on' | 'off') => requestJson<{ success: boolean; device: DeviceItem }>(`/api/devices/${deviceType}/power/${action}/`, { method: 'POST' }),
  listScenarios: () => requestJson<{ success: boolean; scenarios: ScenarioItem[] }>('/api/scenarios/'),
  createScenario: (payload: ScenarioPayload) => requestJson<{ success: boolean; scenario: ScenarioItem }>('/api/scenarios/', { method: 'POST', body: JSON.stringify(payload) }),
  updateScenario: (scenarioId: number, payload: ScenarioPayload) => requestJson<{ success: boolean; scenario: ScenarioItem }>(`/api/scenarios/${scenarioId}/`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteScenario: (scenarioId: number) => requestJson<{ success: boolean }>(`/api/scenarios/${scenarioId}/`, { method: 'DELETE' }),
  pinScenario: (scenarioId: number) => requestJson<{ success: boolean; scenario: ScenarioItem }>(`/api/scenarios/${scenarioId}/pin/`, { method: 'POST' }),
  activateScenario: (scenarioId: number) => requestJson<ApiStatePayload>(`/api/scenarios/${scenarioId}/activate/`, { method: 'POST' }),
  captureScenario: (payload: { name: string; description?: string; scenario_id?: number }) => requestJson<{ success: boolean; scenario: ScenarioItem }>('/api/scenarios/capture/', { method: 'POST', body: JSON.stringify(payload) }),
};

export function formatDuration(milliseconds: number): string {
  const totalSeconds = Math.max(0, Math.floor(milliseconds / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

export function formatBytes(bytes: number): string {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const unitIndex = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** unitIndex).toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}
