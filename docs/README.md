# 声乐评估系统文档索引

> **v7.0-alpha | 2026-07-21** | Phase 0-3 完成, 237 tests passed | 分支: `feat/v7-fastapi-vue-refactor`
> v7.0 全栈重构执行中 — FastAPI + Vue 3 + Element Plus + Electron
> 详见 [V7_MIGRATION_PLAN.md](4-process/V7_MIGRATION_PLAN.md)

本目录按产品、技术、质量、过程和归档五类组织。新增文档应放入对应目录，不在项目根目录散放。

## 1. 产品文档

| 文档 | 说明 |
|------|------|
| [1-product/PRD.md](1-product/PRD.md) | 产品需求、用户场景、六维评分体系 |
| [1-product/GOALS.md](1-product/GOALS.md) | 产品定位、功能全景、设计原则 |

## 2. 技术文档

| 文档 | 说明 |
|------|------|
| [2-technical/ARCHITECTURE.md](2-technical/ARCHITECTURE.md) | v7.0 DDD 四层架构 + FastAPI + 绞杀者模式 |
| [2-technical/API_CONTRACT.md](2-technical/API_CONTRACT.md) | v7.0 API 契约 (16 paths + WebSocket) |
| [2-technical/SCORING.md](2-technical/SCORING.md) | 六维评分算法、权重、Feature Flags |
| [2-technical/frontend/README.md](2-technical/frontend/README.md) | 前端技术文档入口 (Vue 3 + Element Plus) |

## 3. 质量文档

| 文档 | 说明 |
|------|------|
| [3-quality/TDD.md](3-quality/TDD.md) | TDD 规范 (v7.0: 237 tests passed) |
| [3-quality/BDD.md](3-quality/BDD.md) | BDD 场景 (21 Feature files) |

### 测试体系状态 (v7.0-alpha)

| 层级 | 测试数 | 通过率 |
|------|--------|--------|
| v6.3 保留 (Unit) | 121 | ✅ 100% |
| Phase 1 领域 TDD | 88 | ✅ 100% |
| Phase 2 API 集成 | 20 | ✅ 100% |
| Phase 3 WebSocket 集成 | 8 | ✅ 100% |
| **总计** | **237** | ✅ **全部通过, 零回归** |

> 详见 [PROJECT_STATUS.md](4-process/PROJECT_STATUS.md) 和 [CHANGELOG.md](4-process/CHANGELOG.md)。

## 4. 过程文档

| 文档 | 说明 |
|------|------|
| [4-process/PROJECT_STATUS.md](4-process/PROJECT_STATUS.md) | 当前项目状态、v7.0 进度、已知问题 |
| [4-process/CHANGELOG.md](4-process/CHANGELOG.md) | 版本变更记录 (含 v7.0-alpha Phase 0-3) |
| [4-process/V7_MIGRATION_PLAN.md](4-process/V7_MIGRATION_PLAN.md) | **v7.0 全栈重构计划** (六阶段, 8 ADR, 26.5 天) |

## 5. 归档文档

历史文档位于 [5-archive/](5-archive/)。归档文档只作为背景参考，不作为当前开发的权威来源。
