/*
 * Store 出口：业务层只从此处导入领域 store。
 * 同时提供 bootstrap() 一键拉取所有初始数据并建立 SSE 连接。
 */
import { useToastStore } from '@/composables/useToast';

import { useDeviceStore } from './devices';
import { useDisplayStore } from './displays';
import { useRuntimeStore } from './runtime';
import { useScenarioStore } from './scenarios';
import { useSessionStore } from './sessions';
import { useSourceStore } from './sources';

export {
  useRuntimeStore,
  useSessionStore,
  useSourceStore,
  useScenarioStore,
  useDeviceStore,
  useDisplayStore,
};

/**
 * 应用启动数据初始化。
 * - 并发拉取各领域初始快照；
 * - 部分失败仅 Toast 提示，不阻塞 UI；
 * - 完成后建立 SSE 连接，让会话状态保持实时。
 *
 * @return Promise<void>
 */
export async function bootstrapStores(): Promise<void> {
  const runtime = useRuntimeStore();
  const session = useSessionStore();
  const source = useSourceStore();
  const scenario = useScenarioStore();
  const device = useDeviceStore();
  const display = useDisplayStore();
  const toast = useToastStore();

  const tasks = await Promise.allSettled([
    runtime.refresh(),
    runtime.refreshSystemVolume(),
    session.refresh(),
    source.refresh(),
    scenario.refresh(),
    device.refresh(),
    display.refresh(),
  ]);

  // 单个失败不致命：使用 Toast 警告即可，让用户继续操作可用部分。
  const failed = tasks.find((task) => task.status === 'rejected');
  if (failed && failed.status === 'rejected') {
    toast.warning(
      '部分状态加载失败',
      failed.reason instanceof Error ? failed.reason.message : '请稍后重试或检查后端服务',
    );
  }

  runtime.connectEvents();
}
