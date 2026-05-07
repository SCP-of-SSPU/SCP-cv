/*
 * 前端应用入口：
 *   - 注册 Pinia 状态管理；
 *   - 安装 Vue Router；
 *   - 挂载根组件到 #app。
 */
import { createPinia } from 'pinia';
import { createApp } from 'vue';

import App from './App.vue';
import router from './router';
import './styles/base.css';

createApp(App).use(createPinia()).use(router).mount('#app');
