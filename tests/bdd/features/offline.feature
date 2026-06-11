Feature: 离线可用性
  As a 用户
  I want 在没有网络时也能使用核心功能
  So that 练习不受网络限制

  Background:
    Given SPA 前端应用已在浏览器中加载

  # ── 本地依赖加载 ──

  Scenario: GSAP 从本地加载
    Given 我断开网络连接
    When 我加载应用页面
    Then GSAP 应从本地 /lib/gsap/gsap.min.js 加载
    And gsap 全局对象应可用
    And 页面动画应正常工作

  Scenario: Chart.js 从本地加载
    Given 我断开网络连接
    When 我导航到历史页 "#/history"
    Then Chart.js 应从本地 /lib/chart.js/chart.umd.min.js 加载
    And 成长曲线图表应正常渲染

  # ── 离线功能可用 ──

  Scenario: 离线时显示提示
    Given 我断开网络连接
    When 页面检测到离线
    Then Toast 应提示 "网络已断开，离线功能仍可用"

  Scenario: 恢复网络时提示
    Given 我之前处于离线状态
    When 网络恢复
    Then Toast 应提示 "网络已恢复"

  # ── HTML 入口唯一性 ──

  Scenario: 只有一个HTML入口
    Given 我访问应用根路径 "/"
    When 页面加载完成
    Then 应只有 index.html 作为入口
    And 不应出现 analysis.html, compare.html, settings.html 作为独立页面
