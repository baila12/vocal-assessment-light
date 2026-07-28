# 声乐评估系统文档索引

> **v7.3.0 | 2026-07-27** | 分支: `feat/v7-fastapi-vue-refactor`
> audiofeat 评分闭环 + Comparison DDD + 严格测试审计 (12 fixes)
> 375 生产测试 GREEN | 120 domain | 106 infrastructure | 23 middleware | 51 extended | 34 integration

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
| [2-technical/ARCHITECTURE.md](2-technical/ARCHITECTURE.md) | v7.3 DDD 四层架构 + Comparison 领域 + audiofeat 增强 |
| [2-technical/API_CONTRACT.md](2-technical/API_CONTRACT.md) | API 契约 (16 paths + WebSocket + normalization) |
| [2-technical/SCORING.md](2-technical/SCORING.md) | 六维评分 + audiofeat 增强 + v7.3 真实音频基线 |
| [2-technical/TECH_RESEARCH.md](2-technical/TECH_RESEARCH.md) | v7.1 技术研究: 五维度算法验证 + 开源工具评级 + 实施路线 |
| [2-technical/frontend/README.md](2-technical/frontend/README.md) | 前端技术文档入口 (Vue 3 + Element Plus) |

### 外部研究资源

| 路径 | 说明 |
|------|------|
| `参考论文/` | 论文PDF + 六维研究总结 + 综合评估报告 (项目外部目录) |

> 参考论文位于项目目录外的独立路径

## 3. 质量文档

| 文档 | 说明 |
|------|------|
| [3-quality/TDD.md](3-quality/TDD.md) | TDD 规范 |
| [3-quality/BDD.md](3-quality/BDD.md) | BDD 场景 (21 Feature files) |

### 测试体系状态 (v7.3.0)

| 层级 | 测试数 | 通过率 | 说明 |
|------|:-----:|--------|------|
| DDD 领域测试 (含 comparison + audiofeat) | 120 | ✅ 100% | 7 scorers + comparison scoring + value objects |
| DDD 基建测试 (extractors + orchestrator) | 106 | ✅ 100% | audiofeat + audio_utils + pitch + rhythm + breath + technique |
| DDD 对齐 + Flag 测试 | 17 | ✅ 100% | alignment + extraction flag + SPA routes |
| 中间件测试 | 23 | ✅ 100% | SecurityHeaders + RateLimit (含 monkeypatch 修复) |
| **DDD 合计** | **290** | **100% GREEN** | |
| FastAPI 集成测试 | 20 | ✅ 100% | test_api_routes (独立进程) |
| Flask + WS 集成测试 | 14 | ✅ 100% | test_ws_score + test_api (独立进程) |
| 扩展测试 (DTW/repos/calibrator/SPA) | 51 | ✅ 100% | tests/extended/ (独立进程) |
| **生产代码总计** | **375** | **100% GREEN** | |
| Vue 3 前端 (Vitest) | 33 | ✅ 100% | stores + composables |
| 真实音频回归 | 21 | ✅ 21/28 | v5.19→v7.3 基线漂移 7 项 (已更新基线) |
| TDD 未来特性 | 1 skip + 4 xfail | ⏭️ | 按需实现 |
| BDD | 36 steps 未实现 | ⏭️ | Step definitions 待实现 |

## 4. 过程文档

| 文档 | 说明 |
|------|------|
| [4-process/PROJECT_STATUS.md](4-process/PROJECT_STATUS.md) | 当前项目状态、v7.3 进度、已知问题、测试详情 |
| [4-process/CHANGELOG.md](4-process/CHANGELOG.md) | 版本变更记录 (v5.0 → v7.3.0) |
| [4-process/V7_MIGRATION_PLAN.md](4-process/V7_MIGRATION_PLAN.md) | v7.0 全栈重构计划 (六阶段, 8 ADR) |

## 5. 归档文档

历史文档位于 [5-archive/](5-archive/)，仅作背景参考。
