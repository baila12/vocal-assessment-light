# API 契约文档 v7.8

> 更新: 2026-08-01 | FastAPI `/api/v1/` (Flask 已移除 v7.6) | 423 测试 GREEN

---

## 端点一览

| 方法 | 路径 | 说明 | Quick | Pro |
|------|------|------|:--:|:--:|
| GET | `/health` | GPU 状态 + 版本 | ✅ | ✅ |
| POST | `/api/v1/upload` | 上传音频并分析 (FormData, mode=quick\|professional) | ✅ | ✅ |
| POST | `/api/v1/analyze` | 分析已上传文件 | ✅ | ✅ |
| POST | `/api/v1/extract-pitch` | 音高曲线提取 | ✅ | ✅ |
| POST | `/api/v1/separate` | Demucs 人声分离 | ❌ | ✅ |
| GET | `/api/v1/separate/models` | 分离模型列表 | ✅ | ✅ |
| POST | `/api/v1/report` | PDF/图片报告导出 | ❌ | ✅ |
| POST | `/api/v1/compare` | DTW 双文件对比 | — | — |
| GET | `/api/v1/history` | 历史分页列表 + 日期筛选 | ✅ | ✅ |
| GET | `/api/v1/history/{id}` | 单条详情 | ✅ | ✅ |
| DELETE | `/api/v1/history/{id}` | 删除单条 | ✅ | ✅ |
| DELETE | `/api/v1/history/batch` | 批量删除 (JSON body) | ✅ | ✅ |
| POST | `/api/v1/history/batch-delete` | 批量删除 (POST) | ✅ | ✅ |
| DELETE | `/api/v1/history/all` | 清空全部 | ✅ | ✅ |
| GET | `/api/v1/test-files` | 测试音频列表 | ✅ | ✅ |
| GET | `/api/v1/audio?file=...` | 音频文件流 (路径安全校验) | ✅ | ✅ |
| POST | `/api/v1/songs` | 添加歌曲 (multipart 文件+元数据) | ✅ | ✅ v7.9 |
| GET | `/api/v1/songs` | 曲库列表 (page/limit/style/difficulty/search) | ✅ | ✅ v7.9 |
| GET | `/api/v1/songs/{id}` | 歌曲详情 | ✅ | ✅ v7.9 |
| DELETE | `/api/v1/songs/{id}` | 删除歌曲 | ✅ | ✅ v7.9 |
| GET | `/api/v1/flags` | Feature Flag + GPU + 模型状态 (v7.7) | ✅ | ✅ |
| WS | `/ws/v1/score` | 实时流式评分 | — | — |

---

## 核心响应格式

```json
{
  "success": true,
  "is_voice": true,
  "total_score": 74.8,
  "level": "良好",
  "stars": "★★",
  "color": "#10b981",
  "scores": {
    "pitch": 70.3,
    "rhythm": 66.2,
    "breath": 92.5,
    "technique": 25.1,
    "muscle_strength": 80.0,
    "artistry": 76.3
  },
  "timbre_adjustment": 0.0,
  "heuristic_dimensions": ["muscle_strength", "timbre"],
  "voice_quality": { "is_voice": true, "voice_ratio": 0.85 },
  "basic_info": { "filename": "song.mp3", "duration": 180.5 },
  "advice": ["长音支撑优秀", "咬字清晰度偏低"],
  "analysis_id": "abc123"
}
```

---

## 安全

| 机制 | 配置 |
|------|------|
| Security Headers | CSP, X-Content-Type, X-Frame, HSTS, Referrer-Policy |
| Rate Limit (FastAPI) | 120/min global, 20/min upload, 10/min WebSocket |
| Rate Limit (Flask) | Token bucket: 20/60s upload + 120/60s others |
| Max Body Size | 50MB (413 Payload Too Large) |
| Path Traversal | 文件名白名单 + resolved path 校验 |
| Error Response | 通用错误消息, 无原始 traceback 泄露 |

---

## 超时

| 端点 | 超时 |
|------|:---:|
| upload/analyze Quick | 30s |
| upload/analyze Pro | 180s |
| separate | 600s (subprocess) |
| compare | 120s |
| 其他 | 30s |
