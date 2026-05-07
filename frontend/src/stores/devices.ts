/*
 * 设备电源 Store：拼接屏 / 电视左 / 电视右 的 TCP 指令封装。
 * 设计稿 §4.1 + §4.6：仪表盘电源卡 + 设置「设备电源」Tab 共用。
 */
import { defineStore } from 'pinia';

import { api, type DeviceItem } from '@/services/api';

interface DeviceState {
  devices: DeviceItem[];
  /** 上次操作的执行时间戳（毫秒）；用于设置页展示「上次操作 13:42」。 */
  lastActionAt: Record<string, number>;
  /** 上次操作的语义结果：success/error。 */
  lastActionResult: Record<string, 'success' | 'error' | 'pending'>;
  /** 上次操作的错误描述。 */
  lastActionDetail: Record<string, string>;
}

export const useDeviceStore = defineStore('devices', {
  state: (): DeviceState => ({
    devices: [],
    lastActionAt: {},
    lastActionResult: {},
    lastActionDetail: {},
  }),
  getters: {
    spliceScreen: (state): DeviceItem | undefined =>
      state.devices.find((d) => d.device_type === 'splice_screen'),
    tvLeft: (state): DeviceItem | undefined => state.devices.find((d) => d.device_type === 'tv_left'),
    tvRight: (state): DeviceItem | undefined => state.devices.find((d) => d.device_type === 'tv_right'),
  },
  actions: {
    async refresh(): Promise<void> {
      const payload = await api.listDevices();
      this.devices = payload.devices;
    },
    /** 拼接屏：开机/关机；电视：toggle 切换不读真实状态。 */
    async power(deviceType: string, action: 'on' | 'off'): Promise<void> {
      this.lastActionResult[deviceType] = 'pending';
      try {
        await api.powerDevice(deviceType, action);
        this.lastActionResult[deviceType] = 'success';
        this.lastActionDetail[deviceType] = action === 'on' ? '开机指令已发送' : '关机指令已发送';
      } catch (error) {
        this.lastActionResult[deviceType] = 'error';
        this.lastActionDetail[deviceType] = error instanceof Error ? error.message : '设备指令失败';
        throw error;
      } finally {
        this.lastActionAt[deviceType] = Date.now();
      }
    },
    async toggle(deviceType: string): Promise<void> {
      this.lastActionResult[deviceType] = 'pending';
      try {
        await api.toggleDevice(deviceType);
        this.lastActionResult[deviceType] = 'success';
        this.lastActionDetail[deviceType] = '切换指令已发送';
      } catch (error) {
        this.lastActionResult[deviceType] = 'error';
        this.lastActionDetail[deviceType] = error instanceof Error ? error.message : '设备切换失败';
        throw error;
      } finally {
        this.lastActionAt[deviceType] = Date.now();
      }
    },
  },
});
