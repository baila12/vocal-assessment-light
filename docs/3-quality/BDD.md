# 行为驱动开发 (BDD) 规范 v7.11

> 更新: 2026-08-04 | 16 step files | 21 feature files (15 已实现 + 6 规划中) | scoring-config.feature v7.11: 6 维契约更新, API 级 PASS (预设/校验/超50%拒绝), 阈值联动+UI 级 XFAIL | 浏览器基建 v7.11 已修 (base_url→:8000 + `window.__store` 钩子) | upload.feature 38 场景因 `vocals.wav` 测试数据缺失预存失败

---

## 1. BDD 三层结构

```
┌──────────────────────────────────────────────┐
│  Feature 文件 (.feature)                      │
│  Gherkin 场景: Given → When → Then             │
│  受众: 开发者 + 产品                           │
└──────────────────┬───────────────────────────┘
                   │
┌──────────────────▼───────────────────────────┐
│  Step Definitions (.py)                       │
│  @given / @when / @then 映射到 Python 代码     │
│  受众: 开发者                                  │
└──────────────────┬───────────────────────────┘
                   │
┌──────────────────▼───────────────────────────┐
│  Fixtures (conftest.py)                       │
│  pytest fixtures: api_client (Flask 兼容旧步) + │
│  fastapi_client (v7 API) + test data          │
└──────────────────────────────────────────────┘
```

### BDD vs TDD

| 维度 | TDD | BDD |
|------|-----|-----|
| 受众 | 开发者 | 开发者 + 产品 |
| 粒度 | 函数/类级别 | 功能/场景级别 |
| 语言 | `assert score >= 95.0` | `Given 一个人声文件 When 上传 Then 获得评分` |
| 关注点 | 代码正确性 | 业务行为正确性 |
| 工具 | pytest | pytest-bdd |

---

## 2. 目录结构 (v7.11 实际)

```
tests/bdd/
├── features/                         # Gherkin .feature 文件 (21 个)
│   │
│   │  === 已实现 (有 Step Defs, 15 个) ===
│   ├── upload.feature                # 上传与六维评分
│   ├── compare.feature               # DTW 对比分析
│   ├── differentiation.feature       # 评分区分度验证
│   ├── history.feature               # 历史记录管理
│   ├── navigation.feature            # SPA 路由导航
│   ├── compare-ui.feature            # 对比 UI 交互
│   ├── mode-select.feature           # 模式选择
│   ├── sing-song-select.feature      # 演唱选歌
│   ├── song-library.feature          # 标准曲库 (v7.10 前端已按契约实现 UI 选择器)
│   ├── animations.feature            # GSAP 动画 (v7.3.1, ⚠️ 旧架构)
│   ├── offline.feature               # 离线/本地库 (v7.3.1)
│   ├── responsive.feature            # 响应式布局 (v7.3.1)
│   ├── dtw-demotion.feature          # v7.8: DTW 降级为特征提供者 (18 scenarios)
│   ├── scoring-config.feature        # v7.8: 评分配置可定制 (14 scenarios)
│   └── database.feature              # 🆕 v7.9: 标准歌曲数据库 (10 scenarios, 4P+6XF)
│   │
│   │  === 规划中 (无 Step Defs, 6 个) ===
│   ├── auto-match.feature            # 上传自动匹配
│   ├── song-select.feature           # 选歌录音完整流程
│   ├── nonblocking-analysis.feature  # 非阻塞分析 (SSE)
│   ├── pitch-realtime.feature        # 实时音准对比
│   ├── realtime-analysis.feature     # 录音实时后台分析
│   └── multi-dim-analysis.feature    # 多维度对比分析
│
├── steps/                            # Step 实现 (16 files)
│   ├── test_upload_steps.py          # 上传 + 评分
│   ├── test_compare_steps.py         # DTW 对比
│   ├── test_compare_ui_steps.py      # 对比 UI
│   ├── test_differentiation_steps.py # 评分区分度
│   ├── test_history_steps.py         # 历史记录
│   ├── test_mode_select_steps.py     # 模式选择
│   ├── test_navigation_steps.py      # SPA 导航
│   ├── test_sing_song_select_steps.py # 演唱选歌
│   ├── test_song_library_steps.py    # 曲库管理
│   ├── test_spa_steps.py             # SPA 通用步骤
│   ├── test_animations_steps.py      # v7.3.1: 16 GSAP scenarios (⚠️ 旧架构)
│   ├── test_offline_steps.py         # v7.3.1: 5 offline scenarios
│   ├── test_responsive_steps.py      # v7.3.1: 8 responsive scenarios
│   ├── test_dtw_demotion_steps.py    # v7.8: 18 DTW scenarios
│   ├── test_scoring_config_steps.py  # v7.8: 14 评分配置 scenarios
│   └── test_database_steps.py        # 🆕 v7.9: 10 歌曲库 scenarios (4PASS+6XFALL)
│
├── conftest.py                       # BDD fixtures + Playwright
└── __init__.py
```

---

## 3. Feature 示例

### upload.feature

```gherkin
Feature: 音频上传与六维评分

  Scenario: Quick 模式快速评分
    Given 一个包含人声演唱的 WAV 文件
    When 我上传该文件并选择 "quick" 模式
    Then 响应状态码应为 200
    And 响应时间应小于 30 秒
    And 返回的 total_score 应在 0 到 100 之间
    And 应返回六个维度评分: pitch, rhythm, breath, technique, muscle_strength, artistry

  Scenario: 非人声音频拦截
    Given 一个白噪声 WAV 文件
    When 我上传该文件进行评估
    Then 返回的 is_voice 应为 false
    And 返回的 total_score 应为 0.0

  Scenario: 多格式音频支持
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
```

### differentiation.feature

```gherkin
Feature: 评分区分度验证

  Scenario: 专业演唱得分显著高于初学者
    Given 一个专业级演唱音频
    And 一个初学者演唱音频
    When 两个音频都用 quick 模式评估
    Then 专业级 total_score 应比初学者高至少 12 分

  Scenario: Quick 与 Pro 模式评分一致
    Given 同一个人声演唱音频
    When 分别用 quick 和 professional 模式评估
    Then 两个模式的 total_score 差距应小于 10%
```

---

## 4. Step Definitions 结构

```python
# tests/bdd/steps/test_upload_steps.py
from pytest_bdd import given, when, then, parsers, scenarios

scenarios('../features/upload.feature')


@given('一个包含人声演唱的 WAV 文件')
def vocal_wav_file(test_data_dir):
    path = test_data_dir / 'audio' / 'vocal' / 'vocals.wav'
    assert path.exists()
    return path


@when(parsers.parse('我上传该文件并选择 "{mode}" 模式'))
def upload_with_mode(request, api_client, mode):
    file_path = request.getfixturevalue('vocal_wav_file')
    with open(file_path, 'rb') as f:
        response = api_client.post(
            '/api/upload',
            data={'file': (f, file_path.name), 'mode': mode},
            content_type='multipart/form-data'
        )
    return response


@then('响应状态码应为 200')
def check_status_200(upload_with_mode):
    assert upload_with_mode.status_code == 200


@then('返回的 total_score 应在 0 到 100 之间')
def check_total_score_range(upload_with_mode):
    data = upload_with_mode.get_json()
    score = data.get('total_score')
    assert 0 <= score <= 100
```

---

## 5. 版本演进: Step Defs 新增记录

### v7.3.1

| 文件 | Scenarios | 内容 |
|------|:--:|------|
| `test_animations_steps.py` | 16 | GSAP 动画验收 (67 step defs) |
| `test_offline_steps.py` | 5 | 离线/本地库加载 (19 step defs) |
| `test_responsive_steps.py` | 8 | 响应式布局验收 (33 step defs) |
| **合计** | **29** | **119 step defs** |

### v7.8

| 文件 | Scenarios | 内容 |
|------|:--:|------|
| `test_dtw_demotion_steps.py` | 18 | DTW 降级为特征提供者 |
| `test_scoring_config_steps.py` | 14 | 评分配置可定制 |
| **合计** | **32** | |

### v7.9

| 文件 | Scenarios | 内容 |
|------|:--:|------|
| `test_database_steps.py` | 10 | 标准歌曲数据库 (4 PASSED + 6 XFAIL) |

标记: v7.3.1 animations/offline/responsive scenarios 使用 `@pytest.mark.browser` (需要 Playwright)

---

## 6. 运行命令

```bash
# API 级 BDD (不需要浏览器)
pytest tests/bdd/ -v -m "not browser"

# 浏览器 BDD (需要 Playwright)
pytest tests/bdd/ -v -m "browser"

# 运行特定 feature
pytest tests/bdd/ -v -k "upload"
pytest tests/bdd/ -v -k "compare"

# 全量 BDD
pytest tests/bdd/ -v
```

---

## 7. BDD 验收流程

```
需求评审 → 编写 .feature → 实现 Step Defs (RED)
                │
                ▼
         开发功能实现 → 运行 (GREEN)
                │
                ▼
         PR 合并 ← 全量回归通过
```

### 场景设计原则

- **独立性**: 每个 Scenario 可独立运行
- **业务语言**: 用业务术语 (说"上传音频"不说"POST form-data")
- **一个行为**: 一个 Scenario 验证一个用户行为
- **可追溯**: 场景描述追溯到 PRD 用户场景

---

## 8. 参考

| 文档 | 路径 |
|------|------|
| TDD 规范 | [TDD.md](TDD.md) |
| 产品需求 | [PRD.md](../1-product/PRD.md) |
| API 文档 | [API_CONTRACT.md](../2-technical/API_CONTRACT.md) |
| 项目状态 | [PROJECT_STATUS.md](../4-process/PROJECT_STATUS.md) |
