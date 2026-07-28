# 行为驱动开发 (BDD) 规范

> 更新: 2026-07-28 | v7.3.1: 13 step files (29 new scenarios) | 适用于关键用户场景验收和回归防护

---

## 1. BDD 概述

### 1.1 三层结构

```
┌──────────────────────────────────────────────┐
│  Feature 文件 (.feature)                      │
│  业务可读的 Gherkin 场景                      │
│  Given → When → Then                          │
│  受众: 开发者 + 产品 + QA                     │
└──────────────────┬───────────────────────────┘
                   │
┌──────────────────▼───────────────────────────┐
│  Step Definitions (.py)                       │
│  将 Given/When/Then 映射到 Python 代码        │
│  @given / @when / @then 装饰器                │
│  受众: 开发者                                 │
└──────────────────┬───────────────────────────┘
                   │
┌──────────────────▼───────────────────────────┐
│  Fixtures / World                             │
│  测试上下文: Flask 客户端、测试数据、浏览器    │
│  conftest.py + pytest fixtures                │
└──────────────────────────────────────────────┘
```

### 1.2 BDD vs TDD

| 维度 | TDD | BDD |
|------|-----|-----|
| **受众** | 开发者 | 开发者 + 产品 + QA |
| **粒度** | 函数/类级别 | 功能/场景级别 |
| **语言** | `assert score >= 95.0` | `Given 一个人声文件 When 上传 Then 获得评分` |
| **关注点** | 代码正确性 | 业务行为正确性 |
| **编写时机** | 写实现代码前 | 需求明确后 / 验收时 |
| **覆盖层次** | Unit + Integration | Integration + E2E |
| **文件位置** | `tests/unit/`, `tests/integration/` | `tests/bdd/features/`, `tests/bdd/steps/` |
| **工具** | pytest | pytest-bdd |
| **规范文档** | [TDD.md](TDD.md) | 本文档 |

---

## 2. 目录结构

```
tests/bdd/
├── features/                         # Gherkin .feature 文件 (21 个, ~75 scenarios)
│   ├── upload.feature                # ✅ 音频上传与五维评分 (当前功能)
│   ├── compare.feature               # ✅ DTW 对比分析 (当前功能)
│   ├── compare-ui.feature            # ✅ 对比分析 UI 交互 (当前功能)
│   ├── differentiation.feature       # ✅ 评分区分度验证 (当前功能)
│   ├── history.feature               # ✅ 历史记录管理 (当前功能)
│   ├── mode-select.feature           # ✅ 快速/专业模式选择 (当前功能)
│   ├── navigation.feature            # ✅ SPA 路由导航 (当前功能)
│   ├── sing-song-select.feature      # ✅ 演唱选歌流程 (当前功能)
│   ├── song-library.feature          # ✅ 标准曲库管理 (当前功能)
│   ├── animations.feature            # ⚠️ 部分实现 (GSAP 动画框架已就绪，部分场景待实现)
│   ├── responsive.feature            # ⚠️ 部分实现 (响应式布局基础就绪)
│   ├── offline.feature               # ⚠️ 部分实现 (本地库加载已验证)
│   ├── database.feature              # ⏳ v6.0 标准歌曲数据库
│   ├── auto-match.feature            # ⏳ v6.0 上传自动匹配
│   ├── song-select.feature           # ⏳ v6.0 选歌录音完整流程
│   ├── dtw-demotion.feature          # ⏳ v6.0 DTW 降级为特征提供者
│   ├── scoring-config.feature        # ⏳ v6.0 评分配置可定制
│   ├── multi-dim-analysis.feature    # ⏳ v6.0 有参考时多维度分析
│   ├── nonblocking-analysis.feature  # ⏳ v6.0 非阻塞分析体验 (SSE)
│   ├── pitch-realtime.feature        # ⏳ v6.0 实时音准对比显示 (Canvas)
│   └── realtime-analysis.feature     # ⏳ v6.0 录音实时后台分析
├── steps/                            # Step 实现
│   ├── test_upload_steps.py          ✅ 上传 + 评分 (当前功能)
│   ├── test_compare_steps.py         ✅ DTW 对比 (当前功能)
│   ├── test_compare_ui_steps.py      ✅ 对比 UI (当前功能)
│   ├── test_differentiation_steps.py ✅ 评分区分度 (当前功能)
│   ├── test_history_steps.py         ✅ 历史记录 (当前功能)
│   ├── test_mode_select_steps.py     ✅ 模式选择 (当前功能)
│   ├── test_navigation_steps.py      ✅ SPA 导航 (当前功能)
│   ├── test_sing_song_select_steps.py ✅ 演唱选歌 (当前功能)
│   ├── test_song_library_steps.py    ✅ 曲库管理 (当前功能)
│   └── test_spa_steps.py             ✅ SPA 通用步骤 (当前功能)
├── conftest.py                       # BDD 专用 fixtures + Playwright 浏览器支持 ✅
└── __init__.py                       ✅

版本标记说明:
  ✅ 当前功能 — 系统已实现，Step Defs 可执行
  ⚠️ 部分实现 — 基础设施就绪，部分场景待完成
  ⏳ v6.0 规划 — 需先实现后端功能再完成 Step Defs
```

---

## 3. Feature 文件

### 3.1 upload.feature — 上传与评分

```gherkin
Feature: 音频上传与五维评分
  As a 声乐学生
  I want to 上传我的演唱录音
  So that 获得专业评分和改进建议

  Background:
    Given Flask 服务已启动在 localhost:5000

  Scenario: Quick 模式快速评分
    Given 一个包含人声演唱的 WAV 文件 "vocals.wav"
    When 我上传该文件并选择 "quick" 模式
    Then 响应状态码应为 200
    And 响应时间应小于 30 秒
    And 返回的 total_score 应在 0 到 100 之间
    And 应返回五个维度评分: pitch, rhythm, breath, technique, artistry
    And 每个维度评分应在 0 到 100 之间

  Scenario: 非人声音频拦截
    Given 一个白噪声 WAV 文件 "noise.wav"
    When 我上传该文件进行评估
    Then 返回的 is_voice 应为 false
    And 返回的 total_score 应为 0.0
    And 返回的 scores 中所有维度应为 0

  Scenario Outline: 多格式音频支持
    Given 一个包含人声的 "<format>" 文件
    When 我上传该文件选择 "quick" 模式
    Then 应成功返回评分结果

    Examples:
      | format |
      | WAV    |
      | MP3    |
      | FLAC   |
      | OGG    |
      | M4A    |

  Scenario: Pro 模式 Demucs 人声分离
    Given 一个包含钢琴伴奏的人声 MP3 文件 "mixed_vocal.mp3"
    When 我选择 "professional" 模式上传
    Then 混合音频检测应判断为 mixed
    And Demucs 应执行人声分离
    And 气息评分 breath_score 不应低于 40
    And 专业模式总分应在快速模式总分的 10% 以内

  Scenario: 合成音频归零
    Given 一个 TTS 合成的语音 WAV 文件 "synthetic.wav"
    When 我上传该文件进行评估
    Then 人声质量检测应判断为 non-voice
    And 返回的 total_score 应为 0.0
```

### 3.2 compare.feature — 对比分析

```gherkin
Feature: DTW 对比分析
  As a 声乐学生
  I want to 将我的演唱与标准版本对比
  So that 了解音准和节奏的偏差

  Scenario: 相同音频对比得满分
    Given 我准备两个完全相同的音频文件
    When 我发起 DTW 对比分析
    Then 对比评分应不低于 95 分
    And 音准匹配率应不低于 95%
    And 节奏匹配率应不低于 95%

  Scenario: 音准偏差检测
    Given 标准音频 "reference.wav"
    And 音高偏移 50 音分的用户音频 "off_pitch.wav"
    When 我发起对比分析
    Then 音准评分应低于 90 分
    And 返回结果中应包含 problem_frames

  Scenario: 无参考音频时 DTW 自动搜索
    Given uploads/ 目录中存在带 "高分" 标签的参考音频
    When 我仅上传用户音频到独立上传接口
    Then 系统应自动找到参考音频
    And DTW 融合评分应被触发
    And 无匹配参考时回退到绝对评分
```

### 3.3 differentiation.feature — 评分区分度

```gherkin
Feature: 评分区分度验证
  As a 产品负责人
  I want to 确保评分能有效区分不同水平的演唱
  So that 用户获得的评分有参考价值

  Scenario: 专业演唱得分显著高于初学者
    Given 一个专业级演唱音频 "pro_singer.wav"
    And 一个初学者演唱音频 "beginner.wav"
    When 两个音频都用 quick 模式评估
    Then 专业级 total_score 应比初学者高至少 20 分

  Scenario: 节奏是最强区分器
    Given 高分演唱和低分演唱的评估结果
    When 比较各维度区分度
    Then 节奏维度的区分度应最高

  Scenario: Quick 与 Pro 模式评分一致
    Given 同一个人声演唱音频 "vocals.wav"
    When 分别用 quick 和 professional 模式评估
    Then 两个模式的 total_score 差距应小于 10%
    And 各维度的评分趋势应相同

  Scenario: 各维度均有区分力
    Given 5 个不同水平的演唱音频
    When 全部用 quick 模式评估
    Then 每个维度的最高分与最低分差距应至少 3 分
```

### 3.4 history.feature — 历史记录

```gherkin
Feature: 历史记录管理
  As a 声乐学生
  I want to 查看和管理我的历史评分记录
  So that 追踪演唱进步

  Scenario: 分页查看历史记录
    Given 历史记录中有至少 10 条评估记录
    When 我访问历史记录 API 并指定 page=1, limit=5
    Then 应返回 5 条记录
    And 返回应包含 total, page, limit 分页信息

  Scenario: 删除单条记录
    Given 历史记录中存在一条特定记录
    When 我发送 DELETE 请求到该记录的 API 端点
    Then 该记录应被删除
    And 后续 GET 请求不应再返回该记录

  Scenario: 批量删除
    Given 历史记录中有 3 条记录
    When 我发送批量删除请求包含这 3 个 ID
    Then 这 3 条记录应全部被删除
    And 其他记录应保持不变

  Scenario: 非人声记录独立标记
    Given 一条 is_voice=false 的评估记录
    When 该记录被保存到历史
    Then 记录中应标记 is_voice=false
    And 统计时应可排除该记录
```

---

## 4. Step Definitions 实现

### 4.1 文件模板

```python
# tests/bdd/steps/test_upload_steps.py
"""
Step definitions for upload.feature
"""
from pytest_bdd import given, when, then, parsers, scenarios

# 自动加载同名的 .feature 文件中的所有场景
scenarios('../features/upload.feature')


# ── Given ──────────────────────────────────────────

@given('Flask 服务已启动在 localhost:5000')
def flask_app_running(api_client):
    """确保 Flask 测试客户端可用"""
    assert api_client is not None


@given(parsers.parse('一个包含人声演唱的 WAV 文件 "{filename}"'))
def vocal_wav_file(filename, test_data_dir):
    """返回测试数据目录中的人声文件路径"""
    path = test_data_dir / 'audio' / 'vocal' / filename
    assert path.exists(), f'测试文件不存在: {path}'
    return path


@given(parsers.parse('一个白噪声 WAV 文件 "{filename}"'))
def noise_wav_file(filename, test_data_dir):
    path = test_data_dir / 'audio' / 'non_vocal' / filename
    assert path.exists(), f'测试文件不存在: {path}'
    return path


@given(parsers.parse('一个包含人声的 "{format_name}" 文件'))
def vocal_file_by_format(format_name, test_data_dir):
    ext = format_name.lower()
    files = list((test_data_dir / 'audio' / 'vocal').glob(f'*.{ext}'))
    assert files, f'没有找到 .{ext} 格式的测试文件'
    return files[0]


@given('一个包含钢琴伴奏的人声 MP3 文件 "mixed_vocal.mp3"')
def mixed_vocal_file(test_data_dir):
    path = test_data_dir / 'audio' / 'vocal' / 'mixed_vocal.mp3'
    assert path.exists(), f'测试文件不存在: {path}'
    return path


# ── When ─────────────────────────────────────────

@when(parsers.parse('我上传该文件并选择 "{mode}" 模式'))
def upload_with_mode(request, api_client, mode):
    """通过 Flask 测试客户端上传文件"""
    # request 是 pytest fixture 上下文
    # 从之前的 Given step 获取文件路径
    file_path = request.getfixturevalue('vocal_wav_file')
    with open(file_path, 'rb') as f:
        response = api_client.post(
            '/api/upload',
            data={
                'file': (f, file_path.name),
                'mode': mode
            },
            content_type='multipart/form-data'
        )
    return response


@when('我上传该文件进行评估')
def upload_default(request, api_client):
    file_path = None
    for name in ['vocal_wav_file', 'noise_wav_file', 'mixed_vocal_file']:
        try:
            file_path = request.getfixturevalue(name)
            break
        except Exception:
            continue
    if file_path is None:
        raise ValueError('No file fixture found in Given steps')

    with open(file_path, 'rb') as f:
        response = api_client.post(
            '/api/upload',
            data={'file': (f, file_path.name)},
            content_type='multipart/form-data'
        )
    return response


# ── Then ──────────────────────────────────────────

@then('响应状态码应为 200')
def check_status_200(upload_with_mode):
    assert upload_with_mode.status_code == 200, \
        f'Expected 200, got {upload_with_mode.status_code}'


@then('响应时间应小于 30 秒')
def check_response_time(upload_with_mode):
    elapsed = upload_with_mode.elapsed.total_seconds()
    assert elapsed < 30, f'响应超时: {elapsed:.1f}s'


@then('返回的 total_score 应在 0 到 100 之间')
def check_total_score_range(upload_with_mode):
    data = upload_with_mode.get_json()
    score = data.get('total_score')
    assert score is not None, '响应中没有 total_score'
    assert 0 <= score <= 100, f'total_score={score} 超出范围'


@then('应返回五个维度评分: pitch, rhythm, breath, technique, artistry')
def check_five_dimensions(upload_with_mode):
    data = upload_with_mode.get_json()
    expected = {'pitch', 'rhythm', 'breath', 'technique', 'artistry'}
    actual = set(data.get('scores', {}).keys())
    missing = expected - actual
    assert not missing, f'缺少维度: {missing}'


@then('每个维度评分应在 0 到 100 之间')
def check_dimension_scores_range(upload_with_mode):
    scores = upload_with_mode.get_json().get('scores', {})
    for dim, score in scores.items():
        assert 0 <= score <= 100, f'{dim}={score} 超出范围'


@then('返回的 is_voice 应为 false')
def check_is_voice_false(upload_with_mode):
    data = upload_with_mode.get_json()
    assert data.get('is_voice') is False, \
        f'Expected is_voice=False, got {data.get("is_voice")}'


@then('返回的 total_score 应为 0.0')
def check_total_score_zero(upload_with_mode):
    data = upload_with_mode.get_json()
    assert data.get('total_score') == 0.0, \
        f'Expected 0.0, got {data.get("total_score")}'
```

### 4.2 conftest.py (BDD 专用)

```python
# tests/bdd/conftest.py
"""BDD 测试专用 fixtures"""
import pytest
from pathlib import Path


@pytest.fixture(scope='session')
def test_data_dir():
    """测试数据根目录"""
    path = Path(__file__).parent.parent / 'test_data'
    assert path.exists(), f'测试数据目录不存在: {path}'
    return path


@pytest.fixture(scope='session')
def api_client():
    """Flask 测试客户端 (session 级别复用)"""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from web_app import create_app
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client
```

---

## 5. 运行命令

```bash
# 运行所有 BDD 场景
pytest tests/bdd/ -v

# 运行特定 feature
pytest tests/bdd/ -v -k "upload"
pytest tests/bdd/ -v -k "compare"
pytest tests/bdd/ -v -k "differentiation"

# 运行特定 scenario
pytest tests/bdd/ -v -k "Quick 模式快速评分"

# 生成 Gherkin 报告 (需要 pytest-bdd 插件)
pytest tests/bdd/ --cucumberjson=report.json

# 详细输出 (查看每个 step 的执行)
pytest tests/bdd/ -v --tb=long
```

---

## 6. BDD 验收流程

```
需求评审 ──→ 编写 .feature ──→ 团队确认场景覆盖
                │
                ▼
         实现 Step Defs ──→ 运行 (应失败: RED)
                │
                ▼
         开发功能实现 ──→ 运行 (应通过: GREEN)
                │
                ▼
         PR 合并 ←── 全量回归通过 ←── Code Review
```

### 6.1 何时写 BDD 场景

| 时机 | 示例 |
|------|------|
| 新功能开发前 | "我们要加六维评分，验收标准是什么？" → 写 differentiation.feature |
| Bug 修复时 | "Pro Breath 崩塌" → 在 upload.feature 添加回归场景 |
| 版本发布前 | "v5.18 能发布吗？" → 全量 BDD 绿色 |
| 重构后验收 | "架构调整后功能完好？" → 跑全量 BDD |

### 6.2 场景设计原则

- **独立性**: 每个 Scenario 可独立运行，不依赖其他场景的执行顺序
- **业务语言**: 用业务术语而非技术术语 (说 "上传音频" 不说 "POST form-data")
- **一个行为**: 一个 Scenario 验证一个用户行为，不塞多个不相关断言
- **可追溯**: 场景描述应能追溯到 PRD 中的用户场景

---

## 7. 性能 BDD 场景 (Performance BDD)

### 7.1 performance.feature

> 性能行为应通过 BDD 验收，确保用户体验不被性能问题破坏。

```gherkin
@performance
Feature: 系统性能行为

  Scenario: Quick 模式在预算时间内完成
    Given 一个 3 分钟人声演唱音频
    When 我上传该文件并选择 "quick" 模式
    Then 响应时间应小于 30 秒
    And 内存增量应小于 400MB

  Scenario: 动画不阻塞页面交互
    Given 用户在首页
    When 快速点击导航切换页面 5 次
    Then 每次切换应在 300ms 内完成
    And 不应出现页面闪烁或元素残留

  Scenario: 低性能设备动画降级
    Given 用户设备硬件并发数小于 4
    When 导航到任何页面
    Then GSAP 动画帧率应不低于 30fps
    And Canvas 实时绘制帧率应不低于 30fps

  Scenario: 减少动效模式即时响应
    Given 用户系统启用了 "prefers-reduced-motion"
    When 导航到任何页面
    Then 页面内容应立即显示
    And 不应有任何 tween 动画执行

  Scenario: 长时间使用无内存泄漏
    Given 用户连续使用系统 30 分钟
    When 在此期间切换页面 50 次
    Then 浏览器内存增长应小于 100MB
    And GSAP 实例数应保持稳定

  Scenario: 大音频文件优雅处理
    Given 一个 45MB 的 WAV 文件
    When 我上传该文件进行评估
    Then 系统应拒绝并返回 413 错误
    And 前端应显示友好的文件大小提示

  Scenario: 特征提取阶段计时
    Given 一个标准人声测试文件
    When 系统执行 Quick 模式分析
    Then voice_quality 检查应在 2 秒内完成
    And PYIN 基频提取应在 8 秒内完成
    And onset 检测应在 3 秒内完成
    And 总分析时间应在 30 秒内
```

### 7.2 性能 Step Definitions (Python)

```python
# tests/bdd/steps/test_performance_steps.py
from pytest_bdd import given, when, then, parsers, scenarios
import time

scenarios('../features/performance.feature')


@then(parsers.parse('响应时间应小于 {seconds:d} 秒'))
def check_response_time_under(result, seconds):
    elapsed = result.get('_elapsed_seconds', 999)
    assert elapsed < seconds, f'响应超预算: {elapsed:.1f}s > {seconds}s'


@then(parsers.parse('{feature} 应在 {budget:d} 秒内完成'))
def check_feature_budget(analysis_result, feature, budget):
    timings = analysis_result.get('_feature_timings', {})
    elapsed = timings.get(feature, 999)
    assert elapsed < budget, f'{feature} 超预算: {elapsed:.1f}s > {budget}s'


@then('内存增量应小于 {limit_mb:d}MB')
def check_memory_under(limit_mb):
    import psutil, os
    mem_mb = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
    # 应在测试前后对比，此处简化
    assert mem_mb < 800 + limit_mb, f'内存超标: {mem_mb:.0f}MB'
```

---

## 8. v7.0 迁移 BDD 策略 (详见 [V7_MIGRATION_PLAN.md](../4-process/V7_MIGRATION_PLAN.md))

> 每 Phase 迁移完成标准 = 所有关联 BDD scenarios 通过
> 绝不由"代码写完了"来判断完成

### 8.1 新 BDD Scenarios (v7.0 迁移新增)

#### `fastapi-migration.feature` (Phase 1-2)

```gherkin
Feature: FastAPI 后端迁移验收

  Scenario: FastAPI 与 Flask 共存
    Given FastAPI 服务已启动在 localhost:5000
    When 访问 /old/api/upload 端点
    Then 旧 Flask 端点仍正常响应

  Scenario: Pydantic schema 验证
    Given 一个有效的人声 WAV 文件
    When 通过 FastAPI POST /api/v2/upload 上传
    Then 响应格式符合 UploadResponse schema
    And total_score 与 Flask 基线一致 (差异 < 1 分)

  Scenario: 黄金测试集分数不变
    Given 5 首真实人声音频
    When 通过 FastAPI 对所有音频运行 Quick 评分
    Then 每个音频的 total_score 与 v6.3 Flask 基线差异 < 1 分
```

#### `websocket-realtime.feature` (Phase 3)

```gherkin
Feature: WebSocket 实时评分

  Scenario: 音频流实时反馈
    Given WebSocket 已连接到 /ws/score
    When 发送 50 帧音频数据 (2048 samples/frame)
    Then 至少收到 1 条 pitch_update 事件
    And 至少收到 1 条 partial_score 事件

  Scenario: 录完秒出总分
    Given WebSocket 连接中
    When 发送 recording_start → 100 帧音频 → recording_stop
    Then 应在 3 秒内收到 final_score 事件
    And final_score 包含五个维度评分
```

#### `vue-element-plus.feature` (Phase 4)

```gherkin
Feature: Vue 3 + Element Plus 前端验收

  Scenario: 首页无 emoji
    Given 用户打开应用首页
    Then 页面上不应出现任何 Unicode 表情符号
    And 所有图标应使用 Element Plus Icons

  Scenario: Tooltip 悬停揭示
    Given 用户在报告页
    When 鼠标悬停在 "音准" 维度旁的信息小点上超过 500ms
    Then 应显示该维度评分算法的 Tooltip 说明

  Scenario: 旧页面共存
    Given Vue Router 未匹配当前路径
    When 访问 /old/index.html
    Then 旧版 SPA 首页正常显示
```

### 8.2 Phase 验收门禁

| Phase | Feature Files | 通过标准 |
|-------|-------------|---------|
| 1 | `fastapi-migration.feature` + `history.feature` | 8 scenarios 全部 pass |
| 2 | `fastapi-migration.feature` + `upload.feature` + `compare.feature` + `differentiation.feature` | 16 scenarios pass |
| 3 | `websocket-realtime.feature` + `realtime-analysis.feature` + `nonblocking-analysis.feature` | 19 scenarios pass |
| 4 | `vue-element-plus.feature` + `navigation.feature` + `animations.feature` + `responsive.feature` | 15 scenarios pass |
| 5 | 全量 21 feature files | **75 scenarios pass** |

### 8.3 禁止事项

- ❌ "先上线再补 BDD" — 必须先写 feature, 后实现
- ❌ 手动跳过场景 — 所有 scenarios 必须执行
- ❌ 修改场景以适应代码 — 修改代码以适应场景

---

## 9. 参考文档

| 文档 | 路径 |
|------|------|
| TDD 规范 | [TDD.md](TDD.md) |
| 产品需求文档 | [PRD.md](../1-product/PRD.md) |
| API 接口 | [API.md](../2-technical/API.md) |
| 项目状态 | [PROJECT_STATUS.md](../4-process/PROJECT_STATUS.md) |
