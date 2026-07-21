import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/theme-chalk/src/index.scss'
import App from './App.vue'
import router from './router'
import './styles/global.css'
import './styles/element-override.scss'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: undefined })  // Phase 4: 添加 zhCn locale

app.mount('#app')
