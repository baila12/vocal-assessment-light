# 测试驱动开发 (TDD) 规范

> 更新: 2026-07-20 | v7.0 迁移策略: BDD+TDD+DDD | 适用于所有核心算法和评分模块开发
> 
> **测试准则**: 优先使用 `tests/test_data/audio/vocal/` 中的 5 首真实人声音频 (4高分+1低分) 获取真实反馈。
> **v7.0 迁移**: FastAPI + Vue 3 + Electron 分阶段迁移，每阶段 TDD 门禁必过。绝不允许迁移破坏评分精度。

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
      ╱──────────╲       ~45 场景, 关键用户流程, 慢
     ╱ Integration ╲     API 端点 + 评分管线 + v5.19 端到端
    ╱────────────────╲   ~25 场景 + 真实音频回归基线
   ╱    Unit Tests     ╲ 评分器/特征提取/稳健性/工具
  ╱──────────────────────╲ ~150 场景, 覆盖率 ≥ 80%, 快
 ╱   TDD Tests            ╲ v5.19 GREEN(15) + v6.0 RED(6)
╱──────────────────────────╲ 29 场景, 引导开发
```

| 层级 | 工具 | 场景数 | 速度 | 通过率 |
|------|------|--------|------|------|
| Unit | pytest | 150+ (13 文件) | < 30s | 150+/150+ (100%) |
| Integration | pytest + Flask test client | 25 (4 文件) | < 5min | 25/25 (100%) |
| Real Audio Regression | pytest | 27 (1 文件) | < 5min | v5.19 基线已更新 |
| E2E | Playwright | ~45 (10+ 文件) | < 5min | 按需运行 |
| BDD | pytest-bdd | ~75 (21 feature) | < 60s | 4 已实现 Step Defs |
| TDD | pytest (xfail) | 29 (2 文件) | < 60s | 15 GREEN + 6 xfail ✅ |
| **合计 (可自动运行)** | | **~220** | | **190+/190+ (100%)** |

> 🆕 v5.19 评分修复: 气息基线 40→10, 音准阈值 12/35/60→8/45/65, HNR/CPP 天花板提升。
> 新增 `tests/tdd/test_v5_19_features.py` (16 tests), 移除 11 个 xfail 标记。
> 旧版 E2E 测试 (test_upload.py, test_analysis.py, test_real_audio.py) 已标记 skip，替换为 SPA 兼容的 test_spa_e2e.py。
> **真音频黄金测试集**: `tests/test_data/audio/vocal/` — 5 首真实人声 (4 高分 + 1 低分)，所有评分验证优先使用此目录。

---

## 3. 测试文件组织

```
tests/
├── unit/                            # 单元测试 — 无 IO/网络/数据库
│   ├── test_scorers.py              # PitchScorer, RhythmScorer, BreathScorer,
│   │                                #   TechniqueScorer, ArtistryScorer, CriticalRules
│   ├── test_features.py             # PitchAnalyzer, BreathAnalyzer,
│   │                                #   RhythmAnalyzer, TechniqueAnalyzer, AcousticAnalyzer
│   ├── test_services.py             # ScoreService, AdviceService, AudioAnalysisResult
│   ├── test_comparison_dtw.py       # DTW 对齐引擎 (15 tests)
│   ├── test_repositories.py         # HistoryRepository CRUD
│   ├── test_score_calibrator.py     # ScoreCalibrator (15 tests)
│   ├── test_scoring_robustness.py   # 🆕 评分稳健性 (22 tests)
│   │   ├── TestScoringReproducibility    # 相同输入 → 相同分数 (5)
│   │   ├── TestScoringBoundaryInputs     # 零值/极值/检测率边界 (9)
│   │   ├── TestScoreDistribution         # 评分不崩塌到单一区间 (3)
│   │   ├── TestDiagnosisConsistency      # 诊断与分数一致性 (3)
│   │   └── TestCriticalRulesCascade      # 级联惩罚正确性 (2)
│   ├── test_spa_routes.py           # SPA 路由重定向验证 (16 tests)
│   ├── test_store_and_ac.js         # 🆕 Store + AnimationController 集成 (16)
│   ├── test_animation_controller.js # AnimationController 单元 (9)
│   ├── test_mode_select.js          # 模式选择器 (7)
│   └── test_song_library_page.js    # 曲库页面 (8)
├── integration/                     # 集成测试 — 跨模块协作
│   ├── test_api.py                  # Flask API 端点 (6 tests)
│   ├── test_full_pipeline.py        # 🆕 上传→分离→评分 全链路 (7 tests)
│   │   └── TestBreathScoreDifferentiation # 🆕 气息区分度验证 (2 tests)
│   ├── test_real_audio_regression.py # 🆕 真实音频回归基线 (5文件×5+区分度)
│   └── test_v5_18_integration.py    # 🆕 v5.18 新算法端到端管线 (7 tests)
│       ├── TestAudioFeaturesServiceIntegration # HNR/CPP flag 切换 (3)
│       ├── TestScorePipelineIntegration        # 评分管线 + 真音频对比 (3)
│       └── TestVoicingDetectionIntegration     # Voicing 诊断 (1)
├── e2e/                             # E2E — Playwright 浏览器
│   ├── test_spa_e2e.py              # 🆕 SPA 端到端 (24 tests)
│   ├── test_visual_verify.py        # 视觉验证 (36 tests, Edge)
│   ├── test_spa_navigation.py       # SPA 路由导航 (19 tests)
│   ├── test_compare.py              # 对比分析 (保留)
│   ├── test_history.py              # 历史记录 (保留)
│   ├── test_home.py                 # 首页 (保留)
│   ├── test_upload.py               # ⏭️ 已标记 skip (旧架构)
│   ├── test_analysis.py             # ⏭️ 已标记 skip (旧架构)
│   └── test_real_audio.py           # ⏭️ 已标记 skip (旧架构)
├── tdd/                             # TDD 阶段测试 (RED → GREEN)
│   ├── test_future_features.py      # v5.18/v6.0 规划功能 (13 tests)
│   │   ├── TestFeatureFlags              # Feature Flag 机制 (3) ✅ GREEN
│   │   ├── TestMultiScaleHNR             # 多频带 HNR (2) ✅ GREEN
│   │   ├── TestPraatCPP                  # Praat CPP (2) ✅ GREEN
│   │   ├── TestVoicingDetection          # Voicing 检测 (3) ✅ GREEN
│   │   ├── TestTorchCREPEFallback        # CREPE 降级 (2) ✅ GREEN
│   │   ├── TestVolumeDimension           # 音量维度 (2) ✅ GREEN (v5.19)
│   │   ├── TestSSEStreamingProgress      # SSE 流式进度 (2) 🔴 xfail
│   │   ├── TestSongAutoMatch             # 歌曲自动匹配 (3) 🔴 xfail
│   │   └── TestReverbCompensation        # 混响补偿 (1) 🔴 xfail
│   └── test_v5_19_features.py       # 🆕 v5.19 评分修复 (16 tests)
│       ├── TestBreathDifferentiation     # 气息区分度 (3) 🟢 1 GREEN + 2 xfail
│       ├── TestPitchDifferentiation      # 音准区分度 (4) 🟢 3 GREEN + 1 xfail
│       ├── TestTechniqueCeiling          # HNR/CPP 天花板 (3) ✅ GREEN
│       ├── TestCrossDimensionIntegration # 跨维度集成 (4) 🟡 基础通过
│       └── TestVolumeIndependence        # 音量独立 (2) ✅ GREEN
├── bdd/                             # BDD 测试 (见 BDD.md)
│   ├── features/                    # 21 个 .feature 文件
│   └── steps/                       # 9 个 Step 实现文件
├── conftest.py                      # Session 级 fixtures
├── e2e/conftest.py                  # E2E 专用 fixtures (Flask 启动管理)
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
| **CriticalRules** | `test_scorers.py` | 5 | 5/5 | 90% |
| **特征提取** | `test_features.py` | 16 | 16/16 | 80% |
| **VoiceQuality** | `test_services.py` | 6 | 6/6 | 90% |
| **DTW 引擎** | `test_comparison_dtw.py` | 15 | 15/15 | 90% |
| **仓储层** | `test_repositories.py` | 6 | 6/6 | 85% |
| **评分校准** | `test_score_calibrator.py` | 15 | 15/15 | 85% |
| **🆕 评分稳健性** | `test_scoring_robustness.py` | 22 | 22/22 | 新增 |
| **SPA 路由** | `test_spa_routes.py` | 16 | 16/16 | 80% |
| **API 端点** | `test_api.py` | 6 | 6/6 | 80% |
| **全链路** | `test_full_pipeline.py` | 7 | 7/7 | 80% |
| **🆕 真实音频回归** | `test_real_audio_regression.py` | 27 | 27/27 | 新增 |
| **🆕 TDD RED** | `test_future_features.py` | 13 | 13/13 xfail | v5.18+ |
| **🆕 JS 集成** | `test_store_and_ac.js` | 16 | 16/16 | 新增 |
| **整体** | **18 文件** | **191** | **178/178 (100%) + 13 xfail** | **≥80%** |

> 🆕 v5.18 测试审计后: 新增 4 个测试文件 (稳健性、回归基线、TDD RED、JS 集成)，修复 2 个失败，标记 3 个旧 E2E 为 skip。测试数从 91 → 191 (+110%)。

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

## 9. 性能测试 (Performance Testing)

### 9.1 性能测试作为一等测试类型

> 性能测试不是可选的"优化项"，而是每个功能模块的验收标准之一。

```
       ╱  E2E  ╲         
      ╱──────────╲       
     ╱ Integration ╲     
    ╱────────────────╲   
   ╱    Unit Tests     ╲  
  ╱──────────────────────╲
 ╱   Performance Tests    ╲  ← 新增: 耗时/内存/帧率断言
╱──────────────────────────╲
```

### 9.2 后端性能测试

#### 特征提取器耗时断言

```python
# tests/unit/test_performance.py
import time
import pytest

def test_pyin_extraction_within_budget():
    """PYIN f0 提取: 3分钟音频 ≤ 8秒"""
    audio, sr = librosa.load(TEST_AUDIO_3MIN, sr=44100)
    
    start = time.perf_counter()
    f0, voiced_flag, voiced_prob = librosa.pyin(
        audio, fmin=65, fmax=2093, sr=sr
    )
    elapsed = time.perf_counter() - start
    
    assert elapsed < 8.0, f"PYIN 超预算: {elapsed:.1f}s > 8s"


def test_quick_mode_total_within_budget():
    """Quick 模式端到端 ≤ 30秒"""
    start = time.perf_counter()
    result = analyze_and_score(TEST_VOCAL_FILE, mode='quick')
    elapsed = time.perf_counter() - start
    
    assert elapsed < 30.0, f"Quick 超时: {elapsed:.1f}s > 30s"
    assert result['total_score'] > 0  # 确保结果是有效的


def test_memory_no_leak_after_10_runs():
    """连续 10 次 Pro 模式，内存增量 < 200MB"""
    import tracemalloc
    tracemalloc.start()
    
    snapshot1 = tracemalloc.take_snapshot()
    for _ in range(10):
        analyze_and_score(TEST_VOCAL_FILE, mode='quick')
    snapshot2 = tracemalloc.take_snapshot()
    
    diff = snapshot2.compare_to(snapshot1, 'lineno')
    total_increase = sum(stat.size_diff for stat in diff if stat.size_diff > 0)
    increase_mb = total_increase / 1024 / 1024
    
    assert increase_mb < 200, f"内存增长超标: {increase_mb:.0f}MB > 200MB"
```

#### 评分计算耗时

```python
def test_scoring_calculation_within_budget():
    """五维评分计算 ≤ 3秒"""
    features = extract_all_features(TEST_VOCAL)
    
    start = time.perf_counter()
    scores = ScoreServiceV4().calculate(features)
    elapsed = time.perf_counter() - start
    
    assert elapsed < 3.0, f"评分计算超预算: {elapsed:.1f}s > 3s"
```

### 9.3 前端性能测试

#### 动画帧率 (JS 单元测试)

```javascript
// tests/unit/test_animation_performance.js
test('page-enter animation completes within 600ms', async () => {
  const start = performance.now();
  await ac.enter(testEl, { preset: 'page-enter' });
  const elapsed = performance.now() - start;
  
  expect(elapsed).toBeLessThan(600);
});

test('stagger-cards does not block main thread', async () => {
  const cards = Array.from({ length: 20 }, () => createCardEl());
  
  const tasks = [];
  const observer = new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      tasks.push(entry.duration);
    }
  });
  observer.observe({ type: 'longtask', buffered: true });
  
  await ac.stagger(cards, { preset: 'stagger-cards' });
  
  // 不应产生 > 50ms 的长任务
  expect(tasks.filter(d => d > 50).length).toBe(0);
});
```

#### Canvas 帧率测试

```javascript
test('Canvas pitch render maintains 30fps minimum', async () => {
  const fps = await measureCanvasFps(pitchCanvas, 2000); // 2秒采样
  expect(fps).toBeGreaterThanOrEqual(30);
});
```

### 9.4 性能测试运行

```bash
# 运行性能测试 (需要较长运行时间)
pytest tests/unit/test_performance.py -v -m performance

# 跳过性能测试 (日常开发)
pytest tests/ -v -m "not performance and not e2e"

# CI 中运行 (夜间构建)
pytest tests/ -v -m "performance"
```

### 9.5 性能回归触发条件

| 事件 | 运行 | 通过标准 |
|------|------|---------|
| PR 合并 | Quick 性能冒烟 (1个文件) | < 30s |
| 新特征提取器 | 该提取器耗时断言 | 在预算内 |
| 新评分器 | 评分计算耗时断言 | < 3s |
| 夜间构建 | 全量性能测试 | 全部在预算 ±20% 内 |
| 发布前 | Quick + Pro 全链路 | 满足 v4.1.1 表格所有目标 |

---

## 10. v7.0 迁移 TDD 策略

> v7.0 全栈迁移: FastAPI + Vue 3 + Element Plus + Electron
> 核心原则: **每迁移一部分, 测试一部分, 验证一部分, 绝不累积 Bug**

### 10.1 Scoring Domain (零改动迁移)

评分域 (PitchScorer/RhythmScorer/BreathScorer/TechniqueScorer/ArtistryScorer/CriticalRules) 是纯数学函数 — 迁移时**一行代码不改**。

```python
# 直接 import 复用, 无需改动
from services.scoring.pitch_scorer import PitchScorer
from services.scoring.rhythm_scorer import RhythmScorer
# ... etc

# TDD 验证: 迁移后所有 scorer 测试必须 100% 保持通过
pytest tests/unit/test_scorers.py -v          # 26 tests
pytest tests/unit/test_scoring_robustness.py -v  # 22 tests
```

### 10.2 FastAPI 端点 TDD 模板

```python
# tests/tdd/test_v7_fastapi_endpoints.py
import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app

@pytest.mark.asyncio
async def test_health_endpoint_returns_healthy():
    """FastAPI /health 替代 Flask /health"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_upload_quick_returns_pydantic_model():
    """UploadFile → Pydantic UploadResponse, 分数不变"""
    # ... Arrange: 上传黄金测试集音频
    # ... Act: POST /api/v2/upload?mode=quick
    # ... Assert: total_score 与 Flask 基线差 < 1 分
    pass
```

### 10.3 黄金测试集保护 (CRITICAL)

5 首真实音频的回归基线是迁移的**最高门禁**:

```bash
# 每次迁移后必须运行, 分数波动必须 < ±1 分
pytest tests/integration/test_real_audio_regression.py -v
```

### 10.4 Phase 门禁清单

| Phase | TDD Tests | 门禁命令 |
|-------|-----------|---------|
| 1 FastAPI 共存 | 7 (history CRUD) | `pytest tests/unit/test_repositories.py tests/tdd/ -v` |
| 2 评分异步化 | 5 (upload/compare/extract-pitch/separate/report) | `pytest tests/integration/test_real_audio_regression.py -v` ⚠️ 分数波动 < ±1 分 |
| 3 WebSocket | 3 (connect/frames/score) | `pytest tests/tdd/ -v -k ws` |
| 4 Vue + Element Plus | 6 (每页面 1 组件测试) | `npx vitest run` |
| 5 Electron | 2 (smoke/packaging) | 手动验证 |

### 10.5 禁止事项

- ❌ 迁移期间修改任何 scorer 算法 (改变评分精度的唯一原因)
- ❌ 跳过黄金测试集验证就进入下一 Phase
- ❌ 在 Phase N 中修改 Phase N-1 的代码 (单向依赖)
- ❌ 使用 `console.log` 或 `print()` 调试 (用 proper logging)

---

## 11. 参考文档

| 文档 | 路径 |
|------|------|
| BDD 规范 | [BDD.md](BDD.md) |
| 产品需求文档 | [PRD.md](../1-product/PRD.md) |
| 系统架构 | [ARCHITECTURE.md](../2-technical/ARCHITECTURE.md) |
| 评分算法 | [SCORING.md](../2-technical/SCORING.md) |
| 项目状态 | [PROJECT_STATUS.md](../4-process/PROJECT_STATUS.md) |
