Feature: 标准曲库 — 浏览、搜索、导入、删除
  As a 声乐学生
  I want to 管理标准音频曲库
  So that 我可以选择参考歌曲进行练习和对比

  Background:
    Given 标准曲库页已加载

  # ── 曲库浏览 ──

  Scenario: 加载后显示歌曲列表
    Given 曲库中有 5 首标准歌曲
    When 曲库页加载完成
    Then 应展示歌曲卡片网格
    And 每张卡片包含: 歌名, 歌手, 难度标签, 风格标签, 时长
    And 页面不出现 loading 骨架屏
    And 曲库统计信息显示 "共 5 首歌曲"

  Scenario: 空曲库显示引导
    Given 曲库中没有任何歌曲
    When 曲库页加载完成
    Then 应显示空状态提示 "曲库为空"
    And 应显示 "导入第一首标准歌曲" 按钮
    And 不应显示歌曲网格

  # ── 搜索与筛选 ──

  Scenario: 按歌名搜索实时过滤
    Given 曲库中有 "月亮代表我的心"、"小星星"、"告白气球" 三首歌
    When 我在搜索框输入 "月亮"
    Then 列表只显示 "月亮代表我的心"
    And 搜索结果中 "月亮" 二字应高亮
    And 曲库统计显示 "共 1 首歌曲 (筛选)"

  Scenario: 搜索无结果
    Given 曲库中有 5 首歌曲
    When 我搜索不存在的关键词 "zzzzz"
    Then 应显示 "未找到匹配歌曲"
    And 显示 "清空搜索" 按钮
    When 我点击 "清空搜索"
    Then 列表恢复显示全部 5 首歌曲

  Scenario: 按难度筛选
    Given 曲库中歌曲包含初级 3 首、中级 5 首、高级 2 首
    When 我点击筛选栏 "初级"
    Then 只显示初级歌曲 (3 首)
    And 筛选标签 "初级" 应高亮
    When 我点击 "全部"
    Then 恢复显示所有歌曲

  Scenario: 难度+风格组合筛选
    Given 曲库中有多种风格和难度的歌曲
    When 我设置难度=中级, 风格=流行
    Then 只显示中级流行歌曲
    And 筛选后歌曲数 < 全部歌曲数

  # ── 歌曲详情与选择 ──

  Scenario: 展开歌曲详情
    Given 曲库列表中有 "月亮代表我的心"
    When 我点击该歌曲卡片
    Then 卡片应展开显示完整元数据:
      | 调性, 音域, BPM, 原唱调 |
    And 显示 30 秒音频预览播放器
    And 显示 "选择此歌" 按钮
    When 我再次点击卡片
    Then 详情区域收起

  Scenario: 选择歌曲跳转到演唱页
    Given 曲库中有 "月亮代表我的心"
    When 我在歌曲卡片上点击 "选择此歌"
    Then URL hash 应变为 "#/sing/moon_love"
    And 演唱页应显示已选中该歌曲

  # ── 分页 ──

  Scenario: 大曲库分页加载
    Given 曲库中有 45 首歌曲
    When 曲库页加载完成
    Then 第一页显示 20 首歌曲
    And 显示页码指示器 "第 1 页 / 共 3 页"
    When 我点击 "下一页"
    Then 显示第 21-40 首歌曲
    And 页码指示器变为 "第 2 页 / 共 3 页"
