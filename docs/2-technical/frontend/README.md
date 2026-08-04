# 前端技术文档 v7.10

> Vue 3.5 + Element Plus 2.14 + Pinia 2.3 + GSAP 3.15 + Chart.js 4.5 + Electron 28

---

## 架构

| 层 | 文件 | 框架 |
|------|------|------|
| 页面 | `views/` (6 pages) | Vue 3 Composition API + Element Plus + GSAP |
| 布局 | `components/layout/` (3 components) | Element Plus |
| 共享组件 | `components/` (7 components) | Element Plus + Chart.js + Canvas |
| 状态管理 | `stores/` (5 stores) | Pinia setup stores |
| 组合函数 | `composables/` (5 composables) | Vue Composition API + GSAP |
| API 层 | `api/` (1 client) | Fetch API + 零硬编码 URL |
| 路由 | `router/` (1 file) | Vue Router 4.6 (hash history) |
| 类型 | `types/` (2 files) | TypeScript strict mode |
| 桌面 | `electron/` | Electron 28 + preload |

---

## 页面结构

| 路由 | 页面 | GSAP 动效 | 核心组件 |
|------|------|-----------|---------|
| `#/` | HomeView | ✅ 5阶段入场序列 | FileUploader + el-radio-group + ElDrawer |
| `#/report/:id?` | ReportView | ✅ score-reveal Timeline | ScoreRadar + ScoreCard + AudioPlayer + WaveformCanvas |
| `#/history` | HistoryView | ✅ 容器淡入 | ElTable + ElPagination + ElPopconfirm |
| `#/compare` | CompareView | ✅ 双面板滑入 | FileUploader × 2 + DTW 结果卡片 |
| `#/sing` | SingView | ✅ 录音按钮 GSAP 脉冲 | Canvas + AudioWorklet + WebSocket |
| `#/songs` | SongsView | ✅ 卡片网格入场 | AudioPlayer + FileUploader + el-select |

---

## GSAP 动效系统 (v7.10)

### Composable: `useGsap.ts`

| 方法 | 用途 | 动画属性 |
|------|------|---------|
| `tl()` | 创建 Timeline (自动注册到 context) | — |
| `enterFrom(target, vars)` | 从隐藏状态入场 | autoAlpha, y, scale |
| `staggerIn(target, vars)` | 交错入场 (列表/卡片) | autoAlpha, y, stagger |
| `slideInLeft(target, vars)` | 从左侧滑入 | autoAlpha, x: -30 |
| `slideInRight(target, vars)` | 从右侧滑入 | autoAlpha, x: 30 |
| `scaleIn(target, vars)` | 缩放弹入 | autoAlpha, scale, back.out |
| `countUp(target, endValue)` | 数字滚动 | val, power3.out |
| `pulse(target, vars)` | 脉冲动画 (repeat:-1) | scale, yoyo |

### 技术规范
- **Compositor-only**: autoAlpha, x, y, scale, rotation — 零 layout 触发
- **gsap.context(scope)**: 选择器隔离, 不触碰 Element Plus 内部 DOM
- **onBeforeUnmount → ctx.revert()**: 自动清理, 无内存泄漏
- **prefers-reduced-motion**: CSS @media + GSAP matchMedia 双重保护

---

## 状态管理 (Pinia)

| Store | 职责 |
|------|------|
| `assessment.store.ts` | 当前评估生命周期 (isAnalyzing, progress, result, error) |
| `history.store.ts` | 历史记录 (records, filter, pagination, batch select) |
| `preferences.store.ts` | 用户偏好 (theme, evalMode, autoPlay) — localStorage 持久化 |
| `flags.store.ts` | 算法状态 (GPU, audiofeat, DL models, weights) — v7.7 |
| `songs.store.ts` | 标准歌曲库 (songs, pagination, filters, CRUD) — v7.10 |

---

## API 客户端

零硬编码 URL 设计 (ADR-3):
- Electron: `window.BACKEND_URL` (preload 注入)
- Vite dev: 相对路径通过 proxy → `http://127.0.0.1:8000`
- 生产: 相对路径, FastAPI serve `frontend/dist/`

---

## 构建基准

```
Vitest: 57/57 tests passed (4 suites)
TypeScript: Zero errors (vue-tsc --noEmit)
Vite build: ~8.5s
```

## 性能要求

| 指标 | 目标 |
|------|:---:|
| FCP | < 1.5s |
| SPA 路由切换 | < 300ms |
| GSAP 动画帧率 | ≥ 30fps |
| GSAP 入场动画 | < 1s (一次性, idle 零 CPU) |
| JS Bundle (gzip) | < 350KB |
