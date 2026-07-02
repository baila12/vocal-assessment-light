Feature: 演唱页选歌 — 录音前选择标准歌曲作为参考
  As a 声乐学生
  I want to 在录音前从曲库中选择标准歌曲
  So that 我的演唱有参考目标, 实时音高对比有标准线

  Background:
    Given 演唱页已加载

  # ── 路由行为 ──

  Scenario: #/sing 无参数 — 显示选歌区
    Given 曲库中有至少 1 首歌曲
    When 我导航到 "#/sing" (无歌曲ID)
    Then 页面上半区显示歌曲选择列表
    And 下半区录音面板处于禁用状态 (灰色)
    And 显示提示 "请先选择一首标准歌曲"

  Scenario: #/sing/:songId 有参数 — 直接进入录音准备
    Given 曲库中有 "moon_love" 这首歌
    When 我导航到 "#/sing/moon_love"
    Then 歌曲选择区不显示
    And 直接显示录音面板
    And 显示 "准备演唱: 月亮代表我的心 - 邓丽君"
    And 录音按钮处于可用状态 (红色)

  # ── 选歌流程 ──

  Scenario: 选歌后录音面板激活
    Given 我在 #/sing 页面, 录音面板禁用
    When 我从歌曲列表中选择 "月亮代表我的心"
    Then 选中歌曲应高亮
    And 录音面板解除禁用
    And 显示已选歌曲信息: 歌名 + 歌手 + BPM + 调性

  Scenario: 选中后可以取消选择
    Given 我已选中 "月亮代表我的心"
    When 我点击已选歌曲的 "取消选择"
    Then 歌曲选择恢复列表状态
    And 录音面板恢复禁用

  Scenario: 选歌后开始录音
    Given 我已选中歌曲, 录音面板激活
    When 我点击红色录音按钮
    Then 开始录音
    And 实时音高对比 Canvas 显示标准参考线
    And 参考线与选中歌曲的基频数据一致

  # ── 不选歌直接录音 ──

  Scenario: 不选歌直接录音 — 使用 auto-match
    Given 演唱页已加载, 未选择歌曲
    When 我点击 "跳过选歌, 直接录音"
    Then 录音面板激活 (跳过选歌)
    And 实时音高对比 Canvas 不显示标准参考线
    But 录音可正常进行
    When 录音完成
    Then 系统自动匹配参考音频 (auto-match)
    And 若匹配成功则显示对比评分
    And 若匹配失败则显示绝对评分

  # ── 选歌后上传已有录音 ──

  Scenario: 选歌后上传文件而非录音
    Given 我已选中 "月亮代表我的心"
    When 我点击 "上传已有录音" 按钮
    Then 弹出文件选择器
    When 我选择一个音频文件
    Then 文件被上传并与选中标准歌曲进行 DTW 对比
    And 评分结果页面显示歌曲信息

  # ── 曲库为空 ──

  Scenario: 曲库为空进入 #/sing
    Given 曲库中没有任何歌曲
    When 我导航到 "#/sing"
    Then 页面显示 "曲库为空"
    And 显示 "前往曲库导入标准歌曲" 链接
    And 不显示歌曲列表

  Scenario: 曲库为空但可以上传文件
    Given 曲库中没有任何歌曲
    When 点击 "直接上传音频文件分析"
    Then 弹出文件选择器
    When 选择一个音频文件
    Then 走普通上传分析流程 (无 DTW 对比)

  # ── 边界条件 ──

  Scenario: 选歌 ID 不存在
    Given 曲库中没有 song_id="nonexistent"
    When 我导航到 "#/sing/nonexistent"
    Then 显示 "歌曲不存在"
    And 提供 "返回曲库" 链接

  Scenario: 录音中切换歌曲
    Given 我正在录音 (已选中歌曲)
    When 我尝试选择另一首歌曲
    Then 提示 "录音进行中，请先停止录音"
    And 当前录音不受影响
    When 我停止录音
    Then 可以正常切换歌曲

  Scenario: 录音完成后自动返回曲库选择
    Given 我从曲库选歌后录制并完成
    When 录音完成且评分结果展示后
    Then 页面底部显示 "再来一首" 按钮
    When 点击 "再来一首"
    Then 返回选歌状态 (保留已完成的录音结果)
