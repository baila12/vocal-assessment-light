# API 接口文档

> 更新日期: 2026-05-07

---

## 接口列表

| API | 方法 | 功能 | 状态 |
|-----|------|------|------|
| `/api/upload` | POST | 上传音频并分析 | ✅ 稳定 |
| `/api/analyze` | POST | 分析已存在音频 | ✅ 稳定 |
| `/api/compare` | POST | 对比分析两个音频 | 🟡 优化中 |
| `/api/compare/v2` | POST | 对比分析（新版DTW） | 🔴 待实现 |
| `/api/benchmark` | POST | 创建标准音频基准库 | 🔴 待实现 |
| `/api/benchmark/<id>` | GET | 获取基准库特征 | 🔴 待实现 |
| `/api/separate` | POST | 人声分离 | ✅ 稳定 |
| `/api/separate/models` | GET | 获取分离模型列表 | ✅ 稳定 |
| `/api/history` | GET | 历史记录（支持分页） | ✅ 稳定 |
| `/api/history/<id>` | DELETE | 删除记录 | ✅ 稳定 |
| `/api/history/batch` | DELETE | 批量删除 | ✅ 稳定 |
| `/api/report` | POST | 生成评估报告 | ✅ 稳定 |
| `/health` | GET | 健康检查 | ✅ 稳定 |

---

## 上传接口

```
POST /api/upload
Content-Type: multipart/form-data

参数:
- file: 音频文件 (必需)
- mode: quick | professional (可选，默认quick)

返回: {
    success: true,
    scores: { pitch, rhythm, breath, technique, emotion },
    total_score: 85.2,
    level: "良好",
    diagnosis: [...],
    advice: [...],
    basic_info: { filename, duration, ... }
}
```

---

## 对比分析接口 (当前版本)

```
POST /api/compare
Content-Type: multipart/form-data

参数:
- file: 用户音频 (必需)
- standard_file: 标准音频 (可选)

返回: {
    success: true,
    data: {
        score: 88.5,
        level: "良好",
        pitch_match_rate: 85.0,
        rhythm_match_rate: 90.0,
        avg_cents_error: 15.2,
        diagnosis: [...],
        standard: { ... },
        user: { ... },
        comparison: { ... }
    }
}
```

**已知问题**: 相同音频得分仅88分，算法需优化

---

## 对比分析接口 v2 (待实现)

```
POST /api/compare/v2
Content-Type: multipart/form-data

参数:
- file: 用户音频 (必需)
- benchmark_id: 基准库ID (可选，优先使用)
- standard_file: 标准音频 (可选，无基准库时使用)
- style: pop | classical | folk | rap (可选，默认pop)

返回: {
    success: true,
    data: {
        overall_score: 95.2,          # 综合评分
        level: "优秀",
        confidence: 0.92,             # 对齐置信度

        dimensions: {
            pitch: { score: 92, avg_cents: 12, max_cents: 45 },
            rhythm: { score: 88, avg_offset_ms: 80 },
            volume: { score: 90, match_rate: 0.85 },
            breath: { score: 95, stability: 0.92 }
        },

        alignment: {
            warp_path: [[0,0], [1,1], ...],  # DTW对齐路径
            global_offset: 0.5,              # 全局时间偏移(秒)
            sentence_count: 12
        },

        problem_frames: [
            { time: 15.2, type: "pitch_high", cents: 55 },
            { time: 32.1, type: "rhythm_late", offset_ms: 150 }
        ],

        suggestions: [...]
    }
}
```

---

## 基准库接口 (待实现)

### 创建基准库

```
POST /api/benchmark
Content-Type: multipart/form-data

参数:
- file: 标准音频文件 (必需)
- name: 基准库名称 (可选，默认文件名)

返回: {
    success: true,
    benchmark_id: "bm_abc123",
    name: "歌曲名",
    features: {
        duration: 180.5,
        tempo: 120,
        key_signature: "C_major",
        onset_count: 45,
        beat_count: 90
    },
    created_at: "2026-05-07T10:30:00Z"
}
```

### 获取基准库

```
GET /api/benchmark/<benchmark_id>

返回: {
    success: true,
    benchmark: {
        id: "bm_abc123",
        name: "歌曲名",
        version: "2.0",
        features: {
            pitch_frames: [...],      # 基频序列
            energy_frames: [...],     # 能量序列
            onset_times: [...],       # 音符边界
            beat_times: [...],        # 节拍点
            tempo: 120,
            duration: 180.5
        }
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

返回: {
    success: true,
    vocals_path: "/path/to/vocals.mp3",
    accompaniment_path: "/path/to/no_vocals.mp3",
    duration: 180.5,
    model_used: "htdemucs_ft"
}
```

---

## 历史记录接口

```
GET /api/history?page=1&limit=20

返回: {
    success: true,
    records: [
        {
            id: "rec_001",
            filename: "歌曲.mp3",
            filepath: "/path/to/file",
            total_score: 85.2,
            scores: { ... },
            level: "良好",
            created_at: "2026-05-07T10:00:00Z"
        }
    ],
    total: 100,
    page: 1,
    limit: 20
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

返回: {
    success: true,
    pdf_path: "/path/to/report.pdf",   # format=pdf时
    image_path: "/path/to/report.png"  # format=image时
}
```

---

## 响应格式规范

所有API遵循统一响应格式:

```typescript
interface ApiResponse<T> {
    success: boolean;
    data?: T;
    error?: string;
    meta?: {
        total: number;
        page: number;
        limit: number;
    };
}
```

---

## 错误码

| 错误码 | 说明 |
|--------|------|
| 400 | 参数错误 (ValidationError) |
| 403 | 权限拒绝 (ForbiddenError) |
| 404 | 资源不存在 (NotFoundError) |
| 500 | 服务器错误 (InternalError) |
