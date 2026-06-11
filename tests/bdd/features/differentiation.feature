Feature: 评分区分度验证
  As a 产品负责人
  I want to 确保评分能有效区分不同水平的演唱
  So that 用户获得的评分有参考价值

  Scenario: 专业演唱得分显著高于初学者
    Given 一个专业级演唱音频 "pro_singer.wav"
    And 一个初学者演唱音频 "beginner.wav"
    When 两个音频都用 quick 模式评估
    Then 专业级 total_score 应比初学者高至少 20 分

  Scenario: Quick 与 Pro 模式评分一致
    Given 同一个人声演唱音频 "vocals.wav"
    When 分别用 quick 和 professional 模式评估
    Then 两个模式的 total_score 差距应小于 10%
    And 各维度的评分趋势应相同

  Scenario: 各维度均有区分力
    Given 5 个不同水平的演唱音频
    When 全部用 quick 模式评估
    Then 每个维度的最高分与最低分差距应至少 3 分

  Scenario: 非人声全部归零
    Given 5 个合成或噪声音频文件
    When 全部用 quick 模式评估
    Then 每个音频的 total_score 应为 0.0

  # ── 风格切换鲁棒性 (v6.0) ──

  Scenario: 同一首歌用不同风格预设评分 — 有区分但不极端
    Given 一首流行歌曲的人声录音
    When 分别用 "流行" 和 "美声" 风格预设评估
    Then 两个预设的总分差距应在 5-15 分之间
    And "美声" 预设的气息评分应高于 "流行" 预设 (权重更高)
    And "流行" 预设的艺术评分应高于 "美声" 预设
    And 两个预设的音准绝对分值应接近 (音准测量与风格无关, 仅权重不同)
    And 结果中应标注 applied_preset 字段

  Scenario: 说唱歌曲用流行预设 — 自动检测并建议切换
    Given 一首说唱歌曲 (BPM=95, 语速快, 旋律少)
    When 默认使用 "流行" 预设评估
    Then 系统应检测到音频特征与流行风格不匹配
    And 应在结果中提示 "检测到说唱特征, 建议切换为说唱预设以获得更准确评分"
    And 不应强制切换 (用户可选择忽略)

  Scenario: 自定义权重后与默认权重对比
    Given 一首人声录音
    When 先用默认权重评估, 再用自定义权重 (Pitch+10%, Artistry-10%) 评估
    Then 两次评分的 total_score 差异应在合理范围 (≤ 15 分)
    And 自定义权重的 Pitch 维度分数影响应大于默认权重
    And 结果中应可对比两次评分的维度分数变化
