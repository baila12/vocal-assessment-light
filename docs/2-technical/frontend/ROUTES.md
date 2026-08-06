# 前端路由 v7.12

> Vue 3 SPA, Vue Router 4.6, hash history (Electron 兼容)

---

## 当前路由

| 路由 | 组件 | 说明 |
|------|------|------|
| `#/` | `HomeView.vue` | 首页: 上传 + 模式选择 (Quick/Pro) + 录音入口 |
| `#/report/:id?` | `ReportView.vue` | 评分报告: 六维雷达图 + 改进建议 + 音频回放 + 权重配置面板 (v7.11) |
| `#/history` | `HistoryView.vue` | 历史记录: 分页列表 + 搜索 + 批量删除 |
| `#/compare` | `CompareView.vue` | 对比分析: 双文件上传 + DTW 结果 |
| `#/sing/:songId?` | `SingView.vue` | 实时演唱: Canvas + AudioWorklet + WebSocket 流式评分; 选歌录音 (v7.12) |
| `#/songs` | `SongsView.vue` | 标准曲库: 卡片网格 + 搜索/筛选 + 上传/删除/试听 + 选择此歌 (v7.10/v7.12) |

全部懒加载 (`() => import(...)`), hash history (`createWebHashHistory`).

---

## 路由性能

| 指标 | 实际 (Vite build) |
|------|:---:|
| Main chunk (Element Plus + Vue + Chart.js) | ~346 KB gzip |
| ReportView (含 Chart.js radar) | ~65 KB gzip |
| 其他页面 (lazy loaded) | 2-4 KB gzip each |
| Vite build 耗时 | ~8.9s |

---

## 路由特性

- **全部懒加载**: 所有页面组件使用 `() => import(...)` 按需加载。
- **Hash history**: `createWebHashHistory()` 确保 Electron `file://` 协议兼容。
- **无效路由捕获**: `/:pathMatch(.*)*` catch-all 路由 + `router.beforeEach` 守卫，显示 ElMessage.warning 后重定向首页 (v7.7)。
- **选歌录音 (v7.12)**: `#/sing/:songId` 可选参数路由 — 有 songId 时加载参考歌曲并进入录音准备; 无 songId 时显示选歌区。SongsView 卡片"选择此歌"按钮跳转此路由。

## 旧页面重定向

Flask 旧前端 (`web/static/`) 已于 v7.6 移除。旧 HTML 页面 (`/analysis.html`, `/compare.html`, `/settings.html`) 均已废弃。当前所有访问由 FastAPI serve `frontend/dist/` (Vue 3 SPA) 处理。
