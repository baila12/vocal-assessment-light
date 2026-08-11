# 声乐评估系统文档索引

> **v7.14 | 2026-08-10** | 分支: `main`
> 上传音频自动匹配标准歌曲 (song_match DDD 子域: BPM/调性/chroma/duration 特征 + 确定性置信度 + POST /songs/match + upload auto_match + CompareView 自动匹配区) | 714 后端测试 collected (710 passed) + 297 前端 GREEN

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
| [2-technical/ARCHITECTURE.md](2-technical/ARCHITECTURE.md) | v7.14 DDD 四层架构 + 评分权重领域 + 歌曲库领域 + 选歌录音 + 实时音准对比 + 自动匹配 + GSAP 动效 + 安全中间件 |
| [2-technical/API_CONTRACT.md](2-technical/API_CONTRACT.md) | API 契约 (23 paths + WebSocket) |
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
| [3-quality/BDD.md](3-quality/BDD.md) | BDD 场景 (21 Feature files, 18 step files) |
| [3-quality/DEEP_REVIEW_v7.14.md](3-quality/DEEP_REVIEW_v7.14.md) | **深度代码审查报告 v7.14** (2026-08-10): 65 findings (52C/10P/3R) + 6 死模块; 9 维度结论 + 修复优先级 P0/P1/P2 |

### 测试体系状态 (v7.14)

| 层级 | 测试数 | 通过率 | 说明 |
|------|:-----:|--------|------|
| DDD 单元测试 (domain + infrastructure + alignment + flag + middleware + WS 会话) | 575 | ✅ 100% | 领域 363 (含 song_match/ScoringWeights/fallback) + 基建 159 (含 pitch cache LRU/deps 单例) + 对齐/flag 23 + 中间件 23 + WS 会话 7 |
| FastAPI 集成测试 (API 层) | 73 | ✅ 100% | test_api_routes (19) + test_songs_api (21) + scoring API (14) + songs_pitch_api (9) + compare_pitch_api (4) + song_match_api (6, v7.14) (独立进程) |
| WebSocket 集成 | 17 | ✅ 100% | test_ws_score (13) + ws_pitch_update (4, v7.13) |
| 扩展测试 (DTW/repos) | 21 | ✅ 100% | tests/extended/ (独立进程; v7.12 删 test_score_calibrator) |
| **生产代码总计** | **686** | **100% GREEN** | (unit 575 + API 73 + WS 17 + 扩展 21) |
| 真实音频回归 | 28 | ⚠️ 24P+4F | BASELINE_V7_6 (4 breath 基线漂移 0.1-0.8 分, 既有, 见已知问题) |
| **后端 collected** | **714** | **710 passed** | 686 生产 + 28 真实音频; 4 失败均为 breath 基线漂移 |
| Vue 3 前端 (Vitest) | 297 | ✅ 100% | stores 85 + pitch utils 212 (v7.14 +11 songMatch.store) |
| 前端 vue-tsc | 0 errors | ✅ | TypeScript 类型检查 |
| 前端 Vite build | ~16s | ✅ | 生产构建 |
| BDD | 18 step files, 21 feature files | ⚠️ 见 BDD.md | 187 scenarios collected (121 API 级 + 66 browser); API 级存在既有失败 (Flask 遗留 step 文件), 详见 BDD.md/PROJECT_STATUS |

## 4. 过程文档

| 文档 | 说明 |
|------|------|
| [4-process/PROJECT_STATUS.md](4-process/PROJECT_STATUS.md) | 当前项目状态、v7.14 进度、已知问题、测试详情 |
| [4-process/CHANGELOG.md](4-process/CHANGELOG.md) | 版本变更记录 (v5.0 → v7.14) |
| [4-process/TEST_RESULTS.md](4-process/TEST_RESULTS.md) | 测试结果记录 (v7.14: 714 collected / 710 passed) |
| [4-process/V7_MIGRATION_PLAN.md](4-process/V7_MIGRATION_PLAN.md) | v7.0 全栈重构计划 (历史参考) |
| [4-process/audits/README.md](4-process/audits/README.md) | 项目审计与优化计划 |

## 5. 归档文档

历史文档位于 [5-archive/](5-archive/)，仅作背景参考。

---

### v7.14 改进总览

| 类别 | 改进项 | 涉及文件 |
|------|:-----:|------|
| 自动匹配领域 | song_match DDD 子域: MatchFeatures/SongMatchProfile/MatchCandidate/MatchResult + MatchFeatureExtractor (librosa BPM + chroma_stft 12-bin + Krumhansl-Schmuckler 24 键调性) + AutoMatchService + KeyDetector | backend/domain/song_match/* |
| 匹配算法 | 确定性置信度 = 0.30*bpm + 0.40*chroma + 0.15*key + 0.15*duration, 阈值 0.60; 转调不变 chroma 旋转余弦; 双 0 BPM 边界; log2 时长差 | backend/domain/song_match/services.py |
| 应用层 | AutoMatchUseCase: 预算式 ensure_profiles (无 profile 歌曲用 filepath 预计算) + deadline 超时 partial | backend/application/song_match/auto_match_use_case.py |
| 基建 | sqlite song_match_profiles 表 (stdlib sqlite3 + 线程锁, chroma JSON); SongRepository +list_all_with_filepath | backend/infrastructure/persistence/sqlite_song_match_profile_repo.py |
| API | POST /songs/match (Top-N 候选 + fallback_reason) + upload 可选 auto_match 注入 matched_song/candidates; deps +2 单例 | backend/interfaces/api/routes/song_match.py, backend/interfaces/api/routes/assessment.py |
| 前端 | songMatch.store (matchAudio/selectCandidate/compareWithSelected/fetchUserPitch) + CompareView 自动匹配区 (候选列表/置信度/BPM差/调性差 → 一键 DTW 对比) + api.ts 5 新类型 | frontend/src/stores/songMatch.store.ts, frontend/src/views/CompareView.vue, frontend/src/types/api.ts |
| BDD | auto-match.feature 核心场景 step defs (5P+3X); 重度场景 (噪音/100+ 歌/片段) xfail 标注单元测试 | tests/bdd/steps/test_auto_match_steps.py |
| 测试变化 | v7.14: 生产 537→633 (+96) 前端 286→297 (+11); v7.14 修复轮: 633→714 (+81: fallback 11 + streaming 7 + pitch cache 7 + deps 2 + 集成 13 + WS 3 + 其他) | 多个测试文件 |

### v7.12 改进总览

| 类别 | 改进项 | 涉及文件 |
|------|:-----:|------|
| 选歌录音 MVP | 曲库选歌 → /sing/:songId 演唱页 → WS 携带 song_id; SongMetadata.vocal_range 全链路 | backend/domain/songs/value_objects.py, backend/interfaces/ws/*, frontend/src/views/SingView.vue, SongsView.vue, router/index.ts |
| BDD 数据补齐 | vocals.wav 生成脚本 + KMP_DUPLICATE_LIB_OK 崩溃修复 + upload.feature fixture/httpx 修复 (5P+3S) | scripts/gen_bdd_test_data.py, tests/conftest.py, tests/bdd/steps/test_upload_steps.py |
| BDD animations 迁移 | step defs 迁移 Vue 3 data-test 选择器 + 前端 9 个 data-test 钩子 (7P+9X) | tests/bdd/steps/test_animations_steps.py, frontend/src/views/*.vue |
| BDD sing-song-select | step defs 迁移 Vue 3 (6P+6X, 录音相关 xfail) | tests/bdd/steps/test_sing_song_select_steps.py |
| dl_services 清理 | 删零生产引用死代码 (桩/model_manager 子包/features:types/enhanced_dl_assessor) | services/dl_services/*, tests/extended/test_score_calibrator.py |
| 测试变化 | 生产 521→509 (删 calibrator 15 + 新增集成 5), WS 10, 前端 Vitest 68 保持 | 多个测试文件 |
