export interface MediaSourceItem {
  id: number;
  source_type: string;
  name: string;
  uri: string;
  is_available: boolean;
  stream_identifier: string;
  created_at: string;
}

export interface SessionSnapshot {
  window_id: number;
  session_id: number;
  source_name: string;
  source_type: string;
  source_type_label: string;
  source_uri: string;
  playback_state: string;
  playback_state_label: string;
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
  loop_enabled: boolean;
}

export interface ScenarioItem {
  id: number;
  name: string;
  description: string;
  window1_source_id: number | null;
  window1_source_name: string;
  window1_autoplay: boolean;
  window1_resume: boolean;
  window2_source_id: number | null;
  window2_source_name: string;
  window2_autoplay: boolean;
  window2_resume: boolean;
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

export interface ApiStatePayload {
  success: boolean;
  sessions: SessionSnapshot[];
}

export interface UploadOptions {
  onProgress?: (percent: number) => void;
}

interface ApiDetailPayload {
  detail?: string;
}

function buildNonJsonError(statusCode: number, responseText: string): Error {
  const normalizedText = responseText.trim().replace(/\s+/g, ' ');
  const previewText = normalizedText.slice(0, 120) || '空响应';
  return new Error(`服务返回非 JSON 响应（HTTP ${statusCode}）：${previewText}`);
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

async function requestJson<T>(url: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: {
      ...(init.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...(init.headers || {}),
    },
  });
  const responseText = await response.text();
  const payload = parseJsonText<T>(responseText, response.status, response.headers.get('Content-Type') || '');
  if (!response.ok) {
    throw new Error(payload.detail || `请求失败：${response.status}`);
  }
  return payload;
}

function uploadFormData<T>(url: string, formData: FormData, options: UploadOptions = {}): Promise<T> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open('POST', url);
    request.upload.onprogress = (event: ProgressEvent) => {
      if (!event.lengthComputable) return;
      const percent = Math.min(99, Math.round((event.loaded / event.total) * 100));
      options.onProgress?.(percent);
    };
    request.onload = () => {
      let payload: T & ApiDetailPayload;
      try {
        payload = parseJsonText<T>(request.responseText, request.status, request.getResponseHeader('Content-Type') || '');
      } catch (error) {
        reject(error instanceof Error ? error : new Error('响应解析失败'));
        return;
      }
      if (request.status < 200 || request.status >= 300) {
        reject(new Error(payload.detail || `请求失败：${request.status}`));
        return;
      }
      options.onProgress?.(100);
      resolve(payload);
    };
    request.onerror = () => reject(new Error('上传失败：网络连接异常'));
    request.onabort = () => reject(new Error('上传已取消'));
    request.send(formData);
  });
}

export const api = {
  listSources: () => requestJson<{ success: boolean; sources: MediaSourceItem[] }>('/api/sources/'),
  uploadSource: (formData: FormData, options?: UploadOptions) => uploadFormData<{ success: boolean; source: MediaSourceItem }>('/api/sources/upload/', formData, options),
  addLocalSource: (payload: { path: string; name?: string }) => requestJson<{ success: boolean; source: MediaSourceItem }>('/api/sources/local/', { method: 'POST', body: JSON.stringify(payload) }),
  addWebSource: (payload: { url: string; name?: string }) => requestJson<{ success: boolean; source: MediaSourceItem }>('/api/sources/web/', { method: 'POST', body: JSON.stringify(payload) }),
  deleteSource: (sourceId: number) => requestJson<{ success: boolean }>(`/api/sources/${sourceId}/`, { method: 'DELETE' }),
  listSessions: () => requestJson<ApiStatePayload>('/api/sessions/'),
  openSource: (windowId: number, sourceId: number, autoplay = true) => requestJson<ApiStatePayload>(`/api/playback/${windowId}/open/`, { method: 'POST', body: JSON.stringify({ source_id: sourceId, autoplay }) }),
  controlPlayback: (windowId: number, action: string) => requestJson<ApiStatePayload>(`/api/playback/${windowId}/control/`, { method: 'POST', body: JSON.stringify({ action }) }),
  navigateContent: (windowId: number, action: string, targetIndex = 0, positionMs = 0) => requestJson<ApiStatePayload>(`/api/playback/${windowId}/navigate/`, { method: 'POST', body: JSON.stringify({ action, target_index: targetIndex, position_ms: positionMs }) }),
  closeSource: (windowId: number) => requestJson<ApiStatePayload>(`/api/playback/${windowId}/close/`, { method: 'POST' }),
  setLoop: (windowId: number, enabled: boolean) => requestJson<ApiStatePayload>(`/api/playback/${windowId}/loop/`, { method: 'PATCH', body: JSON.stringify({ enabled }) }),
  showWindowIds: () => requestJson<ApiStatePayload>('/api/playback/show-ids/', { method: 'POST' }),
  listDisplays: () => requestJson<{ success: boolean; targets: DisplayTargetItem[]; splice_label: string }>('/api/displays/'),
  selectDisplay: (payload: { window_id: number; display_mode: string; target_label: string }) => requestJson<ApiStatePayload>('/api/displays/select/', { method: 'POST', body: JSON.stringify(payload) }),
  listScenarios: () => requestJson<{ success: boolean; scenarios: ScenarioItem[] }>('/api/scenarios/'),
  createScenario: (payload: Partial<ScenarioItem>) => requestJson<{ success: boolean; scenario: ScenarioItem }>('/api/scenarios/', { method: 'POST', body: JSON.stringify(payload) }),
  updateScenario: (scenarioId: number, payload: Partial<ScenarioItem>) => requestJson<{ success: boolean; scenario: ScenarioItem }>(`/api/scenarios/${scenarioId}/`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteScenario: (scenarioId: number) => requestJson<{ success: boolean }>(`/api/scenarios/${scenarioId}/`, { method: 'DELETE' }),
  activateScenario: (scenarioId: number) => requestJson<ApiStatePayload>(`/api/scenarios/${scenarioId}/activate/`, { method: 'POST' }),
  captureScenario: (payload: { name: string; description?: string; scenario_id?: number }) => requestJson<{ success: boolean; scenario: ScenarioItem }>('/api/scenarios/capture/', { method: 'POST', body: JSON.stringify(payload) }),
};

export function formatDuration(milliseconds: number): string {
  const totalSeconds = Math.max(0, Math.floor(milliseconds / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}
