Feature: 音频上传与五维评分
  As a 声乐学生
  I want to 上传我的演唱录音
  So that 获得专业评分和改进建议

  Background:
    Given FastAPI 服务已启动

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
    When 我上传该文件并选择 "quick" 模式
    Then 应成功返回评分结果

    Examples:
      | format |
      | WAV    |
      | MP3    |
      | FLAC   |
      | OGG    |
      | M4A    |

  @slow
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
