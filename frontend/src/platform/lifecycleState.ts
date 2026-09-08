export interface ResumeDependencies {
  hasServerProfile(): boolean;
  disconnectEvents(): void;
  probeSession(): Promise<boolean>;
  refreshSnapshot(): Promise<void>;
  connectEvents(): void;
}

/** 前台恢复严格按断旧连接→验会话→拉全量→建唯一 SSE 的顺序执行。 */
export async function resumeClientConnection(dependencies: ResumeDependencies): Promise<boolean> {
  dependencies.disconnectEvents();
  if (!dependencies.hasServerProfile()) return false;
  const authenticated = await dependencies.probeSession();
  if (!authenticated) return false;
  await dependencies.refreshSnapshot();
  dependencies.connectEvents();
  return true;
}
