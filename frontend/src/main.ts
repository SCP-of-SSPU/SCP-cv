/*
 * 前端应用入口：
 *   - 注册 Pinia 状态管理；
 *   - 安装 vue-i18n（DESIGN.md O8）；
 *   - 安装 Vue Router；
 *   - 挂载根组件到 #app。
 */
import { createPinia } from 'pinia';
import { createApp } from 'vue';

import App from './App.vue';
import router from './router';
import { i18n } from './locales';
// Material Symbols 字体（DESIGN.md §9 IC1）：提供 .material-symbols-rounded 类与字形。
import 'material-symbols/rounded.css';
import './styles/base.css';

createApp(App).use(createPinia()).use(i18n).use(router).mount('#app');
