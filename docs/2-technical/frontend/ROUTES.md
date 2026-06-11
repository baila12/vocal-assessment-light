# 前端路由契约

> 目标: 让前端路由、BDD、后端计划保持一致。旧 HTML 页面只承担迁移入口职责，主流程统一走 SPA hash route。

## 当前主路由

| 路由 | 状态 | 页面 | 说明 |
|------|------|------|------|
| `#/` | 已有 | Home | 上传、录音、对比入口 |
| `#/sing` | 已有 | Sing | 实时录音/演唱页 |
| `#/compare` | 已有 | Compare | 手动标准音频 + 用户音频对比 |
| `#/report` | 已有 | Report | 当前依赖 store 展示最近结果 |
| `#/report/:analysisId` | 需强化 | Report | 应支持刷新恢复 |
| `#/history` | 已有 | History | 历史记录 |
| `#/settings` | 已有 | Settings | 当前基础设置页 |

## v6.0 预留路由

| 路由 | 页面职责 | 后端来源 |
|------|----------|----------|
| `#/library` | 标准歌曲库浏览、搜索、筛选 | `database.feature`, PRD 3.3 |
| `#/library/new` | 添加标准歌曲、填写元数据、上传标准音频 | `database.feature` |
| `#/library/import` | 批量导入标准歌曲与 metadata | `database.feature` |
| `#/library/:songId` | 标准歌曲详情、试听、评分配置摘要 | `database.feature`, `song-select.feature` |
| `#/practice/:songId` | 选歌后录音准备、标准歌曲信息、原唱试听 | `song-select.feature` |
| `#/settings/scoring` | 风格预设、五维权重、自定义预设导入导出 | `scoring-config.feature` |
| `#/settings/models` | Feature Flag、GPU/模型状态、实验性算法开关 | PRD v5.18 |
| `#/analysis/:taskId` | 非阻塞分析任务详情、阶段性特征展示 | `nonblocking-analysis.feature` |

## 旧页面迁移

| 旧路径 | 建议目标 | 说明 |
|--------|----------|------|
| `/analysis.html` | `/#/report` 或 `/#/report/:analysisId` | 有结果 ID 时进入报告，否则回首页 |
| `/compare.html` | `/#/compare` | 手动对比入口 |
| `/settings.html` | `/#/settings` | 设置入口 |

## BDD 对齐要求

| 要求 | 说明 |
|------|------|
| navigation.feature 是路由验收主入口 | E2E 不再各自定义旧页面 URL 期望 |
| 报告页必须支持刷新恢复 | `#/report/:analysisId` 不应只依赖内存 store |
| 无效路由要有用户可见反馈 | Router 不只 `console.warn`，还要 Toast 或状态提示 |
| 旧页面重定向单独测试 | 不和主导航流程混在一起 |

