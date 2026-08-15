Feature: 上传音频自动匹配标准歌曲
  As a 声乐学生
  I want to 上传演唱录音后系统自动找到对应的标准版本
  So that 我的评分基于与标准演唱的对比，而不只是绝对指标

  Background:
    Given 服务已启动
    And 标准曲库中已有至少 20 首特征已提取的歌曲

  # ── 核心匹配流程 ──

  Scenario: 上传翻唱自动匹配到原唱
    Given 曲库中有标准歌曲 "月亮代表我的心 - 邓丽君" (BPM=78, Key=C)
    And 我录制了一段同歌曲的演唱 (BPM≈80, Key=C, 时长约为原唱的 0.9 倍)
    When 我上传该音频到评估接口
    Then 系统应在 5 秒内完成特征提取和数据库匹配
    And 匹配结果应命中 "月亮代表我的心 - 邓丽君" (置信度 ≥ 0.7)
    And 返回结果应包含 matched_song 字段: { id, title, artist, confidence }
    And 评分模式应自动切换为 DTW 对比模式
    And DTW 对比应使用命中的标准歌曲作为参考音频

  Scenario: 匹配算法对速度变化鲁棒
    Given 曲库中 "月亮代表我的心" 原唱 BPM=78
    And 用户翻唱版本 BPM=85 (比原唱快 ~9%)
    When 我上传该翻唱音频
    Then 系统仍应匹配到 "月亮代表我的心"
    And 匹配置信度不应因速度差异显著下降 (≥ 0.6)

  Scenario: 匹配算法对调性变化鲁棒
    Given 曲库中 "月亮代表我的心" 原唱为 C Major
    And 用户翻唱版本升调至 D Major (+2 半音)
    When 我上传该翻唱音频
    Then 系统仍应匹配到 "月亮代表我的心"
    And 返回的 matched_song 中应标注 detected_key 和 original_key 的差异

  # ── 多候选排序 ──

  Scenario: 匹配到多个候选时选最高置信度
    Given 曲库中有 "月亮代表我的心 - 邓丽君" 和 "月亮代表我的心 - 齐秦"
    And 用户演唱版本更接近邓丽君版 (调性、BPM、编曲)
    When 我上传该音频
    Then 应返回匹配列表 (Top 3)
    And 第一名应为 "邓丽君版" (置信度最高)
    And 返回的 candidates 字段包含每个候选的置信度和差异维度

  Scenario: 无匹配时回退绝对评分
    Given 曲库中没有任何与用户演唱相似的歌曲
    And 用户上传了一首曲库中不存在的原创歌曲
    When 我上传该音频
    Then 匹配结果中 matched_song 应为 null
    And confidence 应为 0.0
    And 评分模式应回退为 absolute (绝对评分)
    And 返回的 fallback_reason 应为 "no_match"
    And 评分功能应正常工作 (五维绝对评分)

  # ── 匹配质量保障 ──

  Scenario: 短音频匹配容错
    Given 用户仅录制了副歌片段 (30 秒)
    And 曲库中完整原唱为 3 分 30 秒
    When 我上传该片段
    Then 系统应尝试在完整原唱中定位匹配段落
    And 若段落定位成功 → 返回 matched_song + matched_segment (起始时间, 结束时间)
    And 若段落过短无法匹配 → 回退绝对评分

  Scenario: 嘈杂环境录音仍可匹配
    Given 用户的录音包含轻度背景噪音 (信噪比 ~15dB)
    When 我上传该音频
    Then 系统应先执行降噪预处理
    And 降噪后的特征用于数据库匹配
    And 匹配置信度不应因轻度噪音显著下降 (下降 < 0.1)

  Scenario: 匹配超时保护
    Given 曲库中歌曲数量较大 (100+ 首)
    When 我上传音频触发匹配
    Then 特征匹配阶段应在 10 秒内完成
    And 若超时, 返回 partial_match (仅匹配已扫描的 Top-K)
    And 不应阻塞整体评分流程
