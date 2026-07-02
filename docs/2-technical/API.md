# API 接口文档

> 更新日期: 2026-07-02 | v5.18 — 新增性能 SLA 与缓存策略

---

## 接口列表

| API | 方法 | 功能 | 状态 | P95 延迟 | 超时 |
|-----|------|------|------|---------|------|
| `/api/upload` | POST | 上传音频并分析 (支持 mode=quick/professional) | ✅ 稳定 | Quick<30s, Pro<180s | 300s |
| `/api/analyze` | POST | 分析已存在音频 | ✅ 稳定 | 同 upload | 300s |
| `/api/compare` | POST | DTW 对比分析两个音频 | ✅ 稳定 | <60s | 120s |
| `/api/separate` | POST | 人声分离 (Demucs) | ✅ 稳定 | CPU<140s, GPU<30s | 200s |
| `/api/separate/models` | GET | 获取分离模型列表 | ✅ 稳定 | <50ms | 5s |
| `/api/extract-pitch` | POST | 音高提取 | ✅ 稳定 | <10s | 30s |
| `/api/audio` | GET | 音频文件流服务 | ✅ 稳定 | <200ms (首字节) | 30s |
| `/api/history` | GET | 历史记录 (支持分页) | ✅ 稳定 | <100ms | 5s |
| `/api/history/<id>` | GET | 获取单条历史记录 | ✅ 稳定 | <50ms | 5s |
| `/api/history/<id>` | DELETE | 删除单条记录 | ✅ 稳定 | <50ms | 5s |
| `/api/history/batch` | DELETE | 批量删除 | ✅ 稳定 | <200ms | 10s |
| `/api/history/all` | DELETE | 清空全部记录 | ✅ 稳定 | <500ms | 10s |
| `/api/report` | POST | 生成评估报告 | ✅ 稳定 | PDF<5s, 图片<3s | 15s |
| `/api/test-files` | GET | 获取测试文件列表 | ✅ 稳定 | <50ms | 5s |
| `/health` | GET | 健康检查 (含 GPU 状态) | ✅ 稳定 | <100ms | 3s |

### 性能监控

- **P95 延迟**: 95% 请求在此时间内完成
- **超时**: 超过此时间返回 504 Gateway Timeout
- **所有读取接口** (`GET`, `HEAD`) 必须 < 200ms 首字节响应
- **写入接口** (`POST`, `DELETE`) 根据操作复杂度有独立超时

### 缓存策略

| 资源类型 | 缓存位置 | TTL | 失效策略 |
|---------|---------|-----|---------|
| 静态资源 (JS/CSS/图标) | 浏览器 HTTP Cache | 1h (带 hash 的文件永久) | 文件名 hash 变更 |
| 可视化图表 (PNG) | 本地文件系统 | 与历史记录同生命周期 | 记录删除时清理 |
| 风格配置 (`styles.yaml`) | 内存 | 服务重启前 | 文件 mtime 变化时重载 |
| 匹配结果 | 内存 dict | 10min | 音频内容哈希 (SHA-256) |
| Demucs 分离结果 | 本地文件系统 | 永久 (手动清理) | 同名文件覆盖 |
| 曲库特征 (v6.0) | SQLite | 永久 (歌曲录入时计算) | 歌曲删除时级联删除 |

### 速率限制

| 接口组 | 限制 | 说明 |
|--------|------|------|
| `/api/upload`, `/api/analyze` | 1 并发 (无队列) | CPU 密集型，排队则阻塞 |
| `/api/compare`, `/api/separate` | 1 并发 | GPU/CPU 密集型 |
| `/api/history/*` | 无限制 | 纯文件 IO，轻量 |
| `/health` | 无限制 | 纯内存，无副作用 |
| 所有接口 | 50MB 请求体上限 | Flask `MAX_CONTENT_LENGTH` |

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
