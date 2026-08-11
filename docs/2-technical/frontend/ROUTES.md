# 前端路由 v7.14

> Vue 3 SPA, Vue Router 4.6, hash history (Electron 兼容)

---

## 当前路由

| 路由 | 组件 | 说明 |
|------|------|------|
| `#/` | `HomeView.vue` | 首页: 上传 + 模式选择 (Quick/Pro) + 录音入口 |
| `#/report/:id?` | `ReportView.vue` | 评分报告: 六维雷达图 + 改进建议 + 音频回放 + 权重配置面板 (v7.11) |
| `#/history` | `HistoryView.vue` | 历史记录: 分页列表 + 搜索 + 批量删除 |
| `#/compare` | `CompareView.vue` | 对比分析: 双文件上传 → DTW → 双轨叠加 (标准虚线 + 用户动态着色实线) + 偏差三色填色 + 热力图条/缩略条 + 低对齐段落标记 + 性能模式降级 + 截图/快捷键 (v7.13 P5) + **上传录音自动匹配区 (候选列表/置信度/BPM差/调性差 → 一键 DTW 对比) (v7.14)** |
| `#/sing/:songId?` | `SingView.vue` | 实时演唱: Canvas + AudioWorklet + WebSocket 流式评分; 选歌录音 (v7.12); v7.13 实时音准对比: 参考 F0 线叠加 + 录音中 live 偏差着色 + 回放控制 (播放/拖拽/倍速/A-B) + 回放统计面板 (精准/略偏/跑调) |
| `#/songs` | `SongsView.vue` | 标准曲库: 卡片网格 + 搜索/筛选 + 上传/删除/试听 + 选择此歌 (v7.10/v7.12) |

全部懒加载 (`() => import(...)`), hash history (`createWebHashHistory`).

---

## 路由性能

| 指标 | 实际 (Vite build) |
|------|:---:|
| Main chunk (Element Plus + Vue + Chart.js) | ~346 KB gzip |
| ReportView (含 Chart.js radar) | ~65 KB gzip |
| 其他页面 (lazy loaded) | 2-4 KB gzip each |
| Vite build 耗时 | ~16s |

---

## 路由特性

- **全部懒加载**: 所有页面组件使用 `() => import(...)` 按需加载。
- **Hash history**: `createWebHashHistory()` 确保 Electron `file://` 协议兼容。
- **无效路由捕获**: `/:pathMatch(.*)*` catch-all 路由 + `router.beforeEach` 守卫，显示 ElMessage.warning 后重定向首页 (v7.7)。
- **选歌录音 (v7.12)**: `#/sing/:songId` 可选参数路由 — 有 songId 时加载参考歌曲并进入录音准备; 无 songId 时显示选歌区。SongsView 卡片"选择此歌"按钮跳转此路由。
- **实时音准对比 (v7.13)**: SingView 选歌后加载参考 F0 曲线 + WS `pitch_update` 实时推送用户音高 (录音中 live 对比/回放分析); CompareView (`#/compare`) 双文件对比升级为双轨叠加 + 偏差三色填色 + 热力图条/缩略条 + 性能降级 + 截图/快捷键。
- **上传自动匹配 (v7.14)**: CompareView 自动匹配区 — 上传用户演唱录音 → `POST /songs/match` 返回最佳匹配 + Top-3 候选 (歌名/歌手/置信度/BPM差/调性差) → 选中候选 → 一键 `POST /songs/{id}/compare` DTW 对比 → 复用 Phase 5 双轨叠加; 无匹配时透传 `fallback_reason` 优雅提示。

## 旧页面重定向

Flask 旧前端 (`web/static/`) 已于 v7.6 移除。旧 HTML 页面 (`/analysis.html`, `/compare.html`, `/settings.html`) 均已废弃。当前所有访问由 FastAPI serve `frontend/dist/` (Vue 3 SPA) 处理。
