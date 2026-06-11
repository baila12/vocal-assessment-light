Feature: 录音实时后台分析 — 录完秒出结果
  As a 声乐学生
  I want to 录音过程中系统就在后台分析我的演唱
  So that 点击结束后几乎立即看到评分, 不用再等几十秒

  Background:
    Given Flask 服务已启动
    And 前端支持通过 SSE 接收实时分析进度

  # ═══════════════════════════════════════════════════════════
  # 一、录音中实时分析 — 核心流程
  # ═══════════════════════════════════════════════════════════

  Scenario: 录音开始后后端立即启动分析
    Given 我已选择标准歌曲 (或跳过选择)
    When 我点击 "开始录音"
    Then 前端应建立 SSE 连接到 /api/record/stream
    And 录音音频数据应以 chunks 形式持续发送到后端 (每 2 秒一个 chunk)
    And 后端应在收到第一个 chunk 后立即开始特征提取
    And SSE 应按以下顺序推送阶段性事件:
      | 事件               | 触发时机                   | 数据                        |
      | recording_started  | 录音开始                   | session_id                  |
      | chunk_processed    | 每个音频 chunk 处理完成     | chunk_index, duration_so_far |
      | pitch_stream       | 实时基频提取 (每个 chunk)   | 基频采样点数组               |
      | partial_score      | 累积到足够数据后的初步评分  | pitch_score, rhythm_score    |
      | voice_quality      | 人声质量初步判断            | is_voice, confidence        |
      | recording_stopped  | 用户点击停止录音            | total_duration              |
      | final_score        | 全量数据最终评分            | 完整五维评分 + 建议           |

  Scenario: 录音结束后秒出结果
    Given 我已录制了一段 2 分钟的演唱
    And 录音过程中后端已实时分析了 80% 的数据
    When 我点击 "停止录音"
    Then SSE 应推送 recording_stopped 事件
    And 后端应处理剩余的 20% 未分析数据 (< 10 秒)
    And SSE 应推送 final_score 事件
    And 从点击停止到看到完整评分结果应在 10 秒内
    And 对比: 如果录音后从头分析, 需要 20-40 秒
    And 结果页应包含: 五维评分, 双曲线音准对比, 问题段落, 建议

  Scenario: 短录音 (< 30 秒) — 几乎瞬间出结果
    Given 我录制了仅 15 秒的短音频
    And 录音过程中后端已分析完所有 chunks
    When 我点击 "停止录音"
    Then final_score 应在 3 秒内推送
    And 用户体验接近 "即时出分"

  # ═══════════════════════════════════════════════════════════
  # 二、实时分析的边界条件
  # ═══════════════════════════════════════════════════════════

  Scenario: 录音开始阶段 — 数据不足时不做评分
    Given 录音刚开始 5 秒
    And 后端只收到了 2 个 chunk
    When 前端尝试请求 partial_score
    Then 后端应返回 status: "insufficient_data"
    And 前端应显示 "数据收集中… 至少需要 15 秒才能给出初步评分"
    And 不应显示虚假的低分或零分

  Scenario: 录音质量差 — 实时提示
    Given 我正在录音
    And 后端检测到以下问题:
      | 问题             | 条件                           |
      | 音量过低         | RMS < -30dB 持续 5 秒          |
      | 背景噪音过大     | SNR < 10dB                     |
      | 未检测到有效人声 | voice_ratio < 0.3 持续 10 秒   |
    When 任一条件触发
    Then SSE 应推送 quality_warning 事件
    And 前端应显示非阻塞提示 (Toast, 不中断录音):
      | 提示内容                         | 图标 |
      | "音量过低, 请靠近麦克风"         | 🔊   |
      | "背景噪音较大, 建议更换环境"      | 🎤   |
      | "未检测到有效人声, 请开始演唱"    | 🎵   |
    And 提示应 3 秒后自动消失

  Scenario: 录音中途网络断开 (chunk 发送失败)
    Given 我正在录音 (使用 SSE + chunk 上传)
    When 网络暂时断开 5 秒
    Then 前端应在本地缓存未发送的 chunks (内存中)
    And 录音界面应显示 "网络不稳定, 数据将在恢复后补传"
    And 网络恢复后, 缓存 chunks 按顺序补发
    And 后端应能处理乱序到达的 chunks (按 sequence_index 排序)
    And 录音不应中断 (本地 MediaRecorder 继续)

  Scenario: 中途取消录音 — 分析数据丢弃
    Given 录音进行了 30 秒, 后端已分析部分数据
    When 我点击 "取消录音" (不是停止)
    Then 前端应发送 cancel 事件
    And 后端应丢弃该 session 的所有分析数据
    And 音频文件应从 uploads/ 中删除
    And SSE 连接应关闭
    And 前端返回录音准备页

  # ═══════════════════════════════════════════════════════════
  # 三、实时分析 + 曲库匹配的交互
  # ═══════════════════════════════════════════════════════════

  Scenario: 选了标准歌曲时录音 — 实时对比已知
    Given 我已选择 "月亮代表我的心" 作为标准歌曲
    And 标准歌曲的基频数据已从曲库预加载到前端
    When 我开始录音
    Then 前端已知道参考音高 (无需等后端匹配)
    And 录音过程中应实时显示:
      | 标准音高虚线 (随BPM滚动) + 用户实时音高圆点 |
    And 后端在收到 chunk 后做 DTW 对齐 (而非匹配搜索)
    And SSE 推送的 partial_score 应基于与已知标准歌曲的对比

  Scenario: 未选标准歌曲时录音 — 录音结束后自动匹配
    Given 我没有选择标准歌曲
    When 我录音完成后端推送 final_score 前
    Then 后端应先用完整音频做曲库匹配 (见 auto-match.feature)
    And 匹配成功 → DTW 对比评分
    And 匹配失败 → 绝对评分
    And 匹配阶段增加 3-5 秒延迟 (在 final_score 推送前)

  # ═══════════════════════════════════════════════════════════
  # 四、实时分析 + Quick/Pro 模式的关系
  # ═══════════════════════════════════════════════════════════

  Scenario: 录音分析默认使用 Quick 路径
    Given 录音模式下的实时分析
    Then 默认使用 Quick 模式的特征提取链路 (快速)
    And 不执行 Demucs 分离 (假设录音环境为纯人声)
    And 在录音停止后如有需要, 可手动触发 Pro 模式重分析

  Scenario: 录音停止后手动切换到 Pro 分析
    Given 我用录音模式得到了 Quick 评分结果
    When 我点击 "用专业模式重新分析"
    Then 应使用已保存的完整音频文件
    And 执行 Demucs 分离 + 逐句评分 + 可视化
    And 此操作按标准 Pro 模式耗时 (~130-170s)
    And 界面走非阻塞分析流程 (见 nonblocking-analysis.feature)
