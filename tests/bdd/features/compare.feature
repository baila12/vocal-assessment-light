# ═══════════════════════════════════════════════════════════════════════
# v7.14 P2 轮 (2026-08-11): 本 feature 由【延期】重写为【可用】。
# 重写原因: 原 12 场景全部因 Flask 遗留 (Background "Flask 服务已启动" /
# .get_json() / /api/compare 前缀 / DTW 融合假想架构) 失败, 非功能回归。
# 实际契约 (v7.13 P5): POST /api/v1/compare → {success, data:{score, level,
# confidence, pitch_match_rate, rhythm_match_rate, avg_cents_error, diagnosis,
# suggestions, dimensions, method, standard, user, comparison, standard_pitch,
# user_pitch, low_alignment_segments}}。
# 未实现的 DTW 融合架构目标 (逐段置信度加权 / DTW 权重上限 / UI 权重面板 /
# 双曲线叠加 UI) 的文档与 xfail 场景见 dtw-demotion.feature, 本 feature 不重复。
# 对应 steps: tests/bdd/steps/test_compare_steps.py (重写, 显式 state + .json()).
# ═══════════════════════════════════════════════════════════════════════

Feature: DTW 对比分析 — 双音频对比契约 (v7.13 P5)
  As a 声乐学生
  I want to 将我的演唱与标准版本对比
  So that 获得 DTW 对齐差异 + 双轨音高曲线 + 低对齐段落提示

  Scenario: /api/v1/compare 返回 DTW 对比核心字段 (真实契约)
    Given 标准音频 "恋人（高分）.mp3" 和用户音频 "手写的从前（高分）.mp3"
    When 我发起对比分析请求
    Then 返回结构应包含 DTW 对比核心字段
    And 应包含双轨音高曲线数据
    And 应包含对比差异摘要
    And 应包含低对齐置信度段落字段

  Scenario: 相同音频 — DTW 对齐接近完美
    Given 同一个音频文件作为标准与用户上传
    When 我发起对比分析请求
    Then 对比总分应接近满分
    And 音准匹配率应不低于 95%
    And 节奏匹配率应不低于 95%
    And 对齐置信度应接近 1.0

  Scenario: 音准偏差精确检测 (需预生成移调音频, 未实现 fixture)
    Given 用户在特定段落音高偏移 50 音分的音频
