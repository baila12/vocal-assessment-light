# 前端技术文档

> **v7.0 Phase 4+5 完成 (2026-07-22)**: Vue 3 + Element Plus + Electron 桌面打包完成。
> 6 shared components + 3 layout components + 5 page views + 3 Pinia stores + 5 composables.
> 33 Vitest tests, zero TypeScript errors (vue-tsc + electron tsc), Vite build 9.89s.
> Electron: embedded Python + process daemon + NSIS installer. 详见 [V7_MIGRATION_PLAN.md](../../4-process/V7_MIGRATION_PLAN.md)。

## v7.0 架构总览

| 层 | 文件 | 框架 |
|----|------|------|
| 状态管理 | `stores/` (3 stores) | Pinia setup stores |
| 组合函数 | `composables/` (5 composables) | Vue Composition API |
| 布局 | `components/layout/` (3 components) | Element Plus |
| 共享组件 | `components/` (6 components) | Element Plus + Chart.js + Canvas |
| 页面 | `views/` (5 pages) | Vue 3 + Element Plus + GSAP |
| 类型 | `types/` (2 files) | TypeScript |
| API 层 | `api/` (1 client) | Fetch + openapi-typescript |

## v7.0 页面映射

| 路由 | 页面 | 关键组件 |
|------|------|---------|
| `#/` | HomeView | ElUpload + ElRadioGroup + ElDrawer(设置/曲库) |
| `#/report/:id?` | ReportView | ScoreRadar + ScoreCard + AudioPlayer + PitchCurveCanvas |
| `#/history` | HistoryView | ElTable + ElPagination + ElPopconfirm |
| `#/compare` | CompareView | FileUploader x2 + DTW 结果卡片 |
| `#/sing` | SingView | Canvas + AudioWorklet + WebSocket + 6步清理 |

## 当前定位

前端已从 v6.3 “功能展示页” 重构为 v7.0 “声乐练习与评估工作台”。服务三个阶段：

| 阶段 | 用户目标 | v7.0 实现 |
|------|----------|----------|
| 开始前 | 选择上传、录音、选歌或对比 | HomeView: 简洁入口 + ElUpload + 模式选择 + ElDrawer(设置/曲库) |
| 分析中 | 理解进度，不被阻塞 | ProgressOverlay (fixed top) + 评估 store 进度追踪 |
| 结果后 | 知道问题在哪里，下一次怎么练 | ReportView: 六维雷达图 + 启发式标签 + 改进建议 + 音频回放 |

## v7.0 构建基准

```bash
Vitest:     33/33 tests passed (3 suites)
TypeScript: Zero errors (vue-tsc --noEmit)
Vite build: 9.55s
  - Main chunk:   346 KB gzip (Element Plus + Vue + Chart.js)
  - ReportView:    65 KB gzip (含 Chart.js radar)
  - Other pages: 2-4 KB gzip each (lazy loaded)
```

## 文档

| 文档 | 说明 |
|------|------|
| [ROUTES.md](ROUTES.md) | SPA 路由、旧页面迁移、预留页面 |
| [BACKEND_ALIGNMENT.md](BACKEND_ALIGNMENT.md) | 前端页面与后端 v5.18/v6.0 计划对齐 |
| [VISUAL_AUDIT.md](VISUAL_AUDIT.md) | 基于浏览器真实页面的视觉、结构和移动端问题审计 |

## 性能要求

所有前端页面和组件必须满足以下性能底线：

| 指标 | 目标 | 测量方式 |
|------|------|---------|
| FCP (首次内容绘制) | < 1.5s | Lighthouse |
| TBT (总阻塞时间) | < 200ms | Lighthouse |
| CLS (累计布局偏移) | < 0.1 | Lighthouse |
| JS Bundle (gzip) | < 300KB | 构建工具 |
| CSS (gzip) | < 50KB | 构建工具 |
| SPA 路由切换 | < 300ms (含动画) | `performance.now()` |
| GSAP 动画帧率 | ≥ 30fps | DevTools FPS |
| Canvas 实时绘制 | ≥ 30fps | DevTools FPS |
| IndexedDB 占用 | < 50MB | Storage API |

## 设计检查方式

实现具体前端页面时，应在浏览器中检查实际页面，而不是只看代码判断：

| 检查项 | 方法 |
|--------|------|
| 首页第一屏 | 浏览器打开 `/` 和 `/#/`，确认核心任务是否清晰 |
| 移动端 | 使用浏览器 viewport 检查 375px、768px、1280px |
| 路由 | 检查 `#/sing`、`#/compare`、`#/report/:id`、`#/library`、`#/settings/scoring` |
| 动效 | 检查 GSAP 时间线是否服务流程，是否尊重 reduced motion，FPS 是否稳定 |
| 视觉 | 检查是否仍依赖 emoji、inline style、无意义样例卡片 |
| 性能 | 检查页面加载时间、动画帧率、内存占用、无 layout thrashing |

当前已完成一轮浏览器真实页面抽样，详见 [VISUAL_AUDIT.md](VISUAL_AUDIT.md)。后续进入实际 UI 重做时，应持续用浏览器检查桌面与移动端首屏，而不是只看代码判断。
