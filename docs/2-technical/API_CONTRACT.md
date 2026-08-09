# API 契约文档 v7.14

> 更新: 2026-08-09 | FastAPI `/api/v1/` (Flask 已移除 v7.6) | 633 测试 GREEN (DDD 541 + 集成 71 + 扩展 21)

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
| POST | `/api/v1/compare` | DTW 双文件对比 [v7.13 P5: 响应附加 `standard_pitch`/`user_pitch` (参考/用户 F0 曲线) + `low_alignment_segments` (低置信度段落), 向后兼容] | — | — |
| GET | `/api/v1/history` | 历史分页列表 + 日期筛选 | ✅ | ✅ |
| GET | `/api/v1/history/{id}` | 单条详情 | ✅ | ✅ |
| DELETE | `/api/v1/history/{id}` | 删除单条 | ✅ | ✅ |
| DELETE | `/api/v1/history/batch` | 批量删除 (JSON body) | ✅ | ✅ |
| POST | `/api/v1/history/batch-delete` | 批量删除 (POST) | ✅ | ✅ |
| DELETE | `/api/v1/history/all` | 清空全部 | ✅ | ✅ |
| GET | `/api/v1/test-files` | 测试音频列表 | ✅ | ✅ |
| GET | `/api/v1/audio?file=...` | 音频文件流 (路径安全校验; v7.10: 白名单新增 songs_dir，支持歌曲库音频播放) | ✅ | ✅ |
| POST | `/api/v1/songs` | 添加歌曲 (multipart 文件+元数据; v7.12: +`vocal_range` 音域) [v7.9] | ✅ | ✅ |
| GET | `/api/v1/songs` | 曲库列表 (page/limit/style/difficulty/search) [v7.9] | ✅ | ✅ |
| GET | `/api/v1/songs/{id}` | 歌曲详情 [v7.9] | ✅ | ✅ |
| DELETE | `/api/v1/songs/{id}` | 删除歌曲 [v7.9] | ✅ | ✅ |
| GET | `/api/v1/songs/{id}/pitch` | 歌曲参考 F0 曲线 (选歌录音参考线数据源; 缓存) [v7.13] | ✅ | ✅ |
| POST | `/api/v1/songs/{id}/compare` | 上传录音与选中歌曲 DTW 对比 (multipart user_file+style) [v7.13] | ✅ | ✅ |
| POST | `/api/v1/songs/match` | 上传录音自动匹配歌曲库标准歌曲 → 最佳匹配 + Top-N 候选 (multipart file+top_n; 无匹配 fallback_reason) [v7.14] | ✅ | ✅ |
| GET | `/api/v1/flags` | Feature Flag + GPU + 模型状态 (v7.7) | ✅ | ✅ |
| GET | `/api/v1/scoring/presets` | 评分权重预设 — 默认 + 4 风格 (v7.11) | ✅ | ✅ |
| POST | `/api/v1/scoring/apply-weights` | 维度分数+权重→总分/等级 — 纯前端重算 (v7.11) | ✅ | ✅ |
| WS | `/ws/v1/score` | 实时流式评分 | — | — |

---

## 核心响应格式

### 分析响应 (upload/analyze)

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

### 评分权重 API (v7.11)

**GET `/api/v1/scoring/presets`** --- 返回默认权重 + 4 风格预设:

```json
{
  "data": {
    "default": {
      "name": "default", "label": "默认 (v7.4)",
      "weights": { "pitch": 0.13, "rhythm": 0.12, "breath": 0.22,
                   "technique": 0.25, "muscle": 0.15, "artistry": 0.13 }
    },
    "presets": [
      { "name": "pop", "label": "流行",
        "weights": { "pitch": 0.21, "rhythm": 0.17, "breath": 0.13,
                     "technique": 0.17, "muscle": 0.15, "artistry": 0.17 } },
      { "name": "bel_canto", "label": "美声",
        "weights": { "pitch": 0.25, "rhythm": 0.13, "breath": 0.21,
                     "technique": 0.17, "muscle": 0.15, "artistry": 0.09 } },
      { "name": "ethnic", "label": "民族",
        "weights": { "pitch": 0.24, "rhythm": 0.15, "breath": 0.15,
                     "technique": 0.15, "muscle": 0.15, "artistry": 0.16 } },
      { "name": "rap", "label": "说唱",
        "weights": { "pitch": 0.08, "rhythm": 0.30, "breath": 0.09,
                     "technique": 0.13, "muscle": 0.15, "artistry": 0.25 } }
    ],
    "default_preset": "pop"
  }
}
```

**POST `/api/v1/scoring/apply-weights`** --- 纯前端重算 (不重新分析音频):

请求 (`preset` 和 `weights` 二选一, 都不传则用 default):
```json
{
  "dimension_scores": {
    "pitch": 90, "rhythm": 50, "breath": 70,
    "technique": 70, "muscle": 70, "artistry": 70
  },
  "preset": "rap",
  "weights": null,
  "timbre_adjustment": 0
}
```

响应:
```json
{
  "data": {
    "total_score": 67.7,
    "level": "良好",
    "grade": "B",
    "color": "#10b981",
    "stars": "★★",
    "weighted_dimensions": {
      "pitch": 7.2, "rhythm": 15.0, "breath": 6.3,
      "technique": 9.1, "muscle": 10.5, "artistry": 17.5
    },
    "applied_weights": {
      "pitch": 0.08, "rhythm": 0.30, "breath": 0.09,
      "technique": 0.13, "muscle": 0.15, "artistry": 0.25
    },
    "applied_preset": "rap"
  }
}
```

**校验规则 (400 Bad Request)**:
- `preset` 和 `weights` 同时传入 → `"preset 和 weights 只能二选一"`
- 权重总和 != 100% → `"权重总和必须为 100%, 当前为 XX%"`
- 单维度 > 50% → `"[维度名] 单个维度权重不能超过 50%, 当前 XX%"`
- 缺失维度分数 → `"缺少维度分数: [维度名列表]"`
- 未知预设名 → `"未知风格预设: XX"`
- 负数权重 → `"[维度名] 权重不能为负: X.XX"`

---

## 自动匹配 API (v7.14)

### POST `/api/v1/songs/match`

上传用户演唱录音 → 提取 BPM/chroma/调性/时长特征 → 与歌曲库标准歌曲特征匹配 → 返回最佳匹配 + Top-N 候选。

**请求** (multipart/form-data):
| 字段 | 类型 | 必需 | 说明 |
|------|------|:--:|------|
| `file` | File | ✅ | 用户演唱录音 (wav/mp3/m4a/flac) |
| `top_n` | int | ❌ | 候选数量 (默认 3, 1-10) |

**响应**:
```json
{
  "success": true,
  "matched": true,
  "matched_song": { "id": "song-uuid", "title": "晴天", "artist": "周杰伦", "confidence": 0.94 },
  "candidates": [
    {
      "song_id": "song-uuid", "title": "晴天", "artist": "周杰伦", "confidence": 0.94,
      "factors": { "bpm": 0.95, "chroma": 0.96, "key": 1.0, "duration": 0.87 },
      "bpm_diff": 1.2, "key_diff_semitones": 0, "detected_key": "C"
    }
  ],
  "fallback_reason": "",
  "detected_key": "C",
  "partial": false,
  "elapsed_ms": 234
}
```

**字段说明**:
- `matched`: 是否命中 (置信度 ≥ `MATCH_THRESHOLD = 0.60`)
- `matched_song`: 最佳匹配摘要 (仅 matched=true 时非空); `null` 表示未命中
- `candidates`: Top-N 候选 (按置信度降序), 每个含 `factors {bpm,chroma,key,duration}` 子分数 + `bpm_diff` (绝对差) + `key_diff_semitones` (+=高) + `detected_key` (检测调性)
- `fallback_reason`: 未命中原因, 取值 `no_match` (全低于阈值) / `no_profiles` (歌曲库无匹配特征) / `audio_too_short` (< 3s) / `timeout` (特征预算超时, partial=true)
- `partial`: 预计算超时导致部分歌曲未参与匹配

**置信度公式** (确定性, 供单元测试构造验证):
```
confidence = 0.30*bpm + 0.40*chroma + 0.15*key + 0.15*duration
bpm_score    = 1 / (1 + (|Δbpm| / max(user_bpm, profile_bpm)) / 0.10)   # 精确=1.0, ±9%≈0.53
chroma_score = max over 12 rotations(cosine(user_chroma, rotate(profile_chroma)))  # 转调不变
key_score    = max(0, 1 - pitch_class_distance/6)                        # 同调=1.0, +2 半音=0.667
duration_score = 1 / (1 + |log2(user_dur / profile_dur)|)                # 0.9x≈0.87
```

**错误** (400 Bad Request): 空文件 / 解码失败 → `{"detail": "..."}`。

### POST `/api/v1/upload` — 可选 `auto_match` 标志

上传时传 `auto_match: true` (FormData 布尔), 响应额外注入 (路由层, 不侵入评分业务; 失败优雅降级不阻塞评分):
```json
{
  "success": true,
  "... 原有评分字段 ...",
  "matched_song": { "id": "...", "title": "...", "artist": "...", "confidence": 0.91 },
  "matched_candidates": [ { "song_id": "...", "title": "...", "artist": "...", "confidence": 0.91, "factors": {...}, "bpm_diff": 0.5, "key_diff_semitones": 0, "detected_key": "G" } ],
  "fallback_reason": ""
}
```
- `auto_match=false` (默认): 不注入上述字段
- 歌曲库为空 / 匹配特征缺失 / 音频过短: `matched_song=null` + `fallback_reason` 透传

---

## 安全

| 机制 | 配置 |
|------|------|
| Security Headers | CSP, X-Content-Type, X-Frame, HSTS, Referrer-Policy |
| Rate Limit (FastAPI) | 120/min global, 20/min upload, 10/min WebSocket |
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
