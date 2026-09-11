import type { Router } from 'vue-router';

import type { PlatformAdapter } from './index';
import { dismissTopLayer } from './lifecycleBack';
import { resumeClientConnection } from './lifecycleState';
import { useAuthStore } from '@/stores/auth';
import { refreshStores } from '@/stores';
import { useRuntimeStore } from '@/stores/runtime';

function isRootRoute(path: string): boolean {
  return ['/dashboard', '/login', '/connect'].includes(path);
}

export function installClientLifecycle(adapter: PlatformAdapter, router: Router): () => void {
  const runtime = useRuntimeStore();
  const auth = useAuthStore();
  let resumeInFlight: Promise<boolean> | null = null;

  const resume = () => {
    if (resumeInFlight) return;
    resumeInFlight = resumeClientConnection({
      hasServerProfile: () => runtime.serverProfile !== null,
      disconnectEvents: () => runtime.disconnectEvents(),
      probeSession: () => auth.probeCurrentServer(),
      refreshSnapshot: () => refreshStores(),
      connectEvents: () => runtime.connectEvents(),
    }).then(async (authenticated) => {
      if (!authenticated && runtime.serverProfile && router.currentRoute.value.path !== '/login') {
        await router.replace('/login');
      }
      return authenticated;
    }).catch(() => false).finally(() => { resumeInFlight = null; });
  };

  const removeLifecycle = adapter.onLifecycleChanged((state) => {
    if (state === 'inactive') runtime.disconnectEvents();
    else resume();
  });
  const removeBack = adapter.onBackRequested(async () => {
    if (dismissTopLayer()) return true;
    if (!isRootRoute(router.currentRoute.value.path)) {
      await router.back();
      return true;
    }
    return false;
  });

  return () => {
    removeLifecycle();
    removeBack();
  };
}
