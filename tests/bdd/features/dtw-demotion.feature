Feature: DTW 降级为偏差提供者 — 对比评分唯一入口是 DDD
  As a 系统架构师
  I want DTW 只做精确对齐/偏差计算
  So that 对比评分统一走 DDD ComparisonScoringService (v7.19 E1 消双轨)

  Background:
    Given 服务已启动
    And 标准音频和用户音频均已上传

  # ═══════════════════════════════════════════════════════════
  # 一、v7.19 E1 架构 — DTW 纯偏差提供者
  # ═══════════════════════════════════════════════════════════

  Scenario: DTW 不再产出评分 — 只产出偏差数据
    Given 标准音频 "reference.wav" 和用户音频 "user.wav"
    When DTW 三级对齐完成
    Then ComparisonService 应输出以下偏差数据 (而非评分):
      | 字段               | 类型    | 说明                       |
      | avg_pitch_cents    | float   | 平均音分偏差 (对齐后)       |
      | max_pitch_cents    | float   | 最大音分偏差               |
      | avg_rhythm_ms      | float   | 平均节拍偏移 ms            |
      | avg_volume_percent | float   | 平均音量偏差 %             |
      | avg_breath_stability | float | 气息稳定性                |
    And 不应输出任何 score, level, suggestions, diagnosis 等评分字段
    And ComparisonService 不应持有 legacy scoring_engine 属性

  Scenario: DDD ComparisonScoringService 是唯一对比评分入口
    Given DTW 已产出偏差数据
    When 进入评分阶段
    Then DDD ComparisonScoringService 应承担对比评分 (legacy scoring_engine.py 已删)
    And 风格权重应单一来源自 COMPARISON_STYLE_WEIGHTS (value_objects)
    And 不应存在独立的 "DTW 评分路径" 或 legacy "对比评分引擎"

  Scenario: 对比建议复用 DDD AdviceGenerator
    Given 对比分析完成
    When 前端请求对比分析建议
    Then 建议应由 CompareAudioUseCase 复用 AdviceGenerator (四维子集) 生成
    And domain 层不应再存在 generate_suggestions 硬编码

  # ═══════════════════════════════════════════════════════════
  # 二、六维评估与对比评分解耦
  # ═══════════════════════════════════════════════════════════

  Scenario: 六维声乐评估不依赖 DTW
    Given 系统未匹配到标准歌曲 (无 DTW 数据)
    When 执行评分
    Then 所有六个维度应使用各自的独立评分逻辑 (pitch/rhythm/breath/technique/muscle/artistry)

  Scenario: 节奏评分 — 无参考时使用 CV 估算 (现有逻辑不变)
    Given 无 DTW 数据 (绝对评分场景)
    When rhythm_scorer 计算节奏分数
    Then 应使用现有的 onset + CV 路径 (行为与绝对评分一致)
    And 不应调用任何 DTW 相关逻辑

  # ═══════════════════════════════════════════════════════════
  # 三、E1 架构不变量 — legacy 引擎已删除
  # ═══════════════════════════════════════════════════════════

  Scenario: scoring_engine.py 应已删除
    Given DTW 降级重构完成
    When Code Review 检查 services/comparison/scoring_engine.py
    Then legacy scoring_engine.py 文件应不存在 (评分统一走 DDD)
    And services/comparison/ 中不应出现 score 或 rating 相关的计算逻辑
    And services/comparison/ 应只有: 偏差数据计算 + 对齐路径生成 + 置信度评估
