# API 接口文档 v7.13

> FastAPI 为主 (Flask 已移除 v7.6)

---

## FastAPI 端点 (`/api/v1/`)

| 方法 | 路径 | 说明 | P95 延迟 |
|------|------|------|:--:|
| POST | `/api/v1/upload` | 上传音频并分析 | Quick < 30s, Pro < 180s |
| POST | `/api/v1/analyze` | 分析已存在音频 | 同上 |
| POST | `/api/v1/extract-pitch` | 音高曲线提取 | < 10s |
| POST | `/api/v1/separate` | Demucs 人声分离 | CPU < 140s, GPU < 30s |
| GET | `/api/v1/separate/models` | 分离模型列表 | < 50ms |
| POST | `/api/v1/report` | PDF/图片报告 | < 5s |
| POST | `/api/v1/compare` | DTW 双文件对比 | < 60s |
| GET | `/api/v1/history` | 历史分页 | < 100ms |
| GET | `/api/v1/history/{id}` | 单条详情 | < 50ms |
| DELETE | `/api/v1/history/{id}` | 删除单条 | < 50ms |
| DELETE | `/api/v1/history/batch` | 批量删除 | < 200ms |
| POST | `/api/v1/history/batch-delete` | 批量删除 (POST) | < 200ms |
| DELETE | `/api/v1/history/all` | 清空全部 | < 500ms |
| GET | `/api/v1/test-files` | 测试音频列表 | < 50ms |
| GET | `/api/v1/audio?file=...` | 音频流 + 路径安全 | < 200ms |
| GET | `/api/v1/songs` | 曲库列表 (page/limit/style/difficulty/search) | < 100ms |
| GET | `/api/v1/songs/{id}` | 歌曲详情 | < 50ms |
| POST | `/api/v1/songs` | 添加歌曲 (multipart; v7.12: +`vocal_range` 音域) | < 200ms |
| DELETE | `/api/v1/songs/{id}` | 删除歌曲 | < 100ms |
| GET | `/api/v1/songs/{id}/pitch` | 歌曲参考音高 F0 曲线 (v7.13, 提取 + 缓存) | < 500ms |
| POST | `/api/v1/songs/{id}/compare` | 上传录音与选中歌曲 DTW 对比 (v7.13) | < 60s |
| GET | `/api/v1/flags` | Feature Flag + GPU + 模型状态 (v7.7) | < 50ms |
| GET | `/api/v1/scoring/presets` | 评分权重预设 (v7.11): 默认 + 4 风格 | < 50ms |
| POST | `/api/v1/scoring/apply-weights` | 维度分数+权重→总分/等级 (v7.11, 纯前端重算) | < 50ms |

### 评分权重 API (v7.11)

**GET `/api/v1/scoring/presets`** — 返回默认权重 (v7.4 13/12/22/25/15/13) + 4 风格预设:
`pop`(流行) / `bel_canto`(美声) / `ethnic`(民族) / `rap`(说唱), 每项含 `name`/`label`/`weights`(6 维小数)。权重单一数据来源 `ScoringWeights`。

**POST `/api/v1/scoring/apply-weights`** — 纯前端重算(不重新分析音频):
```json
{
  "dimension_scores": {"pitch": 90, "rhythm": 50, "breath": 70, "technique": 70, "muscle": 70, "artistry": 70},
  "preset": "rap",            // 或 weights: {"pitch": 0.08, ...} (二选一, 默认用 default)
  "timbre_adjustment": 0      // 复用原分析音色调整
}
```
校验: 权重总和=100% + 单维 ≤50% (400 拒绝)。返回 `total_score`/`level`/`grade`/`color`/`stars`/`weighted_dimensions`。

## WebSocket

| 路径 | 说明 |
|------|------|
| `/ws/v1/score` | 实时流式评分 (AudioWorklet → Float32Array → numpy.frombuffer) + v7.13 `pitch_update` 事件 |

### WS start 消息 (v7.12: 选歌录音携带参考歌曲)

```json
{"type": "start", "song_id": "moon_love", "mode": "quick"}
```

`song_id` 可选 — 选歌录音时前端传入, 服务端存入 `StreamingSession.song_id` (后续用于参考音高对比/DTW 评分)。

### WS pitch_update 事件 (v7.13)

录音过程中服务端每 2s 增量推送 `pitch_update` (样本驱动 PYIN 提取, 绝对时间轴), 前端将用户音高曲线实时渲染到 Canvas。它是用户音高曲线的唯一数据源 (前端无本地音高检测), 与参考 F0 曲线 (`GET /songs/{id}/pitch`) 配合完成实时偏差对比。

## 基础端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | GPU 状态 + 版本号 |
| GET | `/docs` | Swagger UI |
| GET | `/redoc` | ReDoc |

## Flask 遗留 (`/old/api/`) — 已移除 (v7.6)

Flask 路由已于 v7.6 全部移除。旧 `api/` 目录仅保留 `business/` 桥梁层 + `schemas.py`。所有 API 端点现在统一由 FastAPI `/api/v1/` 提供服务。详见 [API_CONTRACT.md](API_CONTRACT.md)。
