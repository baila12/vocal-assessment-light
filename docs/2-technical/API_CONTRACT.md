# API 契约文档 v7.0

> 更新: 2026-07-21 | 16 paths in openapi.json | 绞杀者模式: Flask `/old/` + FastAPI `/api/v1/` 共存

---

## v7.0 端点一览 (FastAPI + WebSocket)

| 方法 | 路径 | 标签 | 说明 | v6.3 兼容 |
|------|------|------|------|----------|
| GET | `/health` | health | GPU info + version 7.0.0 | ✅ |
| POST | `/api/v1/upload` | assessment | 上传分析 (FormData) | ✅ /api/upload |
| POST | `/api/v1/analyze` | assessment | 分析已有文件 | ✅ /api/analyze |
| POST | `/api/v1/extract-pitch` | assessment | 音高曲线提取 | ✅ /api/extract-pitch |
| POST | `/api/v1/separate` | assessment | Demucs 人声分离 | ✅ /api/separate |
| GET | `/api/v1/separate/models` | assessment | 分离模型列表 | ✅ |
| POST | `/api/v1/report` | assessment | PDF/图片导出 | ✅ /api/report |
| POST | `/api/v1/compare` | assessment | DTW 双文件对比 | ✅ /api/compare |
| GET | `/api/v1/history` | history | 分页列表 + 日期筛选 | ✅ |
| GET | `/api/v1/history/{id}` | history | 单条详情 | ✅ |
| DELETE | `/api/v1/history/{id}` | history | 删除单条 | ✅ |
| DELETE | `/api/v1/history/batch` | history | 批量删除 (JSON body) | ✅ |
| DELETE | `/api/v1/history/all` | history | 清空全部 | ✅ |
| GET | `/api/v1/test-files` | history | 测试音频列表 | ✅ |
| GET | `/api/v1/audio?file=...` | audio | 音频流 + 路径安全 | ✅ |
| GET | `/api/v1/songs` | songs | 歌曲库 (Phase 4 stub) | NEW |
| WS | `/ws/v1/score` | ws | 实时评分 (Phase 3) | NEW |

### v7.0 核心响应格式 (Pydantic v2)

### POST `/api/v1/upload` 成功响应

```json
{
  "success": true,
  "is_voice": true,
  "total_score": 74.8,
  "level": "良好",
  "stars": "★★",
  "color": "#10b981",

  "voice_quality": {
    "is_voice": true,
    "voice_ratio": 85.2,
    "quality_score": 72.0,
    "silence_ratio": 5.3,
    "harmonic_ratio": 0.82
  },

  "basic_info": {
    "filename": "song.mp3",
    "duration": 180.5,
    "duration_seconds": 180.5,
    "sample_rate": 22050,
    "file_size": "4.2 MB"
  },

  "music_style": {
    "style": "pop",
    "style_cn": "流行",
    "confidence": 0.85,
    "mood": "calm"
  },

  "dl_assessment": {
    "mos_score": 3.5,
    "mos_normalized": 70.0,
    "method": "singmos",
    "confidence": 0.4,
    "available": false
  },

  "scores": {
    "pitch": 79.6,
    "rhythm": 77.1,
    "breath": 56.4,
    "technique": 84.0,
    "artistry": 75.9,
    "volume": 65.0,
    "total": 74.8
  },

  "diagnosis": {
    "pitch": {
      "score": 79.6,
      "mae_cents": 25.3,
      "level": "良好",
      "issues": [],
      "suggestions": []
    },
    "rhythm": { "score": 77.1, "level": "良好", "issues": [], "suggestions": [] },
    "breath": {
      "score": 56.4,
      "level": "合格",
      "long_note_support": 55.0,
      "dynamic_control": 60.0,
      "breath_design": 65.0,
      "breath_technique": 45.0,
      "issues": [],
      "suggestions": ["建议进行长音气息支撑训练"]
    },
    "technique": {
      "score": 84.0,
      "hnr": 20.5,
      "cpp": 2.1,
      "vibrato_quality": 80.0,
      "level": "专业级",
      "issues": [],
      "suggestions": []
    },
    "artistry": {
      "score": 75.9,
      "level": "良好",
      "positives": ["颤音技巧运用出色", "动态对比丰富"],
      "issues": [],
      "suggestions": []
    },
    "critical_issues": [],
    "is_disqualified": false
  },

  "advice": [
    "音准良好，继续保持",
    "建议加强气息支撑训练"
  ],

  "visualization": { ... },
  "timbre": null,
  "phrases": null,
  "waveform": null,
  "pitch_curve": null,
  "volume_info": { "avg_db": -18.0, "peak_db": -2.0, "dynamic_range": 22.0 },
  "pitch_info": { ... },
  "rhythm_info": { ... },
  "emotion_info": { ... }
}
```

### 评分维度说明

**当前 (v6.3) 五维权重** (API 兼容 — 旧版客户端):

| 维度 | 权重 | 测量方法 | 0分含义 | 100分含义 |
|------|------|---------|---------|----------|
| **pitch** (音准) | 28% | MIDI音分偏差MAE | 偏差>120音分 | 偏差<8音分 |
| **rhythm** (节奏) | 20% | Onset间隔CV→偏差比 | 严重脱拍 | 完美对齐 |
| **breath** (气息) | 20% | 四子维度(长音/动态/气口/气声) | 无气息控制 | 专业气息 |
| **technique** (技术) | 18% | HNR(40%)+CPP(30%)+技巧检测(30%) | 无技巧/差HNR | 出色技巧+HNR |
| **artistry** (艺术) | 14% | 颤音/动态/乐句/音高变化 | 平直单调 | 丰富表现力 |
| **volume** (音量) | 独立 | dynamic_range | 无动态范围 | 宽广动态 |

**v7.0 六维目标权重** (详见 [V7_MIGRATION_PLAN.md](../4-process/V7_MIGRATION_PLAN.md)):

| 维度 | 权重 | 子维度 |
|------|------|--------|
| pitch | **10%** | — |
| rhythm | **10%** | — |
| breath | **20%** | 长音支撑 + 动态控制 + 气口设计 + 气声技巧 |
| technique | **25%** | 咬字清晰度(50%) + 气声比(50%) |
| muscle_strength | **25%** | 身体肌肉力量(50%) + 面部肌肉力量(50%) ⚠️ 启发式 |
| artistry | **10%** | 颤音品质 + 动态控制 + 乐句表现力 + 音高变化 |
| timbre_adjustment | ± | +3~-5 独立加减分 ⚠️ 启发式 |

### 等级划分

| 分数区间 | 等级 | 星级 | 颜色 |
|---------|------|------|------|
| 88-100 | 专业级 | ★★★ | #22c55e |
| 78-88 | 优秀 | ★★☆ | #3b82f6 |
| 62-78 | 良好 | ★★ | #10b981 |
| 45-62 | 中等 | ★☆ | #f59e0b |
| 25-45 | 及格 | ★ | #f97316 |
| 0-25 | 待改进 | ☆ | #ef4444 |

---

## 错误响应

```json
{
  "success": false,
  "error": "文件格式不支持"
}
```

---

## v7.0 Vue 迁移指南

### 不变更
- 所有 API 路径和请求格式不变
- JSON 响应格式保持 v5.0 结构
- `AnalysisResult` DTO 作为前后端数据契约

### 可移除 (前端已结构化的部分)
- `v3_compatibility` / `v2_compatibility` 构建器 — 仅用于旧前端兼容
- `visualization` 字段中的内联 CSS — v7.0 由 Vue 组件处理

### 前端对接建议
```typescript
// Vue 3 TypeScript 接口定义
interface AnalysisScores {
  pitch: number;
  rhythm: number;
  breath: number;
  technique: number;
  artistry: number;
  volume: number;
  total: number;
}

interface AnalysisResponse {
  success: boolean;
  is_voice: boolean;
  total_score: number;
  level: string;
  stars: string;
  color: string;
  scores: AnalysisScores;
  diagnosis: Record<string, DiagnosisBlock>;
  advice: string[];
  // ... 其他字段
}
```

### 评分逻辑独立性
所有评分计算在 `services/` 层完成，API 层仅做格式转换。
Vue 前端无需了解评分算法细节 — 只需消费 `scores` 和 `diagnosis` 字段。
