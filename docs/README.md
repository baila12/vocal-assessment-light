# 声乐评估系统文档索引

> **v7.8 | 2026-08-01** | 分支: `feat/v7-fastapi-vue-refactor`
> GNE 接入 + GSAP 动效美化 + 前后端对齐 | 423 测试 GREEN + 33 前端 GREEN

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
| [2-technical/ARCHITECTURE.md](2-technical/ARCHITECTURE.md) | v7.8 DDD 四层架构 + GSAP 动效 + 安全中间件 |
| [2-technical/API_CONTRACT.md](2-technical/API_CONTRACT.md) | API 契约 (19 paths + WebSocket) |
| [2-technical/SCORING.md](2-technical/SCORING.md) | 六维评分 + audiofeat + GNE 增强 + v7.8 真实音频基线 |
| [2-technical/TECH_RESEARCH.md](2-technical/TECH_RESEARCH.md) | v7.1 技术研究: 五维度算法验证 + 开源工具评级 |
| [2-technical/SCORING_ALGORITHM_IMPROVEMENT_PLAN.md](2-technical/SCORING_ALGORITHM_IMPROVEMENT_PLAN.md) | 评分算法改进计划 (P0/P1 ✅, P2 ✅) |
| [2-technical/frontend/README.md](2-technical/frontend/README.md) | 前端技术文档入口 (Vue 3 + Element Plus + GSAP) |

## 3. 质量文档

| 文档 | 说明 |
|------|------|
| [3-quality/TDD.md](3-quality/TDD.md) | TDD 规范 |
| [3-quality/BDD.md](3-quality/BDD.md) | BDD 场景 (23 Feature files, 15 step files, 61 scenarios) |

### 测试体系状态 (v7.8)

| 层级 | 测试数 | 通过率 | 说明 |
|------|:-----:|--------|------|
| DDD 领域 (scorers + value objects) | 127 | ✅ 100% | 7 scorers + comparison + domain services |
| DDD 基建 (extractors + orchestrator + ABI) | 136 | ✅ 100% | 10 extractors + audio_utils + ABI |
| DDD 对齐 + Flag bridge + GNE | 22 | ✅ 100% | alignment + flag + GNE tests (v7.8: +5) |
| 中间件测试 | 22 | ✅ 100% | SecurityHeaders + RateLimit + MaxBodySize |
| **DDD 合计** | **369** | **100% GREEN** | |
| FastAPI 集成测试 | 20 | ✅ 100% | test_api_routes (独立进程) |
| 扩展测试 (DTW/repos/calibrator) | 34 | ✅ 100% | tests/extended/ (独立进程) |
| **生产代码总计** | **423** | **100% GREEN** | |
| Vue 3 前端 (Vitest) | 33 | ✅ 100% | stores |
| 前端 vue-tsc | 0 errors | ✅ | TypeScript 类型检查 |
| 真实音频回归 | 28 | ✅ 100% | BASELINE_V7_6 |
| BDD | 15 step files, 61 scenarios | ✅ | +dtw-demotion +scoring-config (v7.8) |

## 4. 过程文档

| 文档 | 说明 |
|------|------|
| [4-process/PROJECT_STATUS.md](4-process/PROJECT_STATUS.md) | 当前项目状态、v7.8 进度、已知问题、测试详情 |
| [4-process/CHANGELOG.md](4-process/CHANGELOG.md) | 版本变更记录 (v5.0 → v7.8) |
| [4-process/TEST_RESULTS.md](4-process/TEST_RESULTS.md) | 测试结果记录 (v7.8: 423 tests) |
| [4-process/V7_MIGRATION_PLAN.md](4-process/V7_MIGRATION_PLAN.md) | v7.0 全栈重构计划 (历史参考) |

## 5. 归档文档

历史文档位于 [5-archive/](5-archive/)，仅作背景参考。

---

### v7.8 改进总览

| 类别 | 改进项 | 涉及文件 |
|------|:-----:|------|
| 评分增强 | GNE (AROC=0.886) 接入 TechniqueScorer | technique_scorer.py, test_technique_scorer.py |
| GSAP 动效 | 全站 6 页面 GSAP 动画 + reduced-motion | useGsap.ts, main.ts, AppLayout.vue, 5 views |
| 前后端对齐 | 3 HIGH + 6 MEDIUM 修复 | flags.store.ts, client.ts, types/api.ts, flags.py, ScoreRadar.vue, HistoryView.vue |
| 架构清理 | types.py 引用清零, orchestrator 测试清理 | types.py, test_orchestrator.py |
| BDD 扩展 | +2 step files (32 scenarios) | test_dtw_demotion_steps.py, test_scoring_config_steps.py |
| 文档更新 | 全量文档同步至 v7.8 | 9 个文档文件 |
