# 声乐评估系统文档索引

> **v7.13 | 2026-08-08** | 分支: `main`
> 实时音准对比子系统 Phase 1-5 (参考音高 API + WS pitch_update + 偏差着色/滚动窗口/播放控制 + 录音中实时对比 + 录音后回放分析 + CompareView 双轨叠加/热力图/性能降级/截图/快捷键) | 537 后端测试 GREEN + 286 前端 GREEN

本目录按产品、技术、质量、过程和归档五类组织。

---

## 1. 产品文档

| 文档 | 说明 |
|------|------|
| [1-product/PRD.md](1-product/PRD.md) | 产品需求、用户场景、六维评分体系 |
| [1-product/GOALS.md](1-product/GOALS.md) | 产品定位、功能全景、设计原则 |

## 2. 技术文档

| 文档 | 说明 |
|------|------|
| [2-technical/ARCHITECTURE.md](2-technical/ARCHITECTURE.md) | v7.13 DDD 四层架构 + 评分权重领域 + 歌曲库领域 + 选歌录音 + 实时音准对比 + GSAP 动效 + 安全中间件 |
| [2-technical/API_CONTRACT.md](2-technical/API_CONTRACT.md) | API 契约 (22 paths + WebSocket) |
| [2-technical/SCORING.md](2-technical/SCORING.md) | 六维评分 + audiofeat + GNE 增强 + v7.9 真实音频基线 |
| [2-technical/API.md](2-technical/API.md) | API 参考文档 |
| [2-technical/PERFORMANCE_ANALYSIS_AND_OPTIMIZATION.md](2-technical/PERFORMANCE_ANALYSIS_AND_OPTIMIZATION.md) | 性能分析与优化 |
| [2-technical/TECH_RESEARCH.md](2-technical/TECH_RESEARCH.md) | v7.1 技术研究: 五维度算法验证 + 开源工具评级 |
| [2-technical/SCORING_ALGORITHM_IMPROVEMENT_PLAN.md](2-technical/SCORING_ALGORITHM_IMPROVEMENT_PLAN.md) | 评分算法改进计划 (P0/P1 ✅, P2 ✅) |
| [2-technical/frontend/README.md](2-technical/frontend/README.md) | 前端技术文档入口 (Vue 3 + Element Plus + GSAP) |
| [2-technical/frontend/ROUTES.md](2-technical/frontend/ROUTES.md) | 前端路由 (7 hash routes, 含 /sing/:songId) |

## 3. 质量文档

| 文档 | 说明 |
|------|------|
| [3-quality/TDD.md](3-quality/TDD.md) | TDD 规范 |
| [3-quality/BDD.md](3-quality/BDD.md) | BDD 场景 (21 Feature files, 17 step files) |

### 测试体系状态 (v7.13)

| 层级 | 测试数 | 通过率 | 说明 |
|------|:-----:|--------|------|
| DDD 单元测试 (domain + infrastructure + alignment + flag + middleware) | 451 | ✅ 100% | 6 scorers + 音色调整 + 10 extractors + songs/songs_pitch domain + ScoringWeights + ABI + middleware |
| FastAPI 集成测试 | 65 | ✅ 100% | test_api_routes (19) + test_songs_api (20) + scoring API (14) + songs_pitch_api (9) + compare_pitch_api (3, v7.13 P5) (独立进程) |
| 扩展测试 (DTW/repos) | 21 | ✅ 100% | tests/extended/ (独立进程; v7.12 删 test_score_calibrator) |
| **生产代码总计** | **537** | **100% GREEN** | |
| WebSocket 集成 | 14 | ✅ 100% | test_ws_score (10) + ws_pitch_update (4, v7.13) |
| Vue 3 前端 (Vitest) | 286 | ✅ 100% | stores 74 + pitch utils 212 (v7.13 P1-P5) |
| 前端 vue-tsc | 0 errors | ✅ | TypeScript 类型检查 |
| 前端 Vite build | ~16s | ✅ | 生产构建 |
| 真实音频回归 | 28 | ⚠️ 24P+4F | BASELINE_V7_6 (4 breath 基线漂移 0.1-0.8 分, 见已知问题) |
| BDD | 17 step files, 21 feature files | ✅ | upload 5P+3S, animations 7P+9X, sing-song-select 6P+6X, pitch-realtime 25X (v7.13) |

## 4. 过程文档

| 文档 | 说明 |
|------|------|
| [4-process/PROJECT_STATUS.md](4-process/PROJECT_STATUS.md) | 当前项目状态、v7.13 进度、已知问题、测试详情 |
| [4-process/CHANGELOG.md](4-process/CHANGELOG.md) | 版本变更记录 (v5.0 → v7.13) |
| [4-process/TEST_RESULTS.md](4-process/TEST_RESULTS.md) | 测试结果记录 (v7.13: 537 tests) |
| [4-process/V7_MIGRATION_PLAN.md](4-process/V7_MIGRATION_PLAN.md) | v7.0 全栈重构计划 (历史参考) |
| [4-process/audits/README.md](4-process/audits/README.md) | 项目审计与优化计划 |

## 5. 归档文档

历史文档位于 [5-archive/](5-archive/)，仅作背景参考。

---

### v7.12 改进总览

| 类别 | 改进项 | 涉及文件 |
|------|:-----:|------|
| 选歌录音 MVP | 曲库选歌 → /sing/:songId 演唱页 → WS 携带 song_id; SongMetadata.vocal_range 全链路 | backend/domain/songs/value_objects.py, backend/interfaces/ws/*, frontend/src/views/SingView.vue, SongsView.vue, router/index.ts |
| BDD 数据补齐 | vocals.wav 生成脚本 + KMP_DUPLICATE_LIB_OK 崩溃修复 + upload.feature fixture/httpx 修复 (5P+3S) | scripts/gen_bdd_test_data.py, tests/conftest.py, tests/bdd/steps/test_upload_steps.py |
| BDD animations 迁移 | step defs 迁移 Vue 3 data-test 选择器 + 前端 9 个 data-test 钩子 (7P+9X) | tests/bdd/steps/test_animations_steps.py, frontend/src/views/*.vue |
| BDD sing-song-select | step defs 迁移 Vue 3 (6P+6X, 录音相关 xfail) | tests/bdd/steps/test_sing_song_select_steps.py |
| dl_services 清理 | 删零生产引用死代码 (桩/model_manager 子包/features:types/enhanced_dl_assessor) | services/dl_services/*, tests/extended/test_score_calibrator.py |
| 测试变化 | 生产 521→509 (删 calibrator 15 + 新增集成 5), WS 10, 前端 Vitest 68 保持 | 多个测试文件 |
