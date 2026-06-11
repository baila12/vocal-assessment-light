Feature: 有参考时的完整多维度分析 — DTW 是补充, 五维是主体
  As a 声乐学生
  I want to 在有标准音频对比时, 仍然获得完整的五维评分而不仅是 DTW 分数
  So that 我既知道跟原唱的差距, 也知道自己在每个维度的绝对水平

  Background:
    Given Flask 服务已启动
    And 标准曲库中已有预提取特征的歌曲

  # ═══════════════════════════════════════════════════════════
  # 一、核心理念: DTW 辅助, 五维为主
  # ═══════════════════════════════════════════════════════════

  Scenario: 有参考时的完整评分结构
    Given 系统已匹配到标准歌曲 "月亮代表我的心"
    And 用户上传了同歌曲的翻唱
    When 分析完成
    Then 评分结果应包含两套互补数据:

      # 主体: 绝对五维评分 (与无参考时完全相同的维度)
      | 字段              | 说明                                   |
      | total_score       | 综合评分 (五维加权)                     |
      | scores.pitch      | 音准评分 (基于绝对音分偏差)             |
      | scores.rhythm     | 节奏评分 (基于onset偏差)                |
      | scores.breath     | 气息评分 (四子维度)                     |
      | scores.technique  | 技术评分 (HNR/CPP/技巧)                 |
      | scores.artistry   | 艺术评分 (四维度复合)                   |
      | voice_quality     | 人声质量检测                            |
      | advice            | 基于五维弱点的改进建议                  |

      # 补充: DTW 对比指标 (仅在匹配到参考时存在)
      | 字段                     | 说明                         |
      | dtw_score                | DTW 相对评分 (0-100)         |
      | dtw_pitch_match_rate     | 音准帧匹配率 (%)              |
      | dtw_rhythm_match_rate    | 节奏帧匹配率 (%)              |
      | dtw_alignment_confidence | 对齐置信度                    |
      | dtw_problem_segments     | 偏差最大的段落 (Top 5)       |
      | matched_song             | { id, title, artist }       |

    And total_score 的计算公式应明确标注在结果中
    And DTW 指标作为 "与原唱的差距" 独立展示, 不混入五维总分

  Scenario: 五维评分与 DTW 评分的分工
    Given 一位音准极好但节奏完全不对的演唱者
    When 评估完成
    Then 绝对五维评分应如实反映:
      | pitch: 90+ | rhythm: 20 | breath: 60 | technique: 70 | artistry: 50 |
    And DTW 对比评分应反映与原唱的综合差异:
      | dtw_score: 55 | dtw_pitch_match: 95% | dtw_rhythm_match: 5% |
    And 用户看到的诊断应为: "你的音准很棒(≥原唱), 但节奏完全没跟上, 建议练习节拍感"
    And 不应出现 DTW 分数 "覆盖" 或 "稀释" 绝对五维评分的情况

  Scenario: DTW 置信度低时以五维评分为准
    Given DTW 对齐的某些段落置信度 < 0.5
    When 评估完成
    Then total_score 应完全基于五维绝对评分 (不受 DTW 影响)
    And dtw_score 旁应标注 "⚠️ 部分段落对齐不确定, DTW分数仅供参考"
    And dtw_problem_segments 应排除低置信度段落
    And 最终建议应以五维弱项为主, DTW 偏差为辅

  # ═══════════════════════════════════════════════════════════
  # 二、配置文件驱动的权重系统
  # ═══════════════════════════════════════════════════════════

  Scenario: 配置文件的层次结构
    Given 评分系统加载配置
    When 解析权重参数
    Then 应按以下优先级 (高→低):
      | 优先级 | 来源                        | 说明                         |
      | 1      | 用户请求中指定的权重         | 对比分析/录入歌曲时手动设置    |
      | 2      | 歌曲关联的权重 (曲库中存储)  | 录入标准歌曲时保存的参数       |
      | 3      | 用户本地自定义预设           | "我的预设" JSON文件           |
      | 4      | 风格预设 (config文件)        | 流行/美声/民族/说唱默认值     |
      | 5      | 硬编码安全默认值             | 所有上层失效时的兜底           |
    And 实际使用的配置应在评分结果中记录 (applied_config 字段)
    And 记录应包括每项参数的来源 (source: "user_override" | "song_default" | "style_preset" | "fallback")

  Scenario: 配置热加载 — 修改配置文件不需重启
    Given 我修改了 config/styles.yaml 中美声的 Artistry 权重从 10% 到 15%
    When 配置文件保存后
    Then 系统应在 5 秒内检测到变化并重新加载 (文件监控)
    And /health 端点应返回 config_version: <新hash>
    And 下一个分析请求应使用新权重
    And 正在进行的分析不受影响 (使用变更前的配置)

  Scenario: 配置版本追踪
    Given 系统每次评分使用特定的配置快照
    When 评分结果保存到历史记录
    Then 应记录 config_fingerprint: { preset: "美声", version: "abc123", overrides: {pitch: 30} }
    And 将来即使配置文件修改, 历史记录仍可追溯到当时的配置
    And 重新计算历史分数时可选择 "使用当前配置" 或 "使用历史配置"

  # ═══════════════════════════════════════════════════════════
  # 三、边界条件
  # ═══════════════════════════════════════════════════════════

  Scenario: 五维评分与 DTW 分数矛盾时的诊断
    Given 五维评分 total=85 (优秀), 但 DTW score=40 (与原唱差异大)
    When 我查看分析结果
    Then 系统应在建议中解释:
      | "你的演唱技巧和音准都不错 (五维 85 分)"                         |
      | "但与原唱的风格差异较大 (DTW 40 分)"                            |
      | "可能原因: 你用了不同的演唱风格/调性/节奏处理"                    |
      | "DTW 低分不一定代表唱得差, 可能是风格差异 (如爵士翻唱流行)"       |
    And 不应简单地显示 "你唱得很差" (因为五维分数表明不差)

  Scenario: 无参考时 — 评分结构不变
    Given 系统未匹配到标准歌曲
    When 评估完成
    Then 评分结果应与有参考时的 "主体部分" 完全一致
    And dtw_* 字段应为 null (不是 0, 因为 0 表示 "完全不一致")
    And 前端不应显示 DTW 相关卡片
    And 五维总分和建议正常展示

  Scenario: 用户上传了多段同一首歌的录音 — 权重一致性
    Given 我上周用自定义权重 (Pitch=35%) 录了 "月亮代表我的心"
    And 我这周又录了一次同一首歌
    When 新录音分析完成
    Then 系统应检测到同歌曲历史记录
    And 提示 "上次使用了自定义权重 (Pitch=35%), 是否沿用?"
    And 沿用后两次评分的权重基准一致 → 分数可直接对比
    And 拒绝沿用 → 使用当前默认权重 → 两次分数不完全可比 (会标注)
