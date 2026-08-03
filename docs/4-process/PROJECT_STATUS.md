# 项目状态

> 更新: 2026-08-02 | 版本: **v7.9** | 分支: `feat/v7-fastapi-vue-refactor`

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

## 三、测试状态 (v7.9)

### 生产测试 (全部 GREEN)

| 套件 | 测试数 | 结果 |
|------|:-----:|------|
| DDD 领域 (scorers + value objects + comparison + songs) | 154 | ✅ |
| DDD 基建 (extractors + orchestrator + ABI + sqlite) | 149 | ✅ |
| DDD 对齐 + Flag bridge + GNE | 22 | ✅ |
| 中间件 | 22 | ✅ |
| **DDD 合计** | **406** | **100% GREEN** |
| FastAPI 集成 | 33 | ✅ |
| 扩展测试 (DTW/repos/calibrator) | 36 | ✅ |
| **生产代码总计** | **475** | **100% GREEN** |

> 注: DDD 子项 (领域/基建/对齐/中间件) 为近似归类, 合计以实测命令 `pytest tests/unit/domain/ tests/unit/infrastructure/ ... test_flag_bridge.py` = 406 为准。

### 真实音频回归

| 套件 | 测试数 | 结果 | 说明 |
|------|:-----:|------|------|
| 真实音频 Quick + Pro | 28 | ✅ 100% | BASELINE_V7_6 |
| BDD | 16 step files | ✅ | 162 scenarios collected + 6 features pending step defs |

### 前端测试

| 套件 | 测试数 | 结果 |
|------|:-----:|------|
| Vitest (stores) | 33 | ✅ 100% |
| vue-tsc type check | 0 errors | ✅ |
| Vite build | 8.5s | ✅ |

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

> 更新: 2026-08-02 | v7.9

### 架构残留

| 优先级 | 残留 | 说明 |
|--------|------|------|
| ~~P2~~ | ~~`services/features/types.py`~~ | ✅ v7.8: 外部引用已清理 |
| ~~P2~~ | ~~前后端对齐: flags.store.ts 绕过 apiClient~~ | ✅ v7.8: 已修复 (apiClient + FlagsResponse 强类型) |
| ~~P2~~ | ~~前后端对齐: flags 路由硬编码 /api/v1/flags~~ | ✅ v7.8: 已修复 (prefix 约定一致) |
| ~~P2~~ | ~~前后端对齐: ScoreRadar/HistoryView as any 类型~~ | ✅ v7.8: 已修复 (ChartOptions/HistoryFilter 类型) |
| ~~P2~~ | ~~前后端对齐: ApiResponse<T> 死代码 + HistoryListResponse list[dict]~~ | ✅ v7.8: 已清理 |
| **P2** | `services/dl_services/` (11 files) | style classifier, VAD, DTW 仍在使用 |

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
| **P1** | BDD animations.feature 针对旧架构 | 15 scenarios 需迁移到 Vue 3 DOM 选择器 |

### 测试遗留

| 问题 | 说明 |
|------|------|
| BDD v6.0 规划 features 部分实现 | v7.8: dtw-demotion + scoring-config step defs 已创建; 6 features 仍待实现 |
| BDD animations.feature 旧架构 | 15 scenarios 针对已废弃的 Vanilla JS 架构, 需迁移 |

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
| `backend/main.py` | FastAPI 入口 (Flask 已移除) |

### 启动命令

```bash
# 开发模式
cd frontend && npm run dev          # Vite :5173
python backend/main.py              # FastAPI :8000

# 默认测试 (406 tests, ~16s)
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
