# 项目状态

> 更新: 2026-07-28 | 版本: **v7.3.1** | 分支: `feat/v7-fastapi-vue-refactor`

---

## 一、架构

```
Vue 3 SPA (frontend/dist/)  →  FastAPI (:8000)  ←  Flask /old (绞杀者)
                                      │
    ┌─────────────────────────────────┼──────────────────────────┐
    │  backend/ (DDD 四层)            │  旧服务层 (残留)           │
    │  domain/assessment/ (7 scorers) │  services/features/ (2) ⚠│
    │  domain/audio/ (13 模块自包含)   │  services/dl_services/ (11)│
    │  domain/comparison/ (v7.3)      │  services/audio_service.py │
    │  application/ (orchestrator)    │  api/business/ (bridge)   │
    │  infrastructure/audio/ (4)      │  api/routes/ (Flask, 残留)│
    │  interfaces/api/ + ws/          │  api/routes/rate_limit 🆕 │
    │  shared/ (EventBus, math_utils) │                           │
    └─────────────────────────────────┴──────────────────────────┘
```

### 评分路径 (v7.3: DDD 唯一路径 + audiofeat 增强)

| 路径 | 特征提取 | 评分 | 状态 |
|------|---------|------|:----:|
| **DDD 原生** | `DddFeatureExtractionOrchestrator` → 13 自包含模块 | `ScoringOrchestrator.calculate_ddd()` + audiofeat | ✅ 生产 |
| V4 回退 | `ScoreServiceV4` (五维) | — | ❌ v7.1.4 已移除 |

### 安全中间件 (v7.3.1)

| 中间件 | 层 | 配置 | 状态 |
|--------|-----|------|:--:|
| SecurityHeadersMiddleware | FastAPI | CSP, X-Content-Type, X-Frame, HSTS | ✅ |
| RateLimitMiddleware | FastAPI | 120/min global, 20/min upload, 10/min WS | ✅ |
| MaxBodySizeMiddleware | FastAPI | 50MB (对齐 Flask MAX_CONTENT_LENGTH) | ✅ v7.3.1 |
| Flask rate_limit | Flask /old | @rate_limit(20,60) upload, @rate_limit(120,60) others | ✅ v7.3.1 |
| Global Exception Handler | FastAPI | 防止原始 traceback 泄露 | ✅ v7.3 |

### DDD domain/audio/ 自包含模块 (v7.2 完成)

| 层级 | 模块 | 核心算法 | 外部依赖 |
|------|------|---------|:--:|
| — | `audio_utils.py` | normalize_loudness + vocal_segments + filter | ✅ 纯函数 |
| — | `math_utils.py` (shared/) | safe_float + safe_clamp | ✅ 纯函数 |
| L0 | `acoustic_feature_extractor.py` | HNR + CPP + HPSS + voicing + mixed_audio | ✅ 零依赖 |
| L0 | `audiofeat_extractor.py` | CPPS/GNE/Jitter/Shimmer/等 22 特征 | ✅ audiofeat 1.1.1 |
| L1 | `pitch_extractor.py` | MAE/RPA/RCA/gross/octave/smoothness/breaks | ✅ 零依赖 |
| L1 | `rhythm_extractor.py` | onset CV + irregularity + off-beat + deviation | ✅ 零依赖 |
| L2 | `breath_extractor.py` | long_note + dynamic + design + technique + decay | ✅ 零依赖 |
| L2 | `technique_extractor.py` | vibrato + slides + falsetto + staccato + legato | ✅ 零依赖 |
| L2 | `timbre_extractor.py` | centroid + cluster + harmonic + nasality | ✅ 零依赖 |
| L3 | `muscle_extractor.py` | body/facial proxies (adapter 公式) | ✅ 零依赖 |
| L3 | `artistry_extractor.py` | vibrato + dynamic + phrase + crescendo | ✅ 零依赖 |
| — | `feature_types.py` | AcousticFeatures 冻结数据类 | ✅ 零依赖 |
| — | `feature_protocols.py` | 提取器 Protocol 接口 | ✅ 零依赖 |

### DDD domain/comparison/ (v7.3 新增)

| 文件 | 内容 | 状态 |
|------|------|:--:|
| `entities.py` | `ComparisonResult`, `AlignmentData`, `DeviationData` (frozen) | ✅ |
| `value_objects.py` | `ComparisonScores`, `DimensionComparisonScore` (frozen) | ✅ |
| `services.py` | `ComparisonScoringService` (四维加权评分, 4 风格) | ✅ |
| `__init__.py` | 上下文入口 | ✅ |

### 评分增强路径 (v7.3: audiofeat 接入)

| Scorer | Audiofeat 特征 | 增强方式 |
|--------|---------------|---------|
| **BreathScorer** | CPPS, GNE, HNR_praat | 气声控制力微调 (±8 分) |
| **TechniqueScorer** | Jitter, Shimmer, Closed Quotient | 频率/幅度稳定性微调 (±10 分) |
| **TimbreAdjuster** | Centroid, Roughness, Nasality, Inharmonicity | 增强路径替换启发式 (4→4 维等权) |
| **MuscleStrengthScorer** | Soft Phonation, Vocal Fry | 身体力量代理微调 (20% 权重混合) |

### 绞杀者状态

13/13 模块完全自包含。旧 `services/features/` (原 12 files) 已缩减为 2 文件 (acoustic.py + types.py, 仍被 audio_service 使用, 已添加 DeprecationWarning)。

### 预处理管线

`normalize_loudness()` (RMS→0.05) + `filter_audio_to_vocal_segments()` — 统一预处理, 与旧管线一致。

### 端口策略

开发 → 8000 | Electron → `--port=0` (OS 分配) | 生产 → FastAPI 服务 `frontend/dist/`

---

## 二、完成功能

### v7.3.1 (2026-07-28) — 安全审查修复 + Flask 限速 + BDD 增强 + 代码清理

| 类别 | 项目 | 状态 |
|------|------|------|
| **CRITICAL** | `analyze_and_score` str(e) 泄露 → 通用错误消息 | ✅ |
| **CRITICAL** | `AudioAnalysisResult` 移除 traceback 字段 | ✅ |
| **HIGH** | WebSocket `str(e)` → 通用消息 (2处) | ✅ |
| **HIGH** | FastAPI 新增 MaxBodySizeMiddleware (50MB) | ✅ |
| **HIGH** | `build_error_response()` 移除 traceback 参数 | ✅ |
| **MEDIUM** | Flask `/old` 14 routes 全部添加速率限制 | ✅ |
| **MEDIUM** | `mode` 参数验证 (Flask + FastAPI + Pydantic schema) | ✅ |
| **MEDIUM** | Flask ALLOWED_EXTENSIONS 添加 `.aac` (对齐 FastAPI) | ✅ |
| **LOW** | 移除重复 `import uuid` | ✅ |
| **LOW** | `except Exception as e` → `except Exception` | ✅ |
| **P2** | `services/features/` 添加 DeprecationWarning | ✅ |
| **P2** | BDD 新增 3 step 文件 (29 scenarios) | ✅ |
| **质量** | pytest.ini filterwarnings + browser marker | ✅ |
| **质量** | 基线别名 `BASELINE_v5_19` → `BASELINE` | ✅ |

### v7.3.0 (2026-07-27) — audiofeat 评分接入 + Comparison DDD + 严格测试审计

| 类别 | 项目 | 状态 |
|------|------|------|
| **P1** | audiofeat 22 特征接入 4 scorers (Breath/Technique/Timbre/Muscle) | ✅ |
| **新增** | `ScoringOrchestrator.calculate_ddd()` 接收 audiofeat 参数 | ✅ |
| **新增** | `backend/domain/comparison/` 完整 DDD 实现 (实体+值对象+领域服务) | ✅ |
| **新增** | `CompareAudioUseCase` 应用层对比用例 | ✅ |
| **新增** | `/compare` 路由 DDD 优先路径 + 旧路径 fallback | ✅ |
| **CRITICAL** | 全局异常处理器 (防止原始 traceback 泄露) | ✅ |
| **CRITICAL** | extract-pitch 路由 `str(e)` NameError 修复 | ✅ |
| **CRITICAL** | `/compare` + `/analyze` 信息泄露修复 (str(e)→通用消息) | ✅ |
| **CRITICAL** | SingView `startSinging()` 未处理 Promise rejection 修复 | ✅ |
| **CRITICAL** | WebSocket `except: pass` 静默崩溃添加日志 | ✅ |
| **HIGH** | TopNav + BottomNav 图标导入修复 (Headset/HomeFilled 等) | ✅ |
| **HIGH** | `/analyze` 路由 response_model + `body.mode` 变量修复 | ✅ |
| **HIGH** | `/separate` + `/report` 路由添加 try/catch | ✅ |
| **HIGH** | `HistoryRecordOut` 添加缺失的 `duration` 字段 | ✅ |
| **HIGH** | Rate-limit 中间件测试修复 (monkeypatch env var) | ✅ |
| **测试** | 24 新增 comparison 测试 + 32 audiofeat 测试 | ✅ |
| **测试** | 测试进程隔离策略 (集成测试独立进程运行) | ✅ |

### 更早版本

v7.2.1 ~ v7.1.3: 参见 [CHANGELOG.md](CHANGELOG.md)。

---

## 三、测试状态 (v7.3.1)

### 生产测试 (全部 GREEN)

| 套件 | 测试数 | 结果 | 说明 |
|------|:-----:|------|------|
| DDD 领域 (含 comparison + audiofeat) | 120 | ✅ 100% | 7 scorers + comparison scoring + value objects |
| DDD 基建 (extractors + orchestrator) | 106 | ✅ 100% | audiofeat + audio_utils + acoustic + pitch + rhythm + breath + technique |
| DDD 对齐 + Flag | 17 | ✅ 100% | alignment + extraction flag + SPA routes |
| 中间件 | 23 | ✅ 100% | SecurityHeaders + RateLimit + MaxBodySize |
| **DDD 合计** | **290** | **100% GREEN** | |
| FastAPI 集成 | 20 | ✅ 100% | test_api_routes (独立进程) |
| Flask + WS 集成 | 14 | ✅ 100% | test_ws_score + test_api (独立进程，限速自动跳过) |
| 扩展测试 (DTW/repos/calibrator/SPA) | 51 | ✅ 100% | tests/extended/ (独立进程) |
| **生产代码总计** | **375** | **100% GREEN** | |

### 真实音频回归

| 套件 | 测试数 | 结果 | 说明 |
|------|:-----:|------|------|
| 真实音频 Quick + Pro | 28 | ✅ 100% | v7.3 基线 (BASELINE_V7_3) |
| TDD 未来特性 | 1 skip + 4 xfail | ⏭️ | 按需实现 |
| BDD | 13 step files | ✅ | v7.3.1: 29 new scenarios |

### 真实音频评分 (v7.3 Quick 模式 — DDD 唯一路径)

| 音频文件 | Total | Pitch | Rhythm | Breath | Tech | Muscle | Art | Timbre |
|----------|:-----:|:-----:|:------:|:------:|:----:|:------:|:---:|:------:|
| 恋人（高分） | **65.7** | 67 | 66 | 92 | 25 | 80 | 76 | 0 |
| 手写的从前（高分） | **61.7** | 70 | 42 | 94 | 19 | 76 | 77 | 0 |
| 1（高分） | **65.7** | 71 | 71 | 97 | 20 | 78 | 76 | 0 |
| 音频-3分26秒(高分) | **65.7** | 68 | 58 | 89 | 30 | 80 | 76 | 0 |
| 陈奕迅难听之声（低分） | **52.8** | 66 | 5 | 84 | 16 | 70 | 74 | 0 |

> **v5.19 → v7.3 基线漂移说明**: technique 维度在 v7.0 从 HNR/CPP/技巧完成度重构为咬字清晰度+气声比，评分体系整体偏移 (~30 分)。rhythm 维度在手写的从前（钢琴伴奏）中受和弦变化干扰。高低分差从 20→12.9（六维权重稀释了弱项扣分）。详见 [SCORING.md](../2-technical/SCORING.md)。

---

## 四、已知问题

### 架构残留

| 优先级 | 残留 | 说明 |
|--------|------|------|
| **P2** | `services/features/acoustic.py` | ⚠ 已添加 DeprecationWarning，仍被 audio_service 使用 |
| **P2** | `services/features/types.py` | ⚠ 已添加 DeprecationWarning，仍被测试引用 |
| **P2** | `services/dl_services/` (11 files) | style classifier, VAD, DTW 仍在使用 |
| **P2** | `api/routes/` (Flask, ~700 行) | ✅ 已添加限速，仍与 FastAPI 端点重复 |

### 功能未完成

| 优先级 | 项目 | 说明 |
|--------|------|------|
| **P2** | PyArmor 代码保护 | ADR-8, 构建脚本就绪 |
| **P2** | electron-builder 完整打包 | 配置就绪, 未执行 |
| **P2** | timbral_models 集成 | Python 3.12 兼容性问题, 待上游修复 |
| **P2** | Flask 路由最终移除 | DeprecationWarning + rate_limit 就绪，等待绞杀者完成 |

### 测试遗留

| 问题 | 数量 | 说明 |
|------|------|------|
| BDD v6.0 规划 features 未实现 | ~20 steps | auto-match/database/pitch-realtime/等 8 个 features |
| 集成测试不可混跑 | — | Flask + FastAPI 测试需独立进程 (C 扩展冲突) |

---

## 五、快速参考

### 关键文件

| 文件 | 说明 |
|------|------|
| `backend/domain/audio/audiofeat_extractor.py` | v7.2 — 22 增强声学特征 |
| `backend/domain/comparison/` | v7.3 — DDD 对比分析领域 |
| `backend/application/assessment/scoring_orchestrator.py` | 评分编排 (calculate_ddd + audiofeat) |
| `backend/application/comparison/compare_audio.py` | v7.3 — CompareAudioUseCase |
| `backend/domain/assessment/feature_flags.py` | DimensionFlags (含 enable_audiofeat) |
| `backend/main.py` | v7.3.1 — 全局异常处理器 + MaxBodySizeMiddleware + VAS_SKIP_GPU |
| `api/routes/rate_limit.py` | v7.3.1 — Flask token bucket 限速器 |
| `api/business/audio_analysis.py` | v7.3.1 — 信息泄露修复 (str(e)→通用消息) |
| `backend/interfaces/ws/score_handler.py` | v7.3.1 — WebSocket 信息泄露修复 |
| `tests/conftest.py` | VAS_SKIP_GPU=1 + VAS_DISABLE_RATE_LIMIT=1 |
| `tests/extended/` | v7.3 — 需完整音频栈的测试独立目录 |
| `tests/bdd/steps/test_animations_steps.py` | v7.3.1 — 16 GSAP scenarios |
| `tests/bdd/steps/test_offline_steps.py` | v7.3.1 — 5 offline scenarios |
| `tests/bdd/steps/test_responsive_steps.py` | v7.3.1 — 8 responsive scenarios |

### 启动命令

```bash
# 开发模式
cd frontend && npm run dev          # Vite :5173
python backend/main.py              # FastAPI :8000

# 默认测试 (290 tests, ~17s)
pytest tests/unit/domain/ tests/unit/infrastructure/ \
       tests/unit/test_middleware.py \
       tests/unit/test_ddd_alignment.py \
       tests/unit/test_ddd_extraction_flag.py

# 集成测试 (独立进程, ~20s)
pytest tests/integration/test_api_routes.py -v         # FastAPI (20 tests)
pytest tests/integration/test_ws_score.py \
       tests/integration/test_api.py -v                # Flask + WS (14 tests)

# 扩展测试 (独立进程, ~9s)
pytest tests/extended/ -v                              # DTW/repos/etc (51 tests)

# 真实音频回归 (独立进程, ~27min)
pytest tests/integration/test_real_audio_regression.py -v

# BDD 测试 (需要浏览器)
pytest tests/bdd/ -v -m "not browser"                  # API-level BDD
pytest tests/bdd/ -v -m "browser"                      # Browser BDD (needs Playwright)
```
