# 测试驱动开发 (TDD) 规范

> 更新: 2026-06-05 | 适用于所有核心算法和评分模块开发

---

## 1. TDD 铁律

### 1.1 三步循环

```
  ┌──────────┐
  │   RED    │  写一个会失败的测试，验证测试确实失败
  └────┬─────┘
       │
  ┌────▼─────┐
  │  GREEN   │  写最小实现代码让测试通过，不写多余代码
  └────┬─────┘
       │
  ┌────▼─────┐
  │ REFACTOR │  优化代码结构，消除重复，测试必须保持绿色
  └──────────┘
```

### 1.2 硬性规则

| 规则 | 说明 |
|------|------|
| **绝不先写实现代码** | 新功能、新 scorer、新特征提取器，一律先写测试 |
| **Bug 先复现** | 修 Bug 前先写复现测试，确认测试 RED 再修 |
| **重构先保绿** | 重构前确保全量测试通过，重构后保持通过 |
| **测试即文档** | 测试命名和结构应让新成员看懂被测行为 |
| **一个测试一个行为** | 不把多个不相关断言塞进同一个测试函数 |

---

## 2. 测试金字塔

```
       ╱  E2E  ╲         Playwright 浏览器测试
      ╱──────────╲       ~10 场景, 关键用户流程, 慢
     ╱ Integration ╲     API 端点 + 评分管线
    ╱────────────────╲   ~15 场景, 模块协作, 中速
   ╱    Unit Tests     ╲ 评分器/特征提取/工具函数
  ╱──────────────────────╲ ~60 场景, 覆盖率 ≥ 80%, 快
```

| 层级 | 工具 | 场景数 | 速度 | 通过率 |
|------|------|--------|------|------|
| Unit | pytest | 79 (6 文件) | < 5s | 79/79 (100%) |
| Integration | pytest + Flask test client | 12 (2 文件) | < 60s | 10/12 (83%, 2 pre-existing) |
| E2E | Playwright | ~15 (10+ 文件) | < 5min | 按需运行 |
| BDD | pytest-bdd | 16 (4 feature) | < 60s | 待实现 Step Defs |
| **合计** | | **~107** | | **89/91 (98%)** |

---

## 3. 测试文件组织

```
tests/
├── unit/                            # 单元测试 — 无 IO/网络/数据库
│   ├── test_scorers.py              # PitchScorer, RhythmScorer, BreathScorer,
│   │                                #   TechniqueScorer, ArtistryScorer
│   ├── test_features.py             # PitchAnalyzer, BreathAnalyzer,
│   │                                #   RhythmAnalyzer, TechniqueAnalyzer
│   ├── test_services.py             # VoiceQualityService, AudioService
│   ├── test_comparison_dtw.py       # DTW 对齐引擎 (15 tests)
│   ├── test_repositories.py         # HistoryRepository CRUD
│   └── test_score_calibrator.py     # ScoreCalibrator
├── integration/                     # 集成测试 — 跨模块协作
│   ├── test_api.py                  # Flask API 端点
│   └── test_full_pipeline.py        # 上传→分离→评分 全链路
├── e2e/                             # E2E — Playwright 浏览器
│   ├── test_upload.py               # 上传流程
│   ├── test_compare.py              # 对比分析
│   ├── test_history.py              # 历史记录
│   ├── test_visualization.py        # 可视化
│   ├── test_real_audio.py           # 真实音频验证
│   └── ...
├── bdd/                             # BDD 测试 (见 BDD.md)
│   ├── features/                    # .feature 文件
│   └── steps/                       # Step 实现
├── conftest.py                      # Session 级 fixtures (浏览器等)
├── e2e/conftest.py                  # E2E 专用 fixtures
└── pytest.ini                       # 配置: markers, asyncio
```

---

## 4. 测试命名与 AAA 结构

### 4.1 命名规范

```python
# ✅ 正确: test_<被测模块>_<行为描述>_<期望结果>
def test_pitch_scorer_excellent_mae_returns_score_above_95():
    ...

def test_breath_analyzer_clean_vocal_relaxes_fluctuation_penalty():
    ...

def test_non_vocal_detection_white_noise_returns_is_voice_false():
    ...

# ❌ 错误: 含糊、无行为描述
def test_scorer():          # 测哪个 scorer？
    ...

def test_breath():          # 测 breath 的什么行为？
    ...

def test_bluetooth_speaker():  # 跟被测行为无关
    ...
```

### 4.2 AAA 模式 (Arrange → Act → Assert)

```python
def test_excellent_pitch_returns_professional_level():
    # Arrange — 准备测试数据
    threshold = PitchThresholds()
    scorer = PitchScorer(threshold)
    result = PitchDeviationResult(
        mae_cents=8.0,        # 低于 excellent 阈值 (12)
        detection_rate=0.95,
        pitch_breaks=0,
        pitch_wobble=10.0,
        consecutive_off_notes=0
    )

    # Act — 执行被测方法
    score, diagnosis = scorer.calculate(result)

    # Assert — 验证结果
    assert score >= 95.0
    assert diagnosis.level == "专业级"

def test_rhythm_scorer_clean_vocal_skips_double_penalty():
    # Arrange
    result = RhythmAlignmentResult(
        mean_deviation_ratio=0.15,
        irregularity_cv=1.34,        # 纯净人声典型 CV
        is_clean_vocal=True           # ★ 关键标记
    )

    # Act
    score, diagnosis = RhythmScorer().calculate(result)

    # Assert
    assert score >= 60  # 不应崩塌到 18.6
    # 不应有 "节奏严重不规则" 的误判
    assert "严重不规则" not in diagnosis.description
```

---

## 5. 各模块覆盖率矩阵

| 模块 | 测试文件 | 测试数 | 通过 | 目标覆盖率 |
|------|---------|--------|------|-----------|
| **PitchScorer** | `test_scorers.py` | 5 | 5/5 | 90% |
| **RhythmScorer** | `test_scorers.py` | 4 | 4/4 | 90% |
| **BreathScorer** | `test_scorers.py` | 4 | 4/4 | 85% |
| **ArtistryScorer** | `test_scorers.py` | 3 | 3/3 | 85% |
| **TechniqueScorer** | `test_scorers.py` | 5 | 5/5 | 85% |
| **特征提取** | `test_features.py` | 16 | 16/16 | 80% |
| **VoiceQuality** | `test_services.py` | 6 | 6/6 | 90% |
| **DTW 引擎** | `test_comparison_dtw.py` | 15 | 15/15 | 90% |
| **仓储层** | `test_repositories.py` | 6 | 6/6 | 85% |
| **评分校准** | `test_score_calibrator.py` | 15 | 15/15 | 85% |
| **API 端点** | `test_api.py` | 6 | 6/6 | 80% |
| **全链路** | `test_full_pipeline.py` | 6 | 4/6 | 80% |
| **整体** | **8 文件** | **91** | **89/91 (98%)** | **≥80%** |

> 2 个 pre-existing 失败 (test_vocal_audio_returns_reasonable_scores, test_professional_breath_not_always_100) 与测试数据可用性相关，不影响核心功能。 |

---

## 6. TDD 工作流示例

### 6.1 新增一个 Scorer

```bash
# Step 1: RED — 写测试
# 在 tests/unit/test_scorers.py 中添加:
class TestNewScorer:
    def test_perfect_input_returns_max_score(self):
        ...
    def test_worst_input_returns_min_score(self):
        ...
    def test_boundary_threshold_returns_expected_score(self):
        ...

# 运行，确认失败
$ pytest tests/unit/test_scorers.py::TestNewScorer -v
# → 3 failed (ImportError: NewScorer not found)

# Step 2: GREEN — 最小实现
# 创建 services/scoring/new_scorer.py
# 只写足够通过测试的代码

# 运行，确认通过
$ pytest tests/unit/test_scorers.py::TestNewScorer -v
# → 3 passed

# Step 3: REFACTOR — 优化
# 提取重复逻辑，改进命名，保持测试绿色
$ pytest tests/unit/ -v  # 全量回归
# → 89 passed
```

### 6.2 修复一个 Bug

```bash
# Step 1: RED — 写复现测试
def test_pro_breath_not_collapse_with_clean_vocal():
    """v5.15 回归: Pro Breath = 9.8 崩塌"""
    result = BreathStabilityResult(
        hnr=18.5, rms=0.12, cpp=15.0,
        is_clean_vocal=True
    )
    score = BreathScorer().calculate(result)
    assert score >= 40  # 不应崩塌

$ pytest tests/unit/test_scorers.py::test_pro_breath_not_collapse -v
# → 1 failed (AssertionError: 9.8 < 40)

# Step 2: GREEN — 修复
# 添加 is_clean_vocal 分支处理

$ pytest tests/unit/test_scorers.py::test_pro_breath_not_collapse -v
# → 1 passed

# Step 3: 全量回归
$ pytest tests/ -v -m "not e2e"
# → 89 passed
```

---

## 7. 运行命令

```bash
# 单元测试 (最快, 开发时常用)
pytest tests/unit/ -v

# 集成测试
pytest tests/integration/ -v

# 快速回归 (排除 E2E 和慢速)
pytest tests/ -v -m "not slow and not e2e"

# 全量测试 (含 E2E, 需要 Flask 服务运行)
pytest tests/ -v

# 覆盖率报告
pytest tests/unit/ tests/integration/ \
  --cov=services --cov=api --cov=core \
  --cov-report=term-missing

# 单文件调试
pytest tests/unit/test_scorers.py -v --tb=long

# 按 marker 筛选
pytest tests/ -v -m smoke     # 冒烟测试
pytest tests/ -v -m bdd       # BDD 测试
```

---

## 8. TDD 实践清单

- [ ] 新 scorer 先写 `test_scorers.py` 测试类
- [ ] 新 feature extractor 先写 `test_features.py` 测试函数
- [ ] 新 API 端点先写 `test_api.py` 集成测试
- [ ] 修改阈值/参数后跑 `pytest tests/ -v -m "not e2e"`
- [ ] 覆盖率不降级 (可在 pre-commit hook 中检查)
- [ ] Bug 修复必带回归测试
- [ ] 测试函数名准确描述行为和期望

---

## 9. 参考文档

| 文档 | 路径 |
|------|------|
| BDD 规范 | [BDD.md](BDD.md) |
| 产品需求文档 | [PRD.md](../1-product/PRD.md) |
| 系统架构 | [ARCHITECTURE.md](../2-technical/ARCHITECTURE.md) |
| 评分算法 | [SCORING.md](../2-technical/SCORING.md) |
| 项目状态 | [PROJECT_STATUS.md](../4-process/PROJECT_STATUS.md) |
