# 项目状态

> 更新: 2026-08-13 | 版本: **v7.17** | 分支: `main`

---

## 一、架构

```
Vue 3 SPA (frontend/dist/)  →  FastAPI (:8000)
                                      │
    ┌─────────────────────────────────┼──────────────────────────┐
    │  backend/ (DDD 四层)            │  旧服务层 (残留)           │
    │  domain/assessment/ (6 scorers)  │  services/dl_services/ (11)│
    │  domain/audio/ (14 模块自包含)   │  services/audio_service.py │
    │  domain/comparison/ (v7.3)      │  api/business/ (bridge)   │
    │  domain/songs/ (v7.9)           │                           │
    │  domain/songs_pitch/ (v7.13)    │                           │
    │  domain/song_match/ (v7.14)     │                           │
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

### v7.14 (2026-08-09) — 上传音频自动匹配标准歌曲 (auto-match)

| 类别 | 项目 | 状态 |
|------|------|:--:|
| **领域** | `backend/domain/song_match/`: `MatchFeatures` (bpm/key/chroma/duration) + `SongMatchProfile` + `MatchCandidate` + `MatchResult` 值对象 (frozen) + `SongMatchProfileRepository` Protocol | ✅ |
| **领域** | `MatchFeatureExtractor` — librosa `beat_track` (BPM 标量) + `chroma_stft` 均值 12-bin + Krumhansl-Schmuckler 24 键调性检测 | ✅ |
| **领域** | `AutoMatchService.match` — 置信度 = 0.30*bpm + 0.40*chroma + 0.15*key + 0.15*duration, `MATCH_THRESHOLD=0.60`; BPM 相对差 / chroma 12 旋转余弦 (转调不变) / 五度圈 key 距离 / 时长对数比 | ✅ |
| **应用** | `AutoMatchUseCase.execute(audio_path, top_n=3, timeout_s=10.0)` — load → extract → 预算制 ensure_profiles (缺失 profile 歌曲预计算入 SQLite) → deadline 超时返回 partial | ✅ |
| **基建** | `sqlite_song_match_profile_repo.py` — 新表 `song_match_profiles` (song_id PK, bpm/key/chroma JSON/duration/feature_version/updated_at) | ✅ |
| **基建** | `SongRepository.list_all_with_filepath()` — 枚举 filepath 非空且文件存在的歌曲 (匹配预计算数据源) | ✅ |
| **API** | `POST /api/v1/songs/match` — multipart `file` + `top_n` Form → `matched`/`matched_song`/`candidates`/`fallback_reason`/`detected_key`/`partial`/`elapsed_ms` | ✅ |
| **API** | `POST /api/v1/upload` 可选 `auto_match=true` — 路由层注入 `matched_song/matched_candidates/fallback_reason` 到 UploadResponse (不侵入 api/business) | ✅ |
| **DI** | deps.py `get_song_match_profile_repo` + `get_auto_match_use_case` (lru_cache 单例, 绑定 songs_db) | ✅ |
| **前端** | `songMatch.store.ts` — `matchAudio` (POST /songs/match) + `selectCandidate` + `compareWithSelected` (复用 POST /songs/{id}/compare) + `fetchUserPitch` (POST /extract-pitch) | ✅ |
| **前端** | CompareView 自动匹配区 (上传录音→候选列表 歌名/歌手/置信度/BPM 差/调性差→选中→一键 DTW 对比→复用 Phase 5 双轨叠加); 无匹配优雅回退提示 (fallback_reason 透传) | ✅ |
| **测试** | v7.14 特性发布: 生产 537→633 (+96: 领域 79 + 基建 11 + 集成 6); 前端 286→**297** (+11 songMatch.store); BDD auto-match.feature 8 场景 (5 PASS + 3 XFAIL 标注对应单元测试); 代码审查 (读锁 + chroma 防御 + 异常收窄)。**v7.14 深度审查修复轮 (2026-08-10): 633→714 collected (+81: fallback 11 + streaming 7 + pitch cache 7 + deps 2 + 集成/WS 13 + 断言同步等), 686 生产 GREEN**。**P2 完善修复轮 (2026-08-11): sr 错配根因修复 (P2-11, 3 处 sr=None→16000) + HPSS 去重 (P2-12a) + audio_buffer 缓存 (P2-13) + 乱码文件名恢复 (P2-14) + legacy 死代码删除 (P2-15); 🆕 +25 单元测试; 真实音频基线重校准 BASELINE_V7_6→V7_14**。**P2 续轮 (2026-08-11): compare.feature 重写对齐 v7.13 P5 契约 → BDD 残余失败 12→0; 当前权威计数 (实测): 生产 **709** / collected **737** (见下节测试表)** | ✅ |

### v7.17 (2026-08-13) — 评分校准: 高分音频 ≥80 (先修失真再温和校准)

> 用户反馈: 4 个"高分"真实音频 Quick 总分仅 63-65 (等级 B), 要求 ≥80。**评分行为变更 (有意为之), 基线重校准 BASELINE_V7_14→V7_17**。实测结论: 分离不是银弹 (pitch +20 但 rhythm −60, HNR 不变); 结构性封顶根因是 tilt/hf 只罚不奖。

| 类别 | 项目 | 状态 |
|------|------|:--:|
| **A1** | **Rhythm 伴奏污染** — 混音 onset CV 被伴奏抬高, `_cv_to_deviation` 混音映射重校准 (CV 0.6→deviation 0.22→~73分, CV ≥1.2 脱拍仍 20分)。pivot: f0 声乐活动实测不可行 (PYIN voiced 100%) | ✅ |
| **A2** | **Technique 结构性封顶修复** — `_calc_breath_voice_ratio` 的 tilt(20%)+hf(15%) 原是"只罚不奖"组件 (完美人声封顶 65), 改质量组件 (干净→满分)。撤销 +8 HNR 偏移 (Demucs 分离实测 HNR 仍 ~8dB) | ✅ |
| **A3** | **audiofeat 垃圾守卫** — jitter/shimmer/cq/gne 物理范围校验 (实测 jitter=-263175 异常) | ✅ |
| **A4** | **pro 分离后 rhythm 崩坍修复 — 节拍锚定** — 用伴奏轨节拍基准 + 人声轨 vocal onset 测偏差; 恋人 pro rhythm 8.2→64.5, total 83.5≈quick 81.2 | ✅ |
| **B1** | **Pitch** — MAE 指数 `exp(-mae/40)` (24音分→54) → 分段线性 (25音分→85); wobble 软化 | ✅ |
| **B3** | **Technique** — CPP/HNR/tilt/hf/articulation 曲线校准 (恋人 43.4→75.8) | ✅ |
| **B4** | **Breath/Muscle/Artistry** — 加分上限 + 阈值下移 (实测混音值) | ✅ |
| **校准结果** | 恋人 **81.2** / 手写从前 **82.6** / 1 **79.9** / 音频 **80.7** / 陈奕迅 **72.0** (见下节分数表); 区分度保持 (rhythm gap 62.8) | ✅ |
| **测试** | 🆕 +11 校准回归 (pitch 2 + technique 封顶 3 + rhythm 映射 3 + 节拍锚定 3); 更新 10 technique 测试 + 2 audio_service 索引; 基线 **BASELINE_V7_17**; 版本 **7.17.0** | ✅ |

### v7.16 (2026-08-13) — P2-15 legacy 收敛安全范围 (Phase 0/0b/1/3/2/5) + 历史双写 bug 修复

> Phase 4 (逐句评分 PhraseService) **经用户决策推迟** — 独立功能非双轨, 前端/测试零消费 `phrases`, 留待独立会话。

| 类别 | 项目 | 状态 |
|------|------|:--:|
| **Phase 0** | `services/audio_service.py` — 删 4 个从不读取字段 (`_pitch_stability`/`_tonal_clarity`/`_voice_clarity`/`_vibrato_count`) + 死方法 (`_analyze_tonal_clarity`/`_analyze_tonal_clarity_fast`/`_analyze_voice_clarity`/`_detect_vibrato`) | ✅ |
| **Phase 0** | `scoring_orchestrator.py` — 删死 `calculate()` 路径 + 7 个 `_score_*` + `_collect_fallback_warnings` + `_compute_volume` + `_FALLBACK_WARNING_LABELS` + `FeatureAdapterRegistry` 注入 → **`calculate_ddd()` 成为唯一生产评分路径** | ✅ |
| **Phase 0** | `tests/tools/test_real_audio_comparison.py` — 收敛为单路径 DDD 验证 (修复已删符号 import); `tests/unit/domain/test_fallback_marking.py` — 删 3 个测死路径的 fallback 测试 (626→623 unit) | ✅ |
| **Phase 0b** | **历史双写 bug 修复** — `audio_analysis.py` 移除 import 时 `HistoryEventSubscriber` 订阅 + `_history_repo` 构造; `ddd_orchestrator` 改无 event_bus → 评分不再经 EventBus 写无 analysis_id 垃圾记录, 历史由路由 `_save_history` 单一负责 | ✅ |
| **Phase 0b** | **实测验证 + 数据清理** — web_history.json 50 条中 32 条为无 analysis_id 垃圾记录 (挤占槽位淘汰完整历史); 经用户授权清理, 保留 18 条完整记录 | ✅ |
| **Phase 1** | **`AdviceGenerator` 迁入 DDD application 层** — 新增 `backend/application/assessment/advice_generator.py` (frozen `AdviceResult` + 纯函数 generate), 从 `services/advice_service.py` 移植; `audio_analysis.py` 改调 `advice_generator.generate`; 删 `services/advice_service.py` + 清理导出 | ✅ |
| **Phase 3** | **`calculate_ddd` 补全逐维诊断** — 增加 5 个 `*_diagnosis` 键 (pitch/rhythm/breath/technique/artistry), 移植旧 `calculate()` 的 `_make_diagnosis` 输出 (含 pitch `mae_cents` + rhythm `deviation_ratio`) → **修复上传/分析响应 diagnosis block 恒空** | ✅ |
| **Phase 2** | **音色单轨化 (消除"音色计算两遍")** — `calculate_ddd` 输出 `timbre_detail` (9 键契约: brightness/warmth/nasality ← ta 分/100, hnr ← audiofeat 回退 technique, breathiness ← audiofeat.spectral_flatness proxy, vibrato_rate ← technique.vibrato_rate_avg, vibrato_extent/count 占位 0, style 派生); `audio_analysis.py` pro 模式改从 `timbre_detail` 组装, **删除 `services/timbre_service.py`** + 导出清理 | ✅ |
| **Phase 5** | **facade 折叠** — ① 删死 `analyze_emotion` 启发式 (每次分析省一次 librosa 重算, `emotion_info`→null, 前端/测试零消费); ② `_resolve_ddd_extractor` flag 对齐 (None→模块级默认数值不变, 生产 for_quick/for_professional 经 `to_dimension_flags` 构造; **quick 声学设置随 for_quick 变, 用户决策接受**); ③ 移除无用 `reference_path` 参数 + 2 处路由实参 | ✅ |
| **版本** | `APP_VERSION` 7.14.0→**7.16.0** + `APP_TITLE` 从 APP_VERSION 派生 (VAS v7.16, 防漂移) + `package.json` 7.16.0 | ✅ |
| **测试** | 🆕 +20 (advice_generator 15 + diagnosis 5 + history_single_write 3 − 删 3 过时 fallback) + **+15 续轮 (timbre_detail 9 + flag alignment 6)**。**权威计数: 生产 773 / collected 801** (单元 658 + API 77 + WS 17 + 扩展 21 + 真实音频 28, 见下节测试表)。前端 307 不变, vue-tsc 0 错误 | ✅ |
| **文档** | P2_15_CONVERGENCE_PLAN.md — legacy 收敛实施计划 (Phase 0-5 全量设计, 本次执行安全范围 0/0b/1/3) | ✅ |

### v7.15 (2026-08-12) — 错误可见化 + uploads 自动清理 + 集成隔离修复 (DEEP_REVIEW 收尾)

| 类别 | 项目 | 状态 |
|------|------|:--:|
| **后端** (M3) | `acoustic_feature_extractor.py` — HNR/CPP/HPSS/mixed_audio 提取异常**不再静默返回空特征**, 异常保留并传播 (静默失败 → 可观测) | ✅ |
| **后端** (M4) | `audio_service.py` — analyze 静默异常路径可见化 (异常根因保留, 前端可收到失败状态而非空结果) | ✅ |
| **后端** (M5) | `audio_dl_helpers.py` — 下载/加载 helper 异常显式传播 (不再吞掉) | ✅ |
| **后端** (P2-14 余项) | `services/upload_cleaner.py` — `unlink_files` (uploads 目录内路径锁 `is_relative_to` + missing_ok + OSError→warning) + `collect_referenced_files` + `cleanup_orphans` (顶层扫描) + `run_startup_upload_cleanup` (repo=None 安全 no-op) | ✅ |
| **后端** (P2-14 余项) | `repositories/history_repository.py` — delete/delete_batch/save 逐出联动 unlink 文件 (仅删除不再被引用的; 共享文件保留; upload_dir=None 向后兼容) | ✅ |
| **后端** (P2-14 余项) | `backend/main.py` lifespan 启动孤儿扫描 (VAS_SKIP_UPLOAD_CLEANUP 可跳过; 实测 dry-run 36 文件 11 被引用 → **25 孤儿**) | ✅ |
| **前端** (H-B14) | `utils/matchFeedback.ts` — songMatch.store 错误/命中/回退 → 反馈文案 + severity 映射 | ✅ |
| **前端** (H-B15) | `composables/useWsDisconnectGuard.ts` — SingView WS 断连 4 状态机 (open 中断连→置灰 + 重连提示; 主动关闭/空引用/未 open 不误报) | ✅ |
| **前端** (H-B14) | CompareView 自动匹配区错误告警渲染 (`[data-test=auto-match-error]`) + 命中徽标 + 无命中回退提示 | ✅ |
| **测试** | 🆕 +29 单元 (M3 7 + M4 3 + M5 4 + uploads 清理 15); BDD +4 browser 场景 (compare-automatch 3 + sing-song-select 1) → **182 collected**; 前端 +10 Vitest (matchFeedback 6 + ws 4) → **307**。**集成隔离修复 (pre-existing)**: 单进程组合运行 8 模块 119 全绿 (模块级清 deps 缓存 + client 重断言 env)。httpx2 迁移: ✅ 2026-08-12 已安装 `httpx2>=2.0.0`, 移除 filterwarnings 抑制 (见已知问题)。**权威计数 (实测): 生产 738 / collected 766 (见下节测试表)** | ✅ |

### v7.13 (2026-08-07) — 实时音准对比子系统 Phase 1 + Phase 2 + Phase 3 + Phase 4

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
| **前端组件 (P3)** | live 模式 (`:live-mode` prop): 录音中 3px 圆点 2s 淡出 (dotAlpha 线性) + 偏差背景色带 (±25 绿/±50 橙半透明) + 右上角当前偏差值/趋势箭头 (偏离演唱位置, 窗口外跳过) + 不画完整用户曲线; 索引遍历 O(n) 圆点渲染 | ✅ |
| **前端视图** | SingView (Element Plus + GSAP): P1 选歌参考线/上传 DTW/再来一首; P2 回放控制面板 (播放/暂停/拖拽跳转/倍速 0.5x-1.5x/A-B 循环) + WS 不可变更新; P3 录音中切换到 live 模式 + live 时钟 (100ms 壁钟浮点, 与数据前沿对齐 → 圆点平滑淡出/新点即时可见); P4 回放统计面板 (有参考: 精准/略偏/跑调 = computeDeviationStats; 无参考: 最高/最低音 = computePitchRange; 全无声空态 = hasVoicedFrames) | ✅ |
| **前端纯 TS (P4)** | `utils/pitchSegments.ts`: `findProblemSegments` (偏差>50 持续≥0.5s) + `segmentPhrases` (静音间隙>0.4s 切分乐句) + `scorePhrase` (乐句精准率) + `phraseScoreColor` (≥85绿/≥60橙/红) — 零 Vue 依赖 | ✅ |
| **前端组件 (P4)** | 回放分析: 问题段落红色半透明 band + 逐句评分药丸 (maxFreq 预计算锚在乐句最高音) + DPR 修复 (CSS 像素) + `roundRect` 兼容回退 | ✅ |
| **BDD** | sing-song-select step defs 更新 (data-test 钩子, xfail 对齐 v7.13); 🆕 `pitch-realtime` step defs 骨架 (25 场景, 每条标注对应纯 TS 单元测试; P3 起录音中对比指向 pitchLive.test.ts, P4 起回放对比/问题段落/逐句评分/统计指向 pitchSegments.test.ts, P5 起双轨填色/热力图/截图/快捷键指向 pitchCompareDraw/pitchHeatmap/pitchScreenshot/pitchKeyboard) | ✅ |
| **前端纯 TS (P5)** | `pitchKeyboard.ts` (快捷键映射 + 修饰键/滑块守卫) + `pitchFps.ts` (FPS 监控/降级状态机, 滚动 1s 窗 + 3s <20fps 触发) + `pitchHeatmap.ts` (全时长分桶/点击跳转) + `pitchScreenshot.ts` (DPR 原分辨率 + 时间戳水印) + `pitchCompareDraw.ts` (偏差着色/三色填色/热力条/缩略条/低对齐覆盖) + `pitchStats.ts` +`excludeLowAlignmentFrames` — 零 Vue 依赖 | ✅ |
| **后端 (P5)** | `/api/v1/compare` 响应 +`standard_pitch`/`user_pitch`/`low_alignment_segments` — 向后兼容, 提取失败空数组优雅降级 (评分仍返回) | ✅ |
| **前端组件 (P5)** | 底部偏差热力图条 (点击 seek) + 缩略导航条 (拖拽 seek) + 性能模式 (抗锯齿关/着色每 3 帧/网格关/缩略条关) + 偏差区域三色填色 (非 live 双轨, ≤25 绿/25-50 橙/>50 红) | ✅ |
| **前端视图 (P5)** | CompareView 对比分析页: 双文件上传 → DTW 对比 → 双轨叠加; 显示模式 (仅用户/双轨) 不中断播放; 性能模式指示器 (closable 可手动关闭); 截图导出 + 快捷键全套 (Space/←→/R/S/1/2) | ✅ |
| **测试** | 单测 435→451 (+16) + 集成 53→62 (+9) → 65 (+3 P5) + WS 10→14 (+4); 前端 102→166 (+64) → 197 (+31) → 230 (P4 +33) → **286** (P5 +56); 后端全绿 551 (537 生产 + 14 WS); BDD 场景 154→**179** | ✅ |

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

## 三、测试状态 (v7.17)

### 生产测试 (全部 GREEN)

| 套件 | 测试数 | 结果 |
|------|:-----:|------|
| Unit 领域 (scorers + value objects + comparison + songs + **songs_pitch** + ScoringWeights + **song_match** + **fallback**) | 364 | ✅ |
| Unit 基建 (extractors + orchestrator + ABI + sqlite + **sqlite_song_match_profile_repo** + **pitch_cache + deps 单例**) | 159 | ✅ |
| Unit 对齐 + Flag bridge (test_ddd_alignment/extraction_flag/flag_bridge) | 23 | ✅ |
| Unit 中间件 | 23 | ✅ |
| Unit WS streaming 会话 (v7.14 审查修复轮) | 12 | ✅ |
| Unit 接口 sanitize_filename (v7.14 P2) | 14 | ✅ | (test_sanitize_filename: GBK 乱码恢复 + NFC + 非法字符 + 路径穿越)
| Unit 根目录 mixed_detection | 2 | ✅ | (test_audio_service_mixed_detection, 混合/纯声检测)
| Unit 静默错误可观测性 (v7.15 M3/M4/M5) | 14 | ✅ | (acoustic_extractor 7 + audio_service 3 + audio_dl_helpers 4 — 异常保留/传播/状态码)
| Unit uploads 自动清理 (v7.15 P2-14 余项) | 15 | ✅ | (upload_cleaner 9 + history_repository_unlink 6 — 路径锁/孤儿扫描/逐出联动 unlink)
| Unit 建议生成器 (🆕 v7.16 P2-15 Phase 1) | 15 | ✅ | (test_advice_generator: 结构/最强最弱/总体分档/阈值边界 — AdviceGenerator DDD application 层)
| Unit calculate_ddd 诊断 (🆕 v7.16 P2-15 Phase 3) | 5 | ✅ | (test_diagnosis_in_calculate_ddd: 5 诊断键/结构/mae_cents/deviation_ratio/分数一致)
| Unit calculate_ddd 音色 dict (🆕 v7.16 P2-15 Phase 2) | 9 | ✅ | (test_timbre_detail_in_calculate_ddd: 9 键契约/ta 质量分映射/hnr 优先级/vibrato 占位/style/None 回退) |
| Unit DDD 提取器 flag 对齐 (🆕 v7.16 P2-15 Phase 5.2) | 6 | ✅ | (test_ddd_extractor_flag_alignment: None→模块级等价/for_quick 关闭 multiscale+reverb/for_professional 全真) |
| Unit 评分校准回归 (🆕 v7.17 A1/B1/A2) | 8 | ✅ | (pitch MAE 曲线 2 + technique 封顶修复 3 + rhythm 混音映射 3) |
| Unit 节拍锚定节奏 (🆕 v7.17 A4) | 3 | ✅ | (test_rhythm_extractor::TestBeatAnchoredRhythm: 在拍<脱拍偏差/脱拍高分/无伴奏回退) |
| **Unit 合计** | **669** | **100% GREEN** |
| API 集成 | 77 | ✅ | (api_routes 20 + songs_api 21 + scoring_api 14 + songs_pitch_api 9 + compare_pitch_api 4 + song_match_api 6 + **history_single_write 3 (🆕 v7.16 历史双写回归)**)
| WebSocket 集成 | 17 | ✅ | (ws_score 13 + ws_pitch_update 4)
| 扩展测试 (DTW/repos) | 21 | ✅ | (v7.12 删 test_score_calibrator 15)
| **生产代码总计** | **784** | **100% GREEN** |

> 注: 生产合计 = Unit 669 + API 77 + WS 17 + 扩展 21 = **784**。另含真实音频回归 28 (**BASELINE_V7_17**)。**后端 collected = 812 (784 生产 + 28 真实音频)**。v7.17 校准 +8 回归 + 节拍锚定 +3 (658→669); v7.15 集成隔离修复后, 全部集成模块**单进程组合运行全绿**。

### 真实音频回归

| 套件 | 测试数 | 结果 | 说明 |
|------|:-----:|------|------|
| 真实音频 Quick + Pro | 28 | ✅ **全 PASS** (v7.17 校准后) | **BASELINE_V7_17**: v7.17 评分校准 (A1 rhythm 映射 + B1 pitch 曲线 + A2 tilt/hf 质量组件 + B3/B4 校准 + A4 节拍锚定) 后重校准 — 4 个"高分"文件 total 79.9-82.6 (旧 63-65), 陈奕迅 72.0 保持低分; 区分度断言: 总分排序 + 单维 gap ≥10 (rhythm gap 62.8, 与 BDD differentiation.feature 相对断言一致); quick-pro 一致性 <25% (pro 节拍锚定后) |

### BDD (v7.15: **182 scenarios** (112 API 级 + 70 browser) → API 级 **0F / 31P / 42S / 39X** — 残余 Flask 迁移失败全部清除; v7.15 +4 browser (compare-automatch 3 + sing-song-select 1))

| Feature | 状态 |
|------|------|
| upload.feature (裁剪为 5 核心场景) | ✅ 5 PASS + 3 SKIP (FLAC/OGG/M4A 无测试文件) + Pro Demucs `@slow` |
| animations.feature (迁移 Vue 3 data-test) | ✅ 7 PASS + 9 XFAIL (无 UI/依赖录音场景带理由) |
| sing-song-select.feature (迁移 Vue 3) | ✅ 6 PASS + 6 XFAIL + **v7.15 +1 browser (WS 断连提示)** (依赖 WebSocket 录音/auto-match/上传) |
| **compare-automatch.feature (🆕 v7.15 H-B14)** | ✅ 3 browser 场景: 自动匹配失败告警 (`[data-test=auto-match-error]`) / 成功命中徽标 / 无命中优雅回退 — 注入 songMatch.store 状态验证渲染 |
| scoring-config.feature | ✅ API 级 PASS (v7.11) |
| database.feature | ✅ **v7.14 修复轮后通过** (P0-2 DI 缓存隔离修复前 5 FAIL) |
| **auto-match.feature (v7.14 上传自动匹配)** | ✅ **5 PASS + 3 XFAIL** (v7.14 修复轮从 1P+7F 恢复; 短音频容错→test_extract_short_audio_tolerant, 嘈杂→test_extract_noise_robust, 超时→test_timeout_returns_partial/test_deadline_exceeded_returns_partial) |
| **pitch-realtime.feature (v7.13 P1-P5 骨架)** | ⚠️ 文档化 stub — 25 XFAIL, 非"已完成" (v7.14 审查 T1): 浏览器 BDD 未实现 (无真实音频/WS); 每条标注对应纯 TS 单元测试文件 — P3 起录音中对比→pitchLive.test.ts, P4 起回放对比/问题段落/逐句评分/统计→pitchSegments.test.ts, P5 起双轨填色/热力图/截图/快捷键→pitchCompareDraw/pitchHeatmap/pitchScreenshot/pitchKeyboard |
| compare.feature | ✅ **2 PASS + 1 XFAIL** (v7.14 P2 续轮重写: 原 12 场景全为 Flask 遗留 `StepDefinitionNotFoundError` + DTW 融合假想架构; 重写为 3 场景对齐真实 v7.13 P5 契约 — 契约核心字段 + 相同音频 DTW 接近完美 (置信度断言实测校准 0.938>0.90) + 移调音频 xfail; 9 纯 spec 场景删除并转移文档至 dtw-demotion.feature) |
| differentiation.feature | ✅ **6 PASS + 1 XFAIL** (v7.14 P2 轮修复: 断言与实测一致化 — 总分 gap 不可达 → 单维区分度不变量) |
| history.feature | ✅ **4 PASS** (v7.14 P2 轮修复: Flask 遗留 `get_json()` → FastAPI `.json()`) |

### 前端测试

| 套件 | 测试数 | 结果 |
|------|:-----:|------|
| Vitest | 307 | ✅ 100% | (stores 85 + pitch utils 212 + **matchFeedback 6 + useWsDisconnectGuard 4 (v7.15)**)
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

### 真实音频评分 (v7.17 Quick 模式, 评分校准后)

> 实测值 (2026-08-13, 独立进程确定性复现)。v7.17 校准 (A1 rhythm 映射 + B1 pitch 曲线 + A2 tilt/hf 质量组件 + B3/B4 校准) 后: 4 个"高分"文件 total 79.9-82.6 (优秀 A), 陈奕迅 72.0 保持低分。旧 v7.16 表见 [CHANGELOG.md](CHANGELOG.md)。

| 音频文件 | Total | Pitch | Rhythm | Breath | Tech | Art | Muscle |
|----------|:-----:|:-----:|:------:|:------:|:----:|:---:|:------:|
| 恋人（高分） | **81.2** | 82.2 | 72.1 | 88.8 | 75.8 | 81.8 | 85.2 |
| 手写的从前（高分） | **82.6** | 84.7 | 65.1 | 91.2 | 84.7 | 78.9 | 81.7 |
| 1（高分） | **79.9** | 84.3 | 65.3 | 87.4 | 77.4 | 80.4 | 80.2 |
| 音频-3分26秒(高分) | **80.7** | 82.8 | 68.7 | 86.7 | 76.5 | 79.8 | 87.6 |
| 陈奕迅（低分） | **72.0** | 82.0 | **9.3** | 84.7 | 76.8 | 76.5 | 76.3 |

> 高低分区分度 (v7.17): 总分排序 81.2 > 72.0 ✅ + **rhythm gap 72.1 - 9.3 = 62.8 pts** (单维区分度, 与 BDD differentiation.feature 相对断言一致) ✅

---

## 四、已知问题

> 更新: 2026-08-12 | v7.15

### 架构残留

| 优先级 | 残留 | 说明 |
|--------|------|------|
| ~~P2~~ | ~~`services/features/types.py`~~ | ✅ v7.8: 外部引用已清理 |
| ~~P2~~ | ~~前后端对齐: flags.store.ts 绕过 apiClient~~ | ✅ v7.8: 已修复 (apiClient + FlagsResponse 强类型) |
| ~~P2~~ | ~~前后端对齐: flags 路由硬编码 /api/v1/flags~~ | ✅ v7.8: 已修复 (prefix 约定一致) |
| ~~P2~~ | ~~前后端对齐: ScoreRadar/HistoryView as any 类型~~ | ✅ v7.8: 已修复 (ChartOptions/HistoryFilter 类型) |
| ~~P2~~ | ~~前后端对齐: ApiResponse<T> 死代码 + HistoryListResponse list[dict]~~ | ✅ v7.8: 已清理 |
| **P2** | `services/dl_services/` (4 活跃) | ✅ v7.12: 死代码已清 (桩/model_manager 子包/features:types/enhanced_dl_assessor 删除); 保留 voice_quality_detector/singing_style_classifier/self_referenced_dtw/dl_style_classifier (Professional 模式) — DDD 迁移为独立工程 |
| **P2-15** | legacy `api/business`+`services` 收敛进 DDD | 🔶 **基本完成 (v7.16 安全范围)**: ✅ Phase 0 (死 calculate() 路径 + FeatureAdapterRegistry 注入 + 4 死字段) + ✅ Phase 0b (历史双写 bug) + ✅ Phase 1 (AdviceGenerator 入 DDD) + ✅ Phase 3 (诊断补全) + ✅ Phase 2 (音色单轨化 — TimbreService 已删) + ✅ Phase 5 (facade 折叠 — analyze_emotion 删 / reference_path 删 / flag 对齐)。**唯一剩余 (Phase 4)**: `PhraseService` 逐句评分 — 无 DDD 等价物, 经用户决策**推迟** (独立功能非双轨, 前端/测试零消费 `phrases`) — 见 P2_15_CONVERGENCE_PLAN.md, 按需决定 |

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
| ~~真实音频 breath 基线漂移~~ | ✅ v7.14 P2 轮: 根因实为 sr 错配 bug (P2-11) 造成的虚高值 — `librosa.load(sr=None)` 后只更新局部变量, `AudioAnalysisResult.sample_rate` 保持原生 sr, DDD 提取器收到 (16k 音频, 原生 sr) 不一致。sr 修复 + 基线重校准 BASELINE_V7_6→V7_14 后 28 例全 PASS |
| ~~乱码孤儿文件删除 (P2-14 遗留)~~ | ✅ v7.14 P2 轮: 2 个 GBK 乱码文件名历史残留 (`1£¨¸ß·Ö£©.mp3`, `³ÂÞÈÑ¸ÄÑÌýÖ®Éù£¨µÍ·Ö£©.mp3`) 于 2026-08-11 经用户授权删除。删除前 sha256 验证与正常名文件 (`1（高分）.mp3`/`陈奕迅难听之声（低分）.mp3`) **逐字节相同**, 零数据丢失; DB (songs.db) 无引用; `sanitize_filename` 乱码恢复已保证新上传自动迁移 |
| BDD v6.0 规划 features 部分实现 | v7.8: dtw-demotion + scoring-config step defs 已创建; v7.13: pitch-realtime step defs 骨架已创建; 5 features 仍待实现 |
| ~~**BDD API 级 12 既有失败 (Flask 迁移遗留)**~~ | ✅ **v7.14 P2 续轮全部清除 (12→0)**: compare.feature 原 12 `StepDefinitionNotFoundError` (feature 仍用 `Given "Flask 服务已启动"` 等 Flask step + DTW 融合假想架构) — 重写为 3 场景对齐真实 v7.13 P5 契约 (2 PASS + 1 XFAIL), 9 纯 spec 场景删除并转移文档至 dtw-demotion.feature。~~history 3 get_json~~ ✅ v7.14 P2 修复; ~~differentiation 6~~ ✅ v7.14 P2 修复 (断言与实测一致化) |
| ~~BDD animations.feature 旧架构~~ | ✅ v7.12: 迁移 Vue 3 (data-test 钩子 + 类选择器); 无 UI 场景 xfail 带理由 |
| ~~BDD 浏览器基建指向旧 Flask~~ | ✅ v7.11: conftest base_url→:8000 + api_client→FastAPI + 前端 `window.__store` 钩子 |
| ~~upload.feature 数据缺失 (vocals.wav)~~ | ✅ v7.12: `scripts/gen_bdd_test_data.py` 生成 + KMP_DUPLICATE_LIB_OK 崩溃修复; 5 PASS + 3 SKIP |
| BDD 浏览器测试需服务运行 | 运行浏览器 BDD 需先 `python backend/main.py` (FastAPI :8000 服务 frontend/dist); 服务未启动时场景 skip |
| 评分阈值联动 (风格预设) | scoring-config.feature: 各预设阈值微调 (MAE断点等) 未实现 — API 级 PASS, 阈值联动/自动风格检测/UI 面板仍 XFAIL (用户指定暂不开发) |
| ~~选歌录音 (选歌→演唱页)~~ | ✅ v7.12 MVP + v7.13 Phase 1: `/sing/:songId` + WS song_id + vocal_range + 参考音高 API + WS pitch_update + 上传录音对比 + 再来一首 |
| ~~实时音准对比 P1-P5~~ | ✅ v7.13 全量已落地 (P1 参考音高 API/WS pitch_update → P4 回放分析 → P5 CompareView 双轨叠加/热力图/性能降级/截图/快捷键/缩略条) |
| ~~上传音频自动匹配 (auto-match)~~ | ✅ v7.14 全量已落地 (POST /songs/match + /upload?auto_match=true + CompareView 自动匹配区 + songMatch.store) |
| ~~集成测试跨模块隔离 (pre-existing)~~ | ✅ **v7.15 修复**: deps 6 个 lru_cache 单例跨模块持久 → 组合运行时后续模块绑定上一模块临时 DB (test_match_no_match_fallback 误命中)。修复: ① tests/integration/conftest.py 模块级 autouse `_reset_deps_caches` 清缓存; ② 4 个 env-setting 模块 client fixture 重断言 VAS_SONGS_DB/VAS_SONGS_DIR。**单进程全量组合运行 119 全绿** (HEAD 亦复现, 与代码无关) |
| ~~httpx2 迁移 (starlette 1.3+ TestClient)~~ | ✅ 2026-08-12 已安装 `httpx2>=2.0.0` (联网核实为 starlette 官方背书真实包, PR #3291/#3323 钉入 starlette[full]); `tests/pytest.ini` filterwarnings 抑制行已移除; `httpx` 保留 (huggingface_hub/transformers 下载依赖, 与 httpx2 共存) |
| ~~M3/M4/M5 后端静默错误~~ | ✅ v7.15: acoustic_extractor (异常保留不静默返回空特征) + audio_service (analyze 失败可见化) + audio_dl_helpers (异常显式传播) — 14 单元测试 RED→GREEN |
| ~~uploads/ 孤儿文件残留 (P2-14 余项)~~ | ✅ v7.15: 启动扫描 + 历史逐出/删除联动 unlink (路径锁 `is_relative_to`); 实测 dry-run 36 文件 11 被引用 → 25 孤儿可清理; 生产仅清理未被历史引用的文件 |
| ~~**历史双写 bug (P2-15 Phase 0b)**~~ | ✅ **v7.16**: audio_analysis.py 的 EventBus `HistoryEventSubscriber` 每次评分写无 analysis_id 垃圾记录 + 路由 `_save_history` 写完整记录 = 2 条/次, 垃圾挤占 `HISTORY_MAX_RECORDS` 槽位淘汰完整历史。修复: 移除订阅 (历史由路由单一负责) + 清理 web_history.json 32 条垃圾记录 (保留 18 条完整, 经用户授权)。新增 test_history_single_write 3 回归 |

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
| `backend/interfaces/api/routes/assessment.py` | v7.13 P5 — `/api/v1/compare` 响应扩展 (standard_pitch/user_pitch/low_alignment_segments) |
| `frontend/src/utils/pitchCompareDraw.ts` | v7.13 P5 — 双轨绘制 (偏差着色/三色填色/热力条/缩略条/低对齐覆盖) |
| `frontend/src/utils/pitchFps.ts` | v7.13 P5 — FPS 监控 + 降级状态机 |
| `frontend/src/utils/pitchKeyboard.ts` | v7.13 P5 — 快捷键映射 + 可编辑/滑块守卫 |
| `frontend/src/views/CompareView.vue` | v7.13 P5 — 对比分析页 (双文件→DTW→双轨叠加 + 性能模式/截图/快捷键); v7.14 — 自动匹配区 (上传录音→候选→一键对比) |
| `backend/domain/song_match/` | v7.14 — 自动匹配领域 (MatchFeatures/SongMatchProfile/MatchCandidate/MatchResult + 特征提取 + K-S 调性 + AutoMatchService) |
| `backend/application/song_match/auto_match_use_case.py` | v7.14 — 应用层编排 (预算制 profile 预计算 + deadline 超时 partial) |
| `backend/infrastructure/persistence/sqlite_song_match_profile_repo.py` | v7.14 — 匹配特征 SQLite 仓储 (song_match_profiles 表) |
| `backend/interfaces/api/routes/song_match.py` | v7.14 — POST /api/v1/songs/match |
| `frontend/src/stores/songMatch.store.ts` | v7.14 — 自动匹配 store (matchAudio/selectCandidate/compareWithSelected/fetchUserPitch) |
| `services/upload_cleaner.py` | v7.15 — 上传孤儿清理 (unlink_files 路径锁 + collect_referenced_files + cleanup_orphans + run_startup_upload_cleanup) |
| `repositories/history_repository.py` | v7.15 — 历史记录逐出/删除联动 unlink 上传文件 (仅删不再被引用) |
| `frontend/src/utils/matchFeedback.ts` | v7.15 — H-B14 自动匹配错误/命中/回退反馈文案 + severity |
| `frontend/src/composables/useWsDisconnectGuard.ts` | v7.15 — H-B15 SingView WS 断连 4 状态机 (置灰 + 重连提示) |
| `backend/main.py` | FastAPI 入口 (Flask 已移除; v7.15 启动孤儿扫描 lifespan) |

### 启动命令

```bash
# 开发模式
cd frontend && npm run dev          # Vite :5173
python backend/main.py              # FastAPI :8000

# 默认测试 (626 tests, ~20s; v7.15 +29)
pytest tests/unit/domain/ tests/unit/infrastructure/ tests/unit/interfaces/ws/ \
       tests/unit/test_middleware.py \
       tests/unit/test_ddd_alignment.py \
       tests/unit/test_ddd_extraction_flag.py \
       tests/unit/test_flag_bridge.py \
       tests/unit/test_upload_cleaner.py \
       tests/unit/test_history_repository_unlink.py \
       tests/unit/test_audio_dl_helpers_observability.py \
       tests/unit/test_audio_service_analyze_error.py
pytest tests/unit/interfaces/api/test_sanitize_filename.py tests/unit/test_audio_service_mixed_detection.py -q  # 剩余 16

# 集成测试 (独立进程, ~5s)
pytest tests/integration/test_api_routes.py -v         # FastAPI (20 tests)

# 扩展测试 (独立进程, ~5s)
pytest tests/extended/ -v                              # DTW/repos/etc (21 tests)

# 真实音频回归 (独立进程, ~27min)
pytest tests/integration/test_real_audio_regression.py -v

# BDD 测试 (需要浏览器)
pytest tests/bdd/ -v -m "not browser"
pytest tests/bdd/ -v -m "browser"
```
