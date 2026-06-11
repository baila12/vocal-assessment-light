Feature: GSAP 动画与微交互
  As a 用户
  I want 流畅的动画反馈
  So that 评分展示和页面切换有仪式感

  Background:
    Given SPA 前端应用已在浏览器中加载

  # ── 评分动画序列 ──

  Scenario: 报告页评分环形动画
    Given 我有一份已完成的分析结果 (总分 78.5)
    When 我导航到报告页 "#/report/1"
    Then 总分环形评分应在 1.5 秒内从 0 动画到 78.5
    And 总分颜色应基于分数区间变化

  Scenario: 五维进度条stagger展开
    Given 我有一份已完成的分析结果 (score=78.5)
    When 报告页加载完成
    Then 五个维度进度条应依次展开
    And 相邻进度条展开间隔约 0.15 秒
    And 每个进度条动画时长约 0.8 秒

  Scenario: 建议列表逐条淡入
    Given 分析结果包含至少 3 条改进建议
    When 报告页展示建议区域
    Then 建议条目应逐条淡入 (stagger 0.1 秒)
    And 每条从 opacity:0 y:10 过渡到 opacity:1 y:0

  # ── 页面过渡 ──

  Scenario: 页面切换有过渡动画
    Given 我在首页 "#/"
    When 我导航到 "#/history"
    Then 旧页面应以 opacity 0 + x -20 退出 (0.2秒)
    And 新页面应以 opacity 1 + x 0 进入 (0.3秒)
    And 页面切换期间不应出现白屏

  # ── Toast 动画 ──

  Scenario: Toast 弹出动画
    Given 触发一个 Toast 通知
    When Toast 出现
    Then Toast 应从顶部滑入 (y: -20 → 0)
    And 动画时长约 0.3 秒
    And Toast 应在 3.5 秒后自动消失

  Scenario: 多个 Toast 堆叠
    Given 已有 1 个 Toast 显示中
    When 触发第 2 个 Toast
    Then 两个 Toast 应向下偏移堆叠
    And 不应超过 3 个同时显示

  # ── 命中反馈 ──

  Scenario: PERFECT 命中反馈动画
    Given 我在演唱页 "#/sing" 且正在录音
    When 检测到 PERFECT 命中
    Then 应弹出 "PERFECT" 金色文字
    And 文字从 scale:0 弹到 scale:1.3 (back.out(2) easing)
    And 随后向上飘出消失

  Scenario: 连击数字弹性动画
    Given 当前连击数为 0
    When 连击数变为 1
    Then 连击数字从 scale:0 弹到 scale:1.5
    When 连击数从 5 变为 6
    Then 连击数字 scale:1 → 1.3 → 1

  # ── 减动偏好 ──

  Scenario: prefers-reduced-motion 禁用动画
    Given 系统设置了 prefers-reduced-motion: reduce
    When 我导航到报告页
    Then 所有 GSAP 动画应被禁用
    And 分数应立即显示 (duration: 0)
    And 页面切换也应在 0 秒内完成
