# 声乐评估系统文档索引

> **性能是全部功能的一等需求**。每个文档均涵盖对应模块的性能目标、预算和监控方式。
> 性能总览见 [PRD §4.1](1-product/PRD.md) 和 [PROJECT_STATUS 性能基准](4-process/PROJECT_STATUS.md)。

本目录按产品、技术、质量、过程和归档五类组织。新增文档应放入对应目录，不在项目根目录散放。

## 1. 产品文档

| 文档 | 说明 |
|------|------|
| [1-product/PRD.md](1-product/PRD.md) | 产品需求、用户场景、v5.18/v6.0 路线 |
| [1-product/GOALS.md](1-product/GOALS.md) | 产品定位、功能全景、设计原则 |

## 2. 技术文档

| 文档 | 说明 |
|------|------|
| [2-technical/ARCHITECTURE.md](2-technical/ARCHITECTURE.md) | 系统架构与后端计划 |
| [2-technical/API.md](2-technical/API.md) | 当前稳定 API |
| [2-technical/SCORING.md](2-technical/SCORING.md) | 评分算法、权重、阈值和 DTW 降级策略 |
| [2-technical/frontend/README.md](2-technical/frontend/README.md) | 前端技术文档入口 |
| [2-technical/frontend/ROUTES.md](2-technical/frontend/ROUTES.md) | SPA 路由契约与预留页面 |
| [2-technical/frontend/BACKEND_ALIGNMENT.md](2-technical/frontend/BACKEND_ALIGNMENT.md) | 前端与后端 v5.18/v6.0 计划对齐 |
| [2-technical/frontend/VISUAL_AUDIT.md](2-technical/frontend/VISUAL_AUDIT.md) | 基于浏览器真实页面的前端视觉审计 |

## 3. 质量文档

| 文档 | 说明 |
|------|------|
| [3-quality/TDD.md](3-quality/TDD.md) | 单元/集成/E2E 测试规范 (v5.18 审查后: 141 测试全部通过) |
| [3-quality/BDD.md](3-quality/BDD.md) | BDD 场景、目录和验收流程 (21 Feature 文件, 9 已实现 Step Defs) |

### 测试体系状态 (v5.18 代码审查后)

| 层级 | 文件数 | 测试数 | 通过率 |
|------|--------|--------|--------|
| Unit | 12 | 141+ | 141+ passed ✅ |
| Integration | 4 | 25 | 25/25 (100%) |
| Real Audio Regression | 1 | 27 | 按需运行 |
| E2E (SPA) | 10+ | ~45 | 按需运行 |
| TDD RED | 1 | 13 | 13 xfail (引导开发) |
| BDD | 21 features | ~75 scenarios | 4 features 已实现 Step Defs |

> 详见 [PROJECT_STATUS.md](4-process/PROJECT_STATUS.md) 验收状态和 [CHANGELOG.md](4-process/CHANGELOG.md) 审查修复详情。

## 4. 过程文档

| 文档 | 说明 |
|------|------|
| [4-process/PROJECT_STATUS.md](4-process/PROJECT_STATUS.md) | 当前项目状态和已知问题 |
| [4-process/CHANGELOG.md](4-process/CHANGELOG.md) | 版本变更记录 |
| [4-process/audits/README.md](4-process/audits/README.md) | 审计与规划文档入口 |
| [4-process/audits/PROJECT_AUDIT_AND_OPTIMIZATION_PLAN.md](4-process/audits/PROJECT_AUDIT_AND_OPTIMIZATION_PLAN.md) | 项目审计与优化计划 |

## 5. 归档文档

历史文档位于 [5-archive/](5-archive/)。归档文档只作为背景参考，不作为当前开发的权威来源。
