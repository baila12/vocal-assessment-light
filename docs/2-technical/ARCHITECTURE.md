# 系统架构 v7.13

> 更新: 2026-08-07 | 分支: `main` | Flask 已移除 (v7.6) | GSAP 动效系统 | v7.11 评分权重可配置 | v7.12 选歌录音 MVP | v7.13 实时音准对比子系统 Phase 1
>
> **关联文档**: [PROJECT_STATUS.md](../4-process/PROJECT_STATUS.md) | [SCORING.md](SCORING.md) | [frontend/README.md](frontend/README.md)

---

## 一、架构总览

```
┌──────────────────────────────────────────────────────────────┐
│                     Vue 3 SPA (frontend/dist/)                │
│                     Vite dev → :5173  proxy → :8000           │
└──────────────────────────┬───────────────────────────────────┘
                           │ HTTP + WebSocket
┌──────────────────────────▼───────────────────────────────────┐
│                     FastAPI :8000                              │
│  ┌─────────────┐  ┌──────────────┐                            │
│  │ /api/v1/*   │  │ /ws/v1/score │                            │
│  │ REST routes │  │ WebSocket    │                            │
│  └──────┬──────┘  └──────┬───────┘                            │
│         │                │                                    │
│  ┌──────▼────────────────▼───────────────────────────────────┐ │
│  │              backend/ (DDD 四层)                           │ │
│  │                                                           │ │
│  │  interfaces/          application/                        │ │
│  │  ├─ api/routes/       ├─ assessment/                      │ │
│  │  ├─ api/schemas/      │   ├─ scoring_orchestrator.py      │ │
│  │  ├─ api/middleware.py │   ├─ ddd_feature_orchestrator.py  │ │
│  │  └─ ws/score_handler  │   ├─ feature_adapters.py          │ │
│  │                        │   └─ history_subscriber.py        │ │
│  │                        ├─ comparison/                      │ │
│  │  infrastructure/       │   └─ compare_audio.py             │ │
│  │  ├─ audio/             └─ history/                         │ │
│  │  │   ├─ librosa_loader                                     │ │
│  │  │   ├─ pyin_extractor  domain/                            │ │
│  │  │   ├─ demucs_sep.     ├─ assessment/ (7 scorers)         │ │
│  │  │   ├─ fcpe_extractor  ├─ audio/ (13 extractors)          │ │
│  │  │   └─ protocols.py    └─ comparison/ (entities+services) │ │
│  │  └─ persistence/                                            │ │
│  │      ├─ json_history                                       │ │
│  │      └─ sqlite_song_repo  shared/                           │ │
│  └──────────────────────────┬────────────────────────────────┘ │
└──────────────────────────────┼──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│              旧服务层 (逐步废弃)                                   │
│  services/dl_services/ (4 活跃: VAD/Style/自参照DTW, Pro 模式)     │
│    — v7.12 已删死代码: model_manager/ 子包 + 桩 + features:types  │
│  services/ (audio, separation, phrase, visualization...)         │
│  api/ (business/ 桥梁 + schemas, Flask routes 已移除 v7.6)       │
└──────────────────────────────────────────────────────────────────┘
```

### 端口策略

| 模式 | 后端 | 前端 |
|------|------|------|
| 开发 | `python backend/main.py` → :8000 | `cd frontend && npm run dev` → :5173 (proxy → :8000) |
| 生产 | FastAPI serve `frontend/dist/` + SPA fallback | 同后端 :8000 |
| Electron | `--port=0` OS 动态分配 | `window.BACKEND_URL` 注入 |

---

## 二、评分管线

### 特征提取路径

```
Raw Audio (y, sr)
  │
  ├─ normalize_loudness()           # RMS → 0.05
  ├─ [Pro] detect_mixed_audio()    # 混合音频检测
  │   └─ [Pro] Demucs separate     # 人声分离 (GPU: 25s, CPU: 120s)
  │       └─ re-extract f0
  │
  └─ DddFeatureExtractionOrchestrator
       │
       ├─ L0: Acoustic (HNR / CPP / HPSS / Voicing)
       ├─ L1: Pitch + Rhythm
       ├─ L2: Breath + Technique + Timbre
       └─ L3: Muscle + Artistry
```

### 评分权重 (v7.11 当前生效, 单一数据来源 ScoringWeights)

| 维度 | 权重 | 子维度 | 文献级别 |
|------|:---:|------|:------:|
| Pitch (音准) | 13% | MAE(40%) + RPA(25%) + RCA(10%) + Gross(15%) + Smooth(5%) + Octave(5%) | A |
| Rhythm (节奏) | 12% | Onset CV + irregularity penalty + is_clean_vocal recalibration | B |
| Breath (气息) | 22% | 长音支撑(40%) + 动态控制(25%) + 气口设计(20%) + 气声技巧(15%) | B |
| Technique (技术) | 25% | 咬字清晰度(50%) + 气声比(50%) | C |
| Muscle (肌肉) ⚠️ | 15% | 身体力量(50%) + 面部力量(50%) — HEURISTIC | C |
| Artistry (艺术) | 13% | 颤音(30%) + 动态(30%) + 乐句(25%) + 音高变化(15%) | D |
| **Total** | **100%** | | |
| Timbre (音色) ⚠️ | ±3~-5 | 加减分项, 不占权重, clamp[0,100] | B |

> v7.11: 权重收敛为 `ScoringWeights` 值对象 (frozen dataclass, `backend/domain/assessment/scoring_weights.py`)，作为六维权重的单一数据来源。`Score.weighted()` 方法均委托到 `ScoringWeights.default()`。提供 4 个风格预设 (pop/bel_canto/ethnic/rap) 供评分权重 API (`GET /api/v1/scoring/presets`, `POST /api/v1/scoring/apply-weights`) 使用。
>
> ⚠️ 标记维度使用启发式代理指标，非直接生理测量。详见 [SCORING_ALGORITHM_IMPROVEMENT_PLAN.md](SCORING_ALGORITHM_IMPROVEMENT_PLAN.md)。

### 已知问题

| 问题 | 影响 | 计划 |
|------|------|------|
| ~~气声比 HNR 占 70% 权重~~ | ✅ v7.4 已修复: CPPS(40%)+HNR(25%) reconst | 已解决 |
| ~~咬字缺失 ZCR + Spectral Centroid~~ | ✅ v7.6 已修复: Rathi & Hsu 2:1:1 对齐 | 已解决 |
| 无颤音 → 艺术表现 0 分 | 流行/R&B 受系统性歧视 | [P0 修复](SCORING_ALGORITHM_IMPROVEMENT_PLAN.md#五p0-3-艺术表现无颤音-fallback) |
| 音色置信度门控在生产中始终归零 | 音色维度完全失效 | [P1 修复](SCORING_ALGORITHM_IMPROVEMENT_PLAN.md#八p1-2-音色八维剖面增强) |
| ~~肌肉权重 25%，文献建议 15%~~ | ✅ v7.4 已修复 (25%→15%) | 已解决 |

---

## 三、DDD 四层结构

### domain/ — 领域层 (纯逻辑, 零外部依赖)

```
domain/
├── assessment/                     # 评分领域
│   ├── value_objects.py            # 7 个 frozen dataclass (PitchScore…TimbreAdjustment)
│   ├── services.py                 # ScoringDomainService.calculate_total()
│   ├── scoring_weights.py          # v7.11: 六维权重值对象 + 风格预设 (单一数据来源)
│   ├── events.py                   # AssessmentCompleted 领域事件
│   ├── errors.py                   # InvalidScoreError
│   ├── feature_flags.py            # DimensionFlags (独立开关每个维度)
│   ├── pitch_scorer.py             # 六指标加权融合 (10%)
│   ├── rhythm_scorer.py            # Onset CV + irregularity (10%)
│   ├── breath_scorer.py            # 四子维度 + audiofeat GNE/CPPS (20%)
│   ├── technique_scorer.py         # 咬字 + 气声比 + audiofeat Jitter/Shimmer/CQ (25%)
│   ├── muscle_scorer.py            # 五维身体/面部代理 ⚠️ (25%)
│   ├── artistry_scorer.py          # 四维独立声学信号 (10%)
│   └── timbre_adjuster.py          # 音色加减分 ⚠️ (±3~-5)
│
├── audio/                           # 音频特征领域
│   ├── feature_types.py            # AcousticFeatures frozen dataclass
│   ├── feature_protocols.py        # 提取器 Protocol 接口
│   ├── audio_utils.py              # normalize_loudness + find_vocal_segments
│   ├── acoustic_feature_extractor.py  # L0: HNR/CPP/HPSS/Voicing/Mixed
│   ├── pitch_extractor.py          # L1: MAE/RPA/RCA/Gross/Octave/Smooth/Breaks
│   ├── rhythm_extractor.py         # L1: Onset CV/Irregularity/Off-beat
│   ├── breath_extractor.py         # L2: 长音/动态/气口/气声/decay/stability
│   ├── technique_extractor.py      # L2: Vibrato/Slides/Falsetto/Staccato/Legato
│   ├── timbre_extractor.py         # L2: Centroid/Cluster/Harmonic/Nasality
│   ├── muscle_extractor.py         # L3: Body/Facial proxies
│   ├── artistry_extractor.py       # L3: Vibrato/Dynamic/Phrase/Crescendo
│   └── audiofeat_extractor.py      # 可选: 130+ 谱特征 (CPPS/GNE/Jitter/…)
│
├── comparison/                      # v7.3: DDD 对比领域
    ├── entities.py                  # ComparisonResult, AlignmentData (frozen)
    ├── value_objects.py             # ComparisonScores, DimensionComparisonScore (frozen)
    └── services.py                  # ComparisonScoringService (四维加权)

└── songs/                           # v7.9: 曲库领域 (v7.12: +vocal_range 音域)
    ├── entities.py                  # Song (frozen dataclass)
    ├── value_objects.py             # SongMetadata (v7.12: +vocal_range), 难度/风格
    └── repository.py                # SongRepository 抽象接口

└── songs_pitch/                     # v7.13: 参考音高领域 (实时音准对比数据源)
    ├── value_objects.py             # SongPitchCurve (frozen, NaN→0.0, 序列化)
    ├── repository.py                # PitchCacheRepository Protocol
    └── services.py                  # PitchExtractionService (librosa.yin 纯函数)
```

### application/ — 应用层 (编排, 无领域逻辑)

```
application/
├── assessment/
│   ├── scoring_orchestrator.py      # 统一评分入口 (calculate + calculate_ddd)
│   ├── ddd_feature_orchestrator.py  # DDD 特征提取编排 (L0→L1→L2→L3)
│   ├── feature_adapters.py          # 旧 AudioFeaturesResult → DDD Features 桥梁
│   ├── analyze_audio.py             # AnalyzeAudioUseCase
│   ├── stream_score.py              # StreamScoreUseCase (WebSocket 实时)
│   └── history_subscriber.py        # 评分完成 → 自动保存历史
├── comparison/
│   └── compare_audio.py             # CompareAudioUseCase
└── history/
    └── query_history.py             # QueryHistoryUseCase
```

### infrastructure/ — 基础设施层 (外部依赖)

```
infrastructure/
├── config.py                        # Pydantic Settings (VAS_* env vars)
├── audio/
│   ├── protocols.py                 # AudioLoader/Separator/F0Extractor 接口
│   ├── librosa_loader.py            # librosa.load 实现
│   ├── pyin_extractor.py            # PYIN f0 实现
│   ├── demucs_separator.py          # Demucs 分离实现 + GPU 检测
│   └── fcpe_extractor.py            # FCPE f0 实现 (GPU 优先)
└── persistence/
    ├── json_history_repo.py          # JSON 文件历史存储
    └── sqlite_song_repo.py           # SQLite 歌曲库存储
```

### interfaces/ — 接口层 (HTTP/WS 适配器)

```
interfaces/
├── api/
│   ├── routes/
│   │   ├── assessment.py            # POST upload/analyze/extract-pitch/separate/compare/report
│   │   ├── history.py               # GET/DELETE history
│   │   ├── audio.py                 # GET audio streaming
│   │   ├── songs.py                 # POST/GET/GET:id/DELETE songs (v7.9 CRUD)
│   │   ├── flags.py                 # GET /api/v1/flags (v7.7)
│   │   ├── scoring.py               # v7.11: GET /scoring/presets + POST /scoring/apply-weights
│   │   └── health.py                # GET /health (GPU status)
│   ├── schemas/
│   │   ├── assessment.py            # AnalyzeRequest/UploadResponse
│   │   ├── history.py               # HistoryRecordOut/HistoryListResponse
│   │   ├── scoring.py               # v7.11: ApplyWeightsRequest/ScoringPresetsResponse
│   │   └── common.py                # ErrorResponse
│   ├── middleware.py                 # SecurityHeaders + RateLimit + MaxBodySize
│   └── deps.py                      # FastAPI Depends (Settings, EventBus)
└── ws/
    ├── score_handler.py             # WebSocket 实时评分
    ├── schemas.py                   # WS 消息类型
    └── streaming_session.py          # 流式会话管理
```

### shared/ — 共享内核

```
shared/
├── domain_types.py                  # ScoreValue, ScoreLevel, ScoreGrade
├── event_bus.py                     # 进程内 EventBus (观察者模式)
├── math_utils.py                    # safe_float, safe_clamp
└── result.py                        # Result[T, E] 类型
```

---

## 四、安全中间件

| 中间件 | 层 | 配置 |
|--------|-----|------|
| SecurityHeadersMiddleware | FastAPI | CSP, X-Content-Type-Options, X-Frame-Options, HSTS |
| RateLimitMiddleware | FastAPI | 120/min global, 20/min upload, 10/min WebSocket |
| MaxBodySizeMiddleware | FastAPI | 50MB (413 Payload Too Large) |

---

## 五、数据流

### Quick 模式 (~20s CPU)

```
POST /api/v1/upload (FormData)
  │
  ├─ 1. 文件校验 (扩展名 + 50MB limit)
  ├─ 2. librosa.load → 降采样 16kHz
  ├─ 3. PYIN f0 提取 (~5s)           ← 最大瓶颈 (25%)
  ├─ 4. Onset + RMS + Chroma + Vibrato
  ├─ 5. DDD 特征提取 (~10s)
  │     ├─ L0: Acoustic (HNR/CPP/HPSS)
  │     ├─ L1: Pitch + Rhythm
  │     ├─ L2: Breath + Technique + Timbre
  │     └─ L3: Muscle + Artistry
  ├─ 6. 六维评分计算 (<0.5s)
  └─ 7. 响应 JSON + EventBus → 保存历史
```

### Pro 模式 (~155s CPU / ~55s GPU)

```
Quick 全部 (20s)
  +
  ├─ 混合音频检测 (HPSS 五特征融合, 6s)
  ├─ Demucs 人声分离 (120s CPU / 25s GPU)  ← 最大瓶颈 (77%)
  ├─ 重新 PYIN f0 (5s)
  ├─ DL 模型推理 (VAD + Style + DTW + StyleAnalysis, ~3s)
  ├─ 可视化生成 (matplotlib 3张图, 8s)     ← 可异步
  ├─ 逐句评分 (5s)
  └─ 音色分析 (2s)
```

### WebSocket 实时流

```
AudioWorklet → Float32Array → ws.send() → numpy.frombuffer (零拷贝)
  │
  ├─ 每 2048 samples (~128ms) 推送一帧
  ├─ StreamingSession 累积 (<120s buffer)
  ├─ 每 2s 计算 incremental score
  ├─ 每 2s 新音频段 PYIN → pitch_update (v7.13: 样本驱动, 绝对时间轴)
  ├─ start 消息可携带 song_id (v7.12: 选歌录音参考歌曲, 存入 session)
  └─ 录音完成 → 轻量评分 (<1s, 纯 NumPy, 无 DL; v7.13: ScoringWeights 单一权重来源)
```

---

## 六、绞杀者状态

| 层 | 状态 | 说明 |
|------|:--:|------|
| DDD domain/audio/ | ✅ 13/13 模块自包含 | 零 `services/features/` 依赖 |
| DDD domain/assessment/ | ✅ 7 scorers | DDD 唯一评分路径 |
| DDD domain/comparison/ | ✅ v7.3 完成 | 实体 + 值对象 + 领域服务 |
| `services/features/` | ✅ 已移除 (v7.12) | types.py 死代码已删 |
| `services/dl_services/` | ⚠️ 4 活跃 | Style/VAD/自参照DTW 仍在 Pro 模式; v7.12 已删 8 个死文件 (model_manager 子包等), DDD 迁移为独立工程 |
| `api/routes/` (Flask) | ✅ 已移除 (v7.6) | Flask 路由文件已删除 |
| `web/static/js/` + `web/static/app.js` | ✅ 已移除 (v7.1.4) | 旧 vanilla JS 前端 |

---

## 七、关键设计决策 (ADR)

| ADR | 决策 | 理由 |
|-----|------|------|
| **ADR-1** | 嵌入式 Python (非 PyInstaller) | 启动 <2s vs 10-15s, 增量更新 KB 级 |
| **ADR-2** | 肌肉 & 音色 → HEURISTIC | 纯音频无法测量声门下压/肌肉激活 |
| **ADR-3** | openapi.json 文件驱动 (非 URL) | 前后端并行构建, CI 无需后端 |
| **ADR-4** | 绞杀者模式 | 每 Phase 可独立运行, 新旧共存 |
| **ADR-6** | 评分不使用 DL 模型 | SingMOS/Wav2Vec2/wvmos 跨域不可靠 |
| **ADR-7** | DTW 降级为特征提供者 | 纯 DTW 相关度 0.52, 融合后 0.87 |

---

## 八、性能概要

| 指标 | Quick | Pro CPU | Pro GPU |
|------|:-----:|:------:|:------:|
| 端到端耗时 | ~20s | ~155s | ~55s |
| 最大瓶颈 | PYIN f0 (5s, 25%) | Demucs (120s, 77%) | Demucs (25s, 45%) |
| 内存峰值 | ~170MB | ~1050MB | ~800MB |
| 已知优化潜力 | 2x → ~10s | 3x → ~50s | 2.5x → ~22s |

> 详见 [PERFORMANCE_ANALYSIS_AND_OPTIMIZATION.md](PERFORMANCE_ANALYSIS_AND_OPTIMIZATION.md)

---

## 九、目录结构 (v7.12 实际)

```
vocal_assessment_light/
├── backend/                         # DDD 四层架构 ★主代码
│   ├── main.py                      # FastAPI 入口 + GPU 检测 + 中间件
│   ├── domain/                      # 领域层 (纯逻辑): assessment/audio/comparison/songs
│   ├── application/                 # 应用层 (编排)
│   ├── infrastructure/              # 基础设施层 (librosa/Demucs/DB)
│   ├── interfaces/                  # 接口层 (REST + WebSocket)
│   ├── legacy/                      # V6 历史数据迁移模型 (Flask 已移除 v7.6)
│   ├── migrations/                  # Alembic (预留)
│   └── shared/                      # 共享内核
│
├── frontend/                        # Vue 3 SPA ★当前前端
│   ├── src/
│   │   ├── views/                   # 7 页面 (Home/Report/History/Compare/Sing/Songs)
│   │   │   └── SingView.vue        #   v7.12 选歌录音 (选歌区/歌曲信息/WS song_id)
│   │   │   └── SongsView.vue        #   v7.10 曲库卡片网格页 (v7.12: 选择此歌按钮)
│   │   ├── components/              # 7 共享 + 3 布局组件
│   │   │   └── scoring/             # v7.11: ScoringWeightsPanel.vue 权重配置面板
│   │   ├── stores/                  # 6 Pinia stores
│   │   │   ├── songs.store.ts       #   v7.10 曲库状态管理
│   │   │   └── scoring.store.ts     #   v7.11 评分权重预设/滑块/归一化
│   │   ├── composables/             # 5 composables
│   │   ├── api/                     # API 客户端 (零硬编码 URL)
│   │   ├── router/                  # Vue Router (hash history)
│   │   └── types/                   # TypeScript 类型
│   ├── electron/                    # Electron 主进程 + preload
│   └── dist/                        # 生产构建
│
├── api/                             # Flask 遗留 (v7.6 路由已移除, 仅 business 桥梁)
│   ├── business/                    # analyze_and_score 桥梁 (legacy)
│   ├── schemas.py                   # Pydantic 请求/响应 (legacy)
│   └── errors.py + response_builder.py
│
├── services/                        # 旧服务层 (部分仍在使用)
│   ├── audio_service.py             # 音频分析主管线
│   ├── separation_service.py        # Demucs 分离 (subprocess)
│   ├── dl_services/                 # DL 模型 (4 活跃: VAD/Style/自参照DTW; v7.12 已删 8 死文件)
│   └── (phrase/visualization...)
│
├── config/                          # 配置 (Flask legacy + styles.yaml)
├── repositories/                    # 数据层 (JSON history + SQLite songs)
├── web/static/                      # 旧前端已移除 (v7.1.4), 目录可能为空
│
├── tests/                           # 509 tests (DDD 435 + 集成 53 + 扩展 21)
├── docs/                            # 文档
├── models/                          # 预训练模型文件
├── data/                            # 应用数据 (history.json)
└── uploads/                         # 上传目录
```

---

## 十、技术栈

| 层 | 技术 |
|------|------|
| 后端框架 | FastAPI (uvicorn, workers=1) |
| ~~遗留框架~~ | ~~Flask 3.0~~ — 已于 v7.6 完全移除 |
| 前端框架 | Vue 3.5 + TypeScript + Vite 5 |
| UI 组件 | Element Plus 2.14 |
| 状态管理 | Pinia 2.3 |
| 路由 | Vue Router 4.6 (hash history) |
| 图表 | Chart.js 4.5 + vue-chartjs |
| 动画 | GSAP 3.15 |
| 桌面打包 | Electron 28 (配置就绪) |
| 音频处理 | librosa + parselmouth + pyworld |
| 深度学习 | PyTorch + ONNX Runtime + Demucs |
| 特征提取 | audiofeat 1.1.1 (可选) |
| f0 检测 | PYIN (librosa) + TorchCREPE fallback + FCPE |
| 数据存储 | JSON 文件 + SQLite (曲库) |
| 配置 | Pydantic Settings (FastAPI) |
| 测试 | pytest 509 tests (DDD 435 + 集成 53 + 扩展 21) + Vitest 68 tests |
