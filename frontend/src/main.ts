import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/theme-chalk/src/index.scss'
import App from './App.vue'
import router from './router'
import './styles/global.css'
import './styles/element-override.scss'

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

app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: undefined })  // Phase 4: 添加 zhCn locale

app.mount('#app')
