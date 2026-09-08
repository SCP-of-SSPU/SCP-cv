import type { SessionSnapshot } from '@/services/api';

export type ConnectionLayerState = 'connected' | 'connecting' | 'reconnecting' | 'offline';

export interface ConnectionLayerSummary {
  control: ConnectionLayerState;
  player: 'online' | 'offline';
  onlinePlayerCount: number;
}

/**
 * 控制链路和执行端是两个独立事实：SSE 在线不能证明物理播放器在线。
 */
export function deriveConnectionLayerSummary(
  sseStatus: 'connecting' | 'connected' | 'reconnecting' | 'closed',
  sessions: readonly Pick<SessionSnapshot, 'player_online'>[],
): ConnectionLayerSummary {
  const onlinePlayerCount = sessions.filter((session) => session.player_online).length;
  return {
    control: sseStatus === 'closed' ? 'offline' : sseStatus,
    player: onlinePlayerCount > 0 ? 'online' : 'offline',
    onlinePlayerCount,
  };
}
