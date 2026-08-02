# Findings

> ⚠️ **历史文档 (2026-06-06)** — 本文档 pre-date v7.0 FastAPI+Vue 重构，记录的是 v5.17 ~ v6.3 (Flask + Vanilla JS SPA) 时代的审计发现。其中描述的"Flask 应用工厂""Vanilla JS SPA""emoji UI""旧 HTML 页面""pytest 启动慢"等问题已在 v7.0~v7.9 重构中解决。本文件保留作为项目演进的历史记录。当前状态见 [PROJECT_STATUS.md](../PROJECT_STATUS.md)。

## Completed Capabilities
- 项目文档显示当前版本目标为 v5.17，核心后端能力包括 Quick、Professional、Compare 三模式。
- 后端已有 Flask 应用工厂、API 蓝图、分层服务、历史记录仓储、Demucs 分离、DTW 对比、报告生成。
- 文档记录 v5.15-v5.17 已修复 Pro Rhythm、SingMOS 跨域、DTW 自动搜索、Pro Breath、混合音频检测、GPU 检测。
- 新前端已开始切换到 SPA：`web/static/index.html` 作为单入口，`app.js` 注册 hash routes，`router.js` 实现 HashRouter。
- 本地 GSAP 和 Chart.js 已引入，且已有 `effects/`、`components/` 中的 GSAP 动效模块。
- BDD 已新增 `tests/bdd/features/navigation.feature`、`animations.feature`、`offline.feature` 等，存在 SPA 路由定义雏形。

## Backend Plan Findings
- v5.18 计划重点是 Feature Flag、多尺度 HNR、Praat CPP、voicing detection、TorchCREPE fallback。
- v6.0 轨道 A 计划标准歌曲数据库、自动匹配、选歌录音、曲库管理、特征预计算。
- v6.0 轨道 B 计划校准数据集、评分参数校准、可配置评分系统。
- BDD 已定义 `database.feature`、`auto-match.feature`、`song-select.feature`、`scoring-config.feature`、`nonblocking-analysis.feature`、`realtime-analysis.feature`。
- 当前后端 API 文档仍以 v5.17 稳定接口为主，v6.0 相关 API 尚未落地，需要前端以“预留页面 + 空状态 + mock/schema 契约”的方式推进。

## Frontend Issues
- 新旧前端并存：`analysis.html`、`compare.html`、`settings.html` 仍在目录中，SPA 入口又重定向旧页面，容易造成维护分叉。
- 页面组件中大量 emoji 直接参与信息架构，例如 `HomePage.js`、`ReportPage.js`、`ComparePage.js`、`SingPage.js`。
- 首页仍包含“五维评分”“改进建议”等偏样例/宣传性质内容，和用户真正需要的演唱评估工作流不完全匹配。
- 建议块、评分比例、模式说明等信息缺少真实任务上下文，视觉上像功能堆叠而不是一个清晰的练习/评估产品。
- GSAP 已存在，但更多是零散入场和微交互，缺少统一动效语言、页面级叙事节奏和可审美验收的视频样例。

## Browser Visual Audit Findings
- 静态 SPA 预览 `http://localhost:8000/` 可访问，返回 200；Flask `http://localhost:5000/` 在 3 秒检查中超时，后端服务启动/验证需要另行定位。
- 桌面 Home 首屏可见 `专业声乐能力评估`、`离线分析`、`五维评分`、`改进建议`、`导入音频`、`快速录音`、`评估模式`、`使用说明` 等内容，首页同时承担宣传、说明、入口和样例展示，核心任务被稀释。
- 桌面 Home 抽样显示 emoji 数量约 10，inline style 节点约 27；移动 Home 中 `.sidebar` 计算样式为 `order: -1`，说明/评分/技巧区域在小屏会被提前，和“优先开始上传/录音”的移动端目标冲突。
- Compare 页面抽样显示标题和按钮仍依赖 `⚖️`、`🎯`、`🎤`、`🔍` 等 emoji，inline style 节点约 47；页面有标准音频与我的演唱入口，但没有评分参数、标准曲库选择、自动匹配候选、fallback 状态预留。
- Settings 页面抽样显示 emoji 数量约 6，inline style 节点约 38；当前只有主题、默认评估模式、自动跳转和缓存管理，没有 `Settings/Scoring`、`Settings/Models`、Feature Flag、GPU/模型状态和评分权重入口。
- 移动端底部导航抽样只呈现首页、演唱、对比、历史，设置入口在移动主导航中不可见，和桌面顶部导航的 5 个入口不一致。
- 真实页面问题已沉淀到 `docs/2-technical/frontend/VISUAL_AUDIT.md`，作为后续 UI 重做的浏览器验收依据。

## Test And BDD Issues
- 新 `test_spa_routes.py` 期待旧 HTML 页面 301 到 `/`，但大量旧 E2E 仍期待 `analysis.html`、`compare.html`。
- BDD 有 navigation/animations/offline 特性，但还未成为前端路由和页面设计的唯一真相来源。
- 之前运行 pytest 路由相关测试长时间无输出，说明测试启动或应用 import 可能有较重依赖链。

## Documentation Issues
- 文档已重组到 `docs/1-product`、`docs/2-technical`、`docs/3-quality`、`docs/4-process`，但 `docs/README.md` 仍引用旧路径和旧文件名。
- 前端设计文档在 `docs/5-archive/FRONTEND_DESIGN.md`，当前 SPA 重构缺少新的模块化前端设计规范。
- 当前文档对“已完成算法能力”记录较充分，对“前端体验目标、页面职责、跳转契约、审美验收标准”记录不足。
- 已新增 `docs/2-technical/frontend/VISUAL_AUDIT.md`，但后续仍需要进一步拆出 `DESIGN_SYSTEM.md`、`MOTION.md`、`COMPONENTS.md`，让前端文档从审计进入实施规范。
