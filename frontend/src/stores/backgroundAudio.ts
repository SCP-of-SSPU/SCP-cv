/*
 * 背景音乐 Store：维护全局音频状态、播放列表与远端控制动作。
 */
import { defineStore } from 'pinia';

import {
  api,
  type BackgroundAudioPayload,
  type BackgroundAudioPlaylistItem,
  type BackgroundAudioSnapshot,
  type BackgroundAudioStateSnapshot,
} from '@/services/api';

interface BackgroundAudioStoreState {
  snapshot: BackgroundAudioSnapshot | null;
  loading: boolean;
}

function applyPayload(payload: BackgroundAudioPayload): BackgroundAudioSnapshot {
  return payload.background_audio;
}

export const useBackgroundAudioStore = defineStore('backgroundAudio', {
  state: (): BackgroundAudioStoreState => ({
    snapshot: null,
    loading: false,
  }),
  getters: {
    state: (store): BackgroundAudioStateSnapshot | null => store.snapshot?.state ?? null,
    playlist: (store): BackgroundAudioPlaylistItem[] => store.snapshot?.playlist ?? [],
    isPlaying: (store): boolean => store.snapshot?.state.playback_state === 'playing',
    hasCurrentSource: (store): boolean => Boolean(store.snapshot?.state.source_id),
  },
  actions: {
    applyRemoteSnapshot(snapshot: BackgroundAudioSnapshot): void {
      this.snapshot = snapshot;
    },
    async refresh(): Promise<void> {
      this.loading = true;
      try {
        this.snapshot = applyPayload(await api.getBackgroundAudio());
      } finally {
        this.loading = false;
      }
    },
    async addSource(sourceId: number): Promise<void> {
      this.snapshot = applyPayload(await api.addBackgroundAudioSource(sourceId));
    },
    async playSource(sourceId: number): Promise<void> {
      this.snapshot = applyPayload(await api.playBackgroundAudioSource(sourceId));
    },
    async playItem(itemId: number): Promise<void> {
      this.snapshot = applyPayload(await api.playBackgroundAudioItem(itemId));
    },
    async removeItem(itemId: number): Promise<void> {
      this.snapshot = applyPayload(await api.removeBackgroundAudioItem(itemId));
    },
    async clearPlaylist(): Promise<void> {
      this.snapshot = applyPayload(await api.clearBackgroundAudioPlaylist());
    },
    async control(action: 'play' | 'pause' | 'stop' | 'next' | 'prev' | 'seek', positionMs = 0): Promise<void> {
      this.snapshot = applyPayload(await api.controlBackgroundAudio(action, positionMs));
    },
    async setVolume(volume: number): Promise<void> {
      this.snapshot = applyPayload(await api.setBackgroundAudioVolume(volume));
    },
    async setMute(muted: boolean): Promise<void> {
      this.snapshot = applyPayload(await api.setBackgroundAudioMute(muted));
    },
    async setLoop(enabled: boolean): Promise<void> {
      this.snapshot = applyPayload(await api.setBackgroundAudioLoop(enabled));
    },
  },
});
