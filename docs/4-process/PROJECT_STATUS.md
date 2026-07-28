# 项目状态

> 更新: 2026-07-27 | 版本: **v7.3.0** | 分支: `feat/v7-fastapi-vue-refactor`

---

## 一、架构

```
Vue 3 SPA (frontend/dist/)  →  FastAPI (:8000)  ←  Flask /old (绞杀者)
                                      │
    ┌─────────────────────────────────┼──────────────────────────┐
    │  backend/ (DDD 四层)            │  旧服务层 (残留)           │
    │  domain/assessment/ (7 scorers) │  services/features/ (2)   │
    │  domain/audio/ (13 模块自包含)   │  services/dl_services/ (11)│
    │  domain/comparison/ (NEW v7.3)  │  services/audio_service.py │
    │  application/ (orchestrator)    │  api/business/ (bridge)   │
    │  infrastructure/audio/ (4)      │  api/routes/ (Flask, 残留)│
    │  interfaces/api/ + ws/          │                           │
    │  shared/ (EventBus, math_utils) │                           │
    └─────────────────────────────────┴──────────────────────────┘
```

### 评分路径 (v7.3: DDD 唯一路径 + audiofeat 增强)

| 路径 | 特征提取 | 评分 | 状态 |
|------|---------|------|:----:|
| **DDD 原生** | `DddFeatureExtractionOrchestrator` → 13 自包含模块 | `ScoringOrchestrator.calculate_ddd()` + audiofeat | ✅ 生产 |
| V4 回退 | `ScoreServiceV4` (五维) | — | ❌ v7.1.4 已移除 |

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

13/13 模块完全自包含。旧 `services/features/` (原 12 files) 已缩减为 2 文件 (acoustic.py + types.py, 仍被 audio_service 使用)。

### 预处理管线

`normalize_loudness()` (RMS→0.05) + `filter_audio_to_vocal_segments()` — 统一预处理, 与旧管线一致。

### 端口策略

开发 → 8000 | Electron → `--port=0` (OS 分配) | 生产 → FastAPI 服务 `frontend/dist/`

---

## 二、完成功能

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

### v7.2.1 (2026-07-27) — 代码审查修复

| 类别 | 项目 | 状态 |
|------|------|------|
| **CRITICAL** | analysis_id 存入 history + UUID 查找支持 | ✅ |
| **CRITICAL** | history 字段 created_at 统一 + grade/v7 字段存储 | ✅ |
| **CRITICAL** | FastAPI UploadResponse 补全 timbre_adjustment + normalization | ✅ |
| **CRITICAL** | 修复 dl_services 裸 except: → except Exception: | ✅ |
| **HIGH** | 静默异常增加日志 + 错误信息泄露修复 + math_utils 去重 | ✅ |
| **MEDIUM** | DddFeatureSet frozen=True + API 超时 + 前端不可变更新 | ✅ |
| **测试** | 226/226 DDD GREEN | ✅ |

### v7.2.0 (2026-07-26) — audiofeat 增强特征提取

| 类别 | 项目 | 状态 |
|------|------|------|
| **新增** | `AudiofeatExtractor` + `AudiofeatFeatures` (22 声学特征) | ✅ |
| **特征** | CPPS, HNR_praat, GNE, Jitter, Shimmer 等 + 频谱特征 | ✅ |
| **TDD** | 19/19 GREEN | ✅ |

### 更早版本

v7.1.5 ~ v7.1.3: 参见 [CHANGELOG.md](CHANGELOG.md)。

---

## 三、测试状态 (v7.3.0)

### 生产测试 (全部 GREEN)

| 套件 | 测试数 | 结果 | 说明 |
|------|:-----:|------|------|
| DDD 领域 (含 comparison + audiofeat) | 120 | ✅ 100% | 7 scorers + comparison scoring + value objects |
| DDD 基建 (extractors + orchestrator) | 106 | ✅ 100% | audiofeat + audio_utils + acoustic + pitch + rhythm + breath + technique |
| DDD 对齐 + Flag | 17 | ✅ 100% | alignment + extraction flag + SPA routes |
| 中间件 (修复 rate-limit) | 23 | ✅ 100% | SecurityHeaders + RateLimit (含 monkeypatch 修复) |
| **DDD 合计** | **290** | **100% GREEN** | |
| FastAPI 集成 | 20 | ✅ 100% | test_api_routes (独立进程) |
| Flask + WS 集成 | 14 | ✅ 100% | test_ws_score + test_api (独立进程) |
| 扩展测试 (DTW/repos/calibrator/SPA) | 51 | ✅ 100% | tests/extended/ (独立进程) |
| **生产代码总计** | **375** | **100% GREEN** | |

### 真实音频回归 (基线漂移)

| 套件 | 测试数 | 结果 | 说明 |
|------|:-----:|------|------|
| 真实音频 Quick 模式 | 21 passed + 7 baseline drift | ⚠️ | v5.19 基线需更新到 v7.3 |
| TDD 未来特性 | 1 skip + 4 xfail | ⏭️ | 按需实现 |
| BDD | 36 steps 未实现 | ⏭️ | 按需实现 |

### v7.3 新增测试

| 文件 | 测试数 | 覆盖 |
|------|--------|------|
| `tests/unit/domain/test_comparison_value_objects.py` | 10 | ComparisonScores + DimensionComparisonScore |
| `tests/unit/domain/test_comparison_scoring.py` | 14 | ComparisonScoringService (4 风格 + 边界 + 建议) |
| 各 scorer audiofeat 增强测试 | 32 | Breath/Technique/Timbre/Muscle audiofeat 参数 |

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
| **P2** | `services/features/acoustic.py` | AcousticAnalyzer.detect_mixed_audio (audio_service 仍使用) |
| **P2** | `services/features/types.py` | AudioFeaturesResult 类型 (test_orchestrator 仍使用) |
| **P2** | `services/dl_services/` (11 files) | style classifier, VAD, DTW 仍在使用 |
| **P2** | `api/routes/` (Flask, ~500 行) | 与 FastAPI 端点重复, Flask /old 挂载仍活跃 |

### 功能未完成

| 优先级 | 项目 | 说明 |
|--------|------|------|
| **P2** | PyArmor 代码保护 | ADR-8, 构建脚本就绪 |
| **P2** | electron-builder 完整打包 | 配置就绪, 未执行 |
| **P2** | timbral_models 集成 | Python 3.12 兼容性问题, 待上游修复 |
| **P2** | 真实音频基线更新到 v7.3 | `BASELINE_v5_19` → 需更新为当前值 |

### 测试遗留

| 问题 | 数量 | 说明 |
|------|------|------|
| 真实音频基线漂移 | 7 | v5.19 硬编码基线需更新到 v7.3 |
| BDD 步骤未实现 | ~36 | Step definitions 缺失或 API 契约不匹配 |
| 集成测试不可混跑 | — | Flask + FastAPI 测试需独立进程 (C 扩展冲突, pytest-forked 可解决) |

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
| `backend/main.py` | v7.3 — 全局异常处理器 + VAS_SKIP_GPU |
| `tests/conftest.py` | v7.3 — VAS_SKIP_GPU=1 + VAS_DISABLE_RATE_LIMIT=1 |
| `tests/extended/` | v7.3 — 需完整音频栈的测试独立目录 |

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
```
