# 前端技术文档 v7.3.1

> Vue 3.5 + Element Plus 2.14 + Pinia 2.3 + GSAP 3.15 + Electron 28

---

## 架构

| 层 | 文件 | 框架 |
|------|------|------|
| 页面 | `views/` (5 pages) | Vue 3 Composition API + Element Plus + GSAP |
| 布局 | `components/layout/` (3 components) | Element Plus |
| 共享组件 | `components/` (6 components) | Element Plus + Chart.js + Canvas |
| 状态管理 | `stores/` (3 stores) | Pinia setup stores |
| 组合函数 | `composables/` (5 composables) | Vue Composition API |
| API 层 | `api/` (1 client) | Fetch API + 零硬编码 URL |
| 路由 | `router/` (1 file) | Vue Router 4.6 (hash history) |
| 类型 | `types/` (2 files) | TypeScript strict mode |
| 桌面 | `electron/` | Electron 28 + preload |

---

## 页面结构

| 路由 | 页面 | 核心组件 |
|------|------|---------|
| `#/` | HomeView | ElUpload + ElRadioGroup (Quick/Pro) + ElDrawer |
| `#/report/:id?` | ReportView | ScoreRadar + ScoreCard + AudioPlayer + PitchCurveCanvas |
| `#/history` | HistoryView | ElTable + ElPagination + ElPopconfirm (批量删除) |
| `#/compare` | CompareView | FileUploader × 2 + DTW 结果卡片 |
| `#/sing` | SingView | Canvas + AudioWorklet + WebSocket + 6步清理 |

---

## 状态管理 (Pinia)

| Store | 职责 |
|------|------|
| `assessment.store.ts` | 当前评估生命周期 (isAnalyzing, progress, result, error) |
| `history.store.ts` | 历史记录 (records, filter, pagination, batch select) |
| `preferences.store.ts` | 用户偏好 (theme, evalMode, autoPlay) — localStorage 持久化 |

---

## API 客户端

零硬编码 URL 设计 (ADR-3):
- Electron: `window.BACKEND_URL` (preload 注入)
- Vite dev: 相对路径通过 proxy → `http://127.0.0.1:8000`
- 生产: 相对路径, FastAPI serve `frontend/dist/`

---

## 构建基准 (Vitest)

```
33/33 tests passed (3 suites)
TypeScript: Zero errors (vue-tsc --noEmit)
Vite build: ~9.5s
```

## 性能要求

| 指标 | 目标 |
|------|:---:|
| FCP | < 1.5s |
| SPA 路由切换 | < 300ms |
| GSAP 动画帧率 | ≥ 30fps |
| JS Bundle (gzip) | < 300KB |
