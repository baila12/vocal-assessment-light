# ═══════════════════════════════════════════════════════════════════════
# v7.14 状态: 本 feature 已标记【延期】, 非当前回归范围。
# 原因 (见 docs/4-process/PROJECT_STATUS.md):
#   1. 端点过时: /api/compare, /api/upload → 现为 /api/v1/* 前缀
#   2. 步骤过时: Flask-era content_type= / .get_json() → httpx TestClient
#      files= / .json(); @given 返回值不再注册为 fixture (pytest-bdd 8)
#   3. DTW 融合语义过时: 本 feature 假设 5 维 + 逐段置信度 + 双曲线叠加,
#      当前实现返回 dtw_dims {pitch_diff/rhythm_diff/total_diff}, 需业务确认
#      融合语义后重写 (当前 12 个场景全部因端点/API 错配失败, 非功能回归)。
# 对应 steps: tests/bdd/steps/test_compare_steps.py (同批过期)。
# ═══════════════════════════════════════════════════════════════════════

Feature: DTW 对比分析 — DTW 作为特征提供者, ScoreServiceV4 统一评分
  As a 声乐学生
  I want to 将我的演唱与标准版本对比
  So that 获得基于正确测量方法的五维评分 + DTW 精确偏差数据

  Background:
    Given Flask 服务已启动

  # ═══════════════════════════════════════════════════════════
  # 一、DTW 角色: 偏差数据提供者, 不打分
  # ═══════════════════════════════════════════════════════════

  Scenario: /api/compare 返回五维评分 + DTW 偏差数据
    Given 标准音频 "reference.wav" 和用户音频 "user.wav"
    When 我发起对比分析
    Then 返回结构应与 /api/upload 一致 (五维评分):
      | total_score, scores{pitch,rhythm,breath,technique,artistry} |
      | level, stars, advice, critical_issues                       |
    And 额外返回 DTW 元数据 (非评分):
      | dtw_metadata.alignment_confidence | 对齐置信度            |
      | dtw_metadata.dtw_weight_used      | 实际使用的 DTW 权重    |
      | dtw_deviation.pitch_summary       | 音准偏差摘要 (均值/最大) |
      | dtw_deviation.rhythm_summary      | 节奏偏差摘要           |
    And 不应返回独立的 dtw_score (DTW 不产出评分)

  Scenario: 相同音频 — 五维得满分, DTW 偏差为零
    Given 我上传两个完全相同的音频文件
    When DTW 对齐完成
    Then dtw_pitch_cents 应全部接近 0 (|偏差| < 5 音分)
    And dtw_rhythm_offset 应全部接近 0 (|偏移| < 10ms)
    And alignment_confidence 应接近 1.0
    And pitch_scorer 融合后 pitch_score ≥ 95
    And rhythm_scorer 融合后 rhythm_score ≥ 95
    And breath/technique/artistry 独立评分正常产出

  Scenario: 音准偏差精确检测
    Given 标准音频 "reference.wav"
    And 用户在特定段落音高偏移 50 音分的音频
    When 对比分析完成
    Then dtw_pitch_cents 应在偏移段落显示 ~50 音分偏差
    And pitch_scorer 融合后 pitch_score < 90
    And 返回结果包含 problem_segments (标注偏移段落)
    And breath/technique/artistry 评分不受此音准偏移影响

  # ═══════════════════════════════════════════════════════════
  # 二、各维度 DTW 参与程度
  # ═══════════════════════════════════════════════════════════

  Scenario: 音准 — PYIN + DTW 加权融合
    Given alignment_confidence = 0.9
    When pitch_scorer 计算
    Then dtw_weight = 0.9 × 0.70 = 0.63
    And pitch_final = pitch_pyin × 0.37 + pitch_dtw × 0.63
    And DTW 权重上限 70% (即使置信度=1.0)

  Scenario: 节奏 — Onset + DTW 加权融合
    Given alignment_confidence = 0.9
    When rhythm_scorer 计算
    Then dtw_weight = 0.9 × 0.50 = 0.45
    And rhythm_final = rhythm_onset × 0.55 + rhythm_dtw × 0.45
    And DTW 权重上限 50%
    And 有 DTW 时跳过 CV 估算 + irregularity 惩罚

  Scenario: 气息/技术/艺术 — DTW 完全忽略
    When breath_scorer 计算
    Then 应使用四子维度独立评估 (RMS/HNR/CPP/长音)
    When technique_scorer 计算
    Then 应使用声学特征独立评估 (HNR/CPP/颤音/滑音)
    When artistry_scorer 计算
    Then 应使用四维度复合评分
    And 三个维度均不接收 DTW 数据

  # ═══════════════════════════════════════════════════════════
  # 三、置信度动态加权
  # ═══════════════════════════════════════════════════════════

  Scenario: 高置信度 — DTW 权重接近上限
    Given alignment_confidence = 0.95 (演唱与原唱高度一致)
    Then pitch dtw_weight = 0.95 × 0.70 = 0.665
    And rhythm dtw_weight = 0.95 × 0.50 = 0.475
    And DTW 数据被充分信任

  Scenario: 低置信度 — DTW 自动退出
    Given alignment_confidence = 0.25 (用户即兴改动大)
    Then confidence < 0.3 → pitch dtw_weight = 0.0
    And rhythm dtw_weight = 0.0
    And 评分完全回退到独立评分
    And dtw_metadata.status = "insufficient_confidence"

  Scenario: 逐段置信度 — 不同段落不同权重
    Given 副歌对齐好 (confidence=0.9), 即兴段落对齐差 (confidence=0.2)
    Then 副歌段: pitch_dtw_weight = 0.63, rhythm_dtw_weight = 0.45
    And 即兴段: pitch_dtw_weight = 0, rhythm_dtw_weight = 0
    And 评分应按段分别计算后加权平均

  # ═══════════════════════════════════════════════════════════
  # 四、对比分析 — 评分权重可配置
  # ═══════════════════════════════════════════════════════════

  Scenario: 对比分析时可自定义五维权重
    Given 标准音频和用户音频已上传
    When 我展开 "评分参数" 面板
    Then 应显示风格选择器 + 五维权重滑块
    And 默认加载标准音频关联的风格预设
    And 修改后点击 "应用并分析"
    And 返回结果标注 applied_config

  Scenario: 系统推荐权重
    Given 标准音频特征已分析
    When 我点击 "系统推荐"
    Then 应返回推荐权重 + 逐维度调整理由
    And 推荐权重可一键应用或微调

  # ═══════════════════════════════════════════════════════════
  # 五、回放 — 实时音准叠加
  # ═══════════════════════════════════════════════════════════

  Scenario: DTW 对齐后 — 双曲线叠加 + 偏差热力图
    Given 对比分析完成
    When 我切换到 "音准叠加" 视图并播放
    Then 应显示 DTW 对齐后的双曲线 (标准虚线 + 用户着色实线)
    And 偏差色带填充 + 底部热力图
    And 低置信度段落标记 ⚠️
    And 点击热力图跳转播放位置
