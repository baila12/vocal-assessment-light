# API 接口文档

> 更新日期: 2026-06-04 | v5.17 — 对照源码 `api/routes/` 验证

---

## 接口列表

| API | 方法 | 功能 | 状态 |
|-----|------|------|------|
| `/api/upload` | POST | 上传音频并分析 (支持 mode=quick/professional) | ✅ 稳定 |
| `/api/analyze` | POST | 分析已存在音频 | ✅ 稳定 |
| `/api/compare` | POST | DTW 对比分析两个音频 | ✅ 稳定 |
| `/api/separate` | POST | 人声分离 (Demucs) | ✅ 稳定 |
| `/api/separate/models` | GET | 获取分离模型列表 | ✅ 稳定 |
| `/api/extract-pitch` | POST | 音高提取 | ✅ 稳定 |
| `/api/audio` | GET | 音频文件流服务 | ✅ 稳定 |
| `/api/history` | GET | 历史记录 (支持分页) | ✅ 稳定 |
| `/api/history/<id>` | GET | 获取单条历史记录 | ✅ 稳定 |
| `/api/history/<id>` | DELETE | 删除单条记录 | ✅ 稳定 |
| `/api/history/batch` | DELETE | 批量删除 | ✅ 稳定 |
| `/api/history/all` | DELETE | 清空全部记录 | ✅ 稳定 |
| `/api/report` | POST | 生成评估报告 | ✅ 稳定 |
| `/api/test-files` | GET | 获取测试文件列表 | ✅ 稳定 |
| `/health` | GET | 健康检查 (含 GPU 状态) | ✅ 稳定 |

---

## 上传接口

```
POST /api/upload
Content-Type: multipart/form-data

参数:
- file: 音频文件 (必需)
- mode: quick | professional (可选，默认quick)

返回:
{
    success: true,
    is_voice: true,
    scores: {
        pitch: 79.6,       // 音准
        rhythm: 77.1,      // 节奏
        breath: 56.4,      // 气息
        technique: 84.0,   // 发声技术
        artistry: 75.9,    // 艺术表现
        volume: 56.4,      // 音量 (同 breath)
        emotion: 75.9      // 情感 (同 artistry)
    },
    total_score: 74.8,
    level: "良好",
    stars: "★★",
    color: "#10b981",
    advice: [...],
    critical_issues: [...],
    voice_quality: { quality_score, voice_ratio, ... },
    basic_info: { filename, duration, sample_rate, ... }
}
```

---

## 对比分析接口

```
POST /api/compare
Content-Type: multipart/form-data

参数:
- file: 用户音频 (必需)
- standard_file: 标准音频 (可选)

返回:
{
    success: true,
    data: {
        score: 95.0,           // DTW 综合评分
        confidence: 0.92,      // 对齐置信度
        dimensions: {
            pitch: { score, avg_cents },
            rhythm: { score, avg_offset_ms }
        },
        alignment: { warp_path, global_offset },
        problem_frames: [...],
        suggestions: [...]
    }
}
```

---

## 人声分离接口

```
POST /api/separate
Content-Type: application/json

参数:
- filepath: 音频文件路径 (必需)
- model: htdemucs_ft | htdemucs (可选，默认htdemucs_ft)
- two_stems: vocals | drums | bass | other (可选，默认vocals)

返回:
{
    success: true,
    vocals_path: "/path/to/vocals.mp3",
    accompaniment_path: "/path/to/no_vocals.mp3",
    duration: 180.5,
    model_used: "htdemucs_ft"
}
```

### 获取分离模型列表

```
GET /api/separate/models

返回:
{
    success: true,
    models: ["htdemucs_ft", "htdemucs"],
    default: "htdemucs_ft",
    available: { "htdemucs_ft": true, "htdemucs": false }
}
```

---

## 历史记录接口

```
GET /api/history?page=1&limit=20

返回:
{
    success: true,
    records: [
        {
            id: "rec_001",
            filename: "歌曲.mp3",
            total_score: 85.2,
            scores: { ... },
            level: "良好",
            created_at: "2026-05-07T10:00:00Z"
        }
    ],
    total: 100, page: 1, limit: 20
}
```

---

## 报告生成接口

```
POST /api/report
Content-Type: application/json

参数:
- analysis_result: 分析结果对象 (必需)
- filename: 报告文件名 (可选)
- format: pdf | image (可选，默认image)

返回:
{
    success: true,
    pdf_path: "/path/to/report.pdf",
    image_path: "/path/to/report.png"
}
```

---

## 健康检查

```
GET /health

返回:
{
    status: "ok",
    gpu: {
        available: true,
        device: "NVIDIA GeForce RTX 4060 Laptop GPU",
        cuda_version: "12.4"
    },
    models: { demucs: "loaded" }
}
```

---

## 响应格式规范

所有 API 遵循统一响应格式:

```json
{
    "success": true,
    "data": { ... },
    "error": null
}
```

---

## 错误码

| 错误码 | 说明 |
|--------|------|
| 400 | 参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |
