import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { gsap } from 'gsap'
import ElementPlus from 'element-plus'
import 'element-plus/theme-chalk/src/index.scss'
import App from './App.vue'
import router from './router'
import './styles/global.css'
import './styles/element-override.scss'

// ---- GSAP 全局默认配置 ----
gsap.defaults({
  duration: 0.4,
  ease: 'power2.out',
  overwrite: 'auto',
})

// ---- 全局错误捕获 ----
if (typeof window !== 'undefined') {
  window.addEventListener('error', (e) => {
    const el = document.getElementById('app')
    if (el) {
      const err = document.createElement('div')
      err.style.cssText = 'background:#dc2626;color:white;padding:12px;margin:8px;border-radius:4px;font:13px monospace'
      err.textContent = 'JS ERROR: ' + e.message + ' @ ' + e.filename + ':' + e.lineno
      el.prepend(err)
    }
  })
  window.addEventListener('unhandledrejection', (e) => {
    const el = document.getElementById('app')
    if (el) {
      const err = document.createElement('div')
      err.style.cssText = 'background:#dc2626;color:white;padding:12px;margin:8px;border-radius:4px;font:13px monospace'
      err.textContent = 'PROMISE ERROR: ' + (e.reason?.message || e.reason || 'unknown')
      el.prepend(err)
    }
  })
}

const app = createApp(App)

const pinia = createPinia()
app.use(pinia)
app.use(router)
app.use(ElementPlus, { locale: undefined })  // Phase 4: 添加 zhCn locale

// ---- BDD 浏览器测试钩子 (window.__store) ----
// 浏览器级 BDD (tests/bdd/ 下 mark.browser 场景) 通过该钩子注入/读取 Pinia store
// 状态, 避免依赖真实后端数据。生产构建保留以支持浏览器测试 (本地离线应用)。
// API: setState(partial, storeName) / getState(storeName) / emit(eventName, payload)
if (typeof window !== 'undefined') {
  ;(window as unknown as Record<string, unknown>).__store = {
    setState(partial: Record<string, unknown>, storeName: string) {
      const store = (pinia as unknown as { _s: Map<string, { $patch: (p: unknown) => void }> })._s.get(storeName)
      if (store) store.$patch(partial)
    },
    getState(storeName: string) {
      const store = (pinia as unknown as { _s: Map<string, { $state: unknown }> })._s.get(storeName)
      return store ? store.$state : undefined
    },
    emit(eventName: string, payload?: unknown) {
      window.dispatchEvent(new CustomEvent(`vas:${eventName}`, { detail: payload }))
    },
  }
}

app.mount('#app')
