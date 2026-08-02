# 声乐评估系统文档索引

> **v7.9 | 2026-08-02** | 分支: `feat/v7-fastapi-vue-refactor`
> 标准歌曲库后端 (DDD + TDD + BDD) | 475 测试 GREEN + 33 前端 GREEN

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
| [2-technical/ARCHITECTURE.md](2-technical/ARCHITECTURE.md) | v7.9 DDD 四层架构 + 歌曲库领域 + GSAP 动效 + 安全中间件 |
| [2-technical/API_CONTRACT.md](2-technical/API_CONTRACT.md) | API 契约 (21 paths + WebSocket) |
| [2-technical/SCORING.md](2-technical/SCORING.md) | 六维评分 + audiofeat + GNE 增强 + v7.9 真实音频基线 |
| [2-technical/API.md](2-technical/API.md) | API 参考文档 |
| [2-technical/PERFORMANCE_ANALYSIS_AND_OPTIMIZATION.md](2-technical/PERFORMANCE_ANALYSIS_AND_OPTIMIZATION.md) | 性能分析与优化 |
| [2-technical/TECH_RESEARCH.md](2-technical/TECH_RESEARCH.md) | v7.1 技术研究: 五维度算法验证 + 开源工具评级 |
| [2-technical/SCORING_ALGORITHM_IMPROVEMENT_PLAN.md](2-technical/SCORING_ALGORITHM_IMPROVEMENT_PLAN.md) | 评分算法改进计划 (P0/P1 ✅, P2 ✅) |
| [2-technical/frontend/README.md](2-technical/frontend/README.md) | 前端技术文档入口 (Vue 3 + Element Plus + GSAP) |
| [2-technical/frontend/ROUTES.md](2-technical/frontend/ROUTES.md) | 前端路由 (5 hash routes) |

## 3. 质量文档

| 文档 | 说明 |
|------|------|
| [3-quality/TDD.md](3-quality/TDD.md) | TDD 规范 |
| [3-quality/BDD.md](3-quality/BDD.md) | BDD 场景 (21 Feature files, 16 step files) |

### 测试体系状态 (v7.9)

| 层级 | 测试数 | 通过率 | 说明 |
|------|:-----:|--------|------|
| DDD 单元测试 (domain + infrastructure + alignment + flag + middleware) | 406 | ✅ 100% | 7 scorers + 10 extractors + songs domain + ABI + middleware |
| FastAPI 集成测试 | 33 | ✅ 100% | test_api_routes (19) + test_songs_api (14) (独立进程) |
| 扩展测试 (DTW/repos/calibrator) | 36 | ✅ 100% | tests/extended/ (独立进程) |
| **生产代码总计** | **475** | **100% GREEN** | |
| Vue 3 前端 (Vitest) | 33 | ✅ 100% | stores |
| 前端 vue-tsc | 0 errors | ✅ | TypeScript 类型检查 |
| 前端 Vite build | ~8.6s | ✅ | 生产构建 |
| 真实音频回归 | 28 | ✅ 100% | BASELINE_V7_6 |
| BDD | 16 step files, 21 feature files | ✅ | +database (v7.9) |

## 4. 过程文档

| 文档 | 说明 |
|------|------|
| [4-process/PROJECT_STATUS.md](4-process/PROJECT_STATUS.md) | 当前项目状态、v7.9 进度、已知问题、测试详情 |
| [4-process/CHANGELOG.md](4-process/CHANGELOG.md) | 版本变更记录 (v5.0 → v7.9) |
| [4-process/TEST_RESULTS.md](4-process/TEST_RESULTS.md) | 测试结果记录 (v7.9: 475 tests) |
| [4-process/V7_MIGRATION_PLAN.md](4-process/V7_MIGRATION_PLAN.md) | v7.0 全栈重构计划 (历史参考) |
| [4-process/audits/README.md](4-process/audits/README.md) | 项目审计与优化计划 |

## 5. 归档文档

历史文档位于 [5-archive/](5-archive/)，仅作背景参考。

---

### v7.9 改进总览

| 类别 | 改进项 | 涉及文件 |
|------|:-----:|------|
| 歌曲库后端 | 标准歌曲库 DDD 四层 + TDD + BDD | backend/domain/songs/, infrastructure/ + application/ + routes/ |
| 歌曲库 API | POST/GET/GET id/DELETE /api/v1/songs, 去重+分页+筛选+搜索 | songs.py, schemas/songs.py, deps.py, config.py |
| BDD 扩展 | database.feature 10 场景 (4P+6XF) | test_database_steps.py, conftest.py |
| 测试增长 | 单元 369→406 (+37), 集成 19→33 (+14), 总计 423→475 (+52) | 多个测试文件 |
