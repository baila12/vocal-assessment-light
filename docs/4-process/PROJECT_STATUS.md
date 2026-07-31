# 项目状态

> 更新: 2026-07-31 | 版本: **v7.6** | 分支: `feat/v7-fastapi-vue-refactor`

---

## 一、架构

```
Vue 3 SPA (frontend/dist/)  →  FastAPI (:8000)
                                      │
    ┌─────────────────────────────────┼──────────────────────────┐
    │  backend/ (DDD 四层)            │  旧服务层 (残留)           │
    │  domain/assessment/ (7 scorers) │  services/dl_services/ (11)│
    │  domain/audio/ (14 模块自包含)   │  services/audio_service.py │
    │  domain/comparison/ (v7.3)      │  api/business/ (bridge)   │
    │  application/ (orchestrator)    │  services/features/types.py│
    │  infrastructure/audio/ (4)      │                           │
    │  interfaces/api/ + ws/          │  (Flask /old 已移除 v7.6) │
    │  shared/ (EventBus, math_utils) │  (svc/features/ 已移除)   │
    └─────────────────────────────────┴──────────────────────────┘
```

### 评分路径 (v7.6: DDD 唯一路径 + P0/P1/P2 全部修复)

| 路径 | 特征提取 | 评分 | 状态 |
|------|---------|------|:----:|
| **DDD 原生** | `DddFeatureExtractionOrchestrator` → 14 自包含模块 | `ScoringOrchestrator.calculate_ddd()` | ✅ 生产 |

### 六维权重 (v7.4+, v7.6 保持)

| 维度 | 权重 | 说明 |
|------|:----:|------|
| Pitch (音准) | **13%** | 最可靠维度 (文献 A 级) |
| Rhythm (节奏) | **12%** | 中等可靠 (文献 B 级) |
| Breath (气息) | **22%** | 四子维度丰富 |
| Technique (发声技术) | **25%** | 咬字(50%) + 气声比(50%) + attack_slope |
| Muscle (肌肉力量) | **15%** | ⚠️ HEURISTIC, 文献建议降低 |
| Artistry (艺术表现) | **13%** | crescendo+fluctuation+rubato 修复 |

### DDD domain/audio/ 自包含模块

| 层级 | 模块 | 核心特征 | 外部依赖 |
|------|------|---------|:--:|
| — | `audio_utils.py` | normalize_loudness + vocal_segments | ✅ |
| — | `math_utils.py` (shared/) | safe_float + safe_clamp | ✅ |
| L0 | `acoustic_feature_extractor.py` | HNR + CPP + HPSS + voicing + mixed_audio | ✅ |
| L0 | `audiofeat_extractor.py` | CPPS/GNE/Jitter/Shimmer (22 特征) | audiofeat 1.1.1 |
| L1 | `pitch_extractor.py` | MAE/RPA/RCA/gross/octave/smoothness/breaks | ✅ |
| L1 | `rhythm_extractor.py` | onset CV + irregularity + off-beat + deviation | ✅ |
| L2 | `breath_extractor.py` | long_note + dynamic + design + technique | ✅ |
| L2 | `technique_extractor.py` | ZCR/Centroid/C-V + HF + **attack_slope** 🆕 | ✅ |
| L2 | `timbre_extractor.py` | centroid + cluster + harmonic + nasality | ✅ |
| L3 | `muscle_extractor.py` | MPT/Crest/SPR/F1F2/Alpha proxy | ✅ |
| L3 | `artistry_extractor.py` | vibrato + dynamic + phrase + **rubato** 🆕 | ✅ |
| — | `abi_calculator.py` 🆕 | ABI 9-parameter breathiness (Barsties 2017) | audiofeat |
| — | `feature_types.py` | AcousticFeatures 冻结数据类 | ✅ |

### 安全中间件

| 中间件 | 配置 | 状态 |
|--------|------|:--:|
| SecurityHeadersMiddleware | CSP, X-Content-Type, X-Frame, HSTS | ✅ |
| RateLimitMiddleware | 120/min global, 20/min upload, 10/min WS | ✅ |
| MaxBodySizeMiddleware | 50MB | ✅ |
| Global Exception Handler | 防止原始 traceback 泄露 | ✅ |

### 端口策略

开发 → 8000 | Electron → `--port=0` (OS 分配) | 生产 → FastAPI 服务 `frontend/dist/`

---

## 二、完成功能

### v7.6 (2026-07-31) — P1/P2 修复 + 功能增强 + 架构清理

| 类别 | 项目 | 状态 |
|------|------|:--:|
| **P1-1** | Muscle v7.4 proxies DDD 路径验证 (10 提取验证测试) | ✅ |
| **P1-2** | crescendo_quality: 累积→平均质量×覆盖率 (修复饱和) | ✅ |
| **P1-3** | is_artistic_fluctuation: 布尔→连续 0-100 | ✅ |
| **P2** | CPPS ×100 rescale + HNR graduated (歌声特定阈值) | ✅ |
| **P2** | ABI 9 参数模型 (Barsties 2017) | ✅ |
| **P2** | Flask /old 移除 + api/routes/ 删除 (~700行) | ✅ |
| **P2** | services/features/acoustic.py 替换为 DDD | ✅ |
| **增强** | Rubato (表现性节奏变化) → Artistry | ✅ |
| **增强** | Attack slope (起音斜率) → Technique | ✅ |
| **文献** | Rathi & Hsu 咬字权重对齐 2:1:1 | ✅ |
| **基线** | BASELINE V7_6 with 5 real audio files | ✅ |
| **测试** | 359 unit + 54 integration/extended = 413 GREEN | ✅ |

### v7.5 (2026-07-29) — P1-2b 音色八维 + P0 评分异常修复

| 类别 | 项目 | 状态 |
|------|------|:--:|
| **P1-2b** | 音色八维剖面 (hardness/depth/sharpness/booming) | ✅ |
| **P0-1** | Artistry pitch_cv: 真实 F0 CV 替代 Hz | ✅ |
| **P0-2** | Technique HNR: 移除 >22 惩罚 | ✅ |
| **P0-3** | CPPS-HF 解耦: 实谱 HF 替代 cpp/5.0 | ✅ |
| **P0-4** | Muscle formant/overtone 校准 | ✅ |

### 更早版本

v7.4 ~ v7.0: 参见 [CHANGELOG.md](CHANGELOG.md)。

---

## 三、测试状态 (v7.6)

### 生产测试 (全部 GREEN)

| 套件 | 测试数 | 结果 |
|------|:-----:|------|
| DDD 领域 (scorers + value objects + comparison) | 127 | ✅ |
| DDD 基建 (extractors + orchestrator + ABI) | 136 | ✅ |
| DDD 对齐 + Flag | 17 | ✅ |
| 中间件 | 22 | ✅ |
| **DDD 合计** | **359** | **100% GREEN** |
| FastAPI 集成 | 20 | ✅ |
| 扩展测试 (DTW/repos/calibrator) | 34 | ✅ |
| **生产代码总计** | **413** | **100% GREEN** |

### 真实音频回归

| 套件 | 测试数 | 结果 | 说明 |
|------|:-----:|------|------|
| 真实音频 Quick + Pro | 28 | ✅ 100% | BASELINE_V7_6 |
| BDD | 13 step files | ✅ | 29 scenarios |

### 前端测试

| 套件 | 测试数 | 结果 |
|------|:-----:|------|
| Vitest (stores) | 33 | ✅ 100% |

### 真实音频评分 (v7.6 Quick 模式)

| 音频文件 | Total | Pitch | Rhythm | Breath | Tech | Art | Muscle |
|----------|:-----:|:-----:|:------:|:------:|:----:|:---:|:------:|
| 恋人（高分） | 71.5 | 66.6 | 66.3 | 89.5 | 51.6 | 74.0 | 77.9 |
| 1（高分） | 74.1 | 70.7 | 71.2 | 93.6 | 53.7 | 75.2 | 77.2 |
| 陈奕迅（低分） | 62.4 | 66.4 | 5.2 | 80.3 | 57.1 | 68.7 | 75.4 |

> 高低分区分度: 71.5 - 62.4 = **9.1 pts** (>8 阈值) ✅

---

## 四、已知问题

### 架构残留

| 优先级 | 残留 | 说明 |
|--------|------|------|
| **P2** | `services/features/types.py` | AudioFeaturesResult 仍被旧 adapter 评分路径引用 |
| **P2** | `services/dl_services/` (11 files) | style classifier, VAD, DTW 仍在使用 |

### 文献差距

| 优先级 | 项目 | 说明 |
|:--:|------|------|
| **P1** | audiofeat 默认禁用 | CPPS/GNE/HNR_praat 等核心特征在生产中不可用 |
| **P2** | GNE 未接入气声比评分 | AROC=0.886 的强指标未被 TechniqueScorer 使用 |
| **P2** | timbral_models 集成 | Python 3.12 兼容性问题, 待上游修复 |
| **P2** | PyArmor 代码保护 | ADR-8, 构建脚本就绪 |
| **P2** | electron-builder 完整打包 | 配置就绪, 未执行 |

### 测试遗留

| 问题 | 说明 |
|------|------|
| BDD v6.0 规划 features 未实现 | ~20 steps (auto-match/database/pitch-realtime 等) |
| 集成测试不可混跑 | Flask + FastAPI C 扩展冲突 (已移除 Flask, 此问题已解决) |

---

## 五、快速参考

### 关键文件

| 文件 | 说明 |
|------|------|
| `backend/domain/assessment/artistry_scorer.py` | v7.6 — rubato + crescendo + fluctuation 连续化 |
| `backend/domain/assessment/technique_scorer.py` | v7.6 — CPPS/HNR 歌声阈值 + Rathi & Hsu 2:1:1 + attack_slope |
| `backend/domain/assessment/muscle_scorer.py` | v7.5 — 校准 formant/overtone + 五维代理 |
| `backend/domain/assessment/timbre_adjuster.py` | v7.5 — 八维音色剖面 |
| `backend/domain/assessment/value_objects.py` | v7.4 — 六维权重 |
| `backend/domain/audio/artistry_extractor.py` | v7.6 — rubato 提取 + F0 CV |
| `backend/domain/audio/technique_extractor.py` | v7.6 — attack_slope 提取 + CPP ×100 |
| `backend/domain/audio/muscle_extractor.py` | v7.4 — MPT/Crest/SPR/F1F2/Alpha |
| `backend/domain/audio/abi_calculator.py` | v7.6 — ABI 9 参数气息感模型 |
| `backend/domain/audio/breath_extractor.py` | v7.6 — crescendo avg×coverage |
| `backend/application/assessment/ddd_feature_orchestrator.py` | 特征提取编排 + pitch_cv |
| `backend/application/assessment/scoring_orchestrator.py` | 评分编排 |
| `backend/domain/assessment/feature_flags.py` | DimensionFlags (enable_audiofeat=False) |
| `backend/main.py` | FastAPI 入口 (Flask 已移除) |

### 启动命令

```bash
# 开发模式
cd frontend && npm run dev          # Vite :5173
python backend/main.py              # FastAPI :8000

# 默认测试 (359 tests, ~15s)
pytest tests/unit/domain/ tests/unit/infrastructure/ \
       tests/unit/test_middleware.py \
       tests/unit/test_ddd_alignment.py \
       tests/unit/test_ddd_extraction_flag.py

# 集成测试 (独立进程, ~5s)
pytest tests/integration/test_api_routes.py -v         # FastAPI (20 tests)

# 扩展测试 (独立进程, ~5s)
pytest tests/extended/ -v                              # DTW/repos/etc (34 tests)

# 真实音频回归 (独立进程, ~27min)
pytest tests/integration/test_real_audio_regression.py -v

# BDD 测试 (需要浏览器)
pytest tests/bdd/ -v -m "not browser"
pytest tests/bdd/ -v -m "browser"
```
