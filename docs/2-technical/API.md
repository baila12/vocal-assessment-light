# API 接口文档 v7.5

> 绞杀者模式: FastAPI (主) + Flask /old (遗留)

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
| GET | `/api/v1/songs` | 曲库列表 | < 100ms |
| GET | `/api/v1/songs/{id}` | 歌曲详情 | < 50ms |

## WebSocket

| 路径 | 说明 |
|------|------|
| `/ws/v1/score` | 实时流式评分 (AudioWorklet → Float32Array → numpy.frombuffer) |

## 基础端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | GPU 状态 + 版本号 |
| GET | `/docs` | Swagger UI |
| GET | `/redoc` | ReDoc |

## Flask 遗留 (`/old/api/`)

通过 WSGI 挂载到 `/old`，提供与 FastAPI 相同的 14 个端点。所有端点已添加 token bucket 速率限制。详见 [API_CONTRACT.md](API_CONTRACT.md)。
