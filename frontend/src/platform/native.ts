import type { PlatformAdapter } from './index';

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
