Feature: 音频上传与五维评分
  As a 声乐学生
  I want to 上传我的演唱录音
  So that 获得专业评分和改进建议

  Background:
    Given Flask 服务已启动

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
    Given 一个包含音乐伴奏的人声 MP3 文件 "mixed_vocal.mp3"
    When 我选择 "professional" 模式上传
    Then 混合音频检测应判断为 mixed
    And Pro 模式气息评分与 Quick 模式气息评分的差距应小于 10 分
    And 专业模式总分应在快速模式总分的 10% 以内

  Scenario: 合成音频归零
    Given 一个 TTS 合成的语音 WAV 文件 "synthetic.wav"
    When 我上传该文件进行评估
    Then 人声质量检测应判断为 non-voice
    And 返回的 total_score 应为 0.0

  # ── 非阻塞分析体验 (v6.0) ──

  Scenario: 分析进行中 — 进度不遮挡页面
    Given 我已上传音频并点击 "开始分析"
    When 分析正在进行中 (进度 50%)
    Then 不应显示全屏遮罩或模态框
    And 进度条应为页面顶部的细条 (4px, #3b82f6)
    And 评分卡片区显示各维度依次进行的动画
    And "播放" 按钮应处于可用状态
    And 我可以点击播放音频 (不等分析完成)

  Scenario: 分析中播放音频 — 基频数据到位后显示音准曲线
    Given 分析进行中, 已收到 feature_pitch 事件 (基频可用)
    And 未匹配到标准歌曲
    When 我点击播放音频
    Then 应切换到音准视图
    And 显示单条蓝色用户音高曲线 (随播放滚动)
    And 视图标注 "绝对音高 (分析中…)"
    And 分析完成后 → 评分数字平滑出现 (不打断播放)

  Scenario: 分析中播放音频 — 自动匹配后有参考
    Given 分析进行中, matching 事件已匹配到标准歌曲
    When 我点击播放音频
    Then 应显示双曲线对比 (标准虚线 + 用户绿/橙/红实线)
    And 视图标注 "参考: XXX"
    And 偏差统计在 final_score 到达后平滑出现

  # ── 回放时实时音准对比 ──

  Scenario: 上传翻唱自动匹配标准歌曲
    Given 标准曲库中有歌曲 "月亮代表我的心"
    And 一个翻唱版本音频文件 "moon_cover.wav"
    When 我上传翻唱音频进行评估
    Then 系统应自动搜索标准曲库
    And 匹配到 "月亮代表我的心" 后使用 DTW 对比评分
    And 返回结果应包含 matched_song 字段: { id, title, artist, confidence }

  Scenario: 无匹配歌曲时回退绝对评分
    Given 标准曲库中没有与用户音频匹配的歌曲
    When 我上传一个未知歌曲的翻唱
    Then 匹配结果中 matched_song 应为 null
    And 评分模式应为 absolute (绝对评分)
    And 返回的 fallback_reason 应为 "no_match"
    And 五维评分结果应正常返回

  # ── 回放时实时音准对比 (v6.0 新增) ──

  Scenario: Quick 模式回放 — 无参考时仅显示用户音高曲线
    Given 我用 Quick 模式评估了一首无匹配的歌曲
    And 评估已完成
    When 我切换到 "音准视图" 并点击播放
    Then 应显示单条用户音高曲线 (蓝色 #3b82f6)
    And 视图标注 "绝对音高 (无参考)"
    And 曲线应随播放进度从右向左滚动
    And 播放位置竖线固定在画面中央

  Scenario: Quick 模式回放 — 有自动匹配时显示双曲线对比
    Given 我用 Quick 模式评估了 "月亮代表我的心" 翻唱
    And 系统自动匹配到标准歌曲 (置信度 0.85)
    When 我切换到 "音准视图" 并点击播放
    Then 应显示双曲线: 标准 (#6366f1 虚线) + 用户 (绿/橙/红着色)
    And 视图标注 "参考: 月亮代表我的心 - 邓丽君"
    And 播放结束后显示统计: "精准率 | 略偏 | 跑调"

  Scenario: Pro 模式回放 — 完整可视化包含音准对比
    Given 我用 Professional 模式评估了带伴奏的演唱
    And Demucs 分离 + 评分已完成
    When 我查看评估结果页面
    Then 应同时展示:
      | 可视化类型 |
      | 频谱图 |
      | 基音轨迹图 |
      | 能量波形图 |
      | 实时音准对比视图 |
      | 逐句评分 |
    And 点击逐句评分的任一句 → 音准曲线跳转到该句起始位置
    And 点击音准曲线上的问题段落 → 播放该段落并显示诊断文字
