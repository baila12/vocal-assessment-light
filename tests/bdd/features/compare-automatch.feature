Feature: 对比分析页自动匹配反馈可见化
  As a 声乐学生
  I want to 自动匹配失败/成功/回退时获得明确反馈
  So that 匹配错误不会被静默吞掉, 我能知道该重试还是继续

  Background:
    Given 对比分析页已加载

  # v7.15 H-B14 (HIGH): songMatch.store.error 是死信 ref — matchAudio 失败时记录错误,
  #   但 CompareView 从不读取, 网络/服务端错误被静默吞掉。修复后:
  #     store.error        → 常驻错误告警 data-test="auto-match-error"
  #     matchedSong        → 命中徽标 data-test="auto-match-hit"
  #     fallbackReason     → 回退提示 data-test="auto-match-fallback"
  #   通过 window.__store.setState 注入 songMatch store 状态 (v7.11 测试钩子, 同 _inject_songs 模式)。

  Scenario: 自动匹配失败 — 显示错误告警 (H-B14 核心)
    Given 自动匹配已执行且失败
    Then 显示匹配错误告警 (data-test="auto-match-error")
    And 错误告警展示服务端错误信息

  Scenario: 自动匹配成功 — 显示命中徽标
    Given 自动匹配已执行且成功
    Then 显示匹配命中徽标 (data-test="auto-match-hit")
    And 命中徽标展示匹配到的歌曲名

  Scenario: 自动匹配无命中 — 显示优雅回退提示
    Given 自动匹配已执行且无命中
    Then 显示回退提示 (data-test="auto-match-fallback")
    And 不显示错误告警
