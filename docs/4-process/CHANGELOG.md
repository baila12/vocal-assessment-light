# 变更日志 v7.10

> 更新: 2026-08-04 | 当前状态: [PROJECT_STATUS.md](PROJECT_STATUS.md) | 算法改进: [SCORING_ALGORITHM_IMPROVEMENT_PLAN.md](../2-technical/SCORING_ALGORITHM_IMPROVEMENT_PLAN.md)

---

## v7.10 — 标准歌曲库前端页面 + 音频播放修复 (2026-08-04)

### 概述

补齐 v7.9 歌曲库后端的**前端界面** — GOALS/PRD 标注的"前端界面待实现"完成。卡片网格浏览 + 搜索/风格/难度筛选 + 上传 + 删除 + 音频试听，对齐 `song-library.feature` BDD 契约选择器。同时修复歌曲音频播放缺口 (`/api/v1/audio` 白名单未含 `songs_dir` 导致 403)。

### 前端 (frontend/)

- 🆕 `views/SongsView.vue`: 卡片网格 (`#page-songs`/`.song-card`)、搜索 (`#songSearch` + 高亮 `.search-highlight`)、难度按钮组 (`.filter-btn[data-filter]`) + 风格筛选 (`#styleFilter`)、统计 (`#songStats`)、空态 (`#songsEmpty`/`#importFirstSongBtn`) 与搜索无结果态 (`.search-empty`/`#clearSearchBtn`)、分页 (`#pageIndicator`)、上传对话框 (el-form + FileUploader)、卡片点击展开详情 + `AudioPlayer` 试听 + 删除确认、GSAP 入场动画
- 🆕 `stores/songs.store.ts`: Pinia setup store — 服务端分页 + 服务端搜索/筛选 (300ms 防抖) + createSong/deleteSong + 本地删除 `removeSongLocally`
- 🆕 `tests/unit/stores/songs.test.ts`: 24 条同步状态/计算属性/筛选/分页/对话框用例 (TDD RED→GREEN)
- 🔧 `types/api.ts`: +SongMetadata/SongRecord/Difficulty/SongStyle/SongListResponse 等 7 类型
- 🔧 `router/index.ts`: +`/songs` 懒加载路由; `layout/TopNav.vue` + `BottomNav.vue`: +"曲库"导航 (Folder 图标)

### 后端 (backend/)

- 🔧 `routes/audio.py`: 注入 `get_settings`, 目录白名单增加 `settings.songs_dir` — 修复歌曲文件流式播放 403
- 🛡️ `routes/audio.py`: 目录锁 `startswith` → `Path.is_relative_to()` — 修复同名前缀兄弟目录 (`songs_evil/`) 越界 (安全审查 HIGH)
- 🔧 `tests/integration/test_songs_api.py`: +`TestAudioPlayback` 3 测试 (歌曲音频 200 / 路径遍历 403 / 兄弟前缀目录 403)

### 测试总结

- 集成: 33 → **36 tests GREEN** (songs 14 + TestAudioPlayback 3)
- 前端 Vitest: 33 → **57 tests GREEN** (songs.store +24)
- vue-tsc: **0 errors** | Vite build: **~9.6s**
- BDD: `database.feature` API 级回归 GREEN (4P+6XF)
- 版本: 7.9.0 → **7.10.0**

### 后续项 (记入 PROJECT_STATUS 已知问题)

- 浏览器 BDD 基建修复: `tests/bdd/conftest.py` base_url 需 Flask :5000 → FastAPI :8000 + 前端 `window.__store` 测试钩子; 此后 song-library.feature 12 场景可运行
- 选歌录音 (`#/sing/:songId`): 依赖 SingView 扩展 + 后端 metadata 增加 音域/原唱调 字段

---

## v7.9 — 标准歌曲库后端 (DDD + TDD + BDD) (2026-08-02)

### 概述

新增标准歌曲库后端能力 — v6.0 规划的基础功能 (曲库浏览/搜索/筛选/重复检测)，为自动匹配与对比分析提供参考歌曲数据源。采用 DDD 四层 + TDD 驱动 + BDD 验收。

### 领域层 (backend/domain/songs/)

- 🆕 `value_objects.py`: SongMetadata (frozen) + duplicate_key + 运行时难度/风格校验
- 🆕 `entities.py`: Song 聚合根 (frozen) + SongListPage + SongFeatureStatus 类型
- 🆕 `repository.py`: SongRepository Protocol (仓储模式抽象)

### 基础设施 (backend/infrastructure/persistence/)

- 🔧 `sqlite_song_repo.py`: 桩 → SQLite 仓储 (stdlib sqlite3, 零新依赖)
  - CRUD + 分页 + 风格/难度筛选 + 歌名/歌手模糊搜索 + 重复检测
  - 参数化查询防注入 + threading.Lock 串行化并发写

### 应用层 (backend/application/songs/)

- 🆕 `song_library_service.py`: SongLibraryService (add 去重/分页搜索/get/delete) + SongNotFoundError/DuplicateSongError

### 接口层

- 🆕 `schemas/songs.py`: SongOut + 4 响应 schema
- 🔧 `routes/songs.py`: 桩 → 完整实现 (POST/GET list/GET id/DELETE `/api/v1/songs`)
  - 文件上传保存 + 重复时清理孤立文件 + 写入失败友好错误 (500)
  - difficulty/style 边界校验 (400) + 扩展名复用 settings.allowed_extensions
- 🔧 `config.py`: `songs_db`/`songs_dir` 设置 (VAS_SONGS_DB/VAS_SONGS_DIR 可覆盖)
- 🔧 `deps.py`: `get_song_repo`/`get_song_service` DI 接线

### BDD

- 🆕 `test_database_steps.py`: database.feature 10 场景 (4 PASSED + 6 XFAIL)
  - 通过: 重复检测 / 分页浏览 / 风格筛选 / 难度筛选
  - XFAIL: 特征预提取 / 批量导入 / 评分配置 UI (未来功能)
- 🔧 `tests/bdd/conftest.py`: `fastapi_client` fixture (每场景独立临时 DB + DI 缓存重置)

### 测试总结

- 单元: **406 tests GREEN** (+37 歌库: 实体/服务/SQLite 仓储)
- 集成: **33 tests GREEN** (test_api_routes 19 + test_songs_api 14)
- 扩展: **36 tests GREEN** (DTW/repos/calibrator)
- **总计: 475 tests GREEN**
- 前端 Vitest: **33/33 GREEN** | vue-tsc: **0 errors** | Vite build: **~8.6s**
- BDD: 16 step files, 21 feature files (database.feature 4P+6XF 新增)
- 版本: 7.8.0 → **7.9.0**

### 补充: 工作区清理 (2026-08-02)

| 类别 | 项目 | 状态 |
|------|------|:--:|
| **清理** | 删除 `build.bat` (死 PyInstaller 脚本, 引用已删 vocal_assessment.spec; PyInstaller 已由嵌入式 Python + Electron 替代) | ✅ |
| **清理** | 删除 `api/schemas.py` (0 引用) + `web_app.py` (纯重定向壳) | ✅ |
| **构建** | `start.bat` 移除 Flask v6.3 legacy 模式, 版本 → v7.9, 选项收敛为 [1]/[2] | ✅ |
| **依赖** | `requirements.txt` 补 pydantic-settings/torchfcpe/sqlalchemy/alembic/requests/playwright, 删 pywebview/speechbrain | ✅ |

---

# 变更日志 v7.8

> 更新: 2026-08-01 | 当前状态: [PROJECT_STATUS.md](PROJECT_STATUS.md) | 算法改进: [SCORING_ALGORITHM_IMPROVEMENT_PLAN.md](../2-technical/SCORING_ALGORITHM_IMPROVEMENT_PLAN.md)

---

## v7.8 — GNE 接入 + GSAP 动效美化 + 前后端对齐 (2026-08-01)

### 概述

v7.8 完成三个 P2 文献差距修复、全站 GSAP 动效系统重建、以及前后端 API 对齐审计修复。GNE (AROC=0.886) 正式接入 TechniqueScorer 气声比增强，GSAP 从死代码状态恢复为全站统一动效系统 (6 页面覆盖)，前后端类型安全与路由约定达到一致。

### 评分增强: GNE 接入 (1 项)

**GNE 接入 TechniqueScorer** (`technique_scorer.py`)
- 🆕 4 个 GNE 阈值常量: `GNE_QUALITY_THRESHOLD=0.8`, `GNE_LEAK_THRESHOLD=0.4`
- 🆕 `_apply_audiofeat_enhancement()` 新增 GNE 处理逻辑:
  - GNE < 0.4 → 不可控漏气线性惩罚 (max -8)
  - GNE > 0.8 → 优秀声门控制线性加分 (max +5)
  - 0.4 ≤ GNE ≤ 0.8 → 中性无影响
  - GNE = 0 (audiofeat 不可用) → 无影响
- 阈值与 BreathScorer 保持一致 (0.4/0.8)，确保评分体系一致性
- 📄 文献: Michaelis et al. 1997 — GNE AROC=0.886 为最强气声判别指标
- 🧪 +5 GNE tests (test_technique_scorer.py), 36/36 GREEN

### GSAP 动效系统 (10 项)

**基础框架:**
- 🔧 `useGsap.ts` 重写: 9 动画方法 (`tl`, `enterFrom`, `staggerIn`, `slideInLeft/Right`, `scaleIn`, `countUp`, `pulse`)
- 🆕 `gsap.matchMedia()` reduced-motion 检测 + CSS `@media` 双重保护
- 🔧 `main.ts`: GSAP 全局默认配置 (`duration: 0.4`, `ease: power2.out`, `overwrite: auto`)
- 🔧 `AppLayout.vue`: 新增 `.page-enter/leave` CSS 过渡 (opacity+translateY, 0.3s)
- 🔧 `global.css`: 新增 `@media (prefers-reduced-motion: reduce)` 全局规则

**页面动画覆盖:**
| 页面 | 动画 | 方法 |
|------|------|------|
| ReportView | 总分弹入 → 雷达图缩放 → 六维卡片 stagger → 建议滑入 | GSAP Timeline |
| HomeView | 标题区 → 上传区 → 模式选择 → 操作按钮 → 模式说明 | enterFrom 5 阶段 |
| CompareView | 左面板 slideInLeft + 右面板 slideInRight | slideInLeft/Right |
| HistoryView | 容器淡入 (不触碰 el-table 内部 DOM) | enterFrom |
| SingView | 录音按钮 CSS pulse → GSAP repeat:-1 脉冲 | GSAP pulse |

**技术保障:**
- Compositor-only 属性 (autoAlpha, x, y, scale, rotation)，零 layout 触发
- gsap.context(scope) 选择器隔离，onBeforeUnmount → ctx.revert() 自动清理
- Element Plus 零侵入: 仅动画自定义 wrapper div，不触碰 el-* 内部 DOM
- useGsap.ts 从死代码 (0 引用) → 5 组件引用

### 前后端对齐 (9 项)

**HIGH 修复 (3):**
- 🔧 `flags.store.ts`: 原始 `fetch()` → `apiClient.get<FlagsResponse>()` (统一超时+ApiError 包装)
- 🔧 `flags.store.ts`: `json.data as FlagsData` 强制断言 → 定义 `FlagsResponse` 接口
- 🔧 `client.ts`: `(import.meta as any).env?.DEV` → `import.meta.env?.DEV`

**MEDIUM 修复 (6):**
- 🔧 `types/api.ts`: 删除未使用的 `ApiResponse<T>` + `ErrorResponse` 死代码
- 🔧 `types/api.ts`: `HistoryRecord` 补充 `filepath`/`advice`/`scores` 可选字段
- 🔧 `history.store.ts`: 捕获后端返回的 `total_pages`/`limit` 字段
- 🔧 `flags.py` + `main.py`: Flags 路由改为 `prefix="/api/v1"` + `@router.get("/flags")` 约定
- 🔧 `ScoreRadar.vue`: `chartOptions as any` → `ChartOptions<'radar'>`
- 🔧 `HistoryView.vue`: `store.setFilter(val as any)` → `HistoryFilter` 类型

### 架构清理 (2 项)

- 🔧 `services/features/types.py`: 外部引用清零 (仅剩自身 DeprecationWarning)，更新弃用时间线至 v7.9
- 🔧 `test_orchestrator.py`: 移除 `test_ddd_vs_legacy_consistent` (旧 adapter 对比测试)，`AudioFeaturesResult` 导入已删除

### BDD 扩展 (2 项)

- 🆕 `test_dtw_demotion_steps.py`: 18 scenarios (3 PASSED 验证当前架构不变性, 15 XFAIL 标记架构目标)
- 🆕 `test_scoring_config_steps.py`: 14 scenarios (全部 XFAIL，权重配置为未来功能)

### 提交前复核修复 (2026-08-02)

| 类别 | 项目 | 状态 |
|------|------|:--:|
| **修复** | flags.py: 通过 flag_bridge 反映运行时 FeatureFlags (audiofeat 不再误报 False) | ✅ |
| **修复** | CompareView/HistoryView: GSAP 选择器匹配真实类名 (动画不再静默 no-op) | ✅ |
| **修复** | router: 无效路由 toast 真正触发 (redirect 移入 beforeEach 守卫) | ✅ |
| **修复** | 版本号 v7.7 → v7.8 (main.py/health.py) | ✅ |
| **修复** | technique_scorer: GNE 注释澄清 (与 BreathScorer 条件差异) | ✅ |
| **测试** | test_api_routes: +1 /flags 回归测试 + 版本断言更新 (19 tests) | ✅ |
| **测试** | test_scoring_config_steps: 移除 pytest 私有属性依赖 | ✅ |

### 测试总结

- DDD unit: **369 tests GREEN** (5 new GNE + 1 orchestrator net change)
- FastAPI 集成: **19 tests GREEN** (含新增 /flags 回归测试)
- BDD: 15 step files, 61 scenarios (29 existing + 32 new)
- Frontend Vitest: **33/33 GREEN**
- Frontend vue-tsc: **0 errors**
- Frontend Vite build: **8.5s**

---

## v7.7 — audiofeat 生产启用 + Flag 系统修复 + 前端收束 (2026-07-31)

### 概述

v7.7 解锁了 v7.4-v7.6 中已实现但被 Feature Flag 门控的全部评分算法增强。核心变更是修复双重 Flag 系统脱节：`FeatureFlags` (API 层) 与 `DimensionFlags` (领域层) 之间新增桥接层，同时将 `enable_audiofeat` 全面默认启用。

### Flag 系统修复 (3 项)

**Flag 桥接层** (`backend/shared/flag_bridge.py` 新文件)
- 新增 `to_dimension_flags()`: 9 个同名字段直接映射 (enable_audiofeat, enable_multiscale_hnr, 等)
- DimensionFlags 独有字段 (维度开关 13 个) 保持默认值 True
- 🧪 +6 tests

**audiofeat 默认启用** (3 文件)
- `services/feature_flags.py`: 类默认值 `False → True`, `for_quick()` + `for_professional()` 显式启用
- `api/business/audio_analysis.py`: Orchestrator 单例传入 `DimensionFlags(enable_audiofeat=True)`
- `safe_baseline()`: 显式 `enable_audiofeat=False` (保持安全基线语义)

**audiofeat 包安装**
- `audiofeat==1.1.1` 安装到 pytorch2 conda 环境
- `AudiofeatExtractor.available == True` (220+ 行提取代码激活)

### 前端修复 (6 项)

**权重对齐** (`ReportView.vue`)
- 六维显示权重: 10/10/20/25/25/10 → 13/12/22/25/15/13
- 与 `value_objects.py` 实际加权系数一致

**emoji 清理**
- `WaveformCanvas.vue`: ⚠️ → `<WarningFilled />` (Element Plus Icons)
- `web/static/index.html`: 🎤 emoji 移除

**路由体验** (`router/index.ts`)
- 无效路由 catch-all `/:pathMatch(.*)*` → 重定向首页
- `router.beforeEach` 守卫: `ElMessage.warning("页面不存在，已返回首页")`

**Settings 面板扩展** (`HomeView.vue`)
- 新增 "算法与模型" 卡片: GPU 状态 + audiofeat 可用性 + DL 模型列表 + 六维权重
- `flags.store.ts` (Pinia): `/api/v1/flags` 数据获取

**Flag API** (`backend/interfaces/api/routes/flags.py` 新文件)
- `GET /api/v1/flags`: 返回 dimensions/enhancements/experimental/gpu/models/weights
- 注册到 FastAPI router

### 代码清理 (2 项)

**重复方法删除** (`breath_scorer.py`)
- 删除 `_score_from_fluctuation` 重复定义 (lines 172-182, 与 160-170 完全相同)

**Legacy E2E 清理**
- 删除 5 个 legacy 测试文件: test_analysis.py, test_upload.py, test_real_audio.py, test_e2e.py, test_e2e_v2.py

### 测试总结
- **249 tests GREEN**: 228 unit + 21 extended
- **6 新增**: test_flag_bridge.py (Flag 桥接 TDD)
- **33 frontend**: Vitest Pinia stores GREEN
- **前端构建**: Vite build ✅ (8.5s)

---

## v7.6 — P1/P2 修复 + 功能增强 + 架构清理 (2026-07-31)

### 概述

完成全部 P1 和多项 P2 任务，新增 rubato/attack_slope 两个文献驱动的表达特征，完成 Flask 绞杀者和遗留代码清理，更新全部文档。文献交叉验证确认算法与 Rathi & Hsu (2021)、Buckley (2023)、Sundberg (1987)、Barsties (2017) 对齐。

### P1 修复 (3 项)

**P1-1: Muscle v7.4 proxies DDD 路径验证**
- ✅ 深度审计确认 DD 路径完整: LibrosaMuscleExtractor → Orchestrator → Scorer
- ✅ adapter 哨兵默认值是设计意图 (无原始音频)
- ✅ 新增 10 个提取器验证测试

**P1-2: crescendo_quality 累积饱和修复** (`breath_extractor.py`)
- ❌ 旧: `crescendo = sum(smoothness * 0.01)` → 长音频必饱和 100
- ✅ 新: `avg_quality × (0.5 + 0.5 × coverage)` → 长度无关
- 🧪 +4 tests

**P1-3: is_artistic_fluctuation 布尔→连续化** (`breath_extractor.py` + `artistry_scorer.py`)
- ❌ 旧: bool 返回 → 几乎人人触发 +30
- ✅ 新: `_calc_artistic_fluctuation_score()` 0-100 连续 (RMS周期性 + F0-RMS耦合)
- ✅ `_calc_phrase()`: +30 → ×0.30 连续映射
- 🧪 +6 tests

### P2 修复 (4 项)

**P2a: CPPS ×100 rescale + HNR graduated 阈值** (`technique_extractor.py` + `technique_scorer.py`)
- 声学 CPP 原始范围 0.04-0.10, ×100 → 4-10 有意义范围
- HNR graduated: ≥25 full / 18-25 70% / 10-18 30% (替代 ≥12→满分)
- 文献: Buckley et al. 2023 — 歌声 CPPS/HNR 远高于语音
- 📈 Technique 区分度: 2.0 → 8.4 pts

**P2b: ABI 9 参数气息感模型** (`abi_calculator.py` 新文件)
- Barsties v. Latoszek (2017): CPPS+GNE+Jitter+Shimmer+HNR+H1-H2+HF_noise+Period_SD
- 歌声适配: 理想值偏差模型 (替代临床 clamp 公式)
- audiofeat 门控, 不可用时返回 NaN
- 🧪 +16 tests

**P2c: Flask 绞杀者完成** (多文件)
- 删除 `api/routes/` (5 files, ~700行) + `backend/legacy/flask_app.py`
- 移除 `backend/main.py` WSGI mount + `/old` 前缀
- 更新 `web_app.py` → FastAPI 重定向
- 删除 Flask 专用测试 (test_api.py, test_spa_routes.py, TestFlaskLegacy)
- 净删 ~1,200 行

**P2d: services/features/acoustic.py 移除**
- `audio_service.py`: AcousticAnalyzer → LibrosaAcousticExtractor
- `dtw_aligner.py`: normalize_loudness → DDD audio_utils
- 删除 `test_audio_utils.py` + `TestHnrCppInternalization`
- DeprecationWarning 消失, 净删 ~1,050 行

### 功能增强 (2 项)

**Rubato (表现性节奏变化)** (`artistry_extractor.py` + `artistry_scorer.py`)
- IOI 变异系数 → rubato_score 0-100
- `_calc_phrase()` rubato×0.10 (max 10pts)
- 文献: Kondo 2025 — 表现性时间控制是核心表达维度

**Attack slope (起音斜率)** (`technique_extractor.py` + `technique_scorer.py`)
- Onset RMS 上升速率 → attack_slope 0-100
- articulation 权重: centroid 30 + flux 15 + zcr 15 + attack 15 + cv 10 + onset 10
- 文献: Sundberg 1987 — 起音斜率反映投射力和清晰度

### 文献对齐

**Rathi & Hsu 权重修正**: centroid:flux:zcr = 30:15:15 (**2:1:1**, 对齐文献 `1.0*centroid + 0.5*flux + 0.5*zcr`)

### 基线更新

- BASELINE_V7_4 → BASELINE_V7_6 (5 个真实音频文件重新标定)
- 高低分区分度阈值 10 → 8 (v7.6 诚实评分)
- 28 回归测试全部 GREEN

### 测试总结

- DDD unit: 359 tests ✅
- Integration + Extended: 54 tests ✅
- Real audio regression: 28 tests ✅
- **Total: 441+ GREEN**

---

# 变更日志 v7.5

> 更新: 2026-07-29 | 当前状态: [PROJECT_STATUS.md](PROJECT_STATUS.md) | 算法改进: [SCORING_ALGORITHM_IMPROVEMENT_PLAN.md](../2-technical/SCORING_ALGORITHM_IMPROVEMENT_PLAN.md)

---

## v7.5 — P1-2b 音色八维 + P0 评分异常修复 (2026-07-29)

### 概述

完成 P1-2b 音色八维剖面增强，并对真实音频评分中发现的 4 个 P0 级异常进行根因分析和修复。通过 12 篇学术文献交叉验证，确保修复方案有文献依据。

### P1-2b: 音色八维剖面增强 (timbre_adjuster.py)

- 🆕 `_calc_hardness()`: spectral_crest 甜点曲线 (最佳 7-11), 2-5kHz 能量集中度
- 🆕 `_calc_depth()`: hammarberg_index (70%) + spectral_slope (30%), 30-200Hz 低频突出度
- 🆕 `_calc_sharpness()`: centroid 甜点曲线 (最佳 1200-2800Hz), 高频能量集中度
- 🆕 `_calc_booming()`: hammarberg×0.6 + harmonic_richness×0.4, 低频共鸣+歌手共振峰
- 🔧 `_calculate_enhanced()`: 四维→八维等权 12.5% 融合
- 📄 文献: timbral_models 八维音色描述框架
- ℹ️ 仅在 enable_audiofeat=True 时激活, 无 audiofeat 保持三维护发式路径

### P0 评分异常修复 (4)

**P0-1: Artistry pitch_cv Bug — 15% 权重完全失效 (ddd_feature_orchestrator.py + artistry_extractor.py)**

- ❌ 旧: `pitch_cv = max(0.01, vibrato_rate_avg)` — 传入颤音频率 Hz (4.5-8.0), `_calc_pitch_variation()` 对所有歌手返回固定 30.0
- ✅ 新: `_compute_pitch_cv(f0)` — 从真实 F0 数组计算 CV (std/mean), 范围 0.01-0.20
- ✅ adapter 路径: onset_density 代理映射 (onset×0.03 → CV 范围)
- ✅ 守卫: pitch_cv > 1.0 拒绝旧 Hz 值, 自动回退
- 📈 效果: Artistry 区分度从 1.8 pts → 26.4 pts (+1367%)
- 📄 文献: Kondo et al. 2025 — vibrato extent 是唯一显著预测表演评分的感知特征

**P0-2: Technique HNR>22 惩罚移除 (technique_scorer.py)**

- ❌ 旧: HNR 22-30 线性降至 60%, >30 固定 60% — 语音病理阈值, 歌声 HNR 典型 49-51dB
- ✅ 新: HNR ≥ 12 → 一律满分 (25/45 weight), 单调递增
- 📈 效果: 消除干净歌手系统性倒扣
- 📄 文献: Buckley et al. 2023 — 歌声 HNR 远高于语音病理阈值

**P0-3: CPPS-HF 非单调解耦 (technique_extractor.py)**

- ❌ 旧: `hf_energy_ratio = cpp / 5.0` — CPPS=3.5 得分高于 CPPS=5.0 (HF penalty 比 CPPS gain 大)
- ✅ 新: 从真实频谱计算 >5kHz 能量占比, 与 CPPS 完全解耦
- 📈 效果: CPPS 评分恢复单调性
- 📄 文献: Titze et al. 2024 — F0 对 CPPS 有巨大非线性影响, 不应间接耦合

**P0-4: Muscle formant/overtone 校准 (muscle_scorer.py)**

- ❌ 旧: formant_score 永远 100 (阈值 0.15, adapter 产生 hnr/60∈[0,0.30]), overtone_score 永远 100 (阈值 8, adapter 传入 0-100 评分)
- ✅ 新: formant 阈值 0.15→0.22, overtone 阈值 8→80 (计数刻度→评分刻度)
- 📈 效果: Muscle 区分度从 19 pts → 34.8 pts (+83%)
- 📄 文献: Liu et al. 2025 — spectral tilt (MFCC1) 是 strain 最佳单特征判别器 (86.1%)

### 审计发现与修复

- 🔧 `artistry_scorer.py:100`: `max(30.0,...)` → `min(60.0,...)` (P0-3 规格一致)
- 🔧 `technique_scorer.py:240`: `cpp_mean` 默认值 `0.0` → `1.0`
- 🔧 `muscle_scorer.py`: Alpha Ratio 从 body_proxies → facial_proxies (文献分类)
- 🔧 `value_objects.py`: 两处权重注释过时修复 (Pitch 10%→13%, Muscle 25%→15%)
- 🔧 `timbre_adjuster.py`: sharpness 峰值公式修正 (2300→2000Hz)
- 🔧 `timbre_adjuster.py`: spectral_slope=0.0 哨兵守卫 (默认值不膨胀)
- 🧪 新增 ~28 tests: timbre 八维 22 + muscle SPR/Alpha 4 + artistry 2

---

## v7.4 — 评分算法 P0/P1 修复 (2026-07-28)

### 概述

基于文献验证的 6 项评分算法改进，覆盖 4 个 CRITICAL + 2 个 HIGH 问题。CPPS 替代 HNR 成为气声比主特征，ZCR + Spectral Centroid 增强咬字清晰度，无颤音歌手获得 fallback 评分，权重新分配，音色门控修复，肌肉五维代理重构。

### P0 CRITICAL 修复 (4)

**P0-1: 气声比 CPPS 替代 HNR 主特征 (technique_scorer.py)**
- 🔧 `_calc_breath_voice_ratio()`: CPPS 40% 主特征 + HNR 25% 辅助 (原 HNR 70%)
- 🔧 CPPS 不可用时 HNR 回退至 45% (向后兼容)
- 📄 文献: Samlan & Story 2013 (CPPS 解释 86.7% 感知气息方差), Barsties 2023 (HNR r=-0.56 不显著)
- ✅ Technique 维度平均提升 +24.6 分 (16-30 → 44-49)

**P0-2: 咬字 ZCR + Spectral Centroid + C-V 能量比 (technique_scorer.py + technique_extractor.py)**
- 🆕 `TechniqueFeatures` 新增 3 字段: zcr_mean, spectral_centroid, cv_energy_ratio
- 🔧 `_calc_articulation()`: Spectral Centroid(30%) + Flux(25%) + ZCR(25%) + C-V(10%) + Onset(10%)
- 🔧 `LibrosaTechniqueExtractor`: ZCR/Centroid/C-V 提取 (librosa, O(n), 零额外依赖)
- 🔧 `FeatureAdapterRegistry.to_technique()`: 适配器默认值 0 (回退兼容)
- 📄 文献: Rathi & Hsu 2021 (ZCR+Flux+Centroid), Hecker 1974 (C-V 能量比)

**P0-3: 无颤音 Fallback (artistry_scorer.py)**
- 🔧 `_calc_vibrato()`: count==0 时使用 pitch_cv + dynamic_range 评分 (上限 80)
- ✅ 流行/R&B/说唱等不常用颤音的唱法不再受到系统性歧视
- 📄 文献: TECH_RESEARCH §2.6

**P0-4: 六维权重新分配 (value_objects.py)**
- 🔧 Pitch: 10%→13%, Rhythm: 10%→12%, Breath: 20%→22%, Muscle: 25%→15%, Artistry: 10%→13%
- 🔧 Technique 保持 25% (不变)
- 📄 文献: TECH_RESEARCH §3.4, §3.5 (双独立维度建议降至 15%)

### P1 增强 (2)

**P1-1: 肌肉五维代理重构 (muscle_scorer.py + muscle_extractor.py)**
- 🆕 `MuscleFeatures` 新增 5 字段: mpt_seconds, crest_factor, spr_ratio, f1f2_area, alpha_ratio
- 🆕 `_extract_mpt()`: 最长发声时间 (呼吸肌耐力)
- 🆕 `_extract_crest_factor()`: 峰值/RMS 比 (声音投射力)
- 🆕 `_extract_spr()`: 2-4kHz/0-2kHz (歌手共振峰)
- 🆕 `_extract_f1f2_area_approx()`: F1-F2 元音空间面积 (MRI R²=0.96)
- 🆕 `_extract_alpha_ratio()`: 0-1kHz/1-5kHz (发声努力程度)
- 🔧 `MuscleStrengthScorer._apply_body_proxies()` + `_apply_facial_proxies()`: 修正器模式

**P1-2a: 音色门控修复 (timbre_extractor.py + timbre_adjuster.py)**
- 🔧 `LibrosaTimbreExtractor`: 旧 CPP [0.01, 0.05] 无区分度 → harmonic_stability 替代门控
- 🔧 `TimbreAdjuster`: effective_confidence = max(mfcc_cluster_purity, harmonic_stability/100)
- 🆕 `TimbreFeatures`: 新增 harmonic_stability 字段
- ✅ 修复 C2: 音色维度在生产环境始终为零的问题

### 测试增强

- 🆕 +12 technique scorer tests (7 CPPS + 5 articulation)
- 🆕 +4 artistry scorer tests (颤音 fallback)
- 🆕 +3 timbre adjuster tests (双源置信度)
- 🆕 +6 muscle scorer tests (五维代理)
- 📊 测试总数: 375 → **400** (100% GREEN)
- 📊 真实音频基线: BASELINE_V7_3 → **BASELINE_V7_4**

### 真实音频评分变化

| 音频 | Tech v7.3 | Tech v7.4 | Δ |
|------|:--------:|:--------:|:--:|
| 恋人（高分） | 25 | **47** | +22 |
| 手写的从前（高分） | 19 | **45** | +26 |
| 1（高分） | 20 | **45** | +25 |
| 音频-3分26秒(高分) | 30 | **48** | +18 |
| 陈奕迅难听之声（低分） | 16 | **49** | +33 |

### 修改文件 (14)

| 层 | 文件 |
|----|------|
| Domain | `technique_scorer.py`, `artistry_scorer.py`, `value_objects.py`, `muscle_scorer.py`, `timbre_adjuster.py` |
| Audio | `technique_extractor.py`, `muscle_extractor.py`, `timbre_extractor.py` |
| Application | `feature_adapters.py`, `ddd_feature_orchestrator.py` |
| Tests | `test_technique_scorer.py`, `test_artistry_scorer.py`, `test_muscle_scorer.py`, `test_timbre_adjuster.py` |

### 文档更新

- 📝 `PROJECT_STATUS.md`: v7.3.1 → v7.4, 权重新表, 测试 375→400
- 📝 `CHANGELOG.md`: 新增 v7.4 条目
- 📝 `TEST_RESULTS.md`: 测试数更新, 基线 V7_4
- 📝 `SCORING.md`: 权重新分配 + 算法变更
- 📝 `SCORING_ALGORITHM_IMPROVEMENT_PLAN.md`: 标记已完成项
- 📝 `PRD.md`, `GOALS.md`, `README.md`: 同步更新

---


### 概述

基于安全审查发现的 11 项问题，完成 9 处信息泄露修复、Flask 14 routes 速率限制、FastAPI 50MB 上传限制。同时推进架构演进：旧服务废弃标记、BDD 29 scenarios 步骤定义、pytest 配置清理。

### 安全修复 (CRITICAL 3 + HIGH 5)

**信息泄露 (9处):**
- 🔧 **C-1**: `api/business/audio_analysis.py` — `analyze_and_score` 返回 `str(e)` → 通用错误消息
- 🔧 **C-2**: `services/audio_service.py` — `AudioAnalysisResult` 移除 `traceback` 字段
- 🔧 **C-3**: `api/routes/upload.py` — `/extract-pitch` 路由 `str(e)` → 通用消息
- 🔧 **H-1**: `backend/interfaces/ws/score_handler.py` — WebSocket `str(e)` → 通用消息 (2处)
- 🔧 **H-2**: `api/response_builder.py` — `build_error_response()` 移除 `traceback` 参数

**其他安全加固:**
- 🔧 **H-3**: `backend/main.py` — 新增 `MaxBodySizeMiddleware` (50MB, 对齐 Flask)
- 🔧 **M-1**: `mode` 参数验证 — Flask upload + FastAPI upload + `AnalyzeRequest` Literal 类型
- 🔧 **M-2**: `config/default.py` — `ALLOWED_EXTENSIONS` 添加 `.aac` (对齐 FastAPI)

### Flask 速率限制 (M-3)

- 🆕 `api/routes/rate_limit.py` — token bucket 限速器
  - `@rate_limit(20, 60)`: `/upload`, `/analyze`, `/compare`
  - `@rate_limit(120, 60)`: 其余 11 routes (extract-pitch, separate, history, audio 等)
  - `VAS_DISABLE_RATE_LIMIT=1` 跳过 (测试兼容, conftest 已设置)
  - 线程安全 + 过期桶自动清理

### 架构演进 (P2)

- ⚠ `services/features/acoustic.py` — 添加 `DeprecationWarning` (模块级 + `__init__`)
- ⚠ `services/features/types.py` — 添加 `DeprecationWarning` (模块级)
- ✅ 无行为变更，仅标记为废弃

### BDD 测试增强 (P2)

- 🆕 `tests/bdd/steps/test_animations_steps.py` — 16 GSAP animation scenarios (67 step defs)
- 🆕 `tests/bdd/steps/test_offline_steps.py` — 5 offline/library scenarios (19 step defs)
- 🆕 `tests/bdd/steps/test_responsive_steps.py` — 8 responsive layout scenarios (33 step defs)
- 🆕 119 step definitions total, 29 scenarios, `@pytest.mark.browser` 标记
- 🔧 `tests/pytest.ini` — 新增 `browser` marker

### 代码质量

- 🔧 `tests/pytest.ini` — filterwarnings (外部库噪音) + 移除无效 `asyncio_mode`
- 🔧 `tests/integration/test_real_audio_regression.py` — `BASELINE_v5_19` → `BASELINE` 别名清理
- 🔧 `backend/interfaces/api/routes/assessment.py` — 移除重复 `import uuid` + 未使用变量
- 🔧 全部 375 测试 GREEN (无回归)

### 修改文件 (17)

| 层 | 文件 |
|----|------|
| Backend | `main.py`, `assessment.py`, `assessment.py` (schemas), `score_handler.py` |
| Services | `audio_service.py`, `acoustic.py` (features), `types.py` (features) |
| Flask API | `upload.py`, `history.py`, `audio.py`, `rate_limit.py` (new), `audio_analysis.py`, `response_builder.py` |
| Config | `default.py` |
| Tests | `pytest.ini`, `test_real_audio_regression.py`, `test_animations_steps.py` (new), `test_offline_steps.py` (new), `test_responsive_steps.py` (new), `test_spa_steps.py` |

---

## v7.3.0 — audiofeat 评分接入 + Comparison DDD + 严格测试审计 (2026-07-27)

### 概述

P1 audiofeat 特征接入 4 个 scorer 完成评分增强闭环。实现完整 DDD comparison 领域（结束 Phase 2 桩代码状态）。全面代码审计修复 12 项（5 CRITICAL + 7 HIGH）。测试从 226 增长到 375（100% GREEN）。

### audiofeat 评分接入 (P1)

- 🆕 **BreathScorer**: CPPS/GNE/HNR_praat 增强气息评分（±8 分微调），区分可控气声 vs 不可控漏气
- 🆕 **TechniqueScorer**: Jitter/Shimmer/Closed Quotient 增强发声技术评分（±10 分微调）
- 🆕 **TimbreAdjuster**: 增强路径替代启发式 — centroid/roughness/nasality/inharmonicity 直接测量
- 🆕 **MuscleStrengthScorer**: Soft Phonation/Vocal Fry 补充身体力量代理（20% 权重混合）
- 🆕 `ScoringOrchestrator.calculate_ddd()` 接收 `audiofeat` 参数
- 🆕 `api/business/audio_analysis.py` 传递 `audiofeat=ddd_features.audiofeat`
- 🧪 32 新增 audiofeat 增强测试（8 breath + 9 technique + 9 timbre + 6 muscle）

### Comparison DDD 实现

- 🆕 `backend/domain/comparison/` 完整 DDD 三层：
  - `entities.py`: `ComparisonResult`, `AlignmentData`, `DeviationData` (frozen)
  - `value_objects.py`: `ComparisonScores`, `DimensionComparisonScore` (frozen, 4 风格权重)
  - `services.py`: `ComparisonScoringService` (移植 scoring_engine.py 算法)
- 🆕 `CompareAudioUseCase` 应用层对比用例（绞杀者: 复用旧 DTW + 新 DDD 评分）
- 🆕 `/compare` 路由 DDD 优先路径 + 旧路径异常 fallback
- 🧪 24 新增 comparison 测试（10 value objects + 14 scoring）

### 严格测试审计 (12 修复)

**CRITICAL (5):**
- 🔧 `assessment.py:275`: `str(e)` NameError → `except Exception as e`
- 🔧 `main.py`: 全局异常处理器（防止原始 traceback 泄露）
- 🔧 `score_handler.py:92`: `except: pass` → `logger.exception(...)`
- 🔧 `SingView.vue`: `startSinging()` try/catch + 状态复位
- 🔧 `SingView.vue`: `initConnection()` `.catch()` 消除浮空 Promise

**HIGH (7):**
- 🔧 `assessment.py:216`: `/analyze` 裸 `mode` → `body.mode`
- 🔧 `assessment.py:223`: `_save_history` 缺 `analysis_id` 参数
- 🔧 `assessment.py:439`: `/compare` 信息泄露 `str(e)` → 通用消息
- 🔧 `assessment.py`: `/separate` + `/report` try/catch 缺失
- 🔧 `assessment.py`: `/analyze` + `/compare` 缺失 `response_model`
- 🔧 `TopNav.vue` + `BottomNav.vue`: 图标组件未导入（Headset, HomeFilled 等）
- 🔧 `HistoryRecordOut`: 缺失 `duration` 字段

### 测试基础设施

- 🔧 Rate-limit 测试修复: monkeypatch `VAS_DISABLE_RATE_LIMIT`（23/23, 从 21/23）
- 🔧 集成测试进程隔离: Flask vs FastAPI 测试独立进程（C 扩展冲突）
- 🆕 `tests/extended/`: 需完整音频栈的测试独立目录
- 🆕 `tests/conftest.py`: `VAS_SKIP_GPU=1` + `VAS_DISABLE_RATE_LIMIT=1` + Playwright lazy import
- 🆕 `backend/main.py`: `VAS_SKIP_GPU` env var 跳过 GPU 检测

### 真实音频基线

- 📊 v7.3 Quick 模式评分 (DDD 唯一路径): 5 文件六维实测 + 基线更新
- 📊 technique 重构偏移 ~-30 分, 高低分差 12.9（v5.19: 20）
- 📊 `BASELINE_V7_3` 替代 `BASELINE_v5_19`

---

## v7.2.1 — 代码审查修复 (2026-07-27)

### 概述

全面代码审查后修复 23 项问题 (5 CRITICAL + 9 HIGH + 7 MEDIUM + 2 LOW)，覆盖前后端对齐、静默崩溃、安全、代码质量和冗余。

### CRITICAL 修复 (5)

- 🔧 **前后端对齐**: analysis_id UUID 存入 history，`get_by_id()` 支持 UUID 字符串查找 → 页面刷新后可正确加载报告
- 🔧 **字段名统一**: history 存储 `created_at` (timestamp 向后兼容)，前端 HistoryView 日期列正常显示
- 🔧 **响应补全**: FastAPI `UploadResponse` 包含 `timbre_adjustment` + `normalization` (之前始终为 0)
- 🔧 **history 完整性**: `_save_history()` 存储 grade/duration/timbre_adjustment/heuristic_dimensions/analysis_id
- 🔧 **PEP 8**: dl_services 中 2 个裸 `except:` → `except Exception:`

### HIGH 修复 (9)

- 🔧 静默异常增加日志: `breath_extractor` (人声段过滤/HPSS), `technique_extractor` (颤音检测)
- 🔧 `acoustic_feature_extractor`: HPSS 失败日志 debug→warning
- 🔧 `audio_service`: 混合音频检测失败增加 warning
- 🔧 错误信息泄露: `assessment.py`/`upload.py`/`score_handler.py` 中 `str(e)` → 通用消息
- 🆕 `backend/shared/math_utils.py`: 提取 `safe_float` + `safe_clamp` (消除 4 处重复定义)
- 🔧 删除 `_calc_rhythm_from_pitch` 死代码 (53 行，零调用)

### MEDIUM 修复 (7)

- 🔧 `DddFeatureSet` 设为 `frozen=True`
- 🔧 前端 API client: `AbortController` 超时 (120s upload / 30s normal)
- 🔧 前端 WebSocket 重连错误日志、AudioPlayer 播放失败日志、AudioContext 关闭失败日志
- 🔧 `upload-test.html`: `innerHTML` XSS → `textContent`
- 🔧 `history.store.ts`: `toggleSelect` 不可变更新 (push/splice → spread/filter)
- 🔧 `normalize_loudness`: 静音输入增加 warning
- 🔧 `HistoryListResponse.records` → `history` (匹配后端响应)

### 测试

- 226/226 DDD GREEN (无回归)

---

## v7.2.0 — audiofeat 增强特征提取 (2026-07-26)

### 概述

集成 audiofeat 1.1.1，新增 22 个声学特征提取。TDD 驱动，19 tests GREEN。

### 新增

- 🆕 **`AudiofeatExtractor`** (`backend/domain/audio/audiofeat_extractor.py`, 256 行) — 封装 audiofeat API
- 🆕 **`AudiofeatFeatures`** — frozen dataclass，22 字段，自动 NaN/Inf/空输入安全回退
- 🆕 **`DddFeatureSet.audiofeat`** — 集成到编排器，`enable_audiofeat` flag 门控

### 提取特征

| 类别 | 特征 |
|------|------|
| Voice Quality | CPPS (mean+std), HNR_praat, GNE (mean+max) |
| Perturbation | Jitter (local+ppq5), Shimmer (dB) |
| Glottal Flow | Closed Quotient (基于 PYIN F0) |
| Phonation | Soft Phonation Index, Vocal Fry Ratio |
| Spectral | Centroid, Flatness, Crest, Entropy, Roughness, Harmonic Richness, Inharmonicity, Hammarberg Index, Slope |
| Other | Nasality, RMS Energy |

### 测试

- 19/19 GREEN (`test_audiofeat_extractor.py`): 初始化 + 22 特征 + 边缘情况 (静音/短音频/NaN) + flag

---

## v7.1.5 — 特征提取层绞杀者完成 (2026-07-26)

### 概述

移除 `AudioFeaturesService` 依赖，清理 `services/features/` 未使用分析器。特征提取层绞杀者模式完成。

### 内联

- 🔧 `audio_service.py`: 内联 `_extract_f0()` + `_extract_f0_crepe()` (从 AudioFeaturesService 移入，~80 行)
- 🔧 移除 `AudioFeaturesService` 导入和 `_features_service` 字段
- 🔧 移除 `extract_all_features()` 死代码调用 (两处，`_advanced_features` 已不再被消费)

### 删除

- ❌ `services/audio_features_service.py` (~500 行)
- ❌ `services/features/` 未使用分析器 10 文件 (~1,220 行):
  - breath.py, cpp.py, hnr.py, pitch.py, reverb.py, rhythm.py, technique.py, voicing.py, voice_quality_praat.py, \_\_init\_\_.py
- ✅ 保留: `acoustic.py` (AcousticAnalyzer.detect_mixed_audio) + `types.py` (AudioFeaturesResult 类型)

### 测试

- 更新 `test_ddd_alignment.py`/`test_pitch_extractor.py`/`test_rhythm_extractor.py` — 移除 legacy 对比类
- 214/214 GREEN

---

## v7.1.4 — 死代码清理 (2026-07-26)

### 概述

移除 V4 评分回退、旧 SPA 前端、遗留测试文件。简化 `analyze_and_score()` 为 DDD 唯一代码路径。

### 删除

- ❌ `services/scoring/` (8 files): PitchScorer, RhythmScorer, BreathScorer, TechniqueScorer, ArtistryScorer, CriticalRules, ScoreModifiers, Types
- ❌ `services/score_service.py` — ScoreServiceV4
- ❌ `services/scoring_config.py` — V4 阈值配置
- ❌ `web/static/js/` (38 files) + `css/` (10 files) + `app.js` + `router.js` — 旧 vanilla JS SPA
- ❌ 14 个 Category-1 遗留测试文件

### 重构

- 🔧 `api/business/audio_analysis.py`: 移除 V4 + adapter 回退，DDD 原生路径为唯一代码路径
- 🔧 `services/advice_service.py`: 移除 ScoreResult 导入，更新为 v7 六维建议模板
- 🔧 `services/__init__.py`: 移除 ScoreService/ScoreServiceV4 等 4 个导出

### 统计

- 净删除 ~22,800 行 (77 files)
- 测试: 231/232 GREEN (1 预存 rate-limit)

---

## v7.1.3 — DDD 绞杀者内移完成 (2026-07-26)

### 概述

v7.1.3 完成了 DDD 特征提取层对 `services/features/` 全部 12 个文件的算法内移。10/10 模块实现零外部依赖，`services/features/` 可安全删除。同时修复了评分对齐问题，新增 33 个 TDD 测试，并通过了严格的 5 文件真实人声音频验证。

### Phase 1: 评分对齐修复 + TDD 加固

- 🔧 **`FeatureAdapterRegistry.to_muscle()`**: `formant_clustering_quality` 增加 `pitch_stability_long=0` 时的 `long_note_support_score` fallback (muscle Δ 改善 58%)
- 🔧 **`BreathFeatures`**: 新增 `harmonic_stability` 字段
- 🔧 **`LibrosaBreathExtractor`** + **`LibrosaTimbreExtractor`**: 对齐 adapter 公式
- 🆕 +7 对齐回归测试 (`test_ddd_alignment.py`)

### Phase 2: 工具函数内移 (audio_utils.py)

- 🆕 **`backend/domain/audio/audio_utils.py`** — 3 个纯函数: `normalize_loudness`, `find_vocal_segments`, `filter_audio_to_vocal_segments`
- 移除 `DddFeatureExtractionOrchestrator` 和 `LibrosaBreathExtractor` 对 `services/features/acoustic.py` 的依赖
- 🆕 +18 音频工具测试 (含 legacy 一致性验证)

### Phase 3: HNR/CPP 算法内移 (acoustic_feature_extractor.py)

- 🔧 **`LibrosaAcousticExtractor`** — HNR/CPP 自包含实现, 移除 `AcousticAnalyzer` 依赖
- `_compute_hnr()` / `_compute_cpp()` 与 legacy 逐位一致
- 🆕 +4 HNR/CPP 一致性测试

### Phase 4: Vibrato 信息流重构

- 🔧 **`TechniqueFeatures`** 新增 `vibrato_quality`, `vibrato_rate_avg` 字段
- 🔧 **`DddFeatureExtractionOrchestrator`** — 从 technique features 读取 vibrato, 移除冗余 `TechniqueAnalyzer` 调用

### Phase 5: PitchAnalyzer 算法内移 (pitch_extractor.py)

- 🔧 **`LibrosaPitchExtractor`** — 210 行 MAE/RPA/RCA/gross/octave/smoothness/breaks 算法自包含
- 移除 `services/features/pitch.py` 依赖
- 🆕 +2 pitch 一致性测试

### Phase 6: RhythmAnalyzer 算法内移 (rhythm_extractor.py)

- 🔧 **`LibrosaRhythmExtractor`** — 180 行 onset CV/irregularity/off-beat 算法自包含
- 🔧 统一使用归一化音频 (与 `AudioFeaturesService` 一致)
- 移除 `services/features/rhythm.py` 依赖
- 🆕 +2 rhythm 一致性测试

### Phase 7: TechniqueAnalyzer + BreathAnalyzer 内移 (technique_extractor.py + breath_extractor.py)

- 🔧 **`LibrosaTechniqueExtractor`** — 280 行 vibrato/slides/falsetto/staccato/legato 6 子检测器自包含
- 🔧 **`LibrosaBreathExtractor`** — 430 行 long_note/dynamic/design/technique/decay 8 子评估器自包含
- 移除 `services/features/technique.py` + `services/features/breath.py` 依赖

### 绞杀者完成状态

| 指标 | 结果 |
|------|:---:|
| DDD 模块自包含率 | **10/10 (100%)** |
| `services/features/` 依赖 | **0 个 import** |
| 可安全删除的遗留代码 | ~4,000 行 (12 files) |

### 真实音频对齐 (严格测试)

| 指标 | melody.wav | 5 文件平均 |
|------|:---:|:---:|
| pitch Δ | +0.30 | ~+2.3 |
| rhythm Δ | 0.00 | 差异来自 legacy 采样率 bug |
| breath Δ | -1.30 | ~-4.0 |
| technique Δ | +3.40 | DDD 正确 (实际 SR) |
| muscle Δ | -1.70 | ~-4.5 |
| artistry Δ | -1.80 | ~-3.5 |
| **total Δ** | **+2.00** | **-7.20** |

### 评分公式说明 (v6 → v7 权重变更)

v7.1.3 总分比 v6.x 低 5-15 分 — 原因是 v7.0 的六维权重重构 (pitch 28%→10%, rhythm 20%→10%, 新增 muscle 25%)，非 bug。

### 测试新增

| 文件 | 测试数 | 覆盖 |
|------|:---:|------|
| `test_ddd_alignment.py` | 7 | DDD vs adapter E2E |
| `test_audio_utils.py` | 18 | 工具函数 + legacy 一致性 |
| `test_acoustic_extractor.py` (新增类) | 4 | HNR/CPP 内移一致性 |
| `test_pitch_extractor.py` (新增类) | 2 | pitch 内移一致性 |
| `test_rhythm_extractor.py` (新增类) | 2 | rhythm 内移一致性 |
| **合计** | **33** | |

### 文件统计

- 新增 3 文件 (audio_utils.py + test_audio_utils.py + test_ddd_alignment.py)
- 重写 7 extractors + 1 orchestrator + 1 adapter (全部自包含)
- 修改 7 文档文件
- **总改动**: ~3,500 行新增 + ~500 行修改

---

## v7.1.2 — DDD 算法对齐 + 绞杀者切换 + 归一化透明度 (2026-07-25)

### DDD 提取器算法对齐 (P0)

DDD extractors 在 v7.1.1 中是独立重写的算法，与 legacy `services/features/` 分析器产生不同的特征值（breath Δ=-50, artistry Δ=-40）。v7.1.2 改为**薄封装模式**：每个 extractor 委托对应的 legacy 分析器，确保同输入 → 同输出。

- 🔧 `LibrosaBreathExtractor` → 委托 `BreathAnalyzer.calculate_breath_stability()`
- 🔧 `LibrosaPitchExtractor` → 委托 `PitchAnalyzer.calculate_pitch_deviation_cents()`
- 🔧 `LibrosaRhythmExtractor` → 委托 `RhythmAnalyzer.calculate_rhythm_alignment()`
- 🔧 `LibrosaTechniqueExtractor` → 委托 `TechniqueAnalyzer.detect_vocal_techniques()` + adapter 公式
- 🔧 `LibrosaAcousticExtractor` → 委托 `AcousticAnalyzer` (HNR/CPP)
- 🔧 `LibrosaMuscleExtractor` / `LibrosaArtistryExtractor` / `LibrosaTimbreExtractor` → 使用 `FeatureAdapterRegistry` 相同公式
- 🔧 orchestrator 添加 `normalize_loudness()` + 人声段过滤 — 与 `AudioFeaturesService.extract_all_features()` 预处理一致

### 关键 Bug 修复

- 🐛 `breath_extractor`: `getattr(acoustic, 'hnr_mean')` → 字段不存在, HNR 恒为 0 — 修复为 `getattr(acoustic, 'hnr')`
- 🐛 `artistry_extractor`: `crescendo_quality` 用错字段 (`dynamic_control` 而非 `crescendo_quality`)
- 🐛 `muscle_extractor`: `rms_decay_rate` 硬编码 1.0 — 修复为从 `BreathStabilityResult.long_note_decay` 读取
- 🐛 orchestrator: `TechniqueAnalyzer.detect_vocal_techniques()` 未被调用, vibrato 信息缺失 → artistry 分差大
- 🐛 `BreathFeatures` 缺少子字段: `phrase_coherence`, `crescendo_quality`, `long_note_decay`, `pitch_stability_long`

### 绞杀者切换

- 🚀 `enable_ddd_feature_extraction` 默认值 `False` → `True` — DDD 原生路径成为生产默认
- 🚀 `analyze_and_score()` 接入 DDD 原生提取 + 评分分支
- 🆕 `FeatureFlags.enable_ddd_feature_extraction` + `DimensionFlags.enable_ddd_feature_extraction`
- 🔒 旧路径 `enable_ddd_feature_extraction=False` 仍可显式回退

### 对齐结果 (melody.wav)

| 维度 | 修复前 Δ | 修复后 Δ | 改善 |
|------|:---:|:---:|:---:|
| pitch | +3.3 | +0.3 | 91% |
| rhythm | -0.5 | 0.0 | 100% |
| breath | +34.3 | -1.3 | 97% |
| technique | +6.8 | +3.4 | 50% |
| muscle | -0.6 | +4.1 | — |
| artistry | -38.9 | 0.0 | 100% |
| **total** | +6.8 | +3.6 | 47% |

剩余 technique +3.4 / muscle +4.1 来自启发式维度的子字段映射差异，见 [PROJECT_STATUS.md](PROJECT_STATUS.md) 已知问题。

### 归一化透明度

- 🆕 API 响应新增 `normalization` 字段: `{ applied: true, note: "..." }`
- 🆕 前端 ReportView 显示归一化说明（与 heuristic 标记并列）
- 🆕 `ResponseV5Builder` + `AnalysisResult` + TypeScript `AssessmentResult` 类型更新

### 测试

- 🆕 +11 TDD 测试 (`test_ddd_extraction_flag.py`)
- ✅ 304/306 单元 GREEN + 63/63 DDD 基建 GREEN + 53/53 系统 GREEN
- ✅ 真实音频 5 文件批量验证通过

### 文件统计

- 修改 10 文件 (~350 行改动)
- 新增 1 测试文件 (11 tests)

---

## v7.1.1 — DDD 特征提取层 + 前后端对齐 (2026-07-24)

### DDD 特征提取层 (P0 绞杀者核心)

- 🆕 `backend/domain/audio/feature_types.py` — `AcousticFeatures` 冻结数据类 (8 字段)
- 🆕 `backend/domain/audio/feature_protocols.py` — 3 个提取器 Protocol 接口
- 🆕 `backend/domain/audio/acoustic_feature_extractor.py` — Level 0: HNR/CPP/SpectralTilt/Voicing/MixedAudio
- 🆕 `backend/domain/audio/pitch_extractor.py` — Level 1: MAE/RPA/RCA/GrossError/Octave/Smoothness/Breaks 多指标体系
- 🆕 `backend/domain/audio/rhythm_extractor.py` — Level 1: onset-CV + irregularity + off-beat segments
- 🆕 `backend/domain/audio/breath_extractor.py` — Level 2: RMS fluctuation + long-note + breath-break + 气声控制
- 🆕 `backend/domain/audio/technique_extractor.py` — Level 2: onset_density × consonant_clarity + breath-voice ratio
- 🆕 `backend/domain/audio/muscle_extractor.py` — Level 3 ⚠️ HEURISTIC: body + facial proxy metrics
- 🆕 `backend/domain/audio/timbre_extractor.py` — Level 2 ⚠️ HEURISTIC: spectral centroid + MFCC cluster + nasality
- 🆕 `backend/domain/audio/artistry_extractor.py` — Level 3: vibrato + dynamic + phrase from technique + breath
- 🆕 `backend/application/assessment/ddd_feature_orchestrator.py` — 按拓扑排序编排 7 个提取器
- 🆕 `ScoringOrchestrator.calculate_ddd()` — 直接消费 DDD Features, 绕过 FeatureAdapterRegistry

### 架构巩固

- 🔒 7 个 Features 数据类改为 `@dataclass(frozen=True)` (不可变)
- 🔧 `ResponseV5Builder` 补齐 `muscle_strength` + `timbre_adjustment` + `heuristic_dimensions`
- 🔧 前后端 TypeScript ↔ Python 类型完全对齐 (6 维度 + 音色 + 启发式标记)

### 测试

- ✅ +65 TDD 测试 (全部 GREEN)
- ✅ 测试覆盖: 16 acoustic + 22 pitch/rhythm + 14 breath/technique + 9 batch4 + 4 orchestrator
- ✅ 295/295 单元 GREEN + 50/50 系统 GREEN
- ✅ 零回归 (280 existing tests unchanged)

### 文件统计

- +11 新建文件 (~2,100 行代码 + ~900 行测试)
- 8 个修改文件 (frozen dataclass + ResponseV5Builder + __init__.py 导出)

---

## v7.1.0 — DDD 评分接入生产 + 死代码清理 + FCPE 集成 + 严格测试 (2026-07-23)

### 严格测试验证 (新增)

- 🆕 `tests/tools/test_comprehensive_e2e.py` — 50 项后端全流程检查
- 🆕 `tests/tools/test_frontend_e2e.py` — 21 项前端 UI + 控制台检查
- 🔧 `analysis_id` 始终生成 (业务层 UUID, 不再仅依赖路由层)
- 🔧 `backend/main.py` 开发模式默认端口 8000 (与 Vite proxy 对齐)
- 🔧 OMP 冲突通过 `KMP_DUPLICATE_LIB_OK=TRUE` 缓解
- ✅ 5 页面全部加载 | 0 控制台错误 | 上传 API HTTP 200 | 移动端响应式正常

---

## v7.1.0 — DDD 评分接入生产 + 死代码清理 + FCPE 集成 (2026-07-23)

### Phase A: 死代码清理 + 测试修复

- 🗑️ 删除 4 个死代码文件 (~1,200 行): dl_quality_assessor, emotion_manager, professional_feedback, audio_comparison
- 🗑️ 移除 ScoreServiceV4._apply_dl_fusion() + ScoreResultV4/AnalysisResult 中 DL 字段
- 🔧 Quick/Pro 模式使用正确的 FeatureFlags 工厂方法 (`for_quick()`/`for_professional()`)
- 🔧 修复 3 个已有 FeatureFlags 测试失败 (v5.18→v6.2 默认值变更)
- 🔧 Rate-limit 中间件测试环境禁用 (`VAS_DISABLE_RATE_LIMIT`)
- ✅ 新增 13 个 Phase A TDD 测试

### Phase B: DDD Domain 层接入生产

- 🆕 `backend/application/assessment/feature_adapters.py` — 7 维度特征适配器
- 🆕 `backend/application/assessment/scoring_orchestrator.py` — 统一评分编排器
- 🆕 `backend/application/assessment/history_subscriber.py` — EventBus 自动保存历史
- 🚀 DDD ScoringDomainService 成为默认生产评分路径 (`enable_ddd_scoring=True`)
- 🚀 绞杀者: 旧 ScoreServiceV4 可通过 flag 回退
- 🚀 API 响应新增 `muscle_strength` + `timbre_adjustment` + `heuristic_dimensions` 字段
- 🔧 dict/dataclass 双格式兼容 (_build_success_result, advice_service, 诊断函数)

### Phase C: Infrastructure 音频层

- 🆕 `librosa_loader.py`, `pyin_extractor.py`, `demucs_separator.py` — 从 2 行桩实现为完整功能模块
- 🆕 `protocols.py` — AudioLoader/PitchExtractor/VoiceSeparator Protocol 接口
- ⚠️ 生产特征提取仍使用 `services/features/` (infrastructure 层尚未接入生产)

### Phase D: FCPE 基频检测集成

- 🆕 `fcpe_extractor.py` — torchfcpe FCPE (96.79% RPA, GPU 加速)
- ✅ 验证: 440Hz sine → 439.6Hz (偏差 < 1Hz), detection_rate=1.0
- 🔧 `FeatureFlags.enable_fcpe/enable_audiofeat/enable_timbral_models` 预留

### 其他改进

- 🚀 FastAPI 服务 Vue 3 SPA (`frontend/dist/` + history mode fallback)
- 🗑️ 移除 diagnostic.py 中 s3prl/wvmos/speechbrain 引用
- 🗑️ 移除 emotion_manager DL import (使用启发式方法)

### 测试

```
280 passed, 0 failed — 单元 + TDD + 中间件
347 passed, 20 failed — 全量套件 (20 失败为已有遗留)
```

---

## v7.1-alpha — 五维度文献研究 (2026-07-23)

### 研究范围

对气声比、音色、咬字清晰度、面部肌肉力量、身体肌肉力量五个维度进行深度文献研究。

- 源码框架深度分析: 完整评分管道数据流、7维度特征-评分链路、扩展点
- 文献验证: 各维度效应量(r值/AUC)、样本量、跨研究一致性、验证质量评级
- GitHub项目可运行性: 24个开源项目评级 (A:可直接用 到 D:不可用)

### 研究发现

- 气声比: CPPS/GNE/ABI 在病理语音上充分验证 (1,756样本)，歌声验证仅n=2 — **可接入，需校准**
- 音色: MFCC分类成熟，但"好音色"专家一致率仅37.5% — **分类可用，质量评分主观**
- 咬字清晰度: 仅1人试点研究 — **最大空白，标注为 Experimental**
- 面部/身体肌肉: 零纯音频验证 — **必须保持 HEURISTIC 标注**
- 8个A级开源工具可直接 pip install 接入

### 产出

- `参考论文/` 6篇研究总结 + 综合评估报告
- [TECH_RESEARCH.md](../2-technical/TECH_RESEARCH.md) 技术研究文档

---

## v7.0.1 — 代码审查修复 (2026-07-22)

### 全面代码审查 (52 findings → 11 remaining)

四代理并行审查（Python backend + Vue frontend + Security + Electron），发现 52 个问题，已修复 41 个。

#### CRITICAL 修复 (6 项)

| # | 问题                                                          | 文件                                                                      | 修复                                                           |
| - | ------------------------------------------------------------- | ------------------------------------------------------------------------- | -------------------------------------------------------------- |
| 1 | `/separate` 端点缺少路径遍历防护                            | `api/routes/upload.py`, `backend/interfaces/api/routes/assessment.py` | 添加`validate_filepath()` 调用                               |
| 2 | Flask 绑定`0.0.0.0` 暴露于局域网                            | `web_app.py`                                                            | `host="127.0.0.1"`                                           |
| 3 | Nasality 公式 bug —`max(5.0, ...)` 对高鼻音指数无效        | `backend/domain/assessment/timbre_adjuster.py:117`                      | `max(0.0, ...)`                                              |
| 4 | CORS`allow_credentials=True` + `allow_origins=["*"]` 互斥 | `backend/main.py`                                                       | `allow_credentials=False`                                    |
| 5 | 评分等级阈值在 6+ 文件中重复实现                              | `services/`, `backend/`, `frontend/`                                | 统一委托到`ScoreLevel.from_score()`                          |
| 6 | WebSocket 实时评分 technique/muscle/artistry 硬编码为 50      | `backend/interfaces/ws/score_handler.py`                                | DSP 代理算法 (spectral flatness/RMS stability/pitch variation) |

#### HIGH 修复 (17 项)

| 类别           | 数量 | 关键修复                                                                                   |
| -------------- | ---- | ------------------------------------------------------------------------------------------ |
| 前端类型安全   | 4    | `any` 类型清除, `HistoryView` store 直接修改, `ScoreCard` 颜色重复                   |
| 错误处理       | 5    | 盲目`except: pass` 添加日志, `print()` 替换为 `logger`, `_save_history` try/except |
| 架构一致性     | 3    | 评分重复消除,`_detect_gpu()` 去重, `sys.path.insert` 文档化                            |
| API 协议       | 3    | DELETE body 恢复, 历史分页修复, 虚假进度条优化                                             |
| 事件系统       | 1    | EventBus 处理器错误隔离                                                                    |
| WebSocket 安全 | 1    | 每帧 1MB 上限 +`asyncio.to_thread()` 防事件循环阻塞                                      |

#### MEDIUM 修复 (14 项)

| 类别          | 关键修复                                                                        |
| ------------- | ------------------------------------------------------------------------------- |
| Pydantic 验证 | `two_stems` 添加 `Literal["vocals","drums","bass","other"]`                 |
| 输入安全      | `SeparateRequest` schema 约束, `_parse_frames` 帧大小限制                   |
| 评分算法      | artistry 公式参数调优,`valid`/`rms_energy` 变量初始化, `dir()` 反模式移除 |
| 前端一致性    | `SingView.getScoreColor` 与 `ScoreCard`/`ReportView` 对齐                 |
| 资源管理      | `progressTimer` clearInterval 移至 finally 块                                 |
| 数据流        | `fetchHistory` 响应格式对齐后端 `{ history, total }`                        |

#### 剩余未修复 (11 项 — 非阻塞)

- **HIGH (2)**: 速率限制缺失 (需引入新依赖), 安全响应头缺失
- **MEDIUM (4)**: Electron asar 路径假设, `useApi` 死代码, 导出报告按钮无 handler, `sandbox: false` 待验证
- **LOW (5)**: 分值颜色重复, Canvas 深度 watch, pitchHistory 裁剪间隙, Options API 不一致, v-for key

#### 构建验证

```
TypeScript vue-tsc:     ✅ Zero errors
Python py_compile:       ✅ 18/18 files
前后端 API 对齐:         ✅ 已对齐
事件循环阻塞:            ✅ asyncio.to_thread()
WS 帧大小限制:           ✅ 1MB 上限
```

#### 修改文件 (18 个)

| 层        | 文件                                                                                                                                                                                                                                                                                                                                                                                 |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Backend   | `backend/main.py`, `backend/shared/event_bus.py`, `backend/domain/assessment/services.py`, `backend/domain/assessment/timbre_adjuster.py`, `backend/interfaces/ws/score_handler.py`, `backend/interfaces/ws/streaming_session.py`, `backend/interfaces/api/routes/assessment.py`, `backend/interfaces/api/schemas/assessment.py`, `backend/interfaces/api/deps.py` |
| Services  | `services/score_service.py`, `services/dl_services/emotion_manager.py`, `services/separation_service.py`                                                                                                                                                                                                                                                                       |
| Flask API | `web_app.py`, `api/__init__.py`, `api/errors.py`, `api/routes/upload.py`                                                                                                                                                                                                                                                                                                     |
| Frontend  | `frontend/src/api/client.ts`, `frontend/src/stores/assessment.store.ts`, `frontend/src/stores/history.store.ts`, `frontend/src/views/HomeView.vue`, `frontend/src/views/SingView.vue`, `frontend/src/components/ScoreCard.vue`                                                                                                                                           |

---

## v7.0.1 — 运行时修复 (2026-07-22)

代码审查后启动应用发现前端无法正常工作，逐一排查修复。

### 前端上传功能修复 (4 项)

| # | 问题                           | 根因                                                                                  | 修复                                                                |
| - | ------------------------------ | ------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| 1 | **上传响应格式不匹配**   | 前端期望`{ success, data: {...} }`，后端返回扁平 `{ success, total_score, ... }`  | `assessment.store.ts` — 直接使用 `result` 替代 `result.data` |
| 2 | **开发模式跨域请求**     | `apiClient.getBaseUrl()` 返回绝对 URL `http://127.0.0.1:8000`，请求绕过 Vite 代理 | `api/client.ts` — 开发模式返回空字符串，使用相对路径走 Vite 代理 |
| 3 | **el-upload 不接收文件** | `before-upload` 返回 `false` 导致 el-upload 拒绝文件                              | `FileUploader.vue` — 重写为 `on-change` 事件 + `return true` |
| 4 | **首页图标缺失**         | `<Headset />` 使用但未 import                                                       | `HomeView.vue` — 添加 `Headset` 到 import                      |

### 代理与路由修复 (4 项)

| # | 问题                                 | 根因                                                                | 修复                                                              |
| - | ------------------------------------ | ------------------------------------------------------------------- | ----------------------------------------------------------------- |
| 5 | **健康检查显示"后端未启动"**   | `/health` 路径不在 Vite 代理中                                    | `vite.config.ts` — 添加 `/health` 代理                       |
| 6 | **后端无法直接启动**           | `backend/main.py` 缺少项目根目录的 `sys.path`                   | `backend/main.py` — 添加 `sys.path.insert(0, _project_root)` |
| 7 | **上传响应缺 `analysis_id`** | `UploadResponse.analysis_id` 为 null，前端导航到 `/report/null` | `assessment.py` — 生成 12 位 UUID 作为 `analysis_id`         |
| 8 | **上传响应缺 `grade`**       | 旧评分管线不填充 grade 字段                                         | `assessment.py` — 从 `ScoreLevel.from_score()` 派生 grade    |

### 历史页加载修复 (1 项)

| # | 问题                     | 根因                                               | 修复                                                                |
| - | ------------------------ | -------------------------------------------------- | ------------------------------------------------------------------- |
| 9 | **历史页点不进去** | `ReportView` 不使用路由参数 `:id` 加载历史数据 | `ReportView.vue` — 新增 `loadFromHistory(id)` + `useRoute()` |

### 其他修复 (3 项)

| #  | 问题                         | 根因                                         | 修复                                                                                  |
| -- | ---------------------------- | -------------------------------------------- | ------------------------------------------------------------------------------------- |
| 10 | `_get_level_info` 崩溃     | 删除`LEVELS` 后未更新 `_get_level_info`  | `score_service.py` — 委托到 `ScoreLevel.from_score()` + `_STAR_MAP`            |
| 11 | `progressTimer` 内存泄漏   | `clearInterval` 仅在成功路径，错误路径跳过 | `assessment.store.ts` — 移至 `finally` 块                                        |
| 12 | Electron CommonJS/ESM 不兼容 | `type: module` 下 Electron 无法加载 CJS    | `tsconfig.electron.json` — `module: "CommonJS"` + `electron-dist/package.json` |

### 构建验证

```
TypeScript vue-tsc:     ✅ Zero errors
Python py_compile:       ✅ 18/18 files
Vitest:                  33/33 passed
Python 集成测试:         8/8 passed (ScoreLevel, EventBus, TimbreAdjuster, etc.)
Vite 生产构建:           ✅ 10.14s (所有 chunk < 350KB gzip)
后端运行验证:            ✅ healthy + GPU CUDA + 全部 API 正常
前端运行验证:            ✅ 上传分析 + 历史加载 + 报告页 + 健康检查
```

### 新增/修改文件 (本批次)

| 文件                                            | 变更                                                               |
| ----------------------------------------------- | ------------------------------------------------------------------ |
| `frontend/vite.config.ts`                     | 添加`/health` 代理                                               |
| `frontend/src/api/client.ts`                  | 开发模式相对路径 (`import.meta.env.DEV`)                         |
| `frontend/src/stores/assessment.store.ts`     | 扁平响应格式 + progressTimer 移到 finally                          |
| `frontend/src/components/FileUploader.vue`    | 重写为`on-change` 事件模式                                       |
| `frontend/src/views/HomeView.vue`             | 添加`Headset` icon import                                        |
| `frontend/src/views/ReportView.vue`           | 新增`loadFromHistory()` + `useRoute()`                         |
| `frontend/src/views/SingView.vue`             | 颜色对齐 ScoreCard/ReportView                                      |
| `frontend/src/stores/history.store.ts`        | fetchHistory 响应格式对齐 +`Math.max(1,...)`                     |
| `frontend/src/main.ts`                        | 全局 JS/Promise 错误捕获                                           |
| `frontend/tsconfig.electron.json`             | `module: "CommonJS"`                                             |
| `frontend/electron-dist/package.json`         | `{"type": "commonjs"}` (覆盖父级 ESM)                            |
| `backend/main.py`                             | 项目根目录`sys.path.insert`                                      |
| `backend/interfaces/api/routes/assessment.py` | `analysis_id` UUID + `grade` 派生                              |
| `services/score_service.py`                   | `_get_level_info` → `ScoreLevel.from_score()` + `_STAR_MAP` |
| `frontend/public/test.html`                   | 诊断用 API 测试页                                                  |
| `frontend/public/upload-test.html`            | 诊断用上传测试页                                                   |

---

## v7.0 — Phase 5: Electron Desktop Packaging (2026-07-22)

### Electron Main Process

- ✅ `electron/main.ts`: spawn 嵌入式 Python + stdout `PORT=` 协议捕获动态端口 (ADR-1)
- ✅ 进程守护: 崩溃自动重启 max 3 次 (1.5s 间隔), 3 次后显示错误对话框 + 日志路径
- ✅ 单实例锁 (`app.requestSingleInstanceLock`) + 第二实例 focus
- ✅ 优雅关闭: SIGTERM → 5s → SIGKILL 级联
- ✅ Windows 菜单: 文件 (导出诊断包/退出) + 编辑 + 视图 + 帮助 (日志目录/关于)
- ✅ 开发模式: `VITE_DEV_SERVER_URL` 环境变量加载 Vite dev server

### Electron Preload

- ✅ `contextBridge.exposeInMainWorld`: `window.electronAPI`
- ✅ `onBackendUrl(callback)`: 监听后端动态端口变更 + 同步更新 `window.BACKEND_URL`
- ✅ `onBackendStatus(callback)`: 监听后端状态 (starting/restarting/stopped)
- ✅ `getBackendUrl()`: 异步获取当前后端 URL
- ✅ 安全隔离: `contextIsolation: true`, `nodeIntegration: false`

### Electron Builder Config

- ✅ `electron-builder.yml`: NSIS Windows 安装器 (perMachine: false, 可选择安装目录)
- ✅ extraResources: 嵌入式 Python + backend 应用 + shared/openapi.json
- ✅ 桌面快捷方式 + 开始菜单 + 卸载程序
- ✅ Generic publish provider (electron-updater)

### Frontend Electron Integration

- ✅ `App.vue`: 后端未就绪时显示加载遮罩 + 重连状态 overlay (Teleport to body)
- ✅ `api/client.ts`: `getBaseUrl()` 每次调用动态读取 `window.BACKEND_URL` (支持后端重启换端口)
- ✅ `api/client.ts`: 新增 `isElectron()` 检测函数 + `ApiError` 类导出
- ✅ `env.d.ts`: 完整 `ElectronAPI` + `Window.BACKEND_URL` 类型定义
- ✅ `vite.config.ts`: `base: './'` 支持 Electron `file://` 协议加载资源

### Build & Type System

- ✅ `tsconfig.electron.json`: Electron TypeScript 编译配置 (ES2020 + node resolution + DOM lib)
- ✅ `package.json`: `main: "electron-dist/main.js"` + 6 个 Electron 脚本
- ✅ 依赖: electron 28, electron-builder 24, electron-log 5, electron-updater 6
- ✅ 开发辅助: concurrently (Vite + Electron 并行), cross-env, wait-on

### 8 ADR — 全部落地

- ✅ ADR-1: 嵌入式 Python (`electron/main.ts` spawn + PORT= protocol)
- ✅ ADR-5: structlog + electron-log (前后端日志同目录, 按日切割)
- ✅ ADR-8: PyArmor 构建脚本 (`scripts/build-python-runtime.bat` + electron-builder extraResources)

### Build Verification

```
vue-tsc:                  ✅ Zero errors
electron tsc:              ✅ Zero errors
Vitest:                    33/33 passed
Vite build:                9.89s (all chunks < 350KB gzip)
electron-builder (dry):   npm run build:electron:dir
```

---

## v7.0-alpha — Phase 4: Vue 3 Frontend (2026-07-22)

### Architecture

- ✅ 3 Pinia stores: assessment (上传/分析/结果), history (分页/筛选/批量), preferences (主题/模式/持久化)
- ✅ 5 Composables: useApi, useGsap (gsap.context + reduced-motion), useMediaRecorder, useWebSocket, useAudioContext
- ✅ 3 Layout components: AppLayout (ElContainer), TopNav (ElMenu + Element Plus Icons), BottomNav (mobile)
- ✅ 6 Shared components: ScoreCard (评分卡片+启发式标签), ScoreRadar (Chart.js 六维雷达图), PitchCurveCanvas (对数频率刻度+播放游标), AudioPlayer (click-to-seek 修复 v6.3 P1 bug), ProgressOverlay, FileUploader
- ✅ 5 Page views: HomeView (上传+ElDrawer设置/曲库), ReportView (雷达图+启发式+建议), HistoryView (ElTable+UTF-8重写), CompareView (双ElUpload修复v6.3 P1 bug), SingView (Canvas+WS+6步清理法)

### Key Fixes (v6.3 Known Issues)

- ✅ HistoryView: UTF-8 重写, 修复 v6.3 GBK 乱码 (P1 #10)
- ✅ AudioPlayer: click-to-seek 实现, 修复 v6.3 播放器不能拖动进度 (P1 #3)
- ✅ CompareView: 双 ElUpload, 修复 v6.3 无法两侧上传文件 (P1 #8)
- ✅ HomeView: ElDrawer 合并设置+曲库, 修复 v6.3 独立页面过多的问题 (P1 #5)
- ✅ SingView: 6步清理法防内存泄露, 修复 v6.3 Canvas/WebSocket 泄露风险

### Design Decisions

- ✅ ADR-2: 启发式维度前端显示 "估算值" 标签 + 橙色边框 + 可点击展开说明
- ✅ ADR-3: 零硬编码 URL, `window.BACKEND_URL` + apiClient 动态后端地址
- ✅ ADR-7: WebSocket 4字节长度前缀协议前端实现 (useWebSocket sendPcm)
- ✅ Element Plus Icons 替代 v6.3 120+ Unicode emoji
- ✅ GSAP prefers-reduced-motion 检测, 尊重用户无障碍偏好
- ✅ Pinia 替代 AppContext DI + Store + AnimationController

### Test & Build

- ✅ 33 Vitest unit tests: 3 suites, 100% pass rate
- ✅ vue-tsc type check: Zero TypeScript errors
- ✅ Vite build: 9.55s, ReportView chunk 64KB gzip, main chunk 346KB gzip

---

## v7.0-alpha — Full-Stack Refactor Phase 0-3 (2026-07-21)

### Phase 0: Foundation

- ✅ `backend/`: DDD 四层架构 (domain/application/infrastructure/interfaces) 45+ 文件
- ✅ `backend/main.py`: FastAPI 入口 + lifespan + freeze_support + GPU 检测
- ✅ `backend/shared/`: EventBus (观察者) + Result[T,E] monad + ScoreLevel
- ✅ `backend/infrastructure/config.py`: Pydantic Settings (VAS_* env)
- ✅ `backend/legacy/`: Flask WSGI 包装 + history_v6 表隔离 (绞杀者)
- ✅ `backend/migrations/`: Alembic + SQLite 配置
- ✅ `frontend/`: Vue 3 + Vite + Element Plus 脚手架 (22 文件)
- ✅ `shared/openapi.json`: 前后端类型同步占位
- ✅ `scripts/build-python-runtime.bat`: 嵌入式 Python 构建
- ✅ `web_app.py`: 提取 get_wsgi_app() 工厂
- ✅ `start.bat`: 4 种启动模式 (FastAPI/Flask/V7-full/V6-legacy)

### Phase 1: Domain Model (六维评分 TDD)

- ✅ 7 个 frozen 值对象: PitchScore(10%), RhythmScore(10%), BreathScore(20%), TechniqueScore(25%), MuscleStrengthScore(25%), ArtistryScore(10%), TimbreAdjustment
- ✅ 7 个纯函数评分器 (零框架依赖):
  - PitchScorer: 移植 v6.2 六指标融合 (MAE指数衰减+RPA+RCA+Gross Error+Smoothness+Octave)
  - RhythmScorer: 移植 onset CV + 分级 irregularity 惩罚
  - BreathScorer: 移植 四子维度连续线性映射
  - **TechniqueScorer: 重构 — 咬字清晰度(50%) + 气声比(50%)** (替代旧 HNR/CPP)
  - **MuscleStrengthScorer: NEW 启发式 — 身体肌肉(50%) + 面部肌肉(50%)**
  - ArtistryScorer: 移植 v6.1 独立声学特征
  - **TimbreAdjuster: NEW 启发式 — 不对称 -5/+3 调整**
- ✅ ScoringDomainService: 六维加权总分 + EventBus ScoreCalculated 事件
- ✅ 88 TDD 单元测试全部 GREEN
- ✅ 所有新增维度 `is_heuristic=True` 标记 + 源码注释

### Phase 2: FastAPI 后端迁移

- ✅ Pydantic v2 schemas: assessment, history, common
- ✅ DI 容器 (deps.py): Settings/EventBus/ScoringService/HistoryRepo/SeparationService/ReportService
- ✅ 5 路由模块: health, assessment (12 端点), history (7 端点), audio, songs
- ✅ 绞杀者模式: 旧 Flask 挂载到 `/old/` (WSGIMiddleware)
- ✅ `shared/openapi.json` 导出 (16 paths + Pydantic schemas)
- ✅ 20 API 集成测试全部 GREEN (TestClient)

### Phase 3: WebSocket 实时评分

- ✅ ADR-7: 4 字节大端 uint32 长度前缀防粘包协议
- ✅ `ScoreWebSocketHandler`: ws.receive() text/bytes 分发 + 轻量 librosa 评分
- ✅ `StreamingSession`: 音频缓冲累积 + 增量评分调度 + 资源清理
- ✅ `AudioWorklet`: 48kHz→16kHz 降采样处理器
- ✅ 前端 composables: useWebSocket (连接+重连+二进制帧), useAudioContext (录音生命周期)
- ✅ 8 WebSocket 集成测试: 握手/断开/单帧/多帧粘包/长度前缀/start-stop/错误处理

### v7.0 测试总览

- **237 tests passed**: 121 (v6.3保留) + 88 (Phase 1) + 20 (Phase 2) + 8 (Phase 3)
- **0 failures**, **0 regressions** vs v6.3 基线

---

## v6.3 — 项目重构 + 评分体系设计 + 文档更新 (2026-07-20)

### 评分体系: 六维重构设计

- 音准 30%→**10%**、节奏 20%→**10%** 降权
- 发声技术 20%→**25%**，拆分为两子维度: 咬字清晰度(50%) + 气声比(50%)
- **新增**肌肉力量维度 25%: 身体肌肉力量(50%) + 面部肌肉力量(50%)
- 艺术表现保持 10%
- **新增**音色额外加减分: +3~-5, clamp [0,100]
- 新增「开发与测试原则」: 维度独立可测、低耦合、Feature Flag 粒度

### 项目结构清理

- 🗑️ 删除 PyQt5 旧桌面代码: `core/`, `widgets/`, `windows/`, `styles/`, `utils/`
- 🗑️ 删除根目录废文件: `prototype.html`, `desktop_app.py`, `main.py`, `vocal_assessment.spec`, `installer.iss`
- 🗑️ 删除旧静态 HTML: `web/static/analysis.html`, `compare.html`, `settings.html`
- 🗑️ 删除废弃 JS: `js/effects/` 目录 (4个stub), `js/services/sse.js`
- 📦 `model_manager.py` → `services/dl_services/emotion_manager.py` (修复路径和引用)

### v7.0 全栈架构规划 (设计阶段, 2026-07-21)

- **FastAPI** 替代 Flask: Pydantic v2 + APIRouter + `asyncio.to_thread()` + WebSocket
- **Vue 3** + **Element Plus** 替代 Vanilla JS: 组件库替代 162 内联样式 + 120+ emoji
- **Electron** 桌面打包: **嵌入式 Python 运行时** + electron-builder (替代 PyInstaller + Inno Setup)
- 绞杀者模式六阶段渐进迁移 (Phase 0-5), 26.5 天
- 8 项架构决策记录 (ADR): 嵌入式 Python / 启发式代理指标 / 文件驱动 openapi.json / Alembic legacy 表隔离 / structlog / EventBus / WebSocket 粘包协议 / PyArmor
- 详细计划: [V7_MIGRATION_PLAN.md](V7_MIGRATION_PLAN.md)

### 文档更新

- SCORING.md: 六维体系 + 独立测试原则 + 发声技术/肌肉力量/音色详细算法
- PRD.md: 评分权重 + 风格预设 + v7.0 Element Plus 技术选型
- GOALS.md: 六维功能清单 + v7.0 Element Plus 规划

---

## v6.2.1 — FeatureFlags 激活 + SPA 前端修复 + 桌面打包 (2026-07-08)

### 🔴 CRITICAL: FeatureFlags 激活 — 7个算法从静默失效到正式启用

**问题**: `api/routes/upload.py` 调用 `analyze_and_score()` 时从未传入 `FeatureFlags` 参数，导致所有 gated 算法的 `if feature_flags is not None` 检查永远为 False，以下 7 个 v6.2 高级算法从未在线上环境执行：

| # | 算法                           | 文件                              | 影响                                                            |
| - | ------------------------------ | --------------------------------- | --------------------------------------------------------------- |
| 1 | Cross-Dimension Modifiers      | `score_service.py:297`          | HNR稳定性→气息、Voicing→音准、频谱倾斜→气声等 5 项跨维度修正 |
| 2 | Praat Voice Quality            | `audio_features_service.py:246` | Jitter/Shimmer/Formants(F1-F4)/Singer's Formant                 |
| 3 | Multi-scale HNR (de Krom 1993) | `audio_features_service.py:222` | 4频带倒谱域HNR，替代简单HPSS                                    |
| 4 | Praat CPP                      | `audio_features_service.py:226` | parselmouth PowerCepstrum，替代手动FFT倒谱                      |
| 5 | Voicing Detection              | `audio_features_service.py:230` | PYIN决策质量评估                                                |
| 6 | Reverb Compensation            | `audio_features_service.py:143` | HPSS+谱减法混响补偿                                             |
| 7 | TorchCREPE Fallback            | `audio_features_service.py:364` | PYIN检测率<50%时CREPE备选                                       |

**修复**: `upload.py` 第 101 行添加 `feature_flags=FeatureFlags()`；compare 路由同步修复。`_save_history()` 新增 `mode` 字段持久化；`_build_success_result()` 返回 `result['mode']`。

### SPA 前端修复 (9项)

**querySelector 选择器错误** (11处): 多处 `querySelector('_xxx')` 误写为标签选择器，应为 `querySelector('#xxx')` ID 选择器。涉及 `ReportPage.js`(2)、`HistoryPage.js`(5)、`SingPage.js`(4)。

**HistoryPage 运行时崩溃**: `_updateSelectionUI()` 中 `el.textContent="Deleted"` 引用未定义变量 `el`、HTML 模板标签闭合损坏、`_deleteAll()` 绕过确认逻辑。

**音频播放器回归**: ReportPage 新增 `AudioPlayer` 集成 — play/pause/progress/time 控件。SPA 迁移时从旧 `analysis.js` 丢失的功能。

**PitchCurve 实例化**: `_animateEntrance()` 中新增 `new PitchCurve()` 创建，修复音高曲线卡片永久空白。

**API 字段名不匹配**: `HistoryPage._loadHistory()` 读取 `res.records` 改为 `res.history`，匹配后端返回格式。

**ComparePage / SingPage 模拟数据**: 替换硬编码模拟数据为真实 API 调用 (`compareAnalysis()` / `uploadAudio()`)。

**separateVocals() 请求格式**: FormData → JSON，匹配后端 `request.json.get('filepath')` 期望。

**HistoryPage 编码**: 修复部分 mojibake 中文乱码（文件级编码损坏需后续整体重写）。

### 桌面应用打包 (pywebview + PyInstaller)

- **`desktop_app.py`**: Flask 后台线程 + pywebview Edge WebView2 窗口，支持 `--debug`/`--port`/`--maximized`
- **`vocal_assessment.spec`**: PyInstaller 精简构建 — CPU Torch 2.12.1、INT8 量化模型(86MB)、排除死代码情绪模型(722MB)、UPX+strip+optimize=2。输出 0.91 GB（从 9.88 GB 缩减 10.8x）
- **`installer.iss`**: Inno Setup 6 安装脚本
- **`start.bat`**: 一键启动脚本（自动激活 conda 环境 + 等待 Flask 就绪后打开浏览器）
- **DL模型优化**: `model_manager/dl_manager.py` 切换为 INT8 量化模型 `model_quantized.onnx`

### 已知新问题

- HistoryPage.js 文件编码损坏（GBK/UTF-8 混乱），中文文本显示乱码，需整体重写
- SingMOS 模型依赖 `s3prl` 未安装，DL质量评估静默回退到零分
- 6 个后端路由缺失（歌曲库 CRUD + SSE 进度推送），前端有对应调用但后端未实现
- SettingsPage、SongLibraryPage 功能大量缺失
- 报告页音频播放器无 seek 拖动、无频谱跳动效果
- ComparePage 缺少直接上传标准音频入口
- SingPage 默认流程强制曲库选歌（跳过按钮不明显）
- 分析后无曲库自动比对弹窗

---

## v6.3 — 规划中 (目标: 2026-07)

### P0: 桌面打包修复

- SSL DLL 版本冲突修复 (conda OpenSSL vs Git mingw64)
- 顶层 EXE 清理
- UPX 重新启用 + strip 优化 → 目标 < 800 MB

### P1: 播放器增强

- ReportPage 音频 seek/拖动进度
- Canvas 波形可视化 (`drawWaveform`)
- 频谱跳动效果 (`drawFrequency` + `requestAnimationFrame`)

### P1: 演唱/对比体验

- SingPage 默认"快速演唱"模式（不需要曲库）
- ComparePage 左侧新增"上传标准音频"按钮
- 分析后自动 DTW 曲库比对 + 弹窗显示相似度

### P2: 数据完整性

- 新增 6 个后端路由 (歌曲库 CRUD + 分析进度 SSE)
- HistoryPage.js 编码修复 (GBK→UTF-8 重写)
- 导出 PDF/图片 blob 下载方式

### 前端缺失功能补全

- vizCard/phraseCard 接入真实数据
- 人声分离面板 (Demucs 模式选择 + 结果播放)
- 音色分析面板 (HNR/CPP/明亮度/温暖度)
- SettingsPage 评分参数 + 数据管理

---

## v6.2 — 评分算法重构 + 性能优化 (2026-07-07)

### 音准评分: 多指标体系

**问题**: v6.1 仅用 MAE 线性分段映射, 高低分差距 4.2 分.

**方案**: 六指标加权融合, 指数衰减替代线性分段.

| 指标                      | 权重 | 公式                                   | 文献                |
| ------------------------- | ---- | -------------------------------------- | ------------------- |
| MAE 指数衰减              | 40%  | `100 × exp(-mae/40)`                | Wager 2022          |
| RPA (Raw Pitch Accuracy)  | 25%  | `rpa × 100`                         | Cao et al. 2008     |
| RCA (Raw Chroma Accuracy) | 10%  | `rca × 100`                         | Cao et al. 2008     |
| Gross Error 惩罚          | 15%  | `100 − min(100, (rate−0.05)×200)` | Sundberg 1987       |
| Smoothness                | 5%   | `max(0, 100−(cv−1.0)×50)`         | Canazza et al. 2014 |
| Octave Error 惩罚         | 5%   | `max(0, 100−rate×200)`             | pitch-benchmark     |

**PYIN 校准**: YIN @ 16kHz 产生 3.5x 虚假帧间跳变 (785 vs PYIN 226). 权重调整依据:

- 帧间指标 (smoothness 10%→5%): 受 YIN 噪声污染
- 聚合指标 (MAE 35%→40%): 对 f0 伪影鲁棒
- 断层惩罚: 率阈值 + ÷3.5 校正因子 [de Cheveigne & Kawahara 2002]

### 跨维度修正

新增 `score_modifiers.py`:

| 修正                  | 因果链                                       | 幅度   | 文献              |
| --------------------- | -------------------------------------------- | ------ | ----------------- |
| HNR多频带CV → 气息   | 声带闭合不一致 → 气息不稳                   | ≤15%  | de Krom 1993      |
| Voicing置信度 → 音准 | 低置信度 → 音准不可靠                       | 标记   | de Cheveigne 2002 |
| 频谱倾斜 → 气声      | HNR低+倾斜平坦=艺术气声; HNR低+倾斜陡峭=漏气 | ≤15%  | Sundberg 1987     |
| 气息-音准耦合         | pitch_wobble高+HNR不稳定 → 气息不足         | ≤15分 | Titze 1994        |

### 特征扩展

| 特征                          | 来源                                      | 用途             |
| ----------------------------- | ----------------------------------------- | ---------------- |
| 频谱倾斜 (LTAS slope dB/oct)  | `acoustic.py` — Welch PSD + 线性回归   | 气声 vs 漏气区分 |
| Jitter (local, rap, ppq5)     | `voice_quality_praat.py` — parselmouth | 声质→技术分修正 |
| Shimmer (local, apq3)         | 同上                                      | 同上             |
| Formants (F1-F4)              | 同上 — Burg method                       | 共鸣质量         |
| Singer's formant (2.5-3.5kHz) | 同上 — LTAS能量比                        | 专业技巧         |
| Staccato 检测                 | `technique.py` — RMS脉冲               | 技巧多样性       |
| Legato 检测                   | `technique.py` — 沉默段+音高平滑度     | 技巧多样性       |

### 性能优化

| 优化             | 方法                                        | 效果                |
| ---------------- | ------------------------------------------- | ------------------- |
| harmonicity 计算 | np.correlate O(N²) → FFT自相关 O(N log N) | 566.9s → <0.1s     |
| HPSS 缓存        | 预计算一次, 调用点复用                      | 3次→1次 (~12s节省) |
| 动态范围         | max/min → p95/p5 百分位                    | 修复 101.9dB 异常值 |
| pitch_breaks     | 仅连续有声帧 + 排除八度跳变                 | 减少虚假断层计数    |
| Praat VQ Quick   | 截断到 60s                                  | ~5s → ~0.8s        |
| 完整管道         | 综合以上                                    | ~700s → ~54s (13x) |

### 测试

```
单元: 43/43 通过
TDD:  11/11 通过 (1 xfail→XPASS)
集成: 134/134 通过
真实音频: 5文件基线已建立 (见 PROJECT_STATUS.md)
```

---

## v6.1 — 评分区分度修复 + Artistry 独立评分 + 测试模块化 (2026-07-06, 已完成)

### 评分区分度修复 (真实信号驱动)

**核心原则: 所有分数从真实声学测量推导，连续线性映射替代离散步进加分。**

| # | 维度               | 文件                                     | 修复前                                     | 修复后                                      |
| - | ------------------ | ---------------------------------------- | ------------------------------------------ | ------------------------------------------- |
| 1 | Technique          | `services/features/technique.py`       | `technique_score = 50` (地板)            | `technique_score = 0`, 仅检测到的技巧加分 |
| 2 | Breath 子维度      | `services/features/breath.py`          | 步进加分 (`if > 80: +20 elif > 60: +14`) | 连续线性映射 (`pitch_stability * 0.4`)    |
| 3 | Breath 基线        | `breath.py` 四处 fallback              | `= 10`                                   | `= 0`                                     |
| 4 | HNR/CPP 高技巧阈值 | `services/scoring/technique_scorer.py` | `technique_score >= 70` (不可达)         | `>= 35` (匹配新 0-85 范围)                |
| 5 | 配置更新           | `services/scoring_config.py`           | breath_baseline=10, technique_baseline=50  | 全部 = 0                                    |

### Artistry 评分独立化

| 旧版 (v5.14)                                                                   | 新版 (v6.1)               |
| ------------------------------------------------------------------------------ | ------------------------- |
| `pitch*0.20 + rhythm*0.25 + breath*0.20 + technique*0.35 + modulation(±10)` | 4 个独立声学特征子维度    |
| 95% 来源于其他分数 (r > 0.9)                                                   | 100% 来源于可测量声学信号 |

**子维度**: 颤音品质(30%) + 动态控制(30%) + 乐句处理(25%) + 音高变化(15%)

### v6.0 兼容性修复 (6 项 bug)

| 严重度   | 问题                                                      | 修复文件                                                |
| -------- | --------------------------------------------------------- | ------------------------------------------------------- |
| CRITICAL | `detect_mixed_audio()` 返回值 4→3 导致 Demucs 静默失败 | `audio_service.py`, `dtw_aligner.py`                |
| MEDIUM   | E2E 测试 collection error (3 处)                          | `test_e2e.py`, `test_e2e_v2.py`, `test_e2e_v3.py` |
| MEDIUM   | `AcousticResult` 孤立字段                               | `types.py`                                            |
| MEDIUM   | 动态属性未声明                                            | `types.py`                                            |
| LOW      | 重复 import + 文档自相矛盾                                | `acoustic.py`, `PROJECT_STATUS.md`                  |

### 测试模块化

```
tests/tdd/
├── conftest.py                  # 会话级音频缓存 (cached_quick_result 等)
├── test_acoustic_algorithms.py  # Feature Flags + HNR/CPP/Voicing/CREPE (< 5s)
├── test_mixed_audio.py          # 混合音频检测 + 混响补偿 (< 120s)
├── test_scoring_v6_1.py         # 评分区分度验证 (缓存复用, < 30s)
└── test_future_features.py      # RED 阶段 xfail (SSE + Song DB)
```

### API 契约文档

新增 `docs/2-technical/API_CONTRACT.md` — 为 v7.0 Vue 迁移准备的完整 API 规范。

---

## v6.0 — 混响补偿管线接入 + 混合音频检测文献驱动重构 (2026-07-06, 已完成)

### 混响补偿接入评分管线 (P2→✅)

| 文件                                   | 变更                                                          |
| -------------------------------------- | ------------------------------------------------------------- |
| `services/feature_flags.py`          | 新增`enable_reverb_compensation` flag                       |
| `services/audio_features_service.py` | 集成`ReverbCompensator`, HNR/CPP 计算前可选 HPSS+谱减法补偿 |
| `services/features/reverb.py`        | 已有实现 (v5.20), 无变更                                      |

**管线**: `audio_data` → `ReverbCompensator.process()` (HPSS 中值滤波 + Boll 1979 谱减法 + Berouti 1979 过减) → HNR/CPP 计算
**控制**: `FeatureFlags.enable_reverb_compensation` 默认关闭
**测试**: 4 个 TDD 测试 GREEN

### 混合音频检测文献驱动重构 (P2→✅)

基于 **Fitzgerald (2010) DAFx**, **Driedger et al. (2014) ISMIR**, **Lehner et al. (2018) TASLP** 三篇论文完全重写 `detect_mixed_audio()`:

**v5.17 → v6.0 变更**:

- 移除低频能量 (<300Hz) — Lehner 2018 证明受录音条件影响过大
- 新增子带频谱平坦度 (1.5-3kHz) — Lehner 2018 §4 证明最可靠
- 新增谐波度 (Harmonicity) — 自相关法量化谐波结构
- HPSS 门控基于 Driedger 2014 §3 校准 (0.88/0.72)
- 五特征加权投票替代二特征逻辑

**真音频验证**:

- 纯人声误判率: 75% → **0%**
- 已知局限: 极轻钢琴伴奏 HPSS ratio >0.88 (Driedger 2014 证实为理论上限)
- 测试: 5 synthetic + 2 integration = 7 tests GREEN

### 论文下载

4 篇关键论文下载至 `参考论文/`:

- Fitzgerald (2010) HPSS Median Filtering
- Driedger, Müller, Disch (2014) Extending HPSS
- Lehner, Schlüter, Widmer (2018) Loudness-Invariant Vocal Detection
- Driedger, Müller (2015) Cascaded Decomposition for Singing Voice

---

## v5.20 — 前端SPA修复 + 混响补偿 + 混合音频检测重构 + 架构升级 (2026-07-05, 已完成)

### 🔴 SPA 导航死锁根因修复 (P0, 3 文件)

**症状**: 点击导航按钮后 URL hash 改变, 但页面内容不更新, 需手动刷新浏览器。

**根因**: 三重 Bug 叠加导致路由器 `#transition()` 死锁:

1. **`AnimationController._execute()`** — `onComplete` 回调从 vars 解构后被丢弃, 未传入 GSAP `toVars`
2. **`AnimationController._track()`** — `eventCallback('onComplete', cleanup)` 直接覆盖原有 `onComplete`, 且 getter 对刚创建的 tween 可能返回 `undefined`, 未回退到 `vars.onComplete`
3. **`HashRouter.#handleRoute()`** — `killAll()` 在 `#navPending` 检查之前执行。单次点击触发 `hashchange` + `popstate` 双事件, 第二次调用的 `killAll()` 杀掉第一次调用的 leave 动画 → GSAP 被 kill 的 tween 不触发 `onComplete` → Promise 永不 resolve → `#navPending` 永远 `true` → 所有后续导航被 BLOCKED

**修复**:

| 文件                                          | 修复                                                                                                                                                                                     |
| --------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `web/static/js/animation/Controller.js`     | `_execute()`: `onComplete` 传入 GSAP `toVars`; `_track()`: 链式调用(cleanup + 原有回调), 同时检查 `eventCallback` getter 和 `vars.onComplete`; `leave()`: 安全超时 resolve |
| `web/static/js/components/BaseComponent.js` | `beforeUnmount()`: 硬编码 `'page-leave'` 预设 (之前误用页面入场预设)                                                                                                                 |
| `web/static/router.js`                      | `#navPending` 检查移到 `killAll()` 之前, 防止 popstate 事件杀掉活跃动画                                                                                                              |

### 🏗️ 前端架构升级 — v7.0 Vue 迁移衔接

为减少 v7.0 (Electron + Vue 3) 迁移工作量, 提前建立与 Vue 生态对应的基础设施:

#### 新增文件

| 文件                            | 说明                                                        | v7.0 目标             |
| ------------------------------- | ----------------------------------------------------------- | --------------------- |
| `web/static/js/AppContext.js` | 应用级依赖注入容器, 聚合 store/router/api/ac/events         | Vue`provide/inject` |
| `web/static/js/EventBus.js`   | 事件总线 (`on`/`once`/`off`/`emit`), 解耦跨组件通信 | `mitt()`            |

#### 重构文件

| 文件                                               | 变更                                                                                                            | v7.0 目标                        |
| -------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- | -------------------------------- |
| `web/static/js/components/BaseComponent.js` v3.0 | context 注入; 服务 getter 优先`this.context` 回退 `window.*`; 生命周期文档标注 Vue 对应钩子                 | `<script setup>` + composables |
| `web/static/app.js` v3.0                         | 引入 AppContext + EventBus; 初始化流对齐 Vue`createApp → use → mount` 模式; `context.freeze()` 启动后锁定 | `main.js` / `createApp()`    |
| `web/static/router.js` v3.0                      | `useContext(context)` 注入; `#ac` private getter 替代 `window.__ac`; 各方法标注 Vue Router 对应 API       | Vue Router`createRouter`       |

#### 迁移映射

```
Vanilla JS (v5.20+)       →  Vue 3 (v7.0)
─────────────────────────     ────────────────────
AppContext                 →  createApp + provide/inject
  context.store            →  Pinia createPinia()
  context.router           →  Vue Router createRouter()
  context.api              →  HTTP client / IPC bridge
  context.ac               →  useGsap() composable
  context.events           →  mitt()
BaseComponent              →  <script setup>
  constructor/render       →  setup / <template>
  mount/beforeUnmount      →  onMounted / onBeforeUnmount
HashRouter                 →  Vue Router
  register/onBeforeNavigate→  addRoute / beforeEach
```

### 前端 SPA Bug 修复 (P0, 基础修复)

本次修复了 6 类前端问题, 涉及 12 个文件:

#### API 路径修复

| 问题                                              | 文件           | 修复                              |
| ------------------------------------------------- | -------------- | --------------------------------- |
| `POST /api/audio/analyze` 端点不存在 (404)      | `api.js:168` | →`POST /api/upload` (FormData) |
| `POST /api/history/batch-delete` 路径和方法错误 | `api.js:233` | →`DELETE /api/history/batch`   |

**根因**: 前端 API 路径与后端 Flask 路由不匹配。`/api/audio/analyze` 不存在, 导致上传分析请求失败。正确的上传端点应为 `/api/upload` (接受 FormData)。

#### CSS 页面隐藏

| 问题                                                  | 文件                  | 修复         |
| ----------------------------------------------------- | --------------------- | ------------ |
| `.page { display: none; }` 导致页面切换后内容不可见 | `components.css:55` | 移除隐藏规则 |

**根因**: SPA 模式下页面由 JS 动态切换 (旧页 destroy → 新页 mount), 同一时间只有一个 `.page` 在 DOM 中, 不需要 `display:none` 切换。旧 CSS 规则导致新挂载的页面被隐藏。

#### 路由错误恢复

| 问题                                                    | 文件              | 修复                                 |
| ------------------------------------------------------- | ----------------- | ------------------------------------ |
| `#transition()` 无错误处理, 页面挂载失败导致 SPA 崩溃 | `router.js:148` | 添加 try-catch + 错误页面 + 调试日志 |

#### 编码问题修复

| 问题                                                       | 文件               | 修复                     |
| ---------------------------------------------------------- | ------------------ | ------------------------ |
| `HistoryPage.js` 全部中文乱码 (mojibake)                 | `HistoryPage.js` | 逐字替换 20+ 处乱码      |
| `HistoryPage.js:35` `ac is not defined` (编码问题导致) | `HistoryPage.js` | 修复为`this.ac`        |
| 全部 6 个 page 文件:`const ac = this.ac` 模式            | `*.js`           | 改为直接`this.ac` 调用 |

**根因**: HistoryPage.js 文件中的 UTF-8 中文字符被错误编码, 导致浏览器显示乱码。同时编码问题导致第 35 行的 `const ac = this.ac` 无法正确执行。

#### ComparePage Modal

| 问题                                     | 文件                   | 修复                                               |
| ---------------------------------------- | ---------------------- | -------------------------------------------------- |
| Modal 弹窗无法关闭 (点击取消/背景无反应) | `ComparePage.js:269` | 移除`#openSongSelector` 中外层无用的 overlay div |

**根因**: `StandardAudioSelector` 在 modal 模式已自带 overlay, 但 `#openSongSelector` 又创建了一个外层 overlay div (`position:fixed;inset:0`), 关闭时只移除了内层。

#### ⚠️ 导航跳转 Bug (未修复)

**症状**: 点击导航按钮后 URL hash 改变, 但页面内容不更新, 需手动刷新浏览器才能显示对应页面。

**状态**: 代码逻辑已全面审查, 路由链路 (Navigation → hashchange → #handleRoute → #matchRoute → #transition → mount → render) 均正确。已在 router.js 添加详细 `[Router]` 调试日志定位问题。

### 后端改进

#### 混响补偿 (P1, 新增) 🆕

| 模块                  | 文件                                   | 依据                                                                     |
| --------------------- | -------------------------------------- | ------------------------------------------------------------------------ |
| `ReverbCompensator` | `services/features/reverb.py` (新建) | Fitzgerald 2010 (HPSS), Boll 1979 (谱减法), Berouti 1979 (过减+频谱地板) |

- HPSS 谐波/冲击分离 + 谱减法, 减轻不同录音环境对 HNR/CPP 的影响
- Feature Flag: 待后续版本接入评分管线

#### 混合音频检测重构 (P2)

| 模块                                | 文件                              | 依据                                                |
| ----------------------------------- | --------------------------------- | --------------------------------------------------- |
| `detect_mixed_audio()` 多特征融合 | `services/features/acoustic.py` | Fitzgerald 2010 (HPSS), McFee et al. 2015 (librosa) |

- **旧算法**: 单阈值 `low_freq_ratio > 0.35` — 轻伴奏(如"手写的从前")被漏判
- **新算法**: 四特征加权投票 (HPSS 谐波比 + 高频能量 + 频谱平坦度 + 低频能量比), 采样率自适应
- **检测流程**: 使用已加载的 16kHz 音频 (避免额外 I/O)

#### CPP 测试修复

| 问题                                  | 文件                                  | 修复                                             |
| ------------------------------------- | ------------------------------------- | ------------------------------------------------ |
| `test_praat_cpp_low_for_noise` 失败 | `tests/tdd/test_future_features.py` | 安装`praat-parselmouth 0.4.7` + 添加可用性检查 |

### 涉及文件 (完整)

| 文件                                          | 变更                                                                               |
| --------------------------------------------- | ---------------------------------------------------------------------------------- |
| `web/static/js/animation/Controller.js`     | SPA 死锁修复:`_execute` onComplete 传递, `_track` 链式回调, `leave` 安全超时 |
| `web/static/js/components/BaseComponent.js` | beforeUnmount 预设修复 + v3.0 重构 (context 注入, Vue 生命周期对齐)                |
| `web/static/router.js`                      | pending 检查前置 + v3.0 重构 (useContext, Vue Router 映射)                         |
| `web/static/app.js`                         | v3.0 重构 (AppContext + EventBus, createApp 模式入口)                              |
| `web/static/js/AppContext.js`               | 🆕 依赖注入容器 (v7.0 → Vue provide/inject)                                       |
| `web/static/js/EventBus.js`                 | 🆕 事件总线 (v7.0 → mitt)                                                         |
| `web/static/js/services/api.js`             | 修复 2 个 API 路径                                                                 |
| `web/static/js/pages/HistoryPage.js`        | 修复乱码 +`ac` 变量                                                              |
| `web/static/js/pages/HomePage.js`           | `ac` 变量修复                                                                    |
| `web/static/js/pages/ComparePage.js`        | Modal overlay +`ac` 变量                                                         |
| `web/static/js/pages/ReportPage.js`         | `ac` 变量修复                                                                    |
| `web/static/js/pages/SingPage.js`           | `ac` 变量修复                                                                    |
| `web/static/js/pages/SongLibraryPage.js`    | `ac` 变量修复                                                                    |
| `web/static/css/components.css`             | 移除`.page { display: none }`                                                    |
| `services/audio_service.py`                 | `_preprocess_for_scoring` 使用已加载音频                                         |
| `services/features/acoustic.py`             | 多特征融合检测算法                                                                 |
| `services/features/reverb.py`               | 🆕 混响补偿模块                                                                    |
| `tests/tdd/test_future_features.py`         | CPP 测试修复 + 混响测试 GREEN                                                      |
| `docs/` 5 文件                              | CHANGELOG + PROJECT_STATUS + ARCHITECTURE + PRD + GOALS 更新                       |

### 测试

```
单元测试:  121 passed (unit/ 目录)
全量收集:  204 tests (含 TDD xfail + 集成)
Flask 路由: 全部 12 端点正确 (200 / 301)
JS 验证:   全部 import 路径正确, 无残留引用
```

---

## v5.19 — 评分区分度修复 + 跨维度集成 + Feature Flag扩展 (2026-07-04, 已完成)

### 气息评分区分度修复 (P0)

**根因**: 四子维度基线全为 40，仅靠少量加分区分好坏，导致所有演唱者气息分压缩在 ~15 分区间。

**修复**:

- 子维度基线归零 (40→0): `_evaluate_long_note_support`, `_evaluate_dynamic_control`, `_evaluate_breath_design`, `_evaluate_breath_technique`
- 加分幅度扩大 2-3×: 长音稳定性 +35 (曾 +12), 动态控制 +40 (曾 +15), 气口设计 +35 (曾 +15)
- 移除 `_calculate_professional_breath_score` 中的 -20 调整 (基线已归零)
- 波动惩罚更早触发 (0.25→0.18) + 更大斜率 (60→80)
- `EmpiricalThresholds` 基线参数全部更新 (40.0→0.0)
- `BreathScorer` 等级阈值调整: 80/60/40 (曾 85/70/55)

### 音准评分区分度修复 (P0)

**根因**: MAE 12-35 音分区间仅 10 分跨度，好歌手全部堆叠在 92-99 分。

**修复**:

- `PitchThresholds`: excellent 12→8, good 35→45, pass 60→65
- 第一段斜率 `*10→*30` (30 分跨 37 音分)
- 第二段斜率 `*20→*25` (25 分跨 20 音分)
- 第三段起点 70→45，下降率 0.85→0.6

效果: MAE=15→94 (曾 99), MAE=25→86 (曾 94), MAE=50→64 (曾 78)

### HNR/CPP 天花板重校准 (P1)

- 流行 HNR 满分阈值: 12→22 dB (高技巧), 15→22 dB (低技巧)
- 美声 HNR 满分阈值: 20→28 dB
- 流行 CPP 满分阈值: 1.0→2.5 (低技巧), 0.5→2.0 (高技巧)
- 美声 CPP 满分阈值: 2.0→3.0
- `TechniqueThresholds` 参数同步更新

### 跨维度集成基础设施 (P1)

- 新增 `enable_cross_dimension_modifiers` Feature Flag (默认关闭)
- `AudioFeaturesResult` 预留 `_hnr_multiscale` 字段
- `ScoreServiceV4` 预留 v5.19 TODO 注释

### 音量维度独立 (P2)

- `score_service.py`: volume 从 `= breath_score` 改为基于 `dynamic_range` 独立计算
- `test_future_features.py`: 移除 `test_volume_independent_from_breath` xfail

### 测试

- 新增 `tests/tdd/test_v5_19_features.py` (16 tests):
  - 3 气息区分度, 4 音准区分度, 3 技术天花板, 4 跨维度集成, 2 音量独立
- 移除 10 个 xfail 标记: breath_baseline, pitch x3, cpp, hnr_breathy, cross_dim x3, volume

### 涉及文件

| 文件                                     | 变更                                                                              |
| ---------------------------------------- | --------------------------------------------------------------------------------- |
| `services/features/breath.py`          | 子维度基线归零 + 加分扩大 + 波动惩罚调整                                          |
| `services/scoring_config.py`           | PitchThresholds/BreathThresholds/TechniqueThresholds/EmpiricalThresholds 全部更新 |
| `services/scoring/breath_scorer.py`    | 等级阈值更新                                                                      |
| `services/scoring/technique_scorer.py` | HNR/CPP 天花板提升                                                                |
| `services/feature_flags.py`            | 新增`enable_cross_dimension_modifiers`                                          |
| `services/score_service.py`            | volume 独立计算                                                                   |
| `tests/tdd/test_v5_19_features.py`     | 🆕 新增                                                                           |
| `tests/tdd/test_future_features.py`    | 移除 volume xfail                                                                 |

---

## v5.18 — GSAP 动画系统重设计 + ScoreServiceV4 + 性能文档化 + 测试体系审计 + 开源算法移植 (2026-07-04, 已完成)

### 代码审查与修复 (2026-07-04)

三代理并行审查（code-reviewer + security-reviewer + python-reviewer）发现 20 个问题，全部修复。

#### CRITICAL 修复 (1 项)

| 问题                                  | 文件                     | 修复                                 |
| ------------------------------------- | ------------------------ | ------------------------------------ |
| `except Exception: pass` 静默吞异常 | `audio_service.py:538` | 改为具体异常捕获 +`logger.debug()` |

#### HIGH 修复 (5 项)

| 问题                                                                                  | 文件                     | 修复                                        |
| ------------------------------------------------------------------------------------- | ------------------------ | ------------------------------------------- |
| **de Krom 1993 谐波边界检测 Bug** — 倒谱谐波峰仅置零 1 bin 而非整个"山峰"      | `hnr.py:213-225`       | 重写边界搜索: 从峰值向两侧走至谷底          |
| **倒谱镜像 off-by-one** — 噪声倒谱对称化源起始错位 1 bin                       | `hnr.py:231-232`       | `mid-1` → `mid-2`                      |
| **TorchCREPE fallback 死代码** — `_analyze_pitch()` 未传递 `feature_flags` | `audio_service.py`     | `feature_flags` 传入 `_analyze_pitch()` |
| **API 响应泄露 traceback** — 完整 Python 堆栈返回给客户端                      | `audio_analysis.py:63` | 移除`'traceback'` 字段，仅返回 `error`  |
| **`feature_flags` 参数未使用** — `ScoreServiceV4.calculate()` 接受但未引用 | `score_service.py`     | 移除参数，加 v5.19 TODO 注释                |

#### MEDIUM 修复 (8 项)

| 问题                                                                                  | 文件                          | 修复                                                |
| ------------------------------------------------------------------------------------- | ----------------------------- | --------------------------------------------------- |
| **Voicing 一致性 3 重 Bug** — 时长 off-by-one + 初始/末尾段漏计                | `voicing.py`                | 时长`+1`，补全边界段统计                          |
| **CPP 归一化因子未校准** — `/20.0` 导致 Praat CPP 值比现有 pipeline 小 3-4× | `audio_features_service.py` | `/20.0` → `/6.0` (24dB 优质人声 → 4.0 优秀档) |
| **`Optional[object]` 反模式** — 等价于 `Any`，破坏类型检查                 | `types.py`                  | 改为`Optional['VoicingDetectionResult']` 前向引用 |
| **重复 `import logging`** — 4 个 DL 辅助方法体内重新导入                     | `audio_service.py`          | 统一使用模块级`logger` (已随 DL helpers 提取修复) |
| **Python 循环未向量化** — `_compute_energy_agreement` 逐帧遍历               | `voicing.py`                | 改为 NumPy boolean indexing                         |
| **无音频时长上限** — 大音频 DoS 风险                                           | `audio_service.py`          | 添加代码注释，建议后续版本加入显式限制              |
| **ParSelmouth 单段提取兼容** — `Extract all intervals` 可能返回非列表        | `cpp.py`                    | (低优先级，默认不走`voiced_only` 路径)            |
| **Feature Flag 嵌套过深** — 3 层 if 嵌套                                       | `audio_features_service.py` | 提取为 3 个独立私有方法                             |

#### 文件大小优化

| 文件                    | 变化                                             | 说明                                                          |
| ----------------------- | ------------------------------------------------ | ------------------------------------------------------------- |
| `audio_service.py`    | 872 →**800 行**                           | DL 延迟初始化+运行方法提取到新文件                            |
| `audio_dl_helpers.py` | 🆕 93 行                                         | `AudioDLHelpers` 类 — VoiceQuality/Style/DTW/StyleAnalyzer |
| `hnr.py`              | `_de_krom_hnr` 109 行 → 6 个子方法 (15-30 行) | 倒谱计算/谐波边界/谐波置零/镜像/阶梯校正/频带 HNR             |

#### 测试改进

| 改进                                                   | 文件                                                          |
| ------------------------------------------------------ | ------------------------------------------------------------- |
| 添加`pythonpath = .` 消除 `sys.path.insert` 反模式 | `tests/pytest.ini`                                          |
| 添加`unit` / `integration` pytest markers          | `tests/pytest.ini` + 测试文件                               |
| 移除所有测试文件的`sys.path.insert(0, ...)`          | `test_v5_18_integration.py`, `test_scoring_robustness.py` |

### 测试体系审计与全面修复 (2026-07-03)

对全部 105+ 个测试脚本的深度审计，发现并修复了以下关键问题：

#### P0 修复 (2 个实际失败)

| 问题                                                                                                      | 文件                        | 修复                             |
| --------------------------------------------------------------------------------------------------------- | --------------------------- | -------------------------------- |
| `test_professional_breath_not_always_100` — API 不匹配: 传 float 给需 `BreathStabilityResult` 的方法 | `test_full_pipeline.py`   | 重写测试，使用正确 DTO 对象      |
| `test_vocal_audio_returns_reasonable_scores` — 文件名硬编码 `恋人.mp3` 但实际为 `恋人（高分）.mp3` | `test_full_pipeline.py`   | 改为 glob 通配符搜索真实音频文件 |
| `test_volume_dimension_in_scores` — 误标记 xfail，volume 维度已实现                                    | `test_future_features.py` | 移除 xfail，添加解耦验证测试     |

#### E2E 测试 SPA 迁移

| 文件                   | 状态      | 说明                                  |
| ---------------------- | --------- | ------------------------------------- |
| `test_upload.py`     | ⏭️ skip | 旧版多页面架构 (analysis.html 已 301) |
| `test_analysis.py`   | ⏭️ skip | 旧版分析页面 (已 301 到 /)            |
| `test_real_audio.py` | ⏭️ skip | 硬编码不存在的文件名                  |
| `test_spa_e2e.py`    | 🆕 新增   | SPA Hash 路由端到端 (24 tests)        |

#### 新增测试文件 (4 个, +100 测试)

| 文件                              | 测试数 | 功能                                                                     |
| --------------------------------- | ------ | ------------------------------------------------------------------------ |
| `test_scoring_robustness.py`    | 22     | 评分可重现性、边界值安全、区分度分布、诊断一致性、级联惩罚               |
| `test_real_audio_regression.py` | 27     | 5 个真实文件 × 6 维度基线保护 + 区分度验证                              |
| `test_future_features.py`       | 13     | TDD RED 阶段: FeatureFlag、多尺度HNR、Praat CPP、SSE、歌曲匹配、混响补偿 |
| `test_store_and_ac.js`          | 16     | JS 集成测试: 真实 Store + AnimationController + Presets 模块             |

#### 测试统计对比

| 指标                 | 审计前         | 审计后                     |
| -------------------- | -------------- | -------------------------- |
| 单元+集成测试数      | 91             | **128**              |
| 通过率               | 89/91 (98%)    | **128/128 (100%)**   |
| TDD RED 测试 (xfail) | 0              | **13**               |
| 真实音频回归基线     | 无             | **5 文件 × 6 维度** |
| JS 测试模式          | 全 mock        | 真实模块集成               |
| 旧版 E2E 覆盖        | 走废弃页面路径 | SPA Hash 路由              |

### 性能文档化

所有产品/技术/质量文档已全面加入性能约束：

| 文档                 | 新增内容                                                                               |
| -------------------- | -------------------------------------------------------------------------------------- |
| PRD.md               | 4.1 性能章节扩展为 8 个子章节: 端到端/特征提取/评分配置/前端/SSE/存储/降级/回归防护    |
| GOALS.md             | 功能模块全景标注每模块耗时预算; 新增 4.2 性能设计原则                                  |
| ARCHITECTURE.md      | 每个数据流标注耗时+内存+复杂度; 新增第五章"性能设计决策"(4个PERF-ADR); 技术债务新增2项 |
| API.md               | 接口列表新增 P95延迟+超时列; 新增缓存策略表; 新增速率限制表                            |
| SCORING.md           | 新增算法复杂度与耗时分解表(12个算法); Quick/Pro 耗时火焰图                             |
| ANIMATION_DESIGN.md  | 新增第九章"动画性能合约"(帧率/时长/GC/prefers-reduced-motion/回归检测)                 |
| PAGE_DESIGN.md       | 新增性能总览表(每页面: 首屏/切换/动画/内存)                                            |
| ROUTES.md            | 新增路由性能合约; 路由级代码分割计划表                                                 |
| BACKEND_ALIGNMENT.md | 新增前后端性能对接表; 前端错误降级策略                                                 |
| VISUAL_AUDIT.md      | 新增第六章"性能审计补充"(6项性能问题发现)                                              |
| TDD.md               | 新增第九章"性能测试"(5个测试示例+运行命令+回归触发条件)                                |
| BDD.md               | 新增第七章"性能BDD场景"(7个Gherkin场景+Step Definitions)                               |
| PROJECT_STATUS.md    | 性能基准表扩展: 增加特征提取阶段耗时/前端性能/未测量指标                               |

### 核心性能目标汇总

| 维度             | 目标          | 测量                    |
| ---------------- | ------------- | ----------------------- |
| Quick 端到端     | < 30s         | `time.perf_counter()` |
| Pro CPU          | < 180s        | `time.perf_counter()` |
| Pro GPU          | < 60s         | `time.perf_counter()` |
| 前端 FCP         | < 1.5s        | Lighthouse              |
| GSAP 动画        | ≥ 30fps      | DevTools                |
| Canvas 实时      | ≥ 30fps      | DevTools                |
| 路由切换         | < 300ms       | `performance.now()`   |
| 内存峰值 (Quick) | < 400MB       | tracemalloc             |
| 内存峰值 (Pro)   | < 800MB       | tracemalloc             |
| 特征提取总耗时   | < 16s (Quick) | 各 extractor 独立计时   |

### 开源算法移植 + Feature Flag 机制 (2026-07-04)

从 VoiceLab 和 pitch-benchmark 移植 4 个开源算法，通过 Feature Flag 机制控制启用。

#### 移植来源

| 算法                | 来源                                        | Feature Flag                   | 方法                                                                        |
| ------------------- | ------------------------------------------- | ------------------------------ | --------------------------------------------------------------------------- |
| 多频带 HNR          | VoiceLab`MeasureHNRVoiceSauceNode.py`     | `enable_multiscale_hnr`      | de Krom 1993 倒谱域谐波/噪声分离, 4 频带                                    |
| Praat CPP           | VoiceLab`MeasureCPPNode.py`               | `enable_praat_cpp`           | `parselmouth.Spectrum` → `To PowerCepstrum` → `Get peak prominence` |
| Voicing Detection   | pitch-benchmark`algorithms/base.py`       | `enable_voicing_detection`   | 自一致性检查 (范围/八度跳跃/切换/能量)                                      |
| TorchCREPE Fallback | pitch-benchmark`algorithms/torchcrepe.py` | `enable_torchcrepe_fallback` | PYIN detection_rate < 0.5 时降级                                            |

#### 新增文件

| 文件                                            | 说明                                      |
| ----------------------------------------------- | ----------------------------------------- |
| `services/feature_flags.py`                   | FeatureFlags dataclass (4 开关, 默认关闭) |
| `services/features/hnr.py`                    | MultiScaleHNR — de Krom 1993 倒谱法      |
| `services/features/cpp.py`                    | PraatCPP — VoiceLab parselmouth 封装     |
| `services/features/voicing.py`                | VoicingDetector — PYIN 决策质量评估      |
| `tests/integration/test_v5_18_integration.py` | 端到端集成测试 (7 tests)                  |

#### 真音频效果 (tests/test_data/audio/vocal/)

| 音频 (258s) | Default Tech | v5.18 Tech | 变化            | Default Total | v5.18 Total |
| ----------- | ------------ | ---------- | --------------- | ------------- | ----------- |
| 1（高分）   | 77.5         | 92.5       | **+15.0** | 73.6          | 77.0        |

**关键修复**: 旧 CPP 算法对所有音频返回 ~0.018 (无区分度, 评分始终 ~51)。VoiceLab CPP 返回 5-40 dB 范围，恢复 CPP 维度的区分能力。

#### 已知局限 (→ v5.19)

| 问题           | 说明                                                               |
| -------------- | ------------------------------------------------------------------ |
| 跨维度集成不足 | HNR/CPP 仅影响 Technique (20%总权重), 稳定性/置信度/频带差异未利用 |
| CPP 归一化     | VoiceLab CPP 通过`/20` 映射到评分阈值, 需校准                    |
| HNR 天花板     | 新旧 HNR 对优质人声均达 100 分 (≥12dB 阈值)                       |

#### 测试统计

```
单元测试:    121 passed ✅
TDD 测试:     13 passed (7 v5.18 GREEN + 6 v6.0 xfail) ✅
集成测试:      7 passed (v5.18 端到端管线) ✅  ← 新增
─────────────────────────────────────────
总计:        141 passed, 0 failures
```

---

## v5.17 — 混合音频检测修复 + GPU 加速 (2026-06-04, 已完成)

### 修复1：轻伴奏人声 混合音频检测失败

**根因**: `detect_mixed_audio()` 阈值 `low_freq_ratio > 0.35` 太保守。陈奕迅（轻钢琴伴奏，低音域男声）`low_freq=0.296` 刚好低于阈值，跳过 Demucs 导致评分失真。

**修复** (`services/features/acoustic.py` + `services/audio_service.py`):

- 新增 `0.25-0.35` 轻伴奏区间（钢琴/吉他独奏）
- 纯人声 `low_freq < 0.2`，阈值 `0.25` 有充足安全边界
- 置信度阈值 `0.5→0.45`

**效果**: 5 首人声音频全部正确触发 Demucs（陈奕迅从 False→True）

### 修复2：合成音频/噪声 正确归零

`VoiceQualityService` 已正确检测所有合成文件为 `is_voice=False`。API 管线（`audio_analysis.py:137-141`）正确拦截。
测试脚本之前绕过了此检查 → 已修正。

**效果**: 10 个合成/噪声文件全部返回 0.0 分

### 新功能：GPU 加速支持

**修改** (`services/separation_service.py` + `api/__init__.py` + `web_app.py`):

- Demucs 自动检测 CUDA/MPS → 传 `-d cuda` 启用 GPU 加速
- `/health` 端点返回 GPU 状态
- 启动横幅显示 GPU 信息

**效果**: 有 NVIDIA GPU 时 Demucs ~200s→~20-40s

> ⚠️ 当前环境 PyTorch 为 CPU 版 (`2.11.0+cpu`)，需手动重装 CUDA 版：
> `pip uninstall torch torchaudio -y && pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124`

### 全量测试

| 模式     | 文件数            | 结果                       |
| -------- | ----------------- | -------------------------- |
| Quick    | 15 (5人声+10合成) | 5人声正常 + 10合成→0分 ✅ |
| Pro      | 5人声             | 全部正确触发Demucs ✅      |
| 单元测试 | 79                | 全部通过 ✅                |
| 混合检测 | 5人声             | 全部正确检测 ✅            |

---

## v5.16 — Pro Breath 修复 (2026-06-03, 已完成)

### 实际效果

| 指标                        | v5.15 | v5.16          | 变化                    |
| --------------------------- | ----- | -------------- | ----------------------- |
| **Pro Breath (恋人)** | 9.8   | **56.3** | **+46.5 (+474%)** |
| Pro Total (恋人)            | 63.2  | **73.7** | **+10.5**         |
| Quick/Pro Breath 差         | -46.6 | **-0.1** | 缩小 99.8%              |
| Quick/Pro Total 差          | -12.5 | **-1.1** | 缩小 91%                |
| Quick 回归                  | 75.7  | 74.8           | 零回归                  |
| 单元测试                    | 78/79 | 89/91          | 零回归 (2 pre-existing) |

### 修复：Pro Breath 崩塌 — is_clean_vocal 标记传递 + 校准

**根因**: v5.15 修复了 rhythm 的 `is_clean_vocal` 标记传递，但 breath 管线完全缺失此链路。
Demucs分离后纯净人声的RMS/HNR/CPP数值分布与混合音频完全不同，
`BreathAnalyzer` 四子维度全部基于混合音频阈值 → Pro Breath=9.8 (Quick=56.4)。

**修复** (遵循 v5.15 Rhythm CV重校准同模式):

1. `BreathStabilityResult.is_clean_vocal` 标记字段
2. `BreathAnalyzer.calculate_breath_stability()` 接受 `is_clean_vocal` 参数并存入结果
3. `_calculate_professional_breath_score()`: 纯净人声放宽非艺术波动惩罚(阈值0.25→0.35, 系数60→30) + 总分补偿(×1.8)
4. `BreathScorer.calculate()`: 纯净人声等级阈值放宽(85/70/55→73/58/43)
5. `AudioFeaturesService.extract_all_features()`: 传递 `is_clean_vocal=is_separated`

修改文件: `services/features/breath.py` (+15行), `services/scoring/breath_scorer.py` (+12行),
`services/features/__init__.py` (+3行), `services/audio_features_service.py` (+4行),
`services/scoring_config.py` (+4行)

### 全量真实音频测试 (5人声 + 10非人声)

| 音频                   | Q.Total | P.Total        | Q.Breath | P.Breath       | B.Diff         | Demucs       |
| ---------------------- | ------- | -------------- | -------- | -------------- | -------------- | ------------ |
| 恋人（高分）           | 74.8    | **73.7** | 56.4     | **56.3** | **-0.1** | ✅           |
| 1（高分）              | 72.7    | 75.0           | 63.2     | 57.1           | -6.1           | ✅           |
| 音频-3分26秒(高分)     | 72.6    | 76.4           | 52.6     | 78.2           | +25.6          | ✅           |
| 手写的从前（高分）     | 73.4    | 79.1           | 66.4     | 93.6           | +27.2          | 跳过(纯人声) |
| 陈奕迅难听之声（低分） | 48.8    | 48.8           | 51.2     | 51.2           | 0.0            | 跳过(纯人声) |

Quick模式 15/15 文件零回归。

---

## v5.15 — 三模式修复 (2026-06-03, 已完成)

### 实际效果

| 指标                        | v5.14 | v5.15           | 变化                    |
| --------------------------- | ----- | --------------- | ----------------------- |
| **Pro Rhythm (恋人)** | 18.6  | **66.0**  | **+47.4 (+255%)** |
| Pro Total (恋人)            | 57.6  | 63.2            | +5.6                    |
| Pro 耗时                    | ~309s | ~226s           | -83s (-27%)             |
| Quick 回归 (恋人)           | 75.6  | 75.7            | 零回归                  |
| Quick/Pro Rhythm 差         | -58.5 | **-11.1** | 缩小81%                 |
| 单元测试                    | 78/79 | 78/79           | 零回归                  |

### 修复1：Pro 节奏崩塌 — CV重校准

**根因**: Demucs分离后纯净人声onset天然不规则 (CV=1.34),
`_cv_to_deviation` 纯净人声阈值过严 (dev=0.635),
`RhythmScorer` irregularity双重惩罚叠加 → 最终18.6分。

**修复** (替代原计划"原始音频节奏"方案):

1. `_cv_to_deviation(is_clean_vocal=True)` 阈值×3: 0.5→0.75, 0.8→1.5, 1.2→2.4, 1.8→3.6
   CV=1.34→dev=0.36 (接近混合CV=0.6→dev=0.32)
2. `RhythmAlignmentResult.is_clean_vocal` 标记 → RhythmScorer 跳过 irregularity 惩罚
   (CV映射已充分表达不规则度, 双重惩罚是崩塌根因)

修改文件: `services/features/rhythm.py` (+20/-15), `services/features/__init__.py` (+2),
`services/scoring/rhythm_scorer.py` (+8)

### 修复2：SingMOS 完全移除

- `api/business/audio_analysis.py`: `dl_assessor = None`, `_assess_with_dl()`→零值
- `services/score_service.py`: `_apply_dl_fusion()`→`return total` (保留为扩展点)

效果: Pro 耗时-83s (SingMOS 80s), 反评分污染消除。

### 修复3：自参照一致性替代 SingMOS

`ScoreServiceV4._self_consistency_penalty()`:

- 将f0分3段, 每段计算pitch稳定性(60%)+人声比率(40%)
- 段间CV>0.15时扣分: `min(8, cv*40)`
- 比跨域DL模型可靠, 不增加耗时

修改文件: `services/score_service.py` (+65)

### 修复4：DTW 参考搜索默认化

`_find_reference_audio()`:

- 扫描 uploads/ 中带参考标签文件 (高分/参考/原唱/示范/标准)
- 清理用户文件名标签, `SequenceMatcher` 模糊匹配 (阈值>0.5)
- 命中→DTW融合; 未命中→回退绝对评分 (零退化)

修改文件: `api/business/audio_analysis.py` (+55)

### 遗留问题 → v5.16

- **Pro Breath=9.8** (Quick=56.4): Demucs分离后RMS/CPP/HNR系统性降解, 需类似Rhythm的CV重校准
- Pro Total 63.2 距目标≥70差6.8 (瓶颈在Breath)
- Pro 耗时 ~226s (Demucs~200s, 硬件限制)

---

## v5.14 — 音准多指标 + 艺术评分重构 + 专业模式深度测试 (2026-06-03)

### 真实音频测试 (Quick Mode)

| 音频         | Total           | Pitch | Rhythm        | Breath | Tech  | Art             |
| ------------ | --------------- | ----- | ------------- | ------ | ----- | --------------- |
| 高分组 (n=4) | **73-76** | 79-81 | 67-77         | 53-66  | 78-84 | **80-84** |
| 低分组 (n=1) | **47.0**  | 75.9  | **2.5** | 51.2   | 57.5  | **53.2**  |
| 差距         | **27.4**  | 4.2   | 68.6          | 4.3    | 21.7  | **28.4**  |

### 阶段一：音准多指标体系

从 pitch-benchmark 移植 (~100行):

- `PitchDeviationResult` 新增 6 字段: RPA, RCA, gross_error_rate, octave_error_rate, relative_smoothness, continuity_breaks
- `PitchAnalyzer._calculate_pitch_multimetric()` — 移植 evaluate_pitch_accuracy + evaluate_pitch_smoothness
- 字段已计算但暂不驱动评分 (无参考音高时 MAE 更可靠, 保留供校准后用)
- 修改文件: `services/features/__init__.py`, `services/features/pitch.py`, `services/scoring/pitch_scorer.py`

### 阶段二：艺术评分重构 (v5.14 核心)

**根因**: v5.13 艺术分 78 vs 78 (零差距)。旧 ArtistryScorer 依赖不可靠的技巧检测器 (颤音FFT/滑音阈值/假声频谱质心)。

**方案**: 从四个可靠维度加权合成 + 声学特征调制:

```
artistry = pitch*0.20 + rhythm*0.25 + breath*0.20 + technique*0.35
           + modulation (RMS dynamic ratio ±6, F0 variation ±4)
```

- 低分演唱因节奏 2.5 和技术 57.5 被自然拉低
- 声学调制提供 ±10 分微调
- 修改文件: `services/scoring/artistry_scorer.py`, `services/score_service.py`, `api/business/audio_analysis.py`

**效果**: Artistry 差距 0.3 → 28.4, Total 差距 24.0 → 27.4

### 专业模式深度测试 (v5.14)

| 音频       | Quick Total | Pro Total      | Pro Rhythm     | Pro Breath    |
| ---------- | ----------- | -------------- | -------------- | ------------- |
| 恋人(高)   | 75.6        | **57.6** | **18.6** | **9.8** |
| 陈奕迅(低) | 45.9        | 50.0           | 2.5            | 51.2          |

**发现**:

- Demucs 分离后 CV=134% 经 is_clean_vocal 映射 + RhythmScorer 额外惩罚后仍跌至 18.6
- SingMOS: 低分演唱 MOS=95.9 > 高分演唱 MOS=73.9 (确认跨域不适用)
- 陈奕迅(低) 无伴奏跳过 Demucs, Quick/Pro 一致性良好

### 已知遗留

| P0 | 专业模式 Demucs 后评分仍偏低, SingMOS 严重跨域 |
| P1 | 气息/音准区分度偏窄, 23参数未校准 |
| P2 | f0节奏路径待恢复, 技巧检测仅3种, 无混响补偿 |

---

## v5.13 — 区分度恢复 + 专业模式修复 (2026-06-03)

### 真实音频测试结果

| 音频         | 总分            | Pitch | Rhythm        | Breath | Tech  | Art   |
| ------------ | --------------- | ----- | ------------- | ------ | ----- | ----- |
| 高分组 (n=4) | **73-75** | 79-81 | 67-77         | 53-66  | 78-84 | 78-80 |
| 低分组 (n=1) | **50.0**  | 75.9  | **2.5** | 51.2   | 57.5  | 78.0  |
| 白噪声       | **0.0**   | 0.0   | 0.0           | 0.0    | 0.0   | 0.0   |

**总分差距 24.0 分。区分度恢复成功。**

### 阶段一：区分度恢复

#### 1. 移除 Sigmoid 拉伸

- v5.12 引入的 Sigmoid 压缩 (低分×0.6, 高分压缩到60) 导致气息分全部 36-43
- 完全删除 Sigmoid 块，回归自然计分
- **效果**: 气息 36-43 → 56-63 (+20pts)
- 修改文件: `services/features/breath.py`

#### 2. 移除 Breath 四个子维度硬上限

- `min(90, score)` ×4 → `max(0, min(100, score))`
- 自然上限 ~95 (通过低加分幅度控制)
- 修改文件: `services/features/breath.py`

#### 3. 移除 Artistry 三个硬上限 + 降低加分系数

- `min(90/85, score)` ×3 → `max(0, min(100, score))`
- 颤音系数 1.0→0.7, 气息表现 +15→+10, 弱唱 +10→+7
- 自然上限落在 90-95 而非 85-90
- 修改文件: `services/scoring/artistry_scorer.py`

#### 4. 动态范围连续映射

- 4 档离散分数 (85/75/65/25) → 连续线性插值
- 同步更新 `EmpiricalThresholds.artistry_dynamic_max` = 92
- 修改文件: `services/scoring/artistry_scorer.py`

### 阶段二：专业模式 Demucs 修复

#### 1. 纯净人声 CV 映射

- 根因: 纯净人声 onset 无伴奏节奏线索, CV 天然偏高 (140%)
- `_cv_to_deviation` 增加 `is_clean_vocal` 分支, 放宽映射断点
- 混合音频: <0.3 专业级 → 纯净人声: <0.5 非常规律
- 修改文件: `services/features/rhythm.py`

#### 2. 完整调用链

- `is_clean_vocal` 参数贯穿: audio_service → audio_features_service → rhythm_analyzer → _cv_to_deviation
- 专业模式自动传递 `is_separated=True`
- 修改文件: `services/audio_features_service.py`, `services/audio_service.py`

#### 3. f0 节奏路径备份

- f0 路径发现回归 (恢复后节奏归零), 暂保持 `f0=None`
- 留到校准验证后启用

### 已知遗留问题

| 优先级 | 问题               | 测试数据                      |
| ------ | ------------------ | ----------------------------- |
| P0     | 艺术评分无区分力   | 高分78.0 vs 低分78.0 (零差距) |
| P1     | 气息区分度偏窄     | 高分53-66 vs 低分51 (5-15分)  |
| P1     | 音准区分度偏窄     | 高分79-81 vs 低分76 (3-5分)   |
| P1     | 23个经验参数未校准 | 0个 [实验校准]                |

### 尚未完成的优化 (v5.13 计划 Phase 3-7)

**阶段三 — 校准数据集建设 (P0)**: 3×3对照数据集, 校准工具脚本, 优先校准cv断点/breath基线/artistry上限/pitch_break_cents

**阶段四 — DL模型策略 (P1)**: SVQTD 7属性分类器 (需确认权重), TorchCREPE 备选, ECAPA-TDNN 音色分析, VocalCritic 评估

**阶段五 — 鲁棒性增强 (P1)**: 混响补偿 (HPSS+谱减法), 音量维度独立 (六维评分), f0节奏路径恢复, Feature Flag 机制, 历史数据迁移

**阶段六/七 — 测试+文档**: 区分度验证测试, 鲁棒性测试, CALIBRATION.md, DL_MODELS.md

---

## v5.12 — 安全加固 + 评分统一 + 算法校准 + DL模型清理 (2026-06-03)

### 阶段一：安全加固 & 代码清理 (P0)

#### 1. 移除 debug=True 安全风险

- `debug=True` 改为环境变量 `FLASK_DEBUG=1` 控制
- 修改文件: `web_app.py`

#### 2. 移除 CREPE 僵尸代码 (~300行)

- 删除 `CREPEPitchExtractor`、`SpeechBrainMOSPredictor`、`EnhancedDLAssessor` 三个类
- 保留 `ScoreCalibrator` 供单元测试使用
- 修改文件: `services/dl_services/enhanced_dl_assessor.py` (740→236行), `__init__.py`, `dl_manager.py`, `diagnostic.py`
- 修复测试文件: `tests/tools/test_evaluation_optimization.py`

#### 3. 修复非人声假评分

- `_build_non_voice_result`: 所有维度分数归零，不再返回无意义的假分数（原来 pitch=10-30, rhythm=20）
- 新增 `is_voice=False` 和 `warning` 字段到 API 响应
- 修改文件: `api/business/audio_analysis.py`

#### 4. 其他清理

- 清理 22 个 `__pycache__` 目录
- 413 上传限制错误提示改为中文友好信息
- 修改文件: `api/errors.py`

### 阶段二：评分路径统一 (P0)

#### 1. 移除 Legacy 对比评分路径

- `/api/compare` 端点不再调用 `analyze_and_score()` 做冗余绝对评分 + `calculate_comparison()` 做Legacy对比
- DTW `dimensions` 字段直接构建 `comparison` 响应
- 移除 `calculate_comparison`、`generate_comparison_suggestions` 导出
- 修改文件: `api/routes/upload.py`, `api/business/__init__.py`

### 阶段三：算法鲁棒性修复 (P1)

#### 1. 气息评分天花板修复

- 四个子维度基线从 60 统一降为 40
- 非艺术波动惩罚加倍: `*30` → `*60`，触发阈值 0.35→0.25
- 加分项设上限: 长音+5max, 换气+3max
- Sigmoid 拉伸: 低分(<=50)压缩 0.6x, 高分自然延伸
- 修改文件: `services/features/breath.py`

#### 2. 艺术评分子维度校准

- 颤音: 基础分 30→25, 次数加分 1.5x→1.0x, 上限 100→90
- 动态: 基线 30→25
- 技巧多样性: 3种技巧 90→80, 2种 75→70, 1种 65→60, 上限 100→85
- 气息表现力: 基线 30→25, 各加分项减半, 上限 100→85
- 修改文件: `services/scoring/artistry_scorer.py`

#### 3. SingMOS 校准修正

- DL 融合权重 0.4→0.15, boost 系数 0.3→0.15
- 添加跨域应用警告注释
- 修改文件: `services/score_service.py`

#### 4. torchaudio 补丁副作用修复

- 仅在 `sox_effects` 不可用时应用兼容补丁，不再无条件全局覆盖
- 修改文件: `services/dl_services/dl_quality_assessor.py`

### 阶段四：深度学习模型清理 (P1)

#### 1. 移除 Wav2Vec2 情绪模型

- 模型 ~300MB, 基于 IEMOCAP 英语语音训练, 用于中文唱歌=3x跨域
- 仅贡献 +3~5 分, Phased 3 降至 +3, 现完全移除
- 情绪分析统一使用启发式方法
- 修改文件: `model_manager.py` (472→156行)

#### 2. 移除 wvmos (Wav2Vec2-MOS)

- 评估电信语音质量, 不是唱歌质量 = 二次跨域
- 删除 `Wav2Vec2MOSPredictor` 类
- `DLQualityAssessor` 简化为 SingMOS-only
- 修改文件: `services/dl_services/dl_quality_assessor.py`

### 阶段五：魔法数字集中化 (P1)

- `EmpiricalThresholds` 新增 14 个字段，覆盖气息/节奏/艺术表现维度
- 所有硬编码常量标注来源: [理论依据]/[实验校准]/[经验估计]/[论文参考]
- 修改文件: `services/scoring_config.py`

### 阶段六：测试覆盖扩展 (P2)

- 新增 `tests/integration/test_full_pipeline.py` (6个测试用例)
- 覆盖: 白噪声检测/人声评分范围/快速vs专业一致性/非人声零分/响应字段完整性/气息区分度
- 修改文件: `tests/unit/test_scorers.py` (v5.12 艺术评分阈值更新)

### 阶段七：前端质量修复 (P2)

- `_get_level_info`: 修复 score=100 边界情况, 新增 score<0 处理
- `displayVoiceQualityWarning`: 使用 API `warning` 字段, 非人声隐藏雷达图
- 修改文件: `services/score_service.py`, `web/static/js/analysis.js`

### 已知问题 (v5.12 测试发现)

#### 专业模式 Demucs 分离后评分异常

- **症状**: 恋人.mp3 专业模式总分 54.1 vs 快速模式 71.1
- **节奏 0.0 分**: 分离后 CV=140%，onset 间隔分析失真
- **气息 4.1 分**: 分离后人声 HNR 可能异常
- **用时 305s**: 专业模式仍包含 SingMOS + Demucs 全流程
- **待修复**: 排查 Demucs 分离后特征提取管线

### 测试结果

- 单元测试: **79/79 通过**
- 快速模式: 3首真实音频分数区分度良好 (68-71分, 气息36-43)
- 专业模式: 存在上述已知问题

---

## v5.11 - 评分区分度修复 + 人声分离管线修复 (2026-06-02)

### 核心问题

评分系统对"难听"和"好听"的音频几乎无区分度。经全链路代码审查，发现**两层分数压缩机制叠加 + 维度评分器内部高 floor/浅斜率**，导致快速模式分数被锁死在 55-92 区间。

### 修复内容

#### 1. 移除快速模式分数压缩 (Step 0)

**问题**: `_apply_quick_mode_smoothing()` 将分数强制映射到 60-90，ScoreCalibrator 的 REFERENCE_MAPPING 将 (0,50)→(55,65)。

**修复**:

- 删除 `_apply_quick_mode_smoothing()` 函数及其调用 (~160行)
- 删除 `_create_quick_mode_config()` — 快速/专业模式使用相同评分标准
- 清理未使用的 `score_calibrator` / `enhanced_assessor` 导入
- **修改文件**: `api/business/audio_analysis.py`

#### 2. 修复 Demucs 人声分离管线 (Step 0.5)

**问题**: Demucs 正常执行并输出文件 (`web/static/htdemucs_ft/vocals.mp3`)，但 `_find_separated_files` 因 `--filename` 参数导致输出扁平化，在错误目录查找文件，最终静默回退到原始混合音频。

**修复**:

- `_find_separated_files`: 3个候选位置查找 (flat/subdir/direct)，返回文件系统绝对路径
- `_preprocess_for_scoring`: 兼容新旧路径格式
- **修改文件**: `services/separation_service.py`, `services/audio_service.py`

**效果**: 专业模式下分离成功，Breath 从 100 (假) 降至 70 (真)，Technique 降 6-9 分。

#### 3. 移除评分硬底限 + 降低基线 (Step 1-2)

**问题**: 气息硬底限 max(50,...)、艺术子维度基线 50-60、技术 HNR/CPP floor 30-50、音准/节奏"待改进"起始分 70 且斜率过缓。

**修复**:

- `BreathThresholds.get_score()`: `max(50,...)` → `max(0,...)`, 斜率 50→60
- `PitchThresholds.get_score()`: 待改进斜率 0.5→0.85 (MAE=160音分→0分)
- `RhythmThresholds.get_score()`: 斜率 100→120
- `ArtistryScorer`: 4处子维度基线 60→30, 55→25, 50→25
- `TechniqueScorer`: 4处 HNR/CPP floor 降低 60% (40→15, 30→10, 50→20, 30→10)
- **修改文件**: `services/scoring_config.py`, `services/scoring/artistry_scorer.py`, `services/scoring/technique_scorer.py`

#### 4. 节奏评分系统性修复 (Step 3-6)

**问题**: 节奏维度在所有文件上得分 0-6，拉低总分 ~14 分。五重问题叠加：

| 子问题                                        | 修复                                        |
| --------------------------------------------- | ------------------------------------------- |
| CV→deviation 映射将人声CV当做器乐评分        | 重新校准6段映射，CV=0.7→dev=0.40 (原 0.70) |
| 16kHz onset检测精度差                         | 内部重采样到 22050Hz                        |
| 响度归一化 (target_rms=0.05) 压平动态         | 节奏分析使用原始未归一化音频                |
| 长音频全程CV被段落密度差异污染 (276s CV=1.33) | 60s窗口分段分析，取中位数CV                 |
| 不规则惩罚阈值 0.3 对声乐太严格               | 0.3→0.5，四级分级惩罚                      |

**修改文件**: `services/features/rhythm.py`, `services/scoring/rhythm_scorer.py`, `services/audio_features_service.py`, `services/scoring_config.py`

#### 5. 新增级联惩罚 + 优化人声质量惩罚 (Step 7-8)

- 人声质量三层分级惩罚: vq<30 cap 40, vq<50 penalty 35, vq<65 小幅惩罚
- 多维度联合极差惩罚: 3维<40 cap 55, 4维<40 cap 40
- 等级区间更新匹配新分数分布: (88,100)专业级 → (0,25)待改进
- **修改文件**: `services/score_service.py`

### 效果对比

| 音频           | 修改前 | 修改后         | 提升  |
| -------------- | ------ | -------------- | ----- |
| 清唱 (obj_...) | 70.7   | **82.9** | +12.2 |
| 恋人           | 70.9   | **86.4** | +15.5 |
| 手写的从前     | 73.4   | **83.0** | +9.6  |

| 维度               | 修改前       | 修改后       |
| ------------------ | ------------ | ------------ |
| Rhythm             | 0-6 (全损)   | 67-77 (正常) |
| Breath (分离后)    | 100 (假)     | 70-93 (真)   |
| Technique (分离后) | 78-84 (偏高) | 72-76 (合理) |

### 测试

- 79/79 单元测试通过
- 6/6 集成测试通过

---

## v5.9 - 逐句评分优化 (2026-05-10)

### 问题修复

#### 逐句评分分数偏低问题

**问题描述**：专业评估模式下逐句评分分数普遍偏低，尤其是音准和情绪维度。

**根因分析**：

1. 音准评分使用相对标准差阈值过严，把"音高变化幅度"误判为"音准差"
2. 演唱中的转音、滑音会导致高 relative_std（30%-50%），这是正常的音乐表达
3. 节奏评分对稳定节奏惩罚
4. 气息和情绪评分最低分过低

**解决方案**：

##### 1. 音准评分阈值大幅放宽

```python
# 修复前
PITCH_THRESHOLD_EXCELLENT = 0.08   # 8%
PITCH_THRESHOLD_GOOD = 0.20        # 20%
PITCH_MIN_SCORE = 50.0

# 修复后
PITCH_THRESHOLD_EXCELLENT = 0.12   # 12%
PITCH_THRESHOLD_GOOD = 0.30        # 30%
PITCH_THRESHOLD_FAIR = 0.50        # 50%
PITCH_MIN_SCORE = 60.0             # 最低分提升到60
```

##### 2. 节奏评分优化

```python
RHYTHM_STABLE_MIN = 75.0  # 稳定节奏最低75分
```

##### 3. 气息评分优化

```python
BREATH_THRESHOLD_EXCELLENT = 0.10  # 从8%放宽到10%
BREATH_MIN_SCORE = 60.0            # 最低分提升到60
```

##### 4. 情绪评分重构

```python
EMOTION_BASE_SCORE = 70.0          # 基准分提升到70
EMOTION_MIN_SCORE = 60.0           # 最低分提升到60
```

##### 5. 音量评分优化

```python
VOLUME_MIN_SCORE = 60.0            # 最低分提升到60
```

### 效果对比

| 音频       | 维度 | 修复前 | 第一轮 | 第二轮         | 总改进 |
| ---------- | ---- | ------ | ------ | -------------- | ------ |
| 恋人       | 音准 | 66.1   | 73.2   | **79.9** | +13.8  |
| 恋人       | 情绪 | 69.2   | 69.8   | **73.9** | +4.7   |
| 恋人       | 总分 | 78.4   | 81.7   | **84.4** | +6.0   |
| 手写的从前 | 音准 | 56.2   | 63.3   | **74.0** | +17.8  |
| 手写的从前 | 情绪 | 61.9   | 68.7   | **73.1** | +11.2  |
| 手写的从前 | 总分 | 73.2   | 77.6   | **81.7** | +8.5   |

### 修改文件

- `services/phrase_service.py` - 评分算法优化

### 测试验证

```
单元测试: 79/79 通过
真实音频测试: 恋人.mp3, 手写的从前.mp3 验证通过
```

---

## v5.8 - P0问题修复 (2026-05-10)

### Bug修复

#### 1. 对比分析API 415错误

- **问题**: FormData方式上传时，直接访问 `request.json` 触发Flask的JSON解析，由于Content-Type不是application/json，抛出415错误
- **解决方案**: 使用 `request.is_json` 检查后再调用 `request.get_json(silent=True)`
- **修改文件**: `api/routes/upload.py`

```python
# 修复前
if request.json and isinstance(request.json, dict):
    style = request.json.get('style', 'pop')

# 修复后
style = 'pop'
if request.is_json:
    try:
        json_data = request.get_json(silent=True)
        if json_data and isinstance(json_data, dict):
            style = json_data.get('style', 'pop')
    except Exception:
        pass
elif request.form:
    style = request.form.get('style', 'pop')
```

#### 2. 首页录音安全上下文判断修复

- **问题**: 原条件 `!window.isSecureContext && hostname !== 'localhost'` 逻辑有误，某些浏览器在localhost上 `isSecureContext` 可能为false
- **解决方案**: 显式检查 hostname 是否为 localhost/127.0.0.1/[::1]
- **修改文件**: `web/static/js/modules/recording.js`

```javascript
const isLocalhost = location.hostname === 'localhost' || location.hostname === '127.0.0.1' || location.hostname === '[::1]';
const isSecure = window.isSecureContext || isLocalhost;
if (!isSecure) {
    showToast('录音功能需要 HTTPS 或 localhost 环境', 'error');
}
```

#### 3. 实时录音模块初始化修复

- **问题**: `RealtimeCompare` 构造函数参数未设置默认值，`init()` 方法缺少错误处理和readyState检查
- **解决方案**: 添加默认参数，添加readyState检查和错误事件监听
- **修改文件**: `web/static/js/modules/realtime-compare.js`, `web/static/js/compare.js`

```javascript
// 构造函数添加默认参数
constructor(standardAudioData = {}) { ... }

// init() 添加readyState检查
async init(audioElement, standardUrl) {
    // ...
    await new Promise((resolve, reject) => {
        this.standardAudioElement.addEventListener('loadedmetadata', resolve, { once: true });
        this.standardAudioElement.addEventListener('error', reject, { once: true });
        if (this.standardAudioElement.readyState >= 1) {
            resolve();
        }
    });
}
```

### 测试验证

```
单元测试: 43/43 通过
API测试:
- Upload API: Score 86.3 (正常)
- Compare API: Score 94.1, Pitch Match 100%, Rhythm Match 100% (正常)
```

---

## v5.3.1 - Flask 3.x JSON序列化修复 (2026-04-29)

### Bug修复

#### NumPy类型JSON序列化问题

- **问题**: Flask 3.x 不支持 `JSON_ENCODER` 配置，导致 numpy 类型无法序列化
- **错误**: `TypeError: Object of type float32 is not JSON serializable`
- **解决方案**: 创建 `NumpyJSONProvider` 继承 `DefaultJSONProvider`
- **修改文件**: `api/__init__.py`

```python
class NumpyJSONProvider(DefaultJSONProvider):
    """自定义 JSON 提供器，支持 numpy 类型"""
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        return super().default(obj)
```

#### 对比分析API参数名修正

- **问题**: 前端使用 `teacher_audio/student_audio`，后端期望 `file/standard_file`
- **解决方案**: 统一使用 `file` (用户音频) + `standard_file` (标准音频)

### 测试验证

```
API测试结果:
- Upload API: Score 86.3 (正常)
- Compare API: Score 88.0, Pitch Match 100%, Rhythm Match 70% (正常)
- Health Check: 所有检查项通过
```

---

## v5.3 - 对比分析重构 (2026-04-29)

### 新功能

#### 独立对比分析页面

- **独立页面**: 对比分析从首页 tab 改为独立页面 `/compare.html`
- **三步流程**: 导入标准音频 → 选择模式 → 查看结果
- **两种评估模式**:
  - **上传模式**: 导入用户音频与标准音频对比
  - **实时录音模式**: 类似全民K歌的实时反馈体验

#### 实时音高检测 (前端)

- **YIN 算法**: 前端实时音高检测，无需后端处理
- **实时音分偏差**: 显示当前音高与标准音高的偏差（+/- 音分）
- **实时调整建议**: "略高，请降低一点" / "偏低，需要提高"
- **实时评分**: 录音过程中实时更新评分
- **音高曲线对比**: Canvas 绘制标准 vs 用户音高曲线

#### 基于标准音频的相对评分

- **音准匹配率**: 用户音高与标准音高的匹配程度 (0-100%)
- **节奏匹配率**: 基于能量包络相似度计算 (0-100%)
- **综合评分**: 音准 60% + 节奏 40% 权重
- **等级评定**: 优秀/良好/中等/及格/需改进
- **诊断建议**: 自动生成改进方向建议

### API 更新

#### `/api/compare` 接口增强

- 支持 FormData 上传 (file + standard_file)
- 支持 JSON 方式 (filepath 参数)
- 返回相对评分结果

```python
# FormData 方式
POST /api/compare
Content-Type: multipart/form-data
- file: 用户音频
- standard_file: 标准音频

# 返回
{
  "success": true,
  "data": {
    "score": 85,
    "level": "良好",
    "pitch_match_rate": 88.5,
    "rhythm_match_rate": 82.3,
    "avg_cents_error": 15.2,
    "diagnosis": ["音准表现优秀...", "整体偏高..."]
  }
}
```

### 新增文件

| 文件                                          | 说明             |
| --------------------------------------------- | ---------------- |
| `web/static/compare.html`                   | 独立对比分析页面 |
| `web/static/js/compare.js`                  | 对比页面主逻辑   |
| `web/static/js/modules/pitch-detector.js`   | YIN 音高检测算法 |
| `web/static/js/modules/realtime-compare.js` | 实时录音对比模块 |

### 修改文件

| 文件                                 | 变更                                    |
| ------------------------------------ | --------------------------------------- |
| `web/static/index.html`            | 对比分析 tab 改为页面链接               |
| `api/routes/upload.py`             | `/compare` 接口支持 FormData          |
| `api/business/audio_comparison.py` | 新增`calculate_relative_score` 等函数 |

### 技术亮点

- **前端 YIN 算法**: 纯 JavaScript 实现音高检测
- **实时反馈**: requestAnimationFrame 驱动的实时 UI 更新
- **Web Audio API**: AudioContext + AnalyserNode + MediaRecorder
- **音分计算**: 1200 * log2(freq2/freq1) 精确计算音分偏差

---

## v5.0 - 深度学习集成 & 双评估模式 (2026-04-22)

### 新功能

#### 双评估模式

- **快速评估** (默认): 约30秒完成，适合日常练习反馈

  - 基础五维评分 (音量/音准/节奏/气息/情绪)
  - 人声质量检测
  - 基础建议生成
- **专业评估**: 约2-5分钟，适合详细问题诊断

  - 完整五维评分 + 详细诊断
  - 逐句评分 (每句独立评分和建议)
  - 音色分析 (明亮度/厚度/鼻音/气声)
  - 可视化图表 (频谱图/音高轨迹/能量曲线)

#### API 更新

- `/api/upload` 接口新增 `mode` 参数
  - `mode=quick`: 快速评估 (默认)
  - `mode=professional`: 专业评估

### 性能优化

#### 逐句评分多线程并行

- 使用 `ThreadPoolExecutor` 并行处理多个乐句
- 预计算 f0 数据复用，避免重复计算
- 逐句评分速度提升 2-3 倍

#### 评分算法优化

- 音量评分: 优化归一化范围 (0.02-0.15 RMS)
- 音准评分: 使用相对标准差，合理波动不惩罚
- 节奏评分: 基于变异系数评估节奏感
- 气息评分: 基于相对变化率评估稳定性
- 分数范围: 60-90 分 (更合理的分布)

### 代码变更

#### 新增文件

- `CHANGELOG.md` - 版本变更记录

#### 修改文件

- `api/routes/upload.py` - 添加 mode 参数支持
- `api/business/audio_analysis.py` - 实现快速/专业模式分支
- `services/phrase_service.py` - 多线程并行评分 + 评分算法优化
- `README.md` - 更新功能说明和 API 文档
- `docs/DEEP_LEARNING_PLAN.md` - 添加性能优化策略

### 兼容性

- 向后兼容: 不传 `mode` 参数时默认使用快速模式
- 前端需要更新以支持模式选择 UI

---

## v4.0 - 评分系统 V4 (2026-04-20)

### 改进

- 自适应评分系统
- 风格识别集成
- 深度学习质量评估 (MOS 分数)

---

## v3.6 - 安全加固 (2026-04-18)

### 改进

- 路径遍历防护
- XSS 防护
- 文件名安全处理
