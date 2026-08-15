Feature: 标准歌曲数据库管理
  As a 声乐学生或教师
  I want to 管理系统中的标准歌曲库
  So that 有足够的参考音频用于自动匹配和对比分析

  Background:
    Given 服务已启动

  # ── 添加歌曲 ──

  Scenario: 上传音频并录入歌曲信息
    Given 一个标准演唱音频文件 "reference_song.wav"
    And 歌曲元数据:
      | 字段   | 值             |
      | 歌名   | 月亮代表我的心  |
      | 歌手   | 邓丽君         |
      | 调性   | C Major        |
      | BPM    | 78             |
      | 难度   | 初级           |
      | 风格   | 流行           |
      | 评分配置| 流行默认       |
    When 我提交该歌曲到标准曲库
    Then 歌曲应成功入库
    And 系统应自动预提取特征: 基频曲线, onset序列, 频谱指纹
    And 返回歌曲的唯一 ID

  Scenario: 批量导入歌曲
    Given 一个包含 10 首标准歌曲的文件夹
    And 每首歌曲都有配套的 metadata.json
    When 我触发批量导入
    Then 10 首歌曲应全部入库
    And 每首歌的特征应后台预计算完成
    And 返回导入报告: 成功数, 失败数, 跳过(重复)数

  Scenario: 重复歌曲检测
    Given 曲库中已存在 "月亮代表我的心 - 邓丽君"
    When 我尝试再次导入相同音频文件
    Then 系统应检测到重复
    And 返回提示 "该歌曲已存在 (ID: xxx), 是否覆盖?"
    And 默认行为应为跳过(不覆盖)

  # ── 浏览与搜索 ──

  Scenario: 按条件浏览歌曲库
    Given 曲库中有至少 20 首歌曲
    When 我访问歌曲列表 API, 指定 page=1, limit=10
    Then 应返回 10 首歌曲
    And 每首歌包含: id, 歌名, 歌手, 难度, 风格, 时长
    And 返回分页信息: total, page, limit

  Scenario: 按风格筛选歌曲
    Given 曲库中有流行歌曲 5 首, 美声歌曲 3 首
    When 我筛选风格为 "流行"
    Then 应返回 5 首流行歌曲
    And 不应包含美声歌曲

  Scenario: 按难度筛选歌曲
    Given 曲库中有初级 8 首, 中级 6 首, 高级 3 首
    When 我筛选难度为 "初级" 或 "中级"
    Then 应返回 14 首符合条件的歌曲

  Scenario: 按歌名或歌手搜索
    Given 曲库中包含 "月亮代表我的心"
    When 我搜索关键词 "月亮"
    Then 应返回歌名或歌手包含 "月亮" 的歌曲
    And 支持模糊匹配 (如 "月量" 应也能匹配 "月亮")

  # ── 删除与维护 ──

  Scenario: 删除单首歌曲
    Given 曲库中存在 ID 为 "song_001" 的歌曲
    When 我删除该歌曲
    Then 歌曲记录应从数据库移除
    And 关联的特征缓存文件应同步删除
    And 后续搜索不应再出现该歌曲

  Scenario: 查看歌曲详情
    Given 曲库中存在 ID 为 "song_001" 的歌曲
    When 我访问该歌曲的详情 API
    Then 应返回完整元数据: 歌名, 歌手, 调性, BPM, 难度, 风格, 时长, 音域范围
    And 应返回特征摘要: 基频曲线采样点, onset 数量, 平均能量
    And 应返回入库时间和特征提取状态
    And 应返回关联的评分权重配置 (scoring_config 字段)

  Scenario: 录入歌曲时自定义评分权重
    Given 我正在录入一首高难度美声歌曲
    When 我展开 "评分参数" 面板
    Then 应显示风格选择器 + 五维权重滑块
    And 选择 "美声" → 自动填充美声默认权重: P=30, R=15, B=25, T=20, A=10
    And 点击 "系统推荐" → 分析音频特征 → 返回推荐权重及理由
    And 我可将推荐值保存为该歌曲的默认评分配置
    And 后续匹配到该歌曲时自动使用此配置
