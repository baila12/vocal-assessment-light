Feature: 历史记录管理
  As a 声乐学生
  I want to 查看和管理我的历史评分记录
  So that 追踪演唱进步

  Scenario: 分页查看历史记录
    Given 历史记录中有至少 10 条评估记录
    When 我访问历史记录 API 并指定 page=1, limit=5
    Then 应返回 5 条记录
    And 返回应包含 total, page, limit 分页信息

  Scenario: 删除单条记录
    Given 历史记录中存在一条特定记录
    When 我发送 DELETE 请求到该记录的 API 端点
    Then 该记录应被删除
    And 后续 GET 请求不应再返回该记录

  Scenario: 批量删除
    Given 历史记录中有 3 条记录
    When 我发送批量删除请求包含这 3 个 ID
    Then 这 3 条记录应全部被删除
    And 其他记录应保持不变

  Scenario: 非人声记录独立标记
    Given 一条 is_voice=false 的评估记录
    When 该记录被保存到历史
    Then 记录中应标记 is_voice=false
    And 统计时应可排除该记录
