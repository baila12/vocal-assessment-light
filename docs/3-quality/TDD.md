# 测试驱动开发 (TDD) 规范 v7.13

> 更新: 2026-08-08 | 537 tests 100% GREEN | pytest + Vitest

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

## 2. 测试金字塔 (v7.13 实际)

```
         ╱   E2E   ╲         Playwright, ~19 files, 按需
        ╱────────────╲
       ╱   BDD        ╲       pytest-bdd, 17 step files, 21 feature files
      ╱──────────────────╲
     ╱   Integration +       ╲   FastAPI routes + Songs + Scoring + SongsPitch, 65 tests (不含回归)
    ╱    Extended              ╲  DTW/repos, 21 tests (v7.12 -calibrator)
   ╱──────────────────────────────╲
  ╱   Unit (DDD domain + infra     ╲  451 tests — 核心, 最快
 ╱    + middleware + alignment)      ╲
╱──────────────────────────────────────╲
```

| 层级 | 测试数 | 速度 | 通过率 |
|------|:-----:|------|:---:|
| Unit (DDD 领域: 6 scorers + 音色调整 + comparison + songs + songs_pitch + ScoringWeights) | 273 | < 14s | 100% |
| Unit (DDD 基建: 10 extractors + orchestrator + audio_utils + ABI + sqlite) | 132 | < 10s | 100% |
| Unit (中间件: SecurityHeaders + RateLimit + MaxBodySize) | 23 | < 1s | 100% |
| Unit (DDD 对齐 + extraction flag + flag bridge) | 23 | < 1s | 100% |
| Integration (FastAPI routes) | 19 | ~8s | 100% |
| Integration (Songs API) | 20 | ~6s | 100% | (v7.12 +3 vocal_range)
| Integration (Scoring API) 🆕 v7.11 | 14 | ~5s | 100% |
| Integration (SongsPitch API) 🆕 v7.13 | 9 | ~5s | 100% | (test_song_pitch_api)
| Integration (ComparePitch API) 🆕 v7.13 P5 | 3 | ~5s | 100% | (test_compare_pitch_api)
| Integration (WebSocket) | 14 | ~5s | 100% | (v7.12 +2 song_id, v7.13 +4 pitch_update)
| Extended (DTW/repos) | 21 | ~6s | 100% | (v7.12 删 test_score_calibrator)
| Real Audio Regression | 28 | ~27min | 100% |
| **生产代码合计** | **537** | **~55s (不含回归/WS)** | **100% GREEN** |
| TDD (future features) | 1 skip + 4 xfail | < 1s | ⏭️ |
| BDD | 17 step files | < 60s | ✅ |
| Frontend (Vitest) | 286 | < 5s | 100% |

---

## 3. 测试文件组织 (v7.13 实际)

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
│   │   ├── test_scoring_weights.py       # 🆕 v7.11 六维权重值对象 (25 tests)
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
│   ├── test_middleware.py                # SecurityHeaders + RateLimit + MaxBodySize
│   ├── test_ddd_alignment.py             # DDD vs Legacy 对齐
│   ├── test_ddd_extraction_flag.py       # Feature Flag 切换
│   └── test_flag_bridge.py              # v7.7 Flag 桥接
│
├── integration/
│   ├── test_api_routes.py                # FastAPI endpoints (19 tests)
│   ├── test_songs_api.py                 # v7.9 歌曲库 API (20 tests, 含 TestAudioPlayback)
│   ├── test_scoring_api.py               # 🆕 v7.11 评分权重 API (14 tests)
│   ├── test_song_pitch_api.py            # 🆕 v7.13 参考音高 API (9 tests)
│   ├── test_compare_pitch_api.py         # 🆕 v7.13 P5 compare 音高曲线 (3 tests)
│   ├── test_ws_score.py                  # WebSocket 实时评分 (10 tests)
│   ├── test_ws_pitch_update.py           # 🆕 v7.13 WS pitch_update (4 tests)
│   └── test_real_audio_regression.py     # 真实音频基线 (28 tests)
│
├── extended/                             # 需完整音频栈
│   ├── test_comparison_dtw.py
│   └── test_repositories.py
│
├── bdd/                                  # BDD (见 BDD.md)
│   ├── conftest.py
│   ├── features/ (21 .feature 文件)
│   └── steps/ (17 step files)
│
├── tdd/                                  # 未来特性 (按需实现)
│   ├── conftest.py
│   └── test_future_features.py           # 1 skip + 4 xfail
│
├── e2e/                                  # Playwright 浏览器 (~19 files)
│   ├── test_spa_e2e.py
│   ├── test_spa_navigation.py
│   ├── test_visual_verify.py
│   └── ... (16 more files)
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

## 5. 覆盖率矩阵 (v7.13 实际)

| 模块 | 测试文件 | 测试数 |
|------|---------|:-----:|
| PitchScorer | `test_pitch_scorer.py` | ~12 |
| RhythmScorer | `test_rhythm_scorer.py` | ~10 |
| BreathScorer | `test_breath_scorer.py` | ~14 |
| TechniqueScorer | `test_technique_scorer.py` | ~14 |
| MuscleStrengthScorer | `test_muscle_scorer.py` | ~14 |
| ArtistryScorer | `test_artistry_scorer.py` | ~12 |
| TimbreAdjuster | `test_timbre_adjuster.py` | ~12 |
| ScoringWeights 🆕 v7.11 | `test_scoring_weights.py` | 25 |
| SongsPitch 🆕 v7.13 | `test_song_pitch_vo.py` + `test_song_pitch_service.py` + `test_get_song_pitch_usecase.py` | 16 |
| ScoringDomainService | `test_scoring_domain_service.py` | ~12 |
| Comparison (DDD) | `test_comparison_scoring.py` + `test_comparison_value_objects.py` | ~30 |
| Audiofeat enhancement | `test_audiofeat_extractor.py` + scorer audiofeat tests | ~40 |
| 10 Extractors | `test_*_extractor.py` (7 files) + `test_orchestrator.py` + `test_audio_utils.py` + `test_batch4_extractors.py` | ~132 |
| Middleware | `test_middleware.py` | 23 |
| DDD Alignment + Flag | `test_ddd_alignment.py` + `test_ddd_extraction_flag.py` + `test_flag_bridge.py` | 23 |
| **DDD Unit 合计** | | **451** |
| FastAPI Integration | `test_api_routes.py` | 19 |
| Songs API Integration | `test_songs_api.py` | 20 |
| Scoring API Integration 🆕 v7.11 | `test_scoring_api.py` | 14 |
| SongsPitch API Integration 🆕 v7.13 | `test_song_pitch_api.py` | 9 |
| ComparePitch API Integration 🆕 v7.13 P5 | `test_compare_pitch_api.py` | 3 |
| WebSocket Integration | `test_ws_score.py` + `test_ws_pitch_update.py` | 10 + 4 |
| Extended | `test_comparison_dtw.py` + `test_repositories.py` | 21 | (v7.12 删 test_score_calibrator)
| Real Audio Regression | `test_real_audio_regression.py` | 28 |
| **生产代码合计** | | **537** (DDD 451 + 集成 65 + 扩展 21; 不含 WS 14 / 真实音频回归 28) |

---

## 6. 运行命令

```bash
# DDD 核心 (451 tests, ~25s) — 默认单元测试命令
# ⚠️ 不直接运行 pytest tests/unit/ (PyTorch C 扩展冲突 → 崩溃), 必须使用分组命令:
pytest tests/unit/domain/ tests/unit/infrastructure/ \
       tests/unit/test_middleware.py \
       tests/unit/test_ddd_alignment.py \
       tests/unit/test_ddd_extraction_flag.py \
       tests/unit/test_flag_bridge.py

# FastAPI 集成 (独立进程, ~8s)
pytest tests/integration/test_api_routes.py -v

# Songs API 集成 (独立进程, ~6s)
pytest tests/integration/test_songs_api.py -v

# Scoring API 集成 🆕 v7.11 (独立进程, ~5s)
pytest tests/integration/test_scoring_api.py -v

# WebSocket 集成 (独立进程)
pytest tests/integration/test_ws_score.py -v

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
pytest tests/unit/domain/ tests/unit/infrastructure/ tests/unit/test_middleware.py \
       tests/unit/test_ddd_alignment.py tests/unit/test_ddd_extraction_flag.py \
       tests/unit/test_flag_bridge.py \
       tests/integration/ tests/extended/ -v
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

### 8.1 TDD 案例: ScoringWeights 值对象 (v7.11)

v7.11 的六维权重可配置功能严格遵循 TDD 三步循环。以 `ScoringWeights` 值对象为例:

**RED -- 先写会失败的测试 (test_scoring_weights.py)**

```python
# 测试 1: 默认权重总和必须 = 100%
def test_scoring_weights_default_sums_to_100():
    weights = ScoringWeights.default()
    total = sum(weights.to_dict().values())
    assert total == 100.0  # ❌ RED: ScoringWeights 还不存在

# 测试 2: 单维度不得超过 50%
def test_scoring_weights_rejects_dimension_over_50():
    with pytest.raises(ValueError, match="单维度权重不能超过 50%"):
        ScoringWeights(pitch=60.0, rhythm=10.0, breath=10.0, technique=10.0, muscle=5.0, artistry=5.0)
        # ❌ RED: validate() 尚未实现

# 测试 3: 总和不为 100% 时拒绝
def test_scoring_weights_rejects_non_100_sum():
    with pytest.raises(ValueError, match="总和必须为 100%"):
        ScoringWeights(pitch=10.0, rhythm=10.0, breath=10.0, technique=10.0, muscle=10.0, artistry=10.0)
        # ❌ RED: 10+10+10+10+10+10=60≠100, validate() 尚未实现

# 测试 4: 4 个风格预设均通过校验
@pytest.mark.parametrize("preset", ["pop", "bel_canto", "folk", "rap"])
def test_all_presets_pass_validation(preset):
    weights = ScoringWeights.preset(preset)
    weights.validate()  # ❌ RED: 预设方法尚未实现
    total = sum(weights.to_dict().values())
    assert total == 100.0
```

**GREEN -- 最简实现通过测试**

```python
@dataclass(frozen=True)
class ScoringWeights:
    """六维权重值对象 -- v7.11 单一权重数据来源"""
    pitch: float = 13.0
    rhythm: float = 12.0
    breath: float = 22.0
    technique: float = 25.0
    muscle: float = 15.0
    artistry: float = 13.0

    def __post_init__(self):
        self.validate()

    def validate(self):
        total = self.pitch + self.rhythm + self.breath + self.technique + self.muscle + self.artistry
        if abs(total - 100.0) > 0.01:
            raise ValueError(f"总和必须为 100%, 当前 {total}%")
        for dim_name, val in self.to_dict().items():
            if val > 50.0:
                raise ValueError(f"单维度权重不能超过 50%: {dim_name}={val}%")
            if val < 0:
                raise ValueError(f"权重不能为负: {dim_name}={val}%")

    @classmethod
    def default(cls) -> 'ScoringWeights':
        return cls()  # 使用类默认值 (v7.4 定稿权重)

    @classmethod
    def preset(cls, name: str) -> 'ScoringWeights':
        """风格预设: 原 5 维×0.85 + muscle 15%"""
        # 流行/美声/民族/说唱各有不同的五维分布, muscle 固定 15%
        ...

    def weighted_total(self, scores: dict) -> float:
        return sum(self.to_dict()[dim] * scores[dim] / 100.0 for dim in scores)
```

**REFACTOR -- 优化代码, 测试保持绿色**

- 提取 `_DEFAULT_WEIGHTS` 字典 → `default()` 和 `to_dict()` 复用同一数据源
- `preset()` 改为查表 + `_apply_preset_scaling()` 复用 `__post_init__` 校验
- `weighted_total()` 改为 `weighted_total_from_scores()` 接收 `DimensionScores` 值对象

**结果**: 25 tests GREEN, ScoringWeights 成为 `value_objects.py` 中 6 个 `weighted()` 方法和 `flags.py` 中 `dimension_weights` 的**单一权重数据来源**, 消除了 6 处硬编码权重。

---

## 9. 前端测试 (Vitest)

```
frontend/tests/unit/stores/            # 6 store suites (74 tests)
├── assessment.test.ts    # Assessment store
├── preferences.test.ts   # Preferences store
├── history.test.ts       # History store
├── songs.test.ts         # v7.10 Songs store (24 tests)
├── scoring.test.ts       # 🆕 v7.11 Scoring store (11 tests)
└── songsPitch.test.ts    # 🆕 v7.13 songs.store 音准增强 (fetchSongPitch/compareWithSong)

frontend/tests/unit/utils/             # 13 pure-TS suites (212 tests)
├── pitchDeviation.test.ts    # 🆕 v7.13 偏差着色/八度跳变/对齐
├── pitchScroll.test.ts       # 🆕 v7.13 滚动窗口
├── pitchScrollTicks.test.ts  # 🆕 v7.13 Y 轴刻度
├── pitchNotes.test.ts        # 🆕 v7.13 钢琴键映射
├── pitchStats.test.ts        # 🆕 v7.13 统计面板 + 低对齐排除
├── pitchPlayback.test.ts     # 🆕 v7.13 回放控制/降级目标
├── pitchLive.test.ts         # 🆕 v7.13 录音中实时对比
├── pitchSegments.test.ts     # 🆕 v7.13 回放分析 (问题段/逐句)
├── pitchKeyboard.test.ts     # 🆕 v7.13 P5 键盘快捷键
├── pitchFps.test.ts          # 🆕 v7.13 P5 FPS 监控/降级状态机
├── pitchHeatmap.test.ts      # 🆕 v7.13 P5 热力图分桶
├── pitchScreenshot.test.ts   # 🆕 v7.13 P5 截图导出
└── pitchCompareDraw.test.ts  # 🆕 v7.13 P5 双轨绘制/性能模式

286 tests passed (19 files: stores 74 + utils 212)
```

> vue-tsc: **0 errors** | Vite build: **~16s**

---

## 10. BDD 与真实音频状态

### BDD (v7.13)

| 指标 | 状态 |
|------|:---:|
| 收集 scenarios | 179 |
| Step files | 17 |
| Feature files | 21 |
| scoring-config API 级 | ✅ PASS |
| scoring-config UI 级 | ⚠️ XFAIL (阈值联动未实现) |
| animations.feature (16 scenarios) | ✅ v7.12 迁移 Vue 3 data-test — 7 PASS + 9 XFAIL (无 UI/依赖录音场景) |
| sing-song-select.feature | ✅ v7.12 迁移 Vue 3 — 6 PASS + 6 XFAIL (录音/auto-match/上传) |
| upload.feature | ✅ v7.12 数据补齐 + fixture 修复 — 5 PASS + 3 SKIP (FLAC/OGG/M4A 无文件) |
| pitch-realtime.feature (25 scenarios) | ✅ v7.13 P4 step defs 骨架 — 25 XFAIL (每条标注对应纯 TS 单元测试; P3 起录音中对比指向 pitchLive.test.ts, P4 起回放对比/问题段落/逐句评分指向 pitchSegments.test.ts) |
| 5 features 缺 step defs | ⚠️ auto-match/multi-dim-analysis/nonblocking-analysis/realtime-analysis/song-select |

### 真实音频回归

| 套件 | 测试数 | 结果 | 说明 |
|------|:-----:|------|------|
| 真实音频 Quick + Pro | 28 | ✅ 100% | BASELINE_V7_6 |
| 高低分区分度 | 9.1 pts | ✅ | >8 阈值 |

> ✅ v7.12: upload.feature 测试数据已补齐 (`scripts/gen_bdd_test_data.py` 生成 vocals.wav), 5 PASS + 3 SKIP (FLAC/OGG/M4A 无测试文件合理跳过)。

## 11. 参考

| 文档 | 路径 |
|------|------|
| BDD 规范 | [BDD.md](BDD.md) |
| 产品需求 | [PRD.md](../1-product/PRD.md) |
| 系统架构 | [ARCHITECTURE.md](../2-technical/ARCHITECTURE.md) |
| 评分算法 | [SCORING.md](../2-technical/SCORING.md) |
| 项目状态 | [PROJECT_STATUS.md](../4-process/PROJECT_STATUS.md) |
| 测试结果 | [TEST_RESULTS.md](../4-process/TEST_RESULTS.md) |
