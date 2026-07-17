import { createApp } from 'vue';
import App from './App.vue';
import router from './router';

import ElementPlus from 'element-plus';
import 'element-plus/dist/index.css';
import 'element-plus/theme-chalk/dark/css-vars.css';
import * as ElementPlusIconsVue from '@element-plus/icons-vue';

import './assets/main.css';

const app = createApp(App);

// 注册所有 Element Plus 图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component);
}

app.use(router);
app.use(ElementPlus);

// 全局配置（Vite 代理 /api → Flask 5000）
app.config.globalProperties.serverURL = '';

// axios 实例
import axios from 'axios';
const http = axios.create({
  timeout: 300000, // Agent 协作可能耗时较长
});
app.config.globalProperties.$http = http;

app.mount('#app');