/**
 * 判断异步 PPT 资源响应是否仍对应当前显控会话。
 * 请求序号用于覆盖 A→B→A 的同源回切，源 ID 用于阻止普通切源串写。
 */
export function isCurrentPptResourceRequest(
  requestSequence: number,
  latestSequence: number,
  requestedSourceId: number,
  currentSourceId: number | null,
  isPpt: boolean,
): boolean {
  return isPpt
    && requestSequence === latestSequence
    && requestedSourceId === currentSourceId;
}
