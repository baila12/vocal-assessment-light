import { createRouter, createWebHashHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { h } from 'vue'
import { ElMessage } from 'element-plus'

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
    path: '/sing/:songId?',
    name: 'sing',
    component: () => import('@/views/SingView.vue'),
  },
  {
    path: '/songs',
    name: 'songs',
    component: () => import('@/views/SongsView.vue'),
  },
  // v7.7: 无效路由捕获 — beforeEach 中显示 Toast 后重定向到首页
  // (redirect 会在 beforeEach 之前解析, 故此处用占位组件 + 守卫内重定向)
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: { render: () => h('div') },
  },
]

const router = createRouter({
  // Electron 生产模式使用 hash history (file:// 协议兼容)
  history: createWebHashHistory(),
  routes,
})

// v7.7: 无效路由全局守卫 — 显示 Toast 并重定向到首页
router.beforeEach((to, _from, next) => {
  if (to.name === 'not-found') {
    ElMessage.warning('页面不存在，已返回首页')
    next({ name: 'home' })
  } else {
    next()
  }
})

export default router
