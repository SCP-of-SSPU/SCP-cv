/**
 * 窗口级音量能力必须与后端 playback_window_controls 的入队前校验保持一致。
 * 使用真实 source_type 判断，避免把能力不同的源聚合为同一 UI 大类后误开放操作。
 */
const WINDOW_AUDIO_SOURCE_TYPES = new Set([
  'video',
  'custom_stream',
  'rtsp_stream',
  'srt_stream',
]);

export function supportsWindowAudioControls(sourceType: string | null | undefined): boolean {
  return sourceType !== null
    && sourceType !== undefined
    && WINDOW_AUDIO_SOURCE_TYPES.has(sourceType);
}
