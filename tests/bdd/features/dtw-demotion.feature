Feature: DTW 降级为特征提供者 — 不再打分, 只产出偏差数据
  As a 系统架构师
  I want to DTW 回归其擅长的角色 (精确对齐工具)
  So that 每个评分维度使用正确的测量方法, 而不是用 DTW 越界打分

  Background:
    Given Flask 服务已启动
    And 标准音频和用户音频均已上传

  # ═══════════════════════════════════════════════════════════
  # 一、架构变更 — DTW 角色重新定义
  # ═══════════════════════════════════════════════════════════

  Scenario: DTW 不再产出评分 — 只产出偏差数据
    Given 标准音频 "reference.wav" 和用户音频 "user.wav"
    When DTW 三级对齐完成
    Then scoring_engine.py 应输出以下偏差数据 (而非评分):
      | 字段                 | 类型     | 说明                         |
      | dtw_pitch_cents      | float[]  | 逐帧音分偏差 (对齐后)         |
      | dtw_rhythm_offset    | float[]  | 逐帧节拍偏移 (ms, 对齐后)     |
      | dtw_warp_path        | int[][]  | 对齐路径 (标准帧→用户帧)      |
      | alignment_confidence | float    | 全局对齐置信度 (0-1)          |
      | segment_confidences  | float[]  | 逐段对齐置信度                 |
    And 不应输出任何 dtw_score, dtw_pitch_score, dtw_breath_score 等评分字段
    And 不应输出 dtw_volume, dtw_energy 等能量相关字段 (不相关)

  Scenario: ScoreServiceV4 是唯一评分入口
    Given DTW 已产出偏差数据
    When 进入评分阶段
    Then ScoreServiceV4.calculate() 应接收 DTW 偏差数据作为可选参数
    And 应调用全部五个维度评分器 (无一跳过):
      | pitch_scorer      | ← dtw_pitch_cents      |
      | rhythm_scorer     | ← dtw_rhythm_offset    |
      | breath_scorer     | ← 无 DTW 输入           |
      | technique_scorer  | ← 无 DTW 输入           |
      | artistry_scorer   | ← 无 DTW 输入           |
      | critical_rules    | ← 无 DTW 输入           |
    And 不应存在独立的 "DTW 评分路径" 或 "对比评分路径"
    And 有参考和无参考走完全相同的 ScoreServiceV4 入口
    And 区别仅在于 pitch_scorer 和 rhythm_scorer 是否收到 DTW 数据

  # ═══════════════════════════════════════════════════════════
  # 二、各维度融合策略 — DTW 参与的 AND 不参与的
  # ═══════════════════════════════════════════════════════════

  Scenario: 音准评分 — PYIN 绝对 + DTW 相对 加权融合
    Given DTW 产出 dtw_pitch_cents (逐帧音分偏差)
    And PYIN 产出绝对音分偏差 (pitch_deviation_result)
    When pitch_scorer 计算音准分数
    Then 应使用加权融合公式:
      """
      pitch_final = pitch_pyin × (1 - dtw_weight) + pitch_dtw × dtw_weight
      dtw_weight = alignment_confidence × 0.70
      """
    And DTW 权重上限为 70% (即使置信度=1.0)
    And PYIN 始终保有至少 30% 权重 (保证绝对音准不被 DTW 完全覆盖)
    And 融合后的分数应记录:
      | pitch_pyin_score  | 纯 PYIN 评分            |
      | pitch_dtw_score   | 纯 DTW 偏差评分          |
      | pitch_final_score | 融合后评分                |
      | dtw_weight_used   | 实际使用的 DTW 权重       |

  Scenario: 音准 — DTW 置信度低时自动退出
    Given DTW alignment_confidence = 0.4 (即兴改动大, 对齐困难)
    When pitch_scorer 计算音准分数
    Then dtw_weight = 0.4 × 0.70 = 0.28
    And pitch_final = pitch_pyin × 0.72 + pitch_dtw × 0.28
    And PYIN 占主导 (72%), DTW 只做微弱参考
    And confidence < 0.3 时 dtw_weight = 0 → 纯 PYIN 评分

  Scenario: 节奏评分 — Onset 分析 + DTW 偏移 替代 CV 估算
    Given DTW 产出 dtw_rhythm_offset (逐帧节拍偏移 ms)
    And rhythm analyzer 产出 onset 偏差数据
    When rhythm_scorer 计算节奏分数
    Then 应使用融合公式:
      """
      rhythm_final = rhythm_onset × (1 - dtw_weight) + rhythm_dtw × dtw_weight
      dtw_weight = alignment_confidence × 0.50
      """
    And DTW 权重上限为 50% (节奏上 onset 分析是主体)
    And 有 DTW 偏移时, 跳过 CV 估算路径 (CV 用于无参考场景)
    And 有 DTW 时 rhythm_scorer 不应用 irregularity 惩罚 (已有精确偏移数据)
    And 结果记录: rhythm_onset_score, rhythm_dtw_score, rhythm_final_score

  Scenario: 节奏 — 无 DTW 时使用 CV 估算 (现有逻辑不变)
    Given 无 DTW 数据 (绝对评分场景)
    When rhythm_scorer 计算节奏分数
    Then 应使用现有的 onset + CV 路径 (行为与 v5.17 完全一致)
    And 不应调用任何 DTW 相关逻辑
    And 评分结果中 dtw_weight_used = 0.0

  Scenario: 气息评分 — DTW 完全不参与
    Given DTW 产出了偏差数据
    When breath_scorer 计算气息分数
    Then 应完全使用四子维度评估 (与无参考时完全一致):
      | 长音支撑 (40%)  | RMS + 基频稳定性 → 独立评估          |
      | 动态控制 (25%)  | 弱唱质量 + 渐强渐弱 → 独立评估        |
      | 气口设计 (20%)  | 换气点质量 + 乐句连贯性 → 独立评估     |
      | 气声技巧 (15%)  | 风格适配 HNR 区间 → 独立评估          |
    And 不应接收任何 DTW 数据
    And 不应比较 "能量包络与标准像不像" (那是 DTW 越界打分)
    And 用户即兴处理不应影响气息评分

  Scenario: 技术评分 — DTW 完全不参与
    Given DTW 产出了偏差数据
    When technique_scorer 计算技术分数
    Then 应完全使用声学特征评估:
      | HNR 质量 + CPP 质量 + 颤音检测 + 滑音检测 + 假声识别 |
    And 不应接收任何 DTW 数据
    And 技巧评分不受用户是否 "跟原唱一致" 影响

  Scenario: 艺术评分 — DTW 完全不参与
    Given DTW 产出了偏差数据
    When artistry_scorer 计算艺术分数
    Then 应完全使用四维度复合评分 (Pitch×0.2 + Rhythm×0.25 + Breath×0.2 + Tech×0.35)
    And 加上声学调制因子
    And 不应接收任何 DTW 数据

  Scenario: 关键规则 — DTW 不参与, 全局生效
    Given DTW 产出了偏差数据
    When critical_rules 执行检查
    Then 应检查以下规则 (与 DTW 无关):
      | 连续跑调 > 3 秒 (基于 PYIN, 非 DTW)                  |
      | 气息断层 > 3 处 (基于 RMS 稳定性, 非 DTW)             |
      | 节奏完全脱离 > 5 秒 (基于 onset, 非 DTW)              |
    And 规则触发时的惩罚在 total_score 计算中统一扣除
    And 规则应在有参考和无参考场景下行为一致

  # ═══════════════════════════════════════════════════════════
  # 三、对比分析端点 — 调用 ScoreServiceV4
  # ═══════════════════════════════════════════════════════════

  Scenario: /api/compare 端点不再返回 DTW 独立评分
    Given 标准音频和用户音频已上传到 /api/compare
    When 对比分析完成
    Then 返回的评分结构应与 /api/upload 完全一致:
      | total_score, scores{pitch,rhythm,breath,technique,artistry} |
      | level, stars, advice, critical_issues                       |
    And 额外返回 DTW 元数据 (非评分):
      | dtw_metadata: { alignment_confidence, dtw_weight_used }     |
      | dtw_deviation_summary: { pitch, rhythm }  (偏差摘要, 用于展示) |
    And 不应返回独立的 dtw_score, dtw_pitch_score 等

  Scenario: 对比分析结果包含 DTW 偏差摘要 (用于前端音准视图)
    Given 对比分析完成
    When 前端请求音准对比视图的数据
    Then 应返回:
      | dtw_pitch_cents (逐帧)          | 用于画双曲线对比                      |
      | dtw_rhythm_offset (逐帧)        | 用于偏差热力图                        |
      | dtw_warp_path                   | 用于标注哪些段落 DTW 对齐              |
      | segment_confidences (逐段)      | 用于标注 "⚠️ 对齐不确定" 段落          |
    And 这些数据仅供前端可视化, 不参与评分计算 (评分已在上一步完成)

  # ═══════════════════════════════════════════════════════════
  # 四、回归测试 — 无参考场景零影响
  # ═══════════════════════════════════════════════════════════

  Scenario: 无参考时评分行为与 v5.17 完全一致
    Given 系统未匹配到标准歌曲 (无 DTW 数据)
    When 执行评分
    Then 所有五个维度应使用各自的独立评分逻辑
    And 评分结果应与 v5.17 绝对评分完全一致 (逐维度分数相同)
    And dtw_metadata 应为 null
    And 不应出现任何 DTW 相关的 NaN 或 0 值污染评分

  Scenario: 代码改动不触及 breath/technique/artistry/critical_rules
    Given DTW 降级重构完成
    When 运行全量单元测试
    Then breath_scorer 相关测试应全部通过 (逻辑未变)
    And technique_scorer 相关测试应全部通过 (逻辑未变)
    And artistry_scorer 相关测试应全部通过 (逻辑未变)
    And critical_rules 相关测试应全部通过 (逻辑未变)
    And pitch_scorer 新增 DTW 测试应覆盖: 有DTW/无DTW/置信度高/置信度低
    And rhythm_scorer 新增 DTW 测试应覆盖: 有DTW/无DTW/置信度高/置信度低

  # ═══════════════════════════════════════════════════════════
  # 五、边界条件
  # ═══════════════════════════════════════════════════════════

  Scenario: DTW 对齐完全失败 (confidence=0)
    Given DTW 对齐因音频差异过大而完全失败 (alignment_confidence=0.0)
    When 评分执行
    Then pitch_scorer 和 rhythm_scorer 均应忽略 DTW 数据
    And dtw_weight = 0.0
    And 评分完全回退到独立模式
    And 结果中 dtw_metadata.confidence = 0.0
    And dtw_metadata.status = "failed"
    And 建议中应提示 "DTW 对齐失败, 当前为绝对评分"

  Scenario: 用户音频比标准音频长很多 (2x)
    Given 标准歌曲时长 3:00, 用户音频时长 6:00 (重复唱了两遍)
    When DTW 对齐执行
    Then 应在用户音频中定位最匹配的 3:00 段落
    And alignment_confidence 可能偏低 (因为有一半内容对不上)
    And 偏差数据仅覆盖对齐的 3:00 段落
    And 未对齐部分走绝对评分

  Scenario: 用户音频极短 (仅副歌 30s)
    Given 标准歌曲 3:30, 用户仅唱了副歌 0:30
    When DTW 对齐执行
    Then 应在标准歌曲中定位最匹配的 30s 段落
    And 返回 matched_segment: { start: 120, end: 150 } (标准歌曲中的位置)
    And 仅对匹配段落做评分
    And alignment_confidence 可能较高 (如果段落匹配准确)

  Scenario: scoring_engine.py 重构后不应残留评分逻辑
    Given DTW 降级重构完成
    When Code Review 检查 services/comparison/scoring_engine.py
    Then 文件中不应包含以下方法名:
      | _score_pitch() | _score_rhythm() | _score_breath() | _score_volume() |
    And 文件中不应出现 score 或 rating 相关的计算逻辑
    And 文件应只有: 偏差数据计算 + 对齐路径生成 + 置信度评估
