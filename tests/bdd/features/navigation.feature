Feature: SPA 路由导航
  As a 用户
  I want 流畅的单页导航体验
  So that 页面切换无白屏且 URL 正确更新

  Background:
    Given SPA 前端应用已在浏览器中加载

  # ── Hash 路由切换 ──

  Scenario: 导航"历史记录"更新URL
    Given 我在首页 "#/"
    When 我点击导航栏 "历史记录"
    Then URL hash 应变为 "#/history"
    And 历史记录页面应可见
    And 导航栏"历史"标签应高亮

  Scenario: 导航"对比分析"更新URL
    Given 我在首页 "#/"
    When 我点击导航栏 "对比分析"
    Then URL hash 应变为 "#/compare"
    And 对比分析页面应可见

  Scenario: 导航"演唱"更新URL
    Given 我在首页 "#/"
    When 我点击导航栏 "演唱"
    Then URL hash 应变为 "#/sing"
    And 演唱页面应可见

  Scenario: 导航"设置"更新URL
    Given 我在首页 "#/"
    When 我点击导航栏 "设置"
    Then URL hash 应变为 "#/settings"
    And 设置页面应可见

  Scenario: 点击Logo返回首页
    Given 我在历史记录页 "#/history"
    When 我点击导航栏品牌 Logo
    Then URL hash 应变为 "#/"
    And 首页应可见

  # ── 刷新恢复 ──

  Scenario: 刷新历史页保持路由
    Given 我在历史记录页 "#/history"
    When 我刷新页面
    Then URL hash 仍为 "#/history"
    And 历史记录页面应可见
    And 历史数据应重新加载

  Scenario: 刷新报告页保持路由
    Given 我在报告页 "#/report/42"
    When 我刷新页面
    Then URL hash 仍为 "#/report/42"
    And 报告页应尝试加载 ID=42 的分析结果

  # ── 无效路由处理 ──

  Scenario: 访问无效路由重定向首页
    Given 我访问一个不存在的路由 "#/nonexistent"
    When 页面加载完成
    Then 我应被重定向到 "#/"
    And Toast 提示 "页面不存在"

  # ── 浏览器后退 ──

  Scenario: 浏览器后退恢复前一页
    Given 我在首页 "#/"
    When 我导航到 "#/history"
    And 我再导航到 "#/settings"
    And 我点击浏览器后退
    Then URL hash 应变为 "#/history"
    And 历史记录页面应可见

  # ── 旧页面重定向 (后端单元测试已覆盖: tests/unit/test_spa_routes.py) ──
