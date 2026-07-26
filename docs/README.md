# 声乐评估系统文档索引

> **v7.1.3 | 2026-07-26** | 分支: `feat/v7-fastapi-vue-refactor`
> DDD 绞杀者内移完成 (10/10 模块自包含) | 评分对齐修复 | 严格真实音频验证
> 337 单元 GREEN | 53 系统 GREEN | 10/10 真实音频 PASS

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
| [2-technical/ARCHITECTURE.md](2-technical/ARCHITECTURE.md) | v7.1.3 DDD 四层架构 + 绞杀者完成 + 10/10 自包含模块 |
| [2-technical/API_CONTRACT.md](2-technical/API_CONTRACT.md) | v7.0 API 契约 (16 paths + WebSocket) |
| [2-technical/SCORING.md](2-technical/SCORING.md) | 六维评分 + 权重说明 + 对齐数据 (v7.1.3 版) |
| [2-technical/TECH_RESEARCH.md](2-technical/TECH_RESEARCH.md) | **v7.1 技术研究**: 五维度算法验证 + 开源工具评级 + 实施路线 |
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

### 测试体系状态

| 层级 | 测试数 | 通过率 |
|------|--------|--------|
| DDD 基建测试 (含新增) | 85 | ✅ 100% |
| DDD Flag 测试 | 11 | ✅ 100% |
| DDD 对齐回归测试 (v7.1.3) | 7 | ✅ 100% |
| 音频工具测试 (v7.1.3) | 18 | ✅ 100% |
| v6.3 单元测试 | 79 | ✅ 100% |
| Phase 1 领域 TDD | 88 | ✅ 100% |
| Phase 2 API 集成 | 20 | ✅ 100% |
| Phase 3 WebSocket 集成 | 8 | ✅ 100% |
| Phase 4 Vue 3 前端 | 33 | ✅ 100% (Vitest) |
| v7.0.2 中间件测试 | 23 | ⚠️ 21/23 (2 预存 rate-limit) |
| v6.x TDD + 集成 | 79 | ⚠️ 64 通过 (15 预存失败) |
| 系统 E2E | 53 | ✅ 100% |
| 真实音频验证 | 10 | ✅ 100% (5 files × 2 paths) |
| **总计** | **~441** | **~402 通过** |

## 4. 过程文档

| 文档 | 说明 |
|------|------|
| [4-process/PROJECT_STATUS.md](4-process/PROJECT_STATUS.md) | 当前项目状态、v7.1.3 进度、绞杀者完成 |
| [4-process/CHANGELOG.md](4-process/CHANGELOG.md) | 版本变更记录 (v5.0 → v7.1.3) |
| [4-process/V7_MIGRATION_PLAN.md](4-process/V7_MIGRATION_PLAN.md) | v7.0 全栈重构计划 (六阶段, 8 ADR) |

## 5. 归档文档

历史文档位于 [5-archive/](5-archive/)，仅作背景参考。
