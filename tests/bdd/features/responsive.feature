Feature: 响应式布局
  As a 移动用户
  I want 适配手机屏幕的界面
  So that 在手机上也能方便使用

  Background:
    Given SPA 前端应用已在浏览器中加载

  # ── 移动端导航 ──

  Scenario: 移动端显示底部导航
    Given 视口宽度为 375px (手机)
    When 页面加载完成
    Then 顶部导航应隐藏
    And 底部固定导航应显示
    And 底部导航应包含 4 个标签: 首页, 演唱, 对比, 历史

  Scenario: PC端显示顶部导航
    Given 视口宽度为 1280px (桌面)
    When 页面加载完成
    Then 顶部导航应显示
    And 底部导航应隐藏
    And 顶部导航应包含 5 个标签: 首页, 演唱, 对比, 历史, 设置

  # ── 布局适配 ──

  Scenario: 手机端首页单列布局
    Given 视口宽度为 375px
    When 我在首页 "#/"
    Then 主内容区和侧边栏应堆叠为单列
    And 操作卡片应为单列布局

  Scenario: 手机端历史网格单列
    Given 视口宽度为 375px
    When 我在历史页 "#/history"
    Then 历史卡片应为单列网格

  Scenario: 手机端对比页双卡堆叠
    Given 视口宽度为 375px
    When 我在对比页 "#/compare"
    Then 标准音频和用户音频卡片应垂直堆叠

  # ── 触控交互 ──

  Scenario: 触控设备无300ms延迟
    Given 我使用触控设备
    When 我点击任意按钮
    Then 按钮应立即响应 (无 300ms 延迟)
    And 页面应有 touch-action: manipulation 样式

  # ── 暗色主题 ──

  Scenario: 暗色主题切换
    Given 我在设置页 "#/settings"
    When 我点击暗色主题按钮
    Then body 应添加 dark-theme class
    And CSS 变量应切换为暗色值
    And 主题偏好应保存到 localStorage

  Scenario: 主题切换即时生效
    Given 我已保存暗色主题偏好
    When 我刷新页面
    Then 暗色主题应自动恢复
