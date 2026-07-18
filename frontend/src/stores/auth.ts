/*
 * 鉴权 store：缓存当前会话用户、暴露 login / logout / fetchMe 操作。
 * 与 services/api.ts 配合：
 *   - 进入应用时先拉一次 csrf cookie + me；
 *   - 登录成功后 user 入 store；
 *   - axios 401 全局回调（registerUnauthorizedHandler）会清 store 并跳 /login。
 */
import { defineStore } from 'pinia';

import { api, type AuthUser } from '@/services/api';

interface AuthState {
  user: AuthUser | null;
  /** 是否已完成首次 me 探活（成功/失败都会置 true）。 */
  initialized: boolean;
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    user: null,
    initialized: false,
  }),
  getters: {
    isAuthenticated(state): boolean {
      return state.user !== null;
    },
    username(state): string {
      return state.user?.username ?? '';
    },
  },
  actions: {
    /**
     * 首屏调用：先取 CSRF cookie，再尝试 me 确认登录态。
     * 失败（含 401）只把 initialized=true，user 保持 null。
     * @return Promise<void>
     */
    async ensureInitialized(): Promise<void> {
      if (this.initialized) return;
      try {
        await api.fetchCsrfToken();
      } catch {
        // CSRF 失败一般是后端尚未启动；不阻塞后续 me 调用。
      }
      try {
        const payload = await api.fetchMe();
        this.user = payload.user;
      } catch {
        this.user = null;
      } finally {
        this.initialized = true;
      }
    },
    /**
     * 用户登录：username/password 经 /api/auth/login/ 建立 Django session。
     * @param username 用户名
     * @param password 密码
     * @return 解析后的用户信息
     */
    async login(username: string, password: string): Promise<AuthUser> {
      // 登录前再确保 CSRF cookie 在身上（用户可能直接进了 /login 页）。
      try {
        await api.fetchCsrfToken();
      } catch {
        // 忽略：login 接口自身 csrf_exempt 可被回滚到 cookie，登录后会重新刷新。
      }
      const payload = await api.login({ username, password });
      this.user = payload.user;
      this.initialized = true;
      return payload.user;
    },
    /**
     * 用户登出：清 Django session + 本地状态。
     * @return Promise<void>
     */
    async logout(): Promise<void> {
      try {
        await api.logout();
      } finally {
        this.user = null;
      }
    },
    async changePassword(currentPassword: string, newPassword: string): Promise<void> {
      await api.changePassword({ current_password: currentPassword, new_password: newPassword });
    },
    /**
     * 由 401 全局回调触发的本地清场（不调网络）。
     * @return void
     */
    clearLocal(): void {
      this.user = null;
    },
  },
});
