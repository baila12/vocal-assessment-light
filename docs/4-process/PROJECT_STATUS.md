# 项目状态

> 更新: 2026-07-23 | 版本: **v7.1.0** | 分支: `feat/v7-fastapi-vue-refactor`

---

## 一、架构

```
Vue 3 SPA (frontend/dist/)  →  FastAPI (:8000)  ←  Flask /old (绞杀者)
                                      │
    ┌─────────────────────────────────┼──────────────────────────┐
    │  backend/ (DDD 四层)            │  旧服务层 (绞杀者残留)     │
    │  domain/assessment/ (6 scorers) │  services/features/ (12)  │
    │  application/ (orchestrator)    │  services/scoring/  (8)   │
    │  infrastructure/audio/ (4)      │  services/dl_services/ (11)│
    │  interfaces/api/ + ws/          │  api/business/ (bridge)   │
    │  shared/ (EventBus, ScoreLevel) │  api/routes/ (Flask)      │
    └─────────────────────────────────┴──────────────────────────┘
```

**评分路径**: `analyze_and_score()` → `ScoringOrchestrator` (DDD 六维, 默认)  
**回退路径**: `ScoreServiceV4` (五维, `enable_ddd_scoring=False`)  
**端口策略**: 开发 → 8000 | Electron → `--port=0` (OS 分配) | 生产 → FastAPI 服务 `frontend/dist/`

---

## 二、完成功能

### v7.1.0 (2026-07-23) — DDD 接入生产 + 死代码清理 + FCPE

| 类别 | 项目 | 状态 |
|------|------|------|
| **评分** | DDD `ScoringOrchestrator` 六维评分 (默认) | ✅ |
| **评分** | `ScoreServiceV4` 五维评分 (flag 回退) | ✅ |
| **评分** | 六维权重: pitch 10%, rhythm 10%, breath 20%, technique 25%, muscle 25%, artistry 10% | ✅ |
| **评分** | 音色加减分 (+3~-5, clamp[0,100]) | ✅ |
| **评分** | `ScoreLevel.from_score()` 等级判定 (唯一权威来源) | ✅ |
| **事件** | EventBus → `ScoreCalculated` 自动保存历史 | ✅ |
| **API** | FastAPI 21 端点 + WebSocket `/ws/v1/score` | ✅ |
| **API** | Pydantic v2 请求/响应校验 | ✅ |
| **API** | 速率限制 + 安全响应头 (CSP, HSTS, etc.) | ✅ |
| **API** | 响应含 `muscle_strength` + `timbre_adjustment` + `heuristic_dimensions` | ✅ |
| **前端** | Vue 3 + Element Plus + Pinia (5 页面) | ✅ |
| **前端** | FastAPI 服务 `frontend/dist/` (SPA fallback + /assets) | ✅ |
| **前端** | Element Plus Icons 替换 120+ emoji | ✅ |
| **桌面** | Electron spawn 嵌入式 Python + 进程守护 | ✅ |
| **基建** | `backend/infrastructure/audio/` librosa_loader, pyin_extractor, demucs_separator | ✅ |
| **基建** | `backend/infrastructure/audio/fcpe_extractor.py` (FCPE, 96.79% RPA) | ✅ |
| **基建** | Protocol 接口: AudioLoader, PitchExtractor, VoiceSeparator | ✅ |
| **基建** | `backend/application/assessment/` feature_adapters, scoring_orchestrator, history_subscriber | ✅ |
| **清理** | 删除 4 个死代码文件 (~1,200 行): dl_quality_assessor, emotion_manager, professional_feedback, audio_comparison | ✅ |
| **清理** | 移除 `_apply_dl_fusion()` + DL 字段 (ScoreResultV4, AnalysisResult) | ✅ |
| **清理** | 移除 diagnostic.py 中 s3prl/wvmos/speechbrain | ✅ |
| **修复** | Quick/Pro 使用正确 FeatureFlags (`for_quick()`/`for_professional()`) | ✅ |
| **修复** | `analysis_id` 业务层自动生成 UUID | ✅ |
| **修复** | `main.py` 默认端口 8000 (与 Vite proxy 对齐) | ✅ |
| **测试** | 280 pytest 通过 (单元 + TDD + 中间件) | ✅ |
| **测试** | 50/50 综合系统测试 (`tests/tools/test_comprehensive_e2e.py`) | ✅ |
| **测试** | 21/21 前端 E2E 测试 (`tests/tools/test_frontend_e2e.py`) | ✅ |

### v7.0.x (2026-07-22) — 六阶段重构

| Phase | 内容 | 状态 |
|-------|------|------|
| 0 | Foundation: DDD 目录 + FastAPI + Vue 3 脚手架 + Alembic | ✅ |
| 1 | Domain Model: 六维评分 TDD (88 tests) + EventBus + 启发式标记 | ✅ |
| 2 | FastAPI 迁移: 21 端点 + Pydantic v2 + openapi.json | ✅ |
| 3 | WebSocket: 4 字节长度前缀 + 增量评分 + AudioWorklet | ✅ |
| 4 | Vue 3 前端: 5 页面 + Pinia + Element Plus + Vitest (33 tests) | ✅ |
| 5 | Electron: 嵌入式 Python + 进程守护 + electron-builder 配置 | ✅ |
| 6+ | 速率限制 + 安全头 + 批量删除 + 波形可视化 + 代码审查 52/52 | ✅ |

---

## 三、测试状态

| 套件 | 结果 | 说明 |
|------|------|------|
| pytest 单元 + TDD + 中间件 | **280/280** | 全绿 |
| 全量套件 (含集成/BDD) | **347/280** | 20 个已有遗留失败 (v6.x flag 命名 + 基线范围) |
| 综合系统测试 | **50/50** | 导入 / FeatureFlags / 评分 / DDD / 基建 / FCPE / EventBus / App / 非人声 |
| 前端 E2E | **21/21** | 5 页面加载 / 0 控制台错误 / 上传 API 200 / 响应式 |
| 真实音频 | **melody.wav** | total=58.2, level=中等, 3.2s Quick mode, 6-dim |

---

## 四、已知问题

### 架构残留 (绞杀者模式)

| 优先级 | 残留 | 说明 |
|--------|------|------|
| **P0** | `services/features/` (12 files, ~4,000 行) | 唯一生产特征提取来源, 无 DDD 替代 |
| **P0** | `web/static/js/` (~30 files, ~5,000 行) | 旧 SPA 磁盘残留, Flask 仍可服务 |
| **P1** | `services/scoring/` (8 files, ~2,000 行) | Flag 回退路径 (`enable_ddd_scoring=False`) |
| **P1** | `api/routes/` (Flask, ~500 行) | 与 FastAPI 端点完全重复 |
| **P1** | `services/dl_services/` (11 files, ~2,000 行) | style classifier, VAD, DTW 仍在使用 |
| **P2** | `backend/domain/audio/` (桩) | entities.py, services.py 未实现 |
| **P2** | `backend/domain/comparison/` (桩) | entities.py, services.py 未实现 |

### 功能未完成

| 优先级 | 项目 | 说明 |
|--------|------|------|
| **P1** | audiofeat + timbral_models 集成 | v7.1 P0 工具, flag 已预留 |
| **P2** | PyArmor 代码保护 | ADR-8, 构建脚本就绪 |
| **P2** | electron-builder 完整打包 | 配置就绪, 未执行 |

### 测试遗留

| 问题 | 数量 | 说明 |
|------|------|------|
| 已有 TDD 失败 | ~8 | v6.x FeatureFlags 默认值变更 + 评分范围过窄 |
| 集成测试失败 | ~9 | FastAPI TestClient 部分端点超时 |
| BDD 步骤未实现 | ~36 | Step definitions 缺失或 API 契约不匹配 |
| xfail/skip | 13 | 预存失败 (v6.x RED phase) |

---

## 五、快速参考

| 文档 | 路径 |
|------|------|
| 产品需求 | [PRD.md](../1-product/PRD.md) |
| 系统架构 | [ARCHITECTURE.md](../2-technical/ARCHITECTURE.md) |
| 评分算法 | [SCORING.md](../2-technical/SCORING.md) |
| 技术研究 | [TECH_RESEARCH.md](../2-technical/TECH_RESEARCH.md) |
| API 文档 | [API.md](../2-technical/API.md) |
| 迁移计划 | [V7_MIGRATION_PLAN.md](V7_MIGRATION_PLAN.md) |
| 变更日志 | [CHANGELOG.md](CHANGELOG.md) |
| TDD 规范 | [TDD.md](../3-quality/TDD.md) |
| BDD 规范 | [BDD.md](../3-quality/BDD.md) |

### 启动命令

```bash
# 开发模式
cd frontend && npm run dev          # Vite :5173
python backend/main.py              # FastAPI :8000

# 生产模式 (Electron)
cd frontend && npm run build:electron

# 测试
pytest tests/unit/ tests/tdd/ -q   # 单元测试
python tests/tools/test_comprehensive_e2e.py  # 系统测试
python tests/tools/test_frontend_e2e.py       # 前端测试 (需先启动服务)
```
