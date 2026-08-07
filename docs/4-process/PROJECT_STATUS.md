# 项目状态

> 更新: 2026-08-07 | 版本: **v7.13** | 分支: `main`

---

## 一、架构

```
Vue 3 SPA (frontend/dist/)  →  FastAPI (:8000)
                                      │
    ┌─────────────────────────────────┼──────────────────────────┐
    │  backend/ (DDD 四层)            │  旧服务层 (残留)           │
    │  domain/assessment/ (7 scorers) │  services/dl_services/ (11)│
    │  domain/audio/ (14 模块自包含)   │  services/audio_service.py │
    │  domain/comparison/ (v7.3)      │  api/business/ (bridge)   │
    │  domain/songs/ (v7.9)           │                           │
    │  application/ (orchestrator)    │  services/features/types.py│
    │  infrastructure/audio/ (4)      │                           │
    │  interfaces/api/ + ws/          │  (Flask /old 已移除 v7.6) │
    │  shared/ (EventBus, math_utils) │  (svc/features/ 已移除)   │
    └─────────────────────────────────┴──────────────────────────┘
```

### 评分路径 (v7.7: DDD + audiofeat 增强 + Flag 桥接)

| 路径 | 特征提取 | 评分 | 状态 |
|------|---------|------|:----:|
| **DDD 原生** | `DddFeatureExtractionOrchestrator` → 14 自包含模块 + AudiofeatExtractor (20+ 特征) | `ScoringOrchestrator.calculate_ddd(audiofeat=...)` | ✅ 生产 |

**Flag 系统 (v7.7)**:
```
API Routes → FeatureFlags.for_quick()/.for_professional() [services/feature_flags.py]
  → to_dimension_flags() [backend/shared/flag_bridge.py] ← 桥接层
    → DimensionFlags(enable_audiofeat=True) [backend/domain/assessment/feature_flags.py]
      → DddFeatureExtractionOrchestrator(flags=DimensionFlags)
        → AudiofeatExtractor → AudiofeatFeatures (CPPS/GNE/HNR_praat/Jitter/Shimmer...)
          → ScoringOrchestrator → BreathScorer/TechniqueScorer/MuscleScorer/TimbreAdjuster
```

### 六维权重 (v7.4+, v7.6 保持)

| 维度 | 权重 | 说明 |
|------|:----:|------|
| Pitch (音准) | **13%** | 最可靠维度 (文献 A 级) |
| Rhythm (节奏) | **12%** | 中等可靠 (文献 B 级) |
| Breath (气息) | **22%** | 四子维度丰富 |
| Technique (发声技术) | **25%** | 咬字(50%) + 气声比(50%) + attack_slope |
| Muscle (肌肉力量) | **15%** | ⚠️ HEURISTIC, 文献建议降低 |
| Artistry (艺术表现) | **13%** | crescendo+fluctuation+rubato 修复 |

### DDD domain/audio/ 自包含模块

| 层级 | 模块 | 核心特征 | 外部依赖 |
|------|------|---------|:--:|
| — | `audio_utils.py` | normalize_loudness + vocal_segments | ✅ |
| — | `math_utils.py` (shared/) | safe_float + safe_clamp | ✅ |
| L0 | `acoustic_feature_extractor.py` | HNR + CPP + HPSS + voicing + mixed_audio | ✅ |
| L0 | `audiofeat_extractor.py` | CPPS/GNE/Jitter/Shimmer (22 特征) | audiofeat 1.1.1 |
| L1 | `pitch_extractor.py` | MAE/RPA/RCA/gross/octave/smoothness/breaks | ✅ |
| L1 | `rhythm_extractor.py` | onset CV + irregularity + off-beat + deviation | ✅ |
| L2 | `breath_extractor.py` | long_note + dynamic + design + technique | ✅ |
| L2 | `technique_extractor.py` | ZCR/Centroid/C-V + HF + **attack_slope** 🆕 | ✅ |
| L2 | `timbre_extractor.py` | centroid + cluster + harmonic + nasality | ✅ |
| L3 | `muscle_extractor.py` | MPT/Crest/SPR/F1F2/Alpha proxy | ✅ |
| L3 | `artistry_extractor.py` | vibrato + dynamic + phrase + **rubato** 🆕 | ✅ |
| — | `abi_calculator.py` 🆕 | ABI 9-parameter breathiness (Barsties 2017) | audiofeat |
| — | `feature_types.py` | AcousticFeatures 冻结数据类 | ✅ |

### 安全中间件

| 中间件 | 配置 | 状态 |
|--------|------|:--:|
| SecurityHeadersMiddleware | CSP, X-Content-Type, X-Frame, HSTS | ✅ |
| RateLimitMiddleware | 120/min global, 20/min upload, 10/min WS | ✅ |
| MaxBodySizeMiddleware | 50MB | ✅ |
| Global Exception Handler | 防止原始 traceback 泄露 | ✅ |

### 端口策略

开发 → 8000 | Electron → `--port=0` (OS 分配) | 生产 → FastAPI 服务 `frontend/dist/`

---

## 二、完成功能

### v7.13 (2026-08-07) — 实时音准对比子系统 Phase 1 + Phase 2

| 类别 | 项目 | 状态 |
|------|------|:--:|
| **领域** | `backend/domain/songs_pitch/`: `SongPitchCurve` 值对象 (frozen, NaN→0.0, to_dict/from_dict) + `PitchCacheRepository` Protocol + `PitchExtractionService` (librosa.yin) | ✅ |
| **应用** | `GetSongPitchUseCase` — 查缓存→提取→写缓存 (缓存优先编排) | ✅ |
| **基建** | `InMemoryPitchCacheRepository` 进程内单例缓存 (lru_cache DI) | ✅ |
| **API** | `GET /api/v1/songs/{id}/pitch` — 歌曲参考 F0 曲线 (thread pool, 404/400 边界) | ✅ |
| **API** | `POST /api/v1/songs/{id}/compare` — 上传录音与选中歌曲 DTW 对比 (复用 CompareAudioUseCase) | ✅ |
| **WS** | `pitch_update` 接线 — StreamingSession 样本驱动 (每 2s 新音频段) PYIN → `WsServerPitchUpdate` (绝对时间轴) | ✅ |
| **修复** | `_score_lightweight()` 权重 10/10/20/25/25/10 → `ScoringWeights.default()` 单一来源 (13/12/22/25/15/13) | ✅ |
| **前端纯 TS (P1)** | `types/pitch.ts` + `utils/pitchDeviation.ts` (freqToCents/颜色映射/八度跳变/曲线对齐) + `utils/pitchScroll.ts` (滚动窗口/静音裁剪/自动视口) — 零 Vue 依赖 | ✅ |
| **前端纯 TS (P2)** | `utils/pitchNotes.ts` (freq↔MIDI↔音名/白键/音高刻度) + `utils/pitchStats.ts` (偏差百分比/最高最低音) + `utils/pitchPlayback.ts` (clampSeek/倍速推进/A-B 循环/帧率降级) + `pitchScroll` 扩展 (自动刻度步长/时间刻度) — 零 Vue 依赖 | ✅ |
| **前端 store** | songs.store +`fetchSongPitch` (缓存) + `compareWithSong` | ✅ |
| **前端组件** | `PitchComparisonCanvas.vue` (P1 双曲线 → P2 全功能): 偏差着色 (≤25 绿/≤50 橙/>50 红, 静音灰虚线 40% 延续不跳变) + 滚动窗口 (播放居中) + Y 轴钢琴键/时间刻度 + 八度跳变 ⚠️ + 无参考蓝色单曲线 | ✅ |
| **前端视图** | SingView (Element Plus + GSAP): P1 选歌参考线/上传 DTW/再来一首; P2 回放控制面板 (播放/暂停/拖拽跳转/倍速 0.5x-1.5x/A-B 循环) + WS 不可变更新 | ✅ |
| **BDD** | sing-song-select step defs 更新 (data-test 钩子, xfail 对齐 v7.13); 🆕 `pitch-realtime` step defs 骨架 (25 场景, 每条标注对应纯 TS 单元测试) | ✅ |
| **测试** | 单测 435→451 (+16) + 集成 53→62 (+9) + WS 10→14 (+4); 前端 102→**166** (+64); 后端全绿 548 (534 生产 + 14 WS); BDD 场景 154→**179** | ✅ |

> **后续 Phase (pitch-realtime.feature 全量)**: Phase 3 Sing 录音中实时对比 (圆点/色带/趋势箭头) / Phase 4 回放对比+统计+问题段落+逐句评分 / Phase 5 CompareView 双轨叠加+热力图+性能降级+截图/快捷键 — 均已设计, 未实现。

### v7.12 (2026-08-06) — 选歌录音 MVP + BDD 基建修复 + dl_services 死代码清理

| 类别 | 项目 | 状态 |
|------|------|:--:|
| **选歌录音** | 后端: `SongMetadata.vocal_range` (音域) 全链路 (值对象/SQLite列+旧库迁移/schema/API Form) | ✅ |
| **选歌录音** | 后端 WS: `StreamingSession.song_id` + score_handler 存储 (WsClientStart.song_id 协议接线) | ✅ |
| **选歌录音** | 前端: 路由 `/sing/:songId?` + SingView 选歌区 (无参数) / 歌曲信息+取消选择 (有参数) / WS start 携带 song_id | ✅ |
| **选歌录音** | 前端: SongsView "选择此歌" 按钮 → `/sing/:songId`; 音域展示 | ✅ |
| **选歌录音** | BDD: sing-song-select.feature 迁移 Vue 3 — 6 PASS + 6 XFAIL (录音相关) | ✅ |
| **BDD 数据** | `scripts/gen_bdd_test_data.py` 生成 vocals.wav (60s 人声) + 根 conftest `KMP_DUPLICATE_LIB_OK=TRUE` (OMP Error#15 崩溃修复) | ✅ |
| **BDD upload** | fixture bug (target_fixture) / httpx 适配 (files=/json()/路径) / feature 裁剪 12 无 step 场景 / Pro Demucs @slow | ✅ |
| **BDD animations** | step defs 迁移 Vue 3 data-test 选择器 + 前端 data-test 钩子 (SingView/ReportView/HomeView) + 按钮 72px | ✅ |
| **架构清理** | dl_services 死代码删除 (桩/model_manager 子包/features:types/enhanced_dl_assessor) + 同步删 test_score_calibrator | ✅ |
| **测试** | 集成 50→53 (+3 vocal_range); WS 8→10 (+2 song_id); 扩展 36→21 (-15); 前端 68 全绿 | ✅ |

### v7.11 (2026-08-04) — 评分权重可配置 + 六维权重单一来源 + BDD 基建修复

| 类别 | 项目 | 状态 |
|------|------|:--:|
| **领域** | `ScoringWeights` 值对象 — 权重单一数据来源 (frozen, validate 总和100%+单维≤50%) | ✅ |
| **领域** | 4 个风格预设 (流行/美声/民族/说唱, 6 维适配: 原5维×0.85 + muscle 15%) | ✅ |
| **领域** | `weighted_total()`/`weighted_total_from_scores()` 加权聚合 | ✅ |
| **领域** | `calculate_total()` 注入 `weights` 参数; value_objects `weighted()` 委托单一来源 | ✅ |
| **API** | `GET /api/v1/scoring/presets` — 默认权重 + 4 风格预设 | ✅ |
| **API** | `POST /api/v1/scoring/apply-weights` — 维度分数+权重→总分/等级 (纯前端重算) | ✅ |
| **API** | flags.py `dimension_weights` 改为 ScoringWeights 单一来源 (此前硬编码) | ✅ |
| **前端** | `scoring.store.ts` — 预设加载/滑块权重/合法性/自动归一化/纯前端重算 | ✅ |
| **前端** | `ScoringWeightsPanel.vue` — 预设选择 + 六维滑块 + 总和校验 + 归一化 + 对比重算 | ✅ |
| **前端** | ReportView 集成权重面板 (muscle_strength→muscle 键映射) | ✅ |
| **BDD** | scoring-config.feature 6 维契约更新 (API 级 XFAIL→PASS, UI 级保留 XFAIL) | ✅ |
| **BDD** | 浏览器基建修复: conftest base_url→:8000 + api_client→FastAPI + 前端 `window.__store` 钩子 | ✅ |
| **测试** | +25 领域 (ScoringWeights) +14 集成 (scoring API) +11 Vitest (scoring.store) | ✅ |

### v7.10 (2026-08-04) — 标准歌曲库前端页面 + 音频播放修复

| 类别 | 项目 | 状态 |
|------|------|:--:|
| **前端** | `SongsView.vue` 卡片网格页 (浏览/搜索/风格·难度筛选/上传/删除/试听) — 对齐 song-library.feature BDD 契约选择器 | ✅ |
| **前端** | `songs.store.ts` Pinia store: 服务端分页 + 服务端搜索/筛选 + 300ms 防抖 + CRUD | ✅ |
| **前端** | `/api/v1/songs` 全量对接 + 类型 (SongRecord/SongMetadata/SongListResponse...) | ✅ |
| **前端** | `/songs` 路由 + TopNav/BottomNav 双端导航 ("曲库", Folder 图标) | ✅ |
| **后端** | `/api/v1/audio` 白名单增加 `songs_dir` — 修复歌曲播放 403 (TestAudioPlayback RED→GREEN) | ✅ |
| **安全** | 目录锁 `startswith` → `is_relative_to` — 修复同名前缀兄弟目录越界 (安全审查 HIGH, TDD 回归) | ✅ |
| **测试** | +24 Vitest store tests; +3 集成 (音频播放 + 安全边界); 版本 7.9.0 → 7.10.0 | ✅ |
| **BDD** | song-library.feature 作为行为契约 (浏览器级基建后续项); database.feature API 级回归通过 | ✅ |

### v7.9 (2026-08-02) — 标准歌曲库后端 (DDD+TDD+BDD)

| 类别 | 项目 | 状态 |
|------|------|:--:|
| **领域** | `backend/domain/songs/`: SongMetadata/Song/SongListPage/SongRepository Protocol | ✅ |
| **基建** | `sqlite_song_repo.py` 桩→SQLite 仓储 (CRUD/分页/筛选/搜索/重复检测) | ✅ |
| **应用** | `song_library_service.py`: 去重 add/分页搜索/get/delete + 领域异常 | ✅ |
| **API** | `/api/v1/songs`: POST/GET list/GET id/DELETE 完整实现 | ✅ |
| **API** | 文件上传保存 + 重复清理孤立文件 + 写入失败友好错误 | ✅ |
| **API** | difficulty/style 边界校验 (400) + 扩展名复用 settings | ✅ |
| **配置** | `songs_db`/`songs_dir` 设置 (VAS_SONGS_DB/VAS_SONGS_DIR 覆盖) + DI 接线 | ✅ |
| **BDD** | `test_database_steps.py`: database.feature 10 场景 (4 PASSED + 6 XFAIL) | ✅ |
| **测试** | +37 单元 +14 集成; 版本 7.8.0 → 7.9.0 | ✅ |
| **清理** | 删除 PyInstaller 打包 (build.bat) + api/schemas.py + web_app.py; 更新 requirements/start.bat/.gitignore | ✅ |

### v7.7 (2026-07-31) — audiofeat 生产启用 + Flag 系统修复 + 前端收束

| 类别 | 项目 | 状态 |
|------|------|:--:|
| **Flag** | FeatureFlags ↔ DimensionFlags 桥接 (to_dimension_flags) | ✅ |
| **Flag** | audiofeat 默认启用 (FeatureFlags + DimensionFlags + 工厂方法) | ✅ |
| **Flag** | audiofeat 1.1.1 安装 + 验证 | ✅ |
| **Flag** | `GET /api/v1/flags` 端点 (GPU/模型/权重/开关状态) | ✅ |
| **修复** | breath_scorer.py 重复 _score_from_fluctuation 方法删除 | ✅ |
| **修复** | ReportView 六维权重修正: 10/10/20/25/25/10 → 13/12/22/25/15/13 | ✅ |
| **前端** | WaveformCanvas ⚠️ emoji → Element Plus WarningFilled 图标 | ✅ |
| **前端** | web/static/index.html 🎤 emoji 移除 | ✅ |
| **前端** | 无效路由 ElMessage.warning toast (替代 console.warn) | ✅ |
| **前端** | Settings 抽屉新增 "算法与模型" 状态面板 | ✅ |
| **前端** | flags.store.ts (Pinia, /api/v1/flags 数据获取) | ✅ |
| **清理** | 5 个 legacy E2E 测试文件删除 (test_analysis/test_upload/test_real_audio/test_e2e/test_e2e_v2) | ✅ |
| **测试** | test_flag_bridge.py (6 tests) | ✅ |
| **测试** | 249 tests GREEN (unit 228 + extended 21) | ✅ |

### v7.8 (2026-08-01) — GNE 接入 + GSAP 动效美化 + 前后端对齐

| 类别 | 项目 | 状态 |
|------|------|:--:|
| **评分** | GNE (AROC=0.886) 接入 TechniqueScorer._apply_audiofeat_enhancement() — 气声比增强 | ✅ |
| **评分** | GNE 阈值: <0.4 不可控漏气惩罚, >0.8 优秀声门控制加分 (与 BreathScorer 一致) | ✅ |
| **动效** | useGsap.ts 重写: 9 动画方法 + gsap.matchMedia() reduced-motion 检测 | ✅ |
| **动效** | AppLayout 页面过渡 CSS (opacity + translateY, 0.3s) | ✅ |
| **动效** | ReportView score-reveal GSAP Timeline: 总分弹入→雷达图缩放→六维卡片 stagger→建议滑入 | ✅ |
| **动效** | HomeView/CompareView/HistoryView 入场动画 (enterFrom/slideIn/staggerIn) | ✅ |
| **动效** | SingView 录音按钮 CSS pulse → GSAP repeat: -1 脉冲 | ✅ |
| **动效** | prefers-reduced-motion 双重保护 (CSS @media + GSAP matchMedia) | ✅ |
| **对齐** | flags.store.ts: 原始 fetch() → apiClient + FlagsResponse 强类型 | ✅ |
| **对齐** | flags 路由: 硬编码 /api/v1/flags → prefix="/api/v1" + @router.get("/flags") | ✅ |
| **对齐** | client.ts: (import.meta as any) → import.meta.env?.DEV | ✅ |
| **对齐** | HistoryRecord 补充 filepath/advice/scores 字段; history.store 捕获 total_pages/limit | ✅ |
| **对齐** | ScoreRadar chartOptions as any → ChartOptions<'radar'>; HistoryView val as any → HistoryFilter | ✅ |
| **对齐** | ApiResponse<T> 死代码删除; backend HistoryListResponse list[dict] → list[HistoryRecordOut] | ✅ |
| **清理** | services/features/types.py 外部引用清零 (仅剩 DeprecationWarning) | ✅ |
| **清理** | test_orchestrator.py 移除 legacy adapter 对比测试 (AudioFeaturesResult 导入已删) | ✅ |
| **BDD** | dtw-demotion.feature (18 scenarios) + scoring-config.feature (14 scenarios) step defs 实现 | ✅ |
| **测试** | +5 GNE tests (test_technique_scorer.py); 369 unit + 32 BDD scenarios GREEN | ✅ |

### v7.6 (2026-07-31) — P1/P2 修复 + 功能增强 + 架构清理

| 类别 | 项目 | 状态 |
|------|------|:--:|
| **P1-1** | Muscle v7.4 proxies DDD 路径验证 (10 提取验证测试) | ✅ |
| **P1-2** | crescendo_quality: 累积→平均质量×覆盖率 (修复饱和) | ✅ |
| **P1-3** | is_artistic_fluctuation: 布尔→连续 0-100 | ✅ |
| **P2** | CPPS ×100 rescale + HNR graduated (歌声特定阈值) | ✅ |
| **P2** | ABI 9 参数模型 (Barsties 2017) | ✅ |
| **P2** | Flask /old 移除 + api/routes/ 删除 (~700行) | ✅ |
| **P2** | services/features/acoustic.py 替换为 DDD | ✅ |
| **增强** | Rubato (表现性节奏变化) → Artistry | ✅ |
| **增强** | Attack slope (起音斜率) → Technique | ✅ |
| **文献** | Rathi & Hsu 咬字权重对齐 2:1:1 | ✅ |
| **基线** | BASELINE V7_6 with 5 real audio files | ✅ |
| **测试** | 359 unit + 54 integration/extended = 413 GREEN | ✅ |

### v7.5 (2026-07-29) — P1-2b 音色八维 + P0 评分异常修复

| 类别 | 项目 | 状态 |
|------|------|:--:|
| **P1-2b** | 音色八维剖面 (hardness/depth/sharpness/booming) | ✅ |
| **P0-1** | Artistry pitch_cv: 真实 F0 CV 替代 Hz | ✅ |
| **P0-2** | Technique HNR: 移除 >22 惩罚 | ✅ |
| **P0-3** | CPPS-HF 解耦: 实谱 HF 替代 cpp/5.0 | ✅ |
| **P0-4** | Muscle formant/overtone 校准 | ✅ |

### 更早版本

v7.4 ~ v7.0: 参见 [CHANGELOG.md](CHANGELOG.md)。

---

## 三、测试状态 (v7.13)

### 生产测试 (全部 GREEN)

| 套件 | 测试数 | 结果 |
|------|:-----:|------|
| DDD 领域 (scorers + value objects + comparison + songs + **songs_pitch** + ScoringWeights) | 273 | ✅ |
| DDD 基建 (extractors + orchestrator + ABI + sqlite) | 132 | ✅ |
| DDD 对齐 + Flag bridge (test_ddd_alignment/extraction_flag/flag_bridge) | 23 | ✅ |
| 中间件 | 23 | ✅ |
| **DDD 合计** | **451** | **100% GREEN** |
| FastAPI 集成 | 62 | ✅ | (api_routes 19 + songs_api 20 + scoring_api 14 + **songs_pitch_api 9**)
| 扩展测试 (DTW/repos) | 21 | ✅ | (v7.12 删 test_score_calibrator 15)
| **生产代码总计** | **534** | **100% GREEN** |

> 注: 生产合计 = DDD 451 + 集成 62 + 扩展 21 = 534 (独立进程实测)。另含 WebSocket 集成 14 (v7.12 10 + v7.13 pitch_update 4) 与真实音频回归 28 (BASELINE_V7_6), 不计入生产代码合计。

### 真实音频回归

| 套件 | 测试数 | 结果 | 说明 |
|------|:-----:|------|------|
| 真实音频 Quick + Pro | 28 | ⚠️ 24 PASS + 4 FAIL | 4 个失败均为 `test_dimension_scores_in_baseline_ranges` 的 **breath 维度**越界 0.1-0.8 分 (79.2/83.4/75.9/69.9 vs 基线 80/84/76/70) — BASELINE_V7_6 阈值过紧的既有漂移, 与 v7.13 改动无关 (评分管线零触碰; total/valid 范围测试全 PASS) |
| BDD | 17 step files | ✅ | 179 scenarios collected + 5 features pending step defs |

### BDD (v7.12 浏览器基建 + 场景迁移)

| Feature | 状态 |
|------|------|
| upload.feature (裁剪为 5 核心场景) | ✅ 5 PASS + 3 SKIP (FLAC/OGG/M4A 无测试文件) + Pro Demucs `@slow` |
| animations.feature (迁移 Vue 3 data-test) | ✅ 7 PASS + 9 XFAIL (无 UI/依赖录音场景带理由) |
| sing-song-select.feature (迁移 Vue 3) | ✅ 6 PASS + 6 XFAIL (依赖 WebSocket 录音/auto-match/上传) |
| scoring-config.feature | ✅ API 级 PASS (v7.11) |
| database.feature | ✅ 4 PASS + 6 XFAIL (v7.9) |
| **pitch-realtime.feature (v7.13 P2 骨架)** | ✅ 25 XFAIL (每条标注对应纯 TS 单元测试文件; 浏览器 BDD 无真实音频/WS) |

### 前端测试

| 套件 | 测试数 | 结果 |
|------|:-----:|------|
| Vitest | 166 | ✅ 100% | (stores 74 + **pitch utils 92**; v7.13 P1 +34, P2 +64)
| vue-tsc type check | 0 errors | ✅ |
| Vite build | ~16s | ✅ |

### 前端 GSAP 动效 (v7.8 新增)

| 页面 | 动效 | 方法 |
|------|------|------|
| AppLayout | 页面过渡 | CSS opacity + translateY 0.3s |
| ReportView | score-reveal Timeline | enterFrom + scaleIn + staggerIn |
| HomeView | 入场序列 | enterFrom (5 阶段) |
| CompareView | 双面板入场 | slideInLeft + slideInRight |
| HistoryView | 容器淡入 | enterFrom |
| SingView | 录音脉冲光环 | GSAP pulse repeat:-1 |
| 全局 | prefers-reduced-motion | CSS @media + GSAP matchMedia |

### 真实音频评分 (v7.6 Quick 模式)

| 音频文件 | Total | Pitch | Rhythm | Breath | Tech | Art | Muscle |
|----------|:-----:|:-----:|:------:|:------:|:----:|:---:|:------:|
| 恋人（高分） | 71.5 | 66.6 | 66.3 | 89.5 | 51.6 | 74.0 | 77.9 |
| 1（高分） | 74.1 | 70.7 | 71.2 | 93.6 | 53.7 | 75.2 | 77.2 |
| 陈奕迅（低分） | 62.4 | 66.4 | 5.2 | 80.3 | 57.1 | 68.7 | 75.4 |

> 高低分区分度: 71.5 - 62.4 = **9.1 pts** (>8 阈值) ✅

---

## 四、已知问题

> 更新: 2026-08-07 | v7.13

### 架构残留

| 优先级 | 残留 | 说明 |
|--------|------|------|
| ~~P2~~ | ~~`services/features/types.py`~~ | ✅ v7.8: 外部引用已清理 |
| ~~P2~~ | ~~前后端对齐: flags.store.ts 绕过 apiClient~~ | ✅ v7.8: 已修复 (apiClient + FlagsResponse 强类型) |
| ~~P2~~ | ~~前后端对齐: flags 路由硬编码 /api/v1/flags~~ | ✅ v7.8: 已修复 (prefix 约定一致) |
| ~~P2~~ | ~~前后端对齐: ScoreRadar/HistoryView as any 类型~~ | ✅ v7.8: 已修复 (ChartOptions/HistoryFilter 类型) |
| ~~P2~~ | ~~前后端对齐: ApiResponse<T> 死代码 + HistoryListResponse list[dict]~~ | ✅ v7.8: 已清理 |
| **P2** | `services/dl_services/` (4 活跃) | ✅ v7.12: 死代码已清 (桩/model_manager 子包/features:types/enhanced_dl_assessor 删除); 保留 voice_quality_detector/singing_style_classifier/self_referenced_dtw/dl_style_classifier (Professional 模式) — DDD 迁移为独立工程 |

### 文献差距

| 优先级 | 项目 | 说明 |
|:--:|------|------|
| ~~P1~~ | ~~audiofeat 默认禁用~~ | ✅ v7.7 |
| ~~P2~~ | ~~GNE 未接入气声比评分~~ | ✅ v7.8: AROC=0.886 接入 TechniqueScorer |
| **P2** | timbral_models 集成 | Python 3.12 兼容性问题, 待上游修复 |
| **P2** | PyArmor 代码保护 | ADR-8, 构建脚本就绪 |
| **P2** | electron-builder 完整打包 | 配置就绪, 未执行 |

### GSAP 动效

| 优先级 | 项目 | 说明 |
|:--:|------|------|
| ~~P0~~ | ~~页面切换无过渡动画~~ | ✅ v7.8: AppLayout CSS 过渡 |
| ~~P0~~ | ~~ReportView 评分无 reveal 动画~~ | ✅ v7.8: GSAP Timeline score-reveal |
| ~~P0~~ | ~~HomeView 无入场动画~~ | ✅ v7.8: 5 阶段 enterFrom 序列 |
| ~~P0~~ | ~~prefers-reduced-motion 未处理~~ | ✅ v7.8: CSS + GSAP matchMedia 双重保护 |
| ~~P1~~ | ~~useGsap.ts 死代码 (零引用)~~ | ✅ v7.8: 5 组件引用 |
| ~~P1~~ | ~~BDD animations.feature 针对旧架构~~ | ✅ v7.12: 迁移 Vue 3 data-test 选择器 (7 PASS + 9 XFAIL) |

### 测试遗留

| 问题 | 说明 |
|------|------|
| 真实音频 breath 基线漂移 | `test_dimension_scores_in_baseline_ranges` 4 个文件 breath 越界 0.1-0.8 分 (v7.6 基线阈值过紧, 环境漂移) — 待校准 BASELINE_V7_6 breath_range 或接受漂移 (v7.13 实测 24P+4F) |
| BDD v6.0 规划 features 部分实现 | v7.8: dtw-demotion + scoring-config step defs 已创建; v7.13: pitch-realtime step defs 骨架已创建; 5 features 仍待实现 |
| ~~BDD animations.feature 旧架构~~ | ✅ v7.12: 迁移 Vue 3 (data-test 钩子 + 类选择器); 无 UI 场景 xfail 带理由 |
| ~~BDD 浏览器基建指向旧 Flask~~ | ✅ v7.11: conftest base_url→:8000 + api_client→FastAPI + 前端 `window.__store` 钩子 |
| ~~upload.feature 数据缺失 (vocals.wav)~~ | ✅ v7.12: `scripts/gen_bdd_test_data.py` 生成 + KMP_DUPLICATE_LIB_OK 崩溃修复; 5 PASS + 3 SKIP |
| BDD 浏览器测试需服务运行 | 运行浏览器 BDD 需先 `python backend/main.py` (FastAPI :8000 服务 frontend/dist); 服务未启动时场景 skip |
| 评分阈值联动 (风格预设) | scoring-config.feature: 各预设阈值微调 (MAE断点等) 未实现 — API 级 PASS, 阈值联动/自动风格检测/UI 面板仍 XFAIL (用户指定暂不开发) |
| ~~选歌录音 (选歌→演唱页)~~ | ✅ v7.12 MVP + v7.13 Phase 1: `/sing/:songId` + WS song_id + vocal_range + 参考音高 API + WS pitch_update + 上传录音对比 + 再来一首 |
| **实时音准对比 Phase 3-5** | pitch-realtime.feature 全量 (录音中实时对比/回放对比/CompareView 双轨/性能降级/截图/快捷键) 已设计未实现; auto-match 独立 feature 待开发 |

---

## 五、快速参考

### 关键文件

| 文件 | 说明 |
|------|------|
| `backend/domain/assessment/artistry_scorer.py` | v7.6 — rubato + crescendo + fluctuation 连续化 |
| `backend/domain/assessment/technique_scorer.py` | v7.6 — CPPS/HNR 歌声阈值 + Rathi & Hsu 2:1:1 + attack_slope |
| `backend/domain/assessment/muscle_scorer.py` | v7.5 — 校准 formant/overtone + 五维代理 |
| `backend/domain/assessment/timbre_adjuster.py` | v7.5 — 八维音色剖面 |
| `backend/domain/assessment/value_objects.py` | v7.4 — 六维权重 |
| `backend/domain/audio/artistry_extractor.py` | v7.6 — rubato 提取 + F0 CV |
| `backend/domain/audio/technique_extractor.py` | v7.6 — attack_slope 提取 + CPP ×100 |
| `backend/domain/audio/muscle_extractor.py` | v7.4 — MPT/Crest/SPR/F1F2/Alpha |
| `backend/domain/audio/abi_calculator.py` | v7.6 — ABI 9 参数气息感模型 |
| `backend/domain/audio/breath_extractor.py` | v7.6 — crescendo avg×coverage |
| `backend/application/assessment/ddd_feature_orchestrator.py` | 特征提取编排 + pitch_cv |
| `backend/application/assessment/scoring_orchestrator.py` | 评分编排 |
| `backend/domain/assessment/feature_flags.py` | DimensionFlags (类默认 audiofeat=False; 运行时经 flag_bridge 由 FeatureFlags 设为 True) |
| `backend/domain/songs/entities.py` | v7.9 — Song/SongMetadata 领域实体 |
| `backend/domain/songs/repository.py` | v7.9 — SongRepository Protocol |
| `backend/infrastructure/persistence/sqlite_song_repo.py` | v7.9 — SQLite 仓储 (CRUD/分页/筛选/去重) |
| `backend/application/songs/song_library_service.py` | v7.9 — 应用层服务 |
| `backend/interfaces/api/routes/songs.py` | v7.9 — /api/v1/songs POST/GET/DELETE |
| `backend/domain/assessment/scoring_weights.py` | v7.11 — 六维权重值对象 + 风格预设 + 校验 + 聚合 |
| `backend/interfaces/api/routes/scoring.py` | v7.11 — /api/v1/scoring/presets + apply-weights |
| `frontend/src/stores/scoring.store.ts` | v7.11 — 权重预设/滑块/归一化/纯前端重算 store |
| `frontend/src/components/scoring/ScoringWeightsPanel.vue` | v7.11 — 权重配置面板 (ReportView 集成) |
| `backend/main.py` | FastAPI 入口 (Flask 已移除) |

### 启动命令

```bash
# 开发模式
cd frontend && npm run dev          # Vite :5173
python backend/main.py              # FastAPI :8000

# 默认测试 (435 tests, ~16s)
pytest tests/unit/domain/ tests/unit/infrastructure/ \
       tests/unit/test_middleware.py \
       tests/unit/test_ddd_alignment.py \
       tests/unit/test_ddd_extraction_flag.py \
       tests/unit/test_flag_bridge.py

# 集成测试 (独立进程, ~5s)
pytest tests/integration/test_api_routes.py -v         # FastAPI (19 tests)

# 扩展测试 (独立进程, ~5s)
pytest tests/extended/ -v                              # DTW/repos/etc (34 tests)

# 真实音频回归 (独立进程, ~27min)
pytest tests/integration/test_real_audio_regression.py -v

# BDD 测试 (需要浏览器)
pytest tests/bdd/ -v -m "not browser"
pytest tests/bdd/ -v -m "browser"
```
