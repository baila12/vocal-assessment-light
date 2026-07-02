Feature: 快速/专业模式选择 — 模式切换与视觉区分
  As a 声乐学生
  I want to 在分析前选择评估模式
  So that 日常练习用快速模式, 详细诊断用专业模式

  Background:
    Given 首页已加载

  # ── 模式切换 ──

  Scenario: 首页显示模式选择器
    Given 我没有进行过任何分析
    When 首页加载完成
    Then 应显示模式选择器包含两个选项: "快速模式" 和 "专业模式"
    And 默认选中 "快速模式"
    And 快速模式说明文字为 "快速评估，适合日常练习"

  Scenario: 切换到专业模式
    Given 首页已加载且默认选中快速模式
    When 我点击 "专业模式"
    Then "专业模式" 选项应高亮
    And 说明文字变为 "专业评估，适合详细诊断"
    And URL 或 Store 中应记录模式为 "professional"

  Scenario: 模式偏好持久化
    Given 我选择了 "专业模式"
    When 我刷新页面
    Then 模式选择器应仍显示 "专业模式" 高亮

  # ── 模式影响分析 ──

  Scenario: 快速模式上传 — 传参
    Given 当前模式为快速模式
    When 我上传音频文件进行分析
    Then 发送到后端的 mode 参数应为 "quick"
    And 按钮文字显示 "快速分析"

  Scenario: 专业模式上传 — 传参
    Given 当前模式为专业模式
    When 我上传音频文件进行分析
    Then 发送到后端的 mode 参数应为 "professional"
    And 按钮文字显示 "专业分析"

  # ── 模式切换不影响已上传文件 ──

  Scenario: 选择文件后切换模式保持文件
    Given 我已选择一个音频文件 (未开始分析)
    When 我切换评估模式
    Then 已选文件不应被清除
    And 文件信息仍显示

  # ── 边界条件 ──

  Scenario: 无音频时无法切换模式的意义
    Given 我没有选择音频文件
    When 我在模式间切换
    Then 界面仅更新模式图标和提示文字
    And 不触发任何网络请求
