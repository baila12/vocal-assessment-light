import { createRouter, createWebHashHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

// Phase 4: 懒加载页面组件
// const HomeView = () => import('@/views/HomeView.vue')
// const ReportView = () => import('@/views/ReportView.vue')
// ...

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/HomeView.vue'),
  },
  {
    path: '/report/:id?',
    name: 'report',
    component: () => import('@/views/ReportView.vue'),
  },
  {
    path: '/history',
    name: 'history',
    component: () => import('@/views/HistoryView.vue'),
  },
  {
    path: '/compare',
    name: 'compare',
    component: () => import('@/views/CompareView.vue'),
  },
  {
    path: '/sing',
    name: 'sing',
    component: () => import('@/views/SingView.vue'),
  },
]

const router = createRouter({
  // Electron 生产模式使用 hash history (file:// 协议兼容)
  history: createWebHashHistory(),
  routes,
})

export default router
