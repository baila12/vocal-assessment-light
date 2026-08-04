# 前端与后端计划对齐

> ⚠️ **已废弃**: 本文档描述 v5.17/v6.0 时期的 Flask + Vanilla JS 前后端对齐计划。当前 v7.11 已迁移至 FastAPI (`backend/`) + Vue 3 SPA (`frontend/src/`)。本文档保留作为 v6.0 设计历史参考。标准曲库 API 已于 v7.9 实现、前端页面已于 v7.10 实现 (SongsView)；评分权重 API (`GET /api/v1/scoring/presets` + `POST /api/v1/scoring/apply-weights`) 已于 v7.11 实现，前端权重面板 (ScoringWeightsPanel) 已集成到 ReportView。
>
> 当前前后端状态见: [ARCHITECTURE.md](../ARCHITECTURE.md) | [ROUTES.md](ROUTES.md) | [README.md](README.md)

## 后端计划摘要

| 轨道 | 版本 | 后端能力 | 前端影响 |
|------|------|----------|----------|
| 轨道 B | v5.18 | Feature Flag、多尺度 HNR、Praat CPP、Voicing detection、TorchCREPE fallback | 设置页需要预留算法开关、模型状态、健康检查展示 |
| 轨道 A | v6.0 | 标准歌曲数据库、自动匹配、选歌录音、曲库管理、特征预计算 | 需要曲库、添加歌曲、选歌练习、匹配结果 UI |
| 轨道 B | v6.0 | 校准数据集、评分参数校准、可配置评分系统 | 需要评分参数设置、权重预设、自定义预设导入导出 |
| 通用体验 | v6.0 | 非阻塞分析、SSE 进度、实时录音后台分析 | 需要分析任务状态、顶部进度条、跨页面任务通知 |

## v5.17 时期后端接口 (历史记录；v7.9 路径已改为 `/api/v1/*`)

| v5.17 API | 前端用途 | v7.9 对应路径 |
|-----------|----------|---------------|
| `POST /api/upload` | Quick/Professional 上传分析 | `POST /api/v1/upload` |
| `POST /api/compare` | 手动标准音频与用户音频对比 | `POST /api/v1/compare` |
| `POST /api/extract-pitch` | 标准音频或用户音频音高曲线提取 | `POST /api/v1/extract-pitch` |
| `GET /api/history` | 历史记录和报告恢复基础 | `GET /api/v1/history` |
| `POST /api/report` | 导出 PDF/图片 | `POST /api/v1/report` |
| `GET /health` | GPU、目录、模型健康状态 | `GET /health` (未变) |

## 后端计划接口占位

这些接口在 v5.17 时尚未稳定落地。其中标准曲库 API 已在 v7.9 实现 (`backend/interfaces/api/routes/songs.py`)，其余仍为计划状态。前端应先以页面和 schema 预留，而不是写死临时逻辑。

| 计划 API | 来源 | 前端页面 | v7.9 状态 |
|----------|------|----------|-----------|
| `GET /api/v1/songs` | `database.feature` | `#/library` | **已实现** |
| `POST /api/v1/songs` | `database.feature` | `#/library/new` | **已实现** |
| `GET /api/v1/songs/{id}` | `database.feature` | `#/library/:songId` | **已实现** |
| `DELETE /api/v1/songs/{id}` | `database.feature` | 曲库管理 | **已实现** |
| `POST /api/match` | `auto-match.feature` | 上传后匹配、分析任务 | 计划中 |
| `POST /api/scoring/recommend` | `scoring-config.feature` | 评分参数设置 | 计划中 |
| `GET /api/v1/scoring/presets` | `scoring-config.feature` | 设置页、权重预设 | **已实现 (v7.11)** |
| `POST /api/v1/scoring/apply-weights` | `scoring-config.feature` | 前端重算总分/等级 | **已实现 (v7.11)** |
| `POST /api/analysis/start` | `nonblocking-analysis.feature` | 非阻塞分析任务 | 计划中 |
| `GET /api/analysis/progress?task_id=...` | `nonblocking-analysis.feature` | SSE 进度 | 计划中 |

## 页面预留计划

| 页面 | 当前是否存在 | v7.9 状态 |
|------|--------------|-----------|
| Home | 已存在 | 上传、录音、手动对比、曲库练习入口；不展示静态评分样例 |
| Library | 前端: 已实现 (SongsView, v7.10) | 后端歌曲 CRUD API (v7.9) + 前端卡片网格页 (v7.10) |
| AddSong | 前端: 已实现 (SongsView, v7.10) | 后端 `POST /api/v1/songs` (v7.9) + 前端卡片网格页 (v7.10) |
| SongDetail | 前端: 已实现 (SongsView, v7.10) | 后端 `GET /api/v1/songs/{id}` (v7.9) + 前端卡片网格页 (v7.10) |
| Practice | 部分由 Sing 承担 | 选歌后录音准备、倒计时、标准曲线预加载、伴奏模式 |
| Compare | 已存在但需重做 | 手动双音频对比、参数设置、匹配/未匹配结果 |
| Report | 已存在但需重做 | 匹配歌曲信息、fallback_reason、权重来源、问题段落 |
| Settings/Scoring | 部分实现 (ScoringWeightsPanel, v7.11) | 风格预设、六维权重滑块、自动归一化、自定义预设导入导出 |
| Settings/Models | 部分实现 (HomeView el-drawer, v7.7) | Feature Flag、GPU 状态、模型可用性、实验性算法说明 |
| AnalysisTask | 不存在 | SSE 阶段进度、已到达特征、跨页面任务恢复 |

## 前端数据模型预留

### SongSummary

```json
{
  "id": "song_001",
  "title": "月亮代表我的心",
  "artist": "邓丽君",
  "difficulty": "初级",
  "style": "流行",
  "duration": 180.5,
  "bpm": 78,
  "key": "C Major",
  "feature_status": "ready"
}
```

### MatchResult

```json
{
  "matched_song": {
    "id": "song_001",
    "title": "月亮代表我的心",
    "artist": "邓丽君",
    "confidence": 0.85
  },
  "candidates": [],
  "fallback_reason": null,
  "mode": "dtw"
}
```

### ScoringPreset (v6.0 历史设计；v7.9 已改为六维评分)

```json
{
  "id": "preset_pop_default",
  "name": "流行默认",
  "style": "pop",
  "weights": {
    "pitch": 13,
    "rhythm": 12,
    "breath": 22,
    "technique": 25,
    "muscle_strength": 15,
    "artistry": 13
  },
  "source": "style_preset"
}
```
> **注意**: 以上权重为 v7.9 当前六维评分体系 (Pitch/Rhythm/Breath/Technique/Muscle/Artistry)，与 v6.0 时期的五维设计不同。前端评分页面应展示全部六个维度。

### AnalysisTask

```json
{
  "task_id": "task_001",
  "status": "running",
  "stage": "feature_pitch",
  "progress": 15,
  "available_features": ["voice_check", "feature_pitch"]
}
```

## 设计约束

| 约束 | 说明 |
|------|------|
| 前端先预留页面，不假装后端已完成 | 计划 API 未落地时显示空状态、mock schema 或”后端待接入”状态 |
| 路由先稳定，数据后接入 | v6.0 页面可以先有路由和布局，不必等待 API |
| BDD 先描述用户行为 | 以 `database.feature`、`song-select.feature`、`scoring-config.feature` 驱动页面职责 |
| 浏览器验收是必需步骤 | 进入实际 UI 重做后，使用浏览器检查桌面/移动端真实页面 |

## 前后端性能对接

| 前端状态 | 后端 SLA | 前端超时处理 |
|---------|---------|------------|
| 上传分析中 | Quick<30s, Pro<180s | 超时 → Toast “分析超时，请重试” + 可重试按钮 |
| SSE 进度流 | voice_check < 2s, 后续每阶段推送 | 3s 无事件 → 重连; 30s 无事件 → 超时关闭 |
| 录音 chunk 上传 | < 200ms/chunk (localhost) | 失败 → 本地缓存 + 3s 后重传 |
| 曲库搜索 | < 3s (100首) | 加载中骨架屏 + 3s+ 显示”搜索较慢，请稍候” |
| 匹配搜索 | < 5s | 进度指示 + 5s+ 可跳过直接评分 |
| 报告加载 | < 500ms (JSON) | 骨架屏 |
| Canvas 实时音高 | 后端每 500ms 推送, 前端 30fps 渲染 | 数据断流 → 继续渲染已有曲线 + 灰色标记 |

### 前端错误降级 (网络/超时)

| 场景 | 降级策略 |
|------|---------|
| SSE 连接失败 | 3 次重试 (3s/6s/12s 退避) → 回退轮询 GET `/api/analysis/status?task_id=...` |
| API 超时 | 30s 无响应 → 自动重试 1 次 → 仍超时 → 显示错误 + 重试按钮 |
| 音频播放失败 | 格式不支持 → Toast 提示 + 自动降级到 HTML5 Audio (不是 Web Audio API) |
| IndexedDB 满 | Storage API 检测 → 提示清理历史记录 → 允许继续使用 (历史不保存) |

