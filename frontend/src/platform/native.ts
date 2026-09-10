import type { PlatformAdapter } from './index';

let nativePlatformAdapter: PlatformAdapter | null = null;

export function setNativePlatformAdapter(adapter: PlatformAdapter | null): void {
  nativePlatformAdapter = adapter;
}

export function getNativePlatformAdapter(): PlatformAdapter | null {
  return nativePlatformAdapter;
}

export async function resolveNativePlatformAdapter(): Promise<PlatformAdapter | null> {
  if (typeof window === 'undefined') return null;
  if (window.scpCvElectron) {
    const { createElectronPlatformAdapter } = await import('./electron');
    return createElectronPlatformAdapter(window.scpCvElectron);
  }
  const { Capacitor } = await import('@capacitor/core');
  if (Capacitor.isNativePlatform() && Capacitor.getPlatform() === 'android') {
    const { createCapacitorPlatformAdapter } = await import('./capacitor');
    return createCapacitorPlatformAdapter();
  }
  return null;
}
