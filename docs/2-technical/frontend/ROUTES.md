# 前端路由 v7.3.1

> Vue 3 SPA, Vue Router 4.6, hash history (Electron 兼容)

---

## 当前路由

| 路由 | 组件 | 说明 |
|------|------|------|
| `#/` | `HomeView.vue` | 首页: 上传 + 模式选择 (Quick/Pro) + 录音入口 |
| `#/report/:id?` | `ReportView.vue` | 评分报告: 六维雷达图 + 改进建议 + 音频回放 |
| `#/history` | `HistoryView.vue` | 历史记录: 分页列表 + 搜索 + 批量删除 |
| `#/compare` | `CompareView.vue` | 对比分析: 双文件上传 + DTW 结果 |
| `#/sing` | `SingView.vue` | 实时演唱: Canvas + AudioWorklet + WebSocket 流式评分 |

全部懒加载 (`() => import(...)`), hash history (`createWebHashHistory`).

---

## 路由性能

| 指标 | 实际 (Vite build) |
|------|:---:|
| Main chunk (Element Plus + Vue + Chart.js) | ~346 KB gzip |
| ReportView (含 Chart.js radar) | ~65 KB gzip |
| 其他页面 (lazy loaded) | 2-4 KB gzip each |
| Vite build 耗时 | ~9.5s |

---

## 旧页面重定向

Flask `web/static/index.html` 显示重定向页面，引导用户到 `http://localhost:8000` (Vue 3 SPA)。
旧 HTML 页面 (`/analysis.html`, `/compare.html`, `/settings.html`) 已废弃。
