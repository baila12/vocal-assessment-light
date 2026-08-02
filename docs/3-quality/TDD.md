# 测试驱动开发 (TDD) 规范 v7.8

> 更新: 2026-08-01 | 423 tests 100% GREEN | pytest + Vitest

---

## 1. TDD 铁律

### 三步循环

```
  ┌──────────┐
  │   RED    │  写一个会失败的测试
  └────┬─────┘
       │
  ┌────▼─────┐
  │  GREEN   │  写最小实现让测试通过
  └────┬─────┘
       │
  ┌────▼─────┐
  │ REFACTOR │  优化代码，测试保持绿色
  └──────────┘
```

### 硬性规则

| 规则 | 说明 |
|------|------|
| 不先写实现代码 | 新 scorer、新 extractor 一律先写测试 |
| Bug 先复现 | 修 Bug 前先写复现测试，确认 RED 再修 |
| 重构先保绿 | 重构前确保全量测试通过 |
| 测试即文档 | 命名和结构让新成员看懂被测行为 |
| 一个测试一个行为 | 不把多个不相关断言塞进同一函数 |

---

## 2. 测试金字塔 (v7.3.1 实际)

```
         ╱   E2E   ╲         Playwright, ~22 files, 按需
        ╱────────────╲
       ╱   BDD        ╲       pytest-bdd, 13 step files, 29 scenarios
      ╱──────────────────╲
     ╱   Integration       ╲   FastAPI + Flask/WS, 34 tests
    ╱────────────────────────╲
   ╱   Extended                ╲  DTW/repos/calibrator/SPA, 51 tests
  ╱──────────────────────────────╲
 ╱   Unit (DDD domain + infra)    ╲  290 tests — 核心, 最快
╱────────────────────────────────────╲
```

| 层级 | 测试数 | 速度 | 通过率 |
|------|:-----:|------|:---:|
| Unit (DDD 领域: 7 scorers + comparison + audiofeat) | 120 | < 10s | 100% |
| Unit (DDD 基建: 10 extractors + orchestrator + audio_utils) | 106 | < 5s | 100% |
| Unit (DDD 对齐 + extraction flag) | 17 | < 1s | 100% |
| Unit (中间件: SecurityHeaders + RateLimit + MaxBodySize) | 23 | < 1s | 100% |
| Integration (FastAPI routes) | 20 | ~10s | 100% |
| Integration (Flask + WebSocket) | 14 | ~10s | 100% |
| Extended (DTW/repos/calibrator/SPA) | 51 | ~9s | 100% |
| Real Audio Regression | 28 | ~27min | 100% |
| **生产代码合计** | **375** | **~37s (不含回归)** | **100% GREEN** |
| TDD (future features) | 1 skip + 4 xfail | < 1s | ⏭️ |
| BDD | 13 step files | < 60s | ✅ |
| Frontend (Vitest) | 33 | < 5s | 100% |

---

## 3. 测试文件组织 (v7.3.1 实际)

```
tests/
├── unit/
│   ├── domain/                           # DDD 领域层 — 纯计算
│   │   ├── test_pitch_scorer.py          # 六指标加权融合
│   │   ├── test_rhythm_scorer.py         # Onset CV + irregularity
│   │   ├── test_breath_scorer.py         # 四子维度 + audiofeat
│   │   ├── test_technique_scorer.py      # 咬字 + 气声比
│   │   ├── test_muscle_scorer.py         # 身体/面部代理
│   │   ├── test_artistry_scorer.py       # 四维独立声学
│   │   ├── test_timbre_adjuster.py       # 音色加减分
│   │   ├── test_scoring_domain_service.py
│   │   ├── test_comparison_scoring.py    # v7.3
│   │   └── test_comparison_value_objects.py  # v7.3
│   │
│   ├── infrastructure/                   # DDD 基建层 — 提取器
│   │   ├── test_acoustic_extractor.py    # HNR/CPP/HPSS/Voicing
│   │   ├── test_pitch_extractor.py
│   │   ├── test_rhythm_extractor.py
│   │   ├── test_breath_extractor.py
│   │   ├── test_technique_extractor.py
│   │   ├── test_audiofeat_extractor.py   # v7.2
│   │   ├── test_audio_utils.py           # normalize/filter
│   │   ├── test_orchestrator.py          # DDD 编排器
│   │   └── test_batch4_extractors.py
│   │
│   ├── test_middleware.py                # SecurityHeaders + RateLimit
│   ├── test_ddd_alignment.py             # DDD vs Legacy 对齐
│   └── test_ddd_extraction_flag.py       # Feature Flag 切换
│
├── integration/
│   ├── test_api_routes.py                # FastAPI endpoints (20 tests)
│   ├── test_api.py                       # Flask legacy endpoints
│   ├── test_ws_score.py                  # WebSocket 实时评分
│   └── test_real_audio_regression.py     # 真实音频基线 (28 tests)
│
├── extended/                             # 需完整音频栈
│   ├── test_comparison_dtw.py
│   ├── test_repositories.py
│   ├── test_score_calibrator.py
│   └── test_spa_routes.py
│
├── bdd/                                  # BDD (见 BDD.md)
│   ├── conftest.py
│   └── steps/ (13 files, 29 scenarios)
│
├── tdd/                                  # 未来特性 (按需实现)
│   ├── conftest.py
│   └── test_future_features.py           # 1 skip + 4 xfail
│
├── e2e/                                  # Playwright 浏览器
│   ├── test_spa_e2e.py
│   ├── test_spa_navigation.py
│   ├── test_visual_verify.py
│   └── ... (22 files)
│
├── tools/                                # 辅助测试脚本
│   ├── test_real_audio.py
│   ├── test_real_audio_batch.py
│   ├── test_real_audio_comparison.py
│   └── ...
│
├── conftest.py                           # VAS_SKIP_GPU + VAS_DISABLE_RATE_LIMIT
└── pytest.ini
```

---

## 4. AAA 模式 & 命名规范

```python
# ✅ 正确命名: test_<被测模块>_<行为>_<期望>
def test_pitch_scorer_excellent_mae_returns_score_above_95():
def test_breath_scorer_gne_leak_detection_penalizes_uncontrolled_leak():
def test_muscle_scorer_is_heuristic_true_on_all_scores():

# ✅ AAA 结构
def test_technique_scorer_hnr_optimal_range_gives_max_contribution():
    # Arrange
    features = TechniqueFeatures(hnr_mean=18.0, spectral_tilt=-3.0, hf_energy_ratio=0.3)
    scorer = TechniqueScorer()

    # Act
    result = scorer.calculate(features)

    # Assert
    assert result.raw_score >= 70
    assert result.breath_voice_ratio >= 50
```

---

## 5. 覆盖率矩阵 (v7.3.1 实际)

| 模块 | 测试文件 | 测试数 |
|------|---------|:-----:|
| PitchScorer | `test_pitch_scorer.py` | ~10 |
| RhythmScorer | `test_rhythm_scorer.py` | ~8 |
| BreathScorer | `test_breath_scorer.py` | ~10 |
| TechniqueScorer | `test_technique_scorer.py` | ~10 |
| MuscleStrengthScorer | `test_muscle_scorer.py` | ~10 |
| ArtistryScorer | `test_artistry_scorer.py` | ~8 |
| TimbreAdjuster | `test_timbre_adjuster.py` | ~10 |
| ScoringDomainService | `test_scoring_domain_service.py` | ~5 |
| Comparison (DDD) | `test_comparison_scoring.py` + `test_comparison_value_objects.py` | ~24 |
| Audiofeat enhancement | `test_audiofeat_extractor.py` + scorer audiofeat tests | ~32 |
| 10 Extractors | `test_*_extractor.py` (7 files) + `test_orchestrator.py` | ~106 |
| Middleware | `test_middleware.py` | 23 |
| DDD Alignment | `test_ddd_alignment.py` + `test_ddd_extraction_flag.py` | 17 |
| **DDD 合计** | | **~290** |
| FastAPI Integration | `test_api_routes.py` | 20 |
| Flask + WS Integration | `test_api.py` + `test_ws_score.py` | 14 |
| Extended | `test_*` (4 files) | 51 |
| **生产代码合计** | | **375** |

---

## 6. 运行命令

```bash
# DDD 核心 (290 tests, ~17s)
pytest tests/unit/domain/ tests/unit/infrastructure/ \
       tests/unit/test_middleware.py \
       tests/unit/test_ddd_alignment.py \
       tests/unit/test_ddd_extraction_flag.py

# FastAPI 集成 (独立进程, ~20s)
pytest tests/integration/test_api_routes.py -v

# Flask + WS 集成 (独立进程)
pytest tests/integration/test_ws_score.py tests/integration/test_api.py -v

# 扩展测试 (独立进程, ~9s)
pytest tests/extended/ -v

# 真实音频回归 (独立进程, ~27min)
pytest tests/integration/test_real_audio_regression.py -v

# BDD (API 级别)
pytest tests/bdd/ -v -m "not browser"

# BDD (浏览器级别, 需要 Playwright)
pytest tests/bdd/ -v -m "browser"

# 快速冒烟 (开发时)
pytest tests/unit/domain/ tests/unit/test_middleware.py -v

# 全量 (不含真实音频回归和 E2E)
pytest tests/unit/ tests/integration/ tests/extended/ -v
```

---

## 7. Feature Flag 测试策略

每个 dimension flag 独立可测:

```python
def test_muscle_disabled_returns_neutral():
    flags = DimensionFlags(enable_muscle_strength=False)
    orch = ScoringOrchestrator(flags=flags)
    result = orch.calculate_ddd(...)
    assert result["muscle_strength_score"] == 0.0

def test_pitch_disabled_returns_neutral():
    flags = DimensionFlags(enable_pitch=False)
    orch = ScoringOrchestrator(flags=flags)
    result = orch.calculate_ddd(...)
    assert result["pitch_score"] == 0.0
```

---

## 8. TDD 实践清单

- [ ] 新 scorer 先写 `tests/unit/domain/test_*_scorer.py`
- [ ] 新 extractor 先写 `tests/unit/infrastructure/test_*_extractor.py`
- [ ] 修改阈值/参数后跑 `pytest tests/unit/ -v`
- [ ] Bug 修复必带回归测试
- [ ] 测试函数名准确描述行为和期望
- [ ] 集成测试独立进程运行 (C 扩展冲突)

---

## 9. 前端测试 (Vitest)

```
frontend/tests/unit/stores/
├── assessment.test.ts    # Assessment store
└── preferences.test.ts   # Preferences store

33/33 tests passed (3 suites)
```

---

## 10. 参考

| 文档 | 路径 |
|------|------|
| BDD 规范 | [BDD.md](BDD.md) |
| 产品需求 | [PRD.md](../1-product/PRD.md) |
| 系统架构 | [ARCHITECTURE.md](../2-technical/ARCHITECTURE.md) |
| 评分算法 | [SCORING.md](../2-technical/SCORING.md) |
| 项目状态 | [PROJECT_STATUS.md](../4-process/PROJECT_STATUS.md) |
