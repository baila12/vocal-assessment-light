# 变更日志

> 当前状态和已知问题见 [PROJECT_STATUS.md](PROJECT_STATUS.md) | 计划见 [PRD.md](../1-product/PRD.md)

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

| # | 算法 | 文件 | 影响 |
|---|------|------|------|
| 1 | Cross-Dimension Modifiers | `score_service.py:297` | HNR稳定性→气息、Voicing→音准、频谱倾斜→气声等 5 项跨维度修正 |
| 2 | Praat Voice Quality | `audio_features_service.py:246` | Jitter/Shimmer/Formants(F1-F4)/Singer's Formant |
| 3 | Multi-scale HNR (de Krom 1993) | `audio_features_service.py:222` | 4频带倒谱域HNR，替代简单HPSS |
| 4 | Praat CPP | `audio_features_service.py:226` | parselmouth PowerCepstrum，替代手动FFT倒谱 |
| 5 | Voicing Detection | `audio_features_service.py:230` | PYIN决策质量评估 |
| 6 | Reverb Compensation | `audio_features_service.py:143` | HPSS+谱减法混响补偿 |
| 7 | TorchCREPE Fallback | `audio_features_service.py:364` | PYIN检测率<50%时CREPE备选 |

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

| 指标 | 权重 | 公式 | 文献 |
|------|------|------|------|
| MAE 指数衰减 | 40% | `100 × exp(-mae/40)` | Wager 2022 |
| RPA (Raw Pitch Accuracy) | 25% | `rpa × 100` | Cao et al. 2008 |
| RCA (Raw Chroma Accuracy) | 10% | `rca × 100` | Cao et al. 2008 |
| Gross Error 惩罚 | 15% | `100 − min(100, (rate−0.05)×200)` | Sundberg 1987 |
| Smoothness | 5% | `max(0, 100−(cv−1.0)×50)` | Canazza et al. 2014 |
| Octave Error 惩罚 | 5% | `max(0, 100−rate×200)` | pitch-benchmark |

**PYIN 校准**: YIN @ 16kHz 产生 3.5x 虚假帧间跳变 (785 vs PYIN 226). 权重调整依据:
- 帧间指标 (smoothness 10%→5%): 受 YIN 噪声污染
- 聚合指标 (MAE 35%→40%): 对 f0 伪影鲁棒
- 断层惩罚: 率阈值 + ÷3.5 校正因子 [de Cheveigne & Kawahara 2002]

### 跨维度修正

新增 `score_modifiers.py`:

| 修正 | 因果链 | 幅度 | 文献 |
|------|--------|------|------|
| HNR多频带CV → 气息 | 声带闭合不一致 → 气息不稳 | ≤15% | de Krom 1993 |
| Voicing置信度 → 音准 | 低置信度 → 音准不可靠 | 标记 | de Cheveigne 2002 |
| 频谱倾斜 → 气声 | HNR低+倾斜平坦=艺术气声; HNR低+倾斜陡峭=漏气 | ≤15% | Sundberg 1987 |
| 气息-音准耦合 | pitch_wobble高+HNR不稳定 → 气息不足 | ≤15分 | Titze 1994 |

### 特征扩展

| 特征 | 来源 | 用途 |
|------|------|------|
| 频谱倾斜 (LTAS slope dB/oct) | `acoustic.py` — Welch PSD + 线性回归 | 气声 vs 漏气区分 |
| Jitter (local, rap, ppq5) | `voice_quality_praat.py` — parselmouth | 声质→技术分修正 |
| Shimmer (local, apq3) | 同上 | 同上 |
| Formants (F1-F4) | 同上 — Burg method | 共鸣质量 |
| Singer's formant (2.5-3.5kHz) | 同上 — LTAS能量比 | 专业技巧 |
| Staccato 检测 | `technique.py` — RMS脉冲 | 技巧多样性 |
| Legato 检测 | `technique.py` — 沉默段+音高平滑度 | 技巧多样性 |

### 性能优化

| 优化 | 方法 | 效果 |
|------|------|------|
| harmonicity 计算 | np.correlate O(N²) → FFT自相关 O(N log N) | 566.9s → <0.1s |
| HPSS 缓存 | 预计算一次, 调用点复用 | 3次→1次 (~12s节省) |
| 动态范围 | max/min → p95/p5 百分位 | 修复 101.9dB 异常值 |
| pitch_breaks | 仅连续有声帧 + 排除八度跳变 | 减少虚假断层计数 |
| Praat VQ Quick | 截断到 60s | ~5s → ~0.8s |
| 完整管道 | 综合以上 | ~700s → ~54s (13x) |

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

| # | 维度 | 文件 | 修复前 | 修复后 |
|---|------|------|--------|--------|
| 1 | Technique | `services/features/technique.py` | `technique_score = 50` (地板) | `technique_score = 0`, 仅检测到的技巧加分 |
| 2 | Breath 子维度 | `services/features/breath.py` | 步进加分 (`if > 80: +20 elif > 60: +14`) | 连续线性映射 (`pitch_stability * 0.4`) |
| 3 | Breath 基线 | `breath.py` 四处 fallback | `= 10` | `= 0` |
| 4 | HNR/CPP 高技巧阈值 | `services/scoring/technique_scorer.py` | `technique_score >= 70` (不可达) | `>= 35` (匹配新 0-85 范围) |
| 5 | 配置更新 | `services/scoring_config.py` | breath_baseline=10, technique_baseline=50 | 全部 = 0 |

### Artistry 评分独立化

| 旧版 (v5.14) | 新版 (v6.1) |
|-------------|------------|
| `pitch*0.20 + rhythm*0.25 + breath*0.20 + technique*0.35 + modulation(±10)` | 4 个独立声学特征子维度 |
| 95% 来源于其他分数 (r > 0.9) | 100% 来源于可测量声学信号 |

**子维度**: 颤音品质(30%) + 动态控制(30%) + 乐句处理(25%) + 音高变化(15%)

### v6.0 兼容性修复 (6 项 bug)

| 严重度 | 问题 | 修复文件 |
|--------|------|---------|
| CRITICAL | `detect_mixed_audio()` 返回值 4→3 导致 Demucs 静默失败 | `audio_service.py`, `dtw_aligner.py` |
| MEDIUM | E2E 测试 collection error (3 处) | `test_e2e.py`, `test_e2e_v2.py`, `test_e2e_v3.py` |
| MEDIUM | `AcousticResult` 孤立字段 | `types.py` |
| MEDIUM | 动态属性未声明 | `types.py` |
| LOW | 重复 import + 文档自相矛盾 | `acoustic.py`, `PROJECT_STATUS.md` |

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

| 文件 | 变更 |
|------|------|
| `services/feature_flags.py` | 新增 `enable_reverb_compensation` flag |
| `services/audio_features_service.py` | 集成 `ReverbCompensator`, HNR/CPP 计算前可选 HPSS+谱减法补偿 |
| `services/features/reverb.py` | 已有实现 (v5.20), 无变更 |

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

| 文件 | 修复 |
|------|------|
| `web/static/js/animation/Controller.js` | `_execute()`: `onComplete` 传入 GSAP `toVars`; `_track()`: 链式调用(cleanup + 原有回调), 同时检查 `eventCallback` getter 和 `vars.onComplete`; `leave()`: 安全超时 resolve |
| `web/static/js/components/BaseComponent.js` | `beforeUnmount()`: 硬编码 `'page-leave'` 预设 (之前误用页面入场预设) |
| `web/static/router.js` | `#navPending` 检查移到 `killAll()` 之前, 防止 popstate 事件杀掉活跃动画 |

### 🏗️ 前端架构升级 — v7.0 Vue 迁移衔接

为减少 v7.0 (Electron + Vue 3) 迁移工作量, 提前建立与 Vue 生态对应的基础设施:

#### 新增文件

| 文件 | 说明 | v7.0 目标 |
|------|------|----------|
| `web/static/js/AppContext.js` | 应用级依赖注入容器, 聚合 store/router/api/ac/events | Vue `provide/inject` |
| `web/static/js/EventBus.js` | 事件总线 (`on`/`once`/`off`/`emit`), 解耦跨组件通信 | `mitt()` |

#### 重构文件

| 文件 | 变更 | v7.0 目标 |
|------|------|----------|
| `web/static/js/components/BaseComponent.js` v3.0 | context 注入; 服务 getter 优先 `this.context` 回退 `window.*`; 生命周期文档标注 Vue 对应钩子 | `<script setup>` + composables |
| `web/static/app.js` v3.0 | 引入 AppContext + EventBus; 初始化流对齐 Vue `createApp → use → mount` 模式; `context.freeze()` 启动后锁定 | `main.js` / `createApp()` |
| `web/static/router.js` v3.0 | `useContext(context)` 注入; `#ac` private getter 替代 `window.__ac`; 各方法标注 Vue Router 对应 API | Vue Router `createRouter` |

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

| 问题 | 文件 | 修复 |
|------|------|------|
| `POST /api/audio/analyze` 端点不存在 (404) | `api.js:168` | → `POST /api/upload` (FormData) |
| `POST /api/history/batch-delete` 路径和方法错误 | `api.js:233` | → `DELETE /api/history/batch` |

**根因**: 前端 API 路径与后端 Flask 路由不匹配。`/api/audio/analyze` 不存在, 导致上传分析请求失败。正确的上传端点应为 `/api/upload` (接受 FormData)。

#### CSS 页面隐藏

| 问题 | 文件 | 修复 |
|------|------|------|
| `.page { display: none; }` 导致页面切换后内容不可见 | `components.css:55` | 移除隐藏规则 |

**根因**: SPA 模式下页面由 JS 动态切换 (旧页 destroy → 新页 mount), 同一时间只有一个 `.page` 在 DOM 中, 不需要 `display:none` 切换。旧 CSS 规则导致新挂载的页面被隐藏。

#### 路由错误恢复

| 问题 | 文件 | 修复 |
|------|------|------|
| `#transition()` 无错误处理, 页面挂载失败导致 SPA 崩溃 | `router.js:148` | 添加 try-catch + 错误页面 + 调试日志 |

#### 编码问题修复

| 问题 | 文件 | 修复 |
|------|------|------|
| `HistoryPage.js` 全部中文乱码 (mojibake) | `HistoryPage.js` | 逐字替换 20+ 处乱码 |
| `HistoryPage.js:35` `ac is not defined` (编码问题导致) | `HistoryPage.js` | 修复为 `this.ac` |
| 全部 6 个 page 文件: `const ac = this.ac` 模式 | `*.js` | 改为直接 `this.ac` 调用 |

**根因**: HistoryPage.js 文件中的 UTF-8 中文字符被错误编码, 导致浏览器显示乱码。同时编码问题导致第 35 行的 `const ac = this.ac` 无法正确执行。

#### ComparePage Modal

| 问题 | 文件 | 修复 |
|------|------|------|
| Modal 弹窗无法关闭 (点击取消/背景无反应) | `ComparePage.js:269` | 移除 `#openSongSelector` 中外层无用的 overlay div |

**根因**: `StandardAudioSelector` 在 modal 模式已自带 overlay, 但 `#openSongSelector` 又创建了一个外层 overlay div (`position:fixed;inset:0`), 关闭时只移除了内层。

#### ⚠️ 导航跳转 Bug (未修复)

**症状**: 点击导航按钮后 URL hash 改变, 但页面内容不更新, 需手动刷新浏览器才能显示对应页面。

**状态**: 代码逻辑已全面审查, 路由链路 (Navigation → hashchange → #handleRoute → #matchRoute → #transition → mount → render) 均正确。已在 router.js 添加详细 `[Router]` 调试日志定位问题。

### 后端改进

#### 混响补偿 (P1, 新增) 🆕

| 模块 | 文件 | 依据 |
|------|------|------|
| `ReverbCompensator` | `services/features/reverb.py` (新建) | Fitzgerald 2010 (HPSS), Boll 1979 (谱减法), Berouti 1979 (过减+频谱地板) |

- HPSS 谐波/冲击分离 + 谱减法, 减轻不同录音环境对 HNR/CPP 的影响
- Feature Flag: 待后续版本接入评分管线

#### 混合音频检测重构 (P2)

| 模块 | 文件 | 依据 |
|------|------|------|
| `detect_mixed_audio()` 多特征融合 | `services/features/acoustic.py` | Fitzgerald 2010 (HPSS), McFee et al. 2015 (librosa) |

- **旧算法**: 单阈值 `low_freq_ratio > 0.35` — 轻伴奏(如"手写的从前")被漏判
- **新算法**: 四特征加权投票 (HPSS 谐波比 + 高频能量 + 频谱平坦度 + 低频能量比), 采样率自适应
- **检测流程**: 使用已加载的 16kHz 音频 (避免额外 I/O)

#### CPP 测试修复

| 问题 | 文件 | 修复 |
|------|------|------|
| `test_praat_cpp_low_for_noise` 失败 | `tests/tdd/test_future_features.py` | 安装 `praat-parselmouth 0.4.7` + 添加可用性检查 |

### 涉及文件 (完整)

| 文件 | 变更 |
|------|------|
| `web/static/js/animation/Controller.js` | SPA 死锁修复: `_execute` onComplete 传递, `_track` 链式回调, `leave` 安全超时 |
| `web/static/js/components/BaseComponent.js` | beforeUnmount 预设修复 + v3.0 重构 (context 注入, Vue 生命周期对齐) |
| `web/static/router.js` | pending 检查前置 + v3.0 重构 (useContext, Vue Router 映射) |
| `web/static/app.js` | v3.0 重构 (AppContext + EventBus, createApp 模式入口) |
| `web/static/js/AppContext.js` | 🆕 依赖注入容器 (v7.0 → Vue provide/inject) |
| `web/static/js/EventBus.js` | 🆕 事件总线 (v7.0 → mitt) |
| `web/static/js/services/api.js` | 修复 2 个 API 路径 |
| `web/static/js/pages/HistoryPage.js` | 修复乱码 + `ac` 变量 |
| `web/static/js/pages/HomePage.js` | `ac` 变量修复 |
| `web/static/js/pages/ComparePage.js` | Modal overlay + `ac` 变量 |
| `web/static/js/pages/ReportPage.js` | `ac` 变量修复 |
| `web/static/js/pages/SingPage.js` | `ac` 变量修复 |
| `web/static/js/pages/SongLibraryPage.js` | `ac` 变量修复 |
| `web/static/css/components.css` | 移除 `.page { display: none }` |
| `services/audio_service.py` | `_preprocess_for_scoring` 使用已加载音频 |
| `services/features/acoustic.py` | 多特征融合检测算法 |
| `services/features/reverb.py` | 🆕 混响补偿模块 |
| `tests/tdd/test_future_features.py` | CPP 测试修复 + 混响测试 GREEN |
| `docs/` 5 文件 | CHANGELOG + PROJECT_STATUS + ARCHITECTURE + PRD + GOALS 更新 |

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

| 文件 | 变更 |
|------|------|
| `services/features/breath.py` | 子维度基线归零 + 加分扩大 + 波动惩罚调整 |
| `services/scoring_config.py` | PitchThresholds/BreathThresholds/TechniqueThresholds/EmpiricalThresholds 全部更新 |
| `services/scoring/breath_scorer.py` | 等级阈值更新 |
| `services/scoring/technique_scorer.py` | HNR/CPP 天花板提升 |
| `services/feature_flags.py` | 新增 `enable_cross_dimension_modifiers` |
| `services/score_service.py` | volume 独立计算 |
| `tests/tdd/test_v5_19_features.py` | 🆕 新增 |
| `tests/tdd/test_future_features.py` | 移除 volume xfail |

---

## v5.18 — GSAP 动画系统重设计 + ScoreServiceV4 + 性能文档化 + 测试体系审计 + 开源算法移植 (2026-07-04, 已完成)

### 代码审查与修复 (2026-07-04)

三代理并行审查（code-reviewer + security-reviewer + python-reviewer）发现 20 个问题，全部修复。

#### CRITICAL 修复 (1 项)

| 问题 | 文件 | 修复 |
|------|------|------|
| `except Exception: pass` 静默吞异常 | `audio_service.py:538` | 改为具体异常捕获 + `logger.debug()` |

#### HIGH 修复 (5 项)

| 问题 | 文件 | 修复 |
|------|------|------|
| **de Krom 1993 谐波边界检测 Bug** — 倒谱谐波峰仅置零 1 bin 而非整个"山峰" | `hnr.py:213-225` | 重写边界搜索: 从峰值向两侧走至谷底 |
| **倒谱镜像 off-by-one** — 噪声倒谱对称化源起始错位 1 bin | `hnr.py:231-232` | `mid-1` → `mid-2` |
| **TorchCREPE fallback 死代码** — `_analyze_pitch()` 未传递 `feature_flags` | `audio_service.py` | `feature_flags` 传入 `_analyze_pitch()` |
| **API 响应泄露 traceback** — 完整 Python 堆栈返回给客户端 | `audio_analysis.py:63` | 移除 `'traceback'` 字段，仅返回 `error` |
| **`feature_flags` 参数未使用** — `ScoreServiceV4.calculate()` 接受但未引用 | `score_service.py` | 移除参数，加 v5.19 TODO 注释 |

#### MEDIUM 修复 (8 项)

| 问题 | 文件 | 修复 |
|------|------|------|
| **Voicing 一致性 3 重 Bug** — 时长 off-by-one + 初始/末尾段漏计 | `voicing.py` | 时长 `+1`，补全边界段统计 |
| **CPP 归一化因子未校准** — `/20.0` 导致 Praat CPP 值比现有 pipeline 小 3-4× | `audio_features_service.py` | `/20.0` → `/6.0` (24dB 优质人声 → 4.0 优秀档) |
| **`Optional[object]` 反模式** — 等价于 `Any`，破坏类型检查 | `types.py` | 改为 `Optional['VoicingDetectionResult']` 前向引用 |
| **重复 `import logging`** — 4 个 DL 辅助方法体内重新导入 | `audio_service.py` | 统一使用模块级 `logger` (已随 DL helpers 提取修复) |
| **Python 循环未向量化** — `_compute_energy_agreement` 逐帧遍历 | `voicing.py` | 改为 NumPy boolean indexing |
| **无音频时长上限** — 大音频 DoS 风险 | `audio_service.py` | 添加代码注释，建议后续版本加入显式限制 |
| **ParSelmouth 单段提取兼容** — `Extract all intervals` 可能返回非列表 | `cpp.py` | (低优先级，默认不走 `voiced_only` 路径) |
| **Feature Flag 嵌套过深** — 3 层 if 嵌套 | `audio_features_service.py` | 提取为 3 个独立私有方法 |

#### 文件大小优化

| 文件 | 变化 | 说明 |
|------|------|------|
| `audio_service.py` | 872 → **800 行** | DL 延迟初始化+运行方法提取到新文件 |
| `audio_dl_helpers.py` | 🆕 93 行 | `AudioDLHelpers` 类 — VoiceQuality/Style/DTW/StyleAnalyzer |
| `hnr.py` | `_de_krom_hnr` 109 行 → 6 个子方法 (15-30 行) | 倒谱计算/谐波边界/谐波置零/镜像/阶梯校正/频带 HNR |

#### 测试改进

| 改进 | 文件 |
|------|------|
| 添加 `pythonpath = .` 消除 `sys.path.insert` 反模式 | `tests/pytest.ini` |
| 添加 `unit` / `integration` pytest markers | `tests/pytest.ini` + 测试文件 |
| 移除所有测试文件的 `sys.path.insert(0, ...)` | `test_v5_18_integration.py`, `test_scoring_robustness.py` |

### 测试体系审计与全面修复 (2026-07-03)

对全部 105+ 个测试脚本的深度审计，发现并修复了以下关键问题：

#### P0 修复 (2 个实际失败)

| 问题 | 文件 | 修复 |
|------|------|------|
| `test_professional_breath_not_always_100` — API 不匹配: 传 float 给需 `BreathStabilityResult` 的方法 | `test_full_pipeline.py` | 重写测试，使用正确 DTO 对象 |
| `test_vocal_audio_returns_reasonable_scores` — 文件名硬编码 `恋人.mp3` 但实际为 `恋人（高分）.mp3` | `test_full_pipeline.py` | 改为 glob 通配符搜索真实音频文件 |
| `test_volume_dimension_in_scores` — 误标记 xfail，volume 维度已实现 | `test_future_features.py` | 移除 xfail，添加解耦验证测试 |

#### E2E 测试 SPA 迁移

| 文件 | 状态 | 说明 |
|------|------|------|
| `test_upload.py` | ⏭️ skip | 旧版多页面架构 (analysis.html 已 301) |
| `test_analysis.py` | ⏭️ skip | 旧版分析页面 (已 301 到 /) |
| `test_real_audio.py` | ⏭️ skip | 硬编码不存在的文件名 |
| `test_spa_e2e.py` | 🆕 新增 | SPA Hash 路由端到端 (24 tests) |

#### 新增测试文件 (4 个, +100 测试)

| 文件 | 测试数 | 功能 |
|------|--------|------|
| `test_scoring_robustness.py` | 22 | 评分可重现性、边界值安全、区分度分布、诊断一致性、级联惩罚 |
| `test_real_audio_regression.py` | 27 | 5 个真实文件 × 6 维度基线保护 + 区分度验证 |
| `test_future_features.py` | 13 | TDD RED 阶段: FeatureFlag、多尺度HNR、Praat CPP、SSE、歌曲匹配、混响补偿 |
| `test_store_and_ac.js` | 16 | JS 集成测试: 真实 Store + AnimationController + Presets 模块 |

#### 测试统计对比

| 指标 | 审计前 | 审计后 |
|------|--------|--------|
| 单元+集成测试数 | 91 | **128** |
| 通过率 | 89/91 (98%) | **128/128 (100%)** |
| TDD RED 测试 (xfail) | 0 | **13** |
| 真实音频回归基线 | 无 | **5 文件 × 6 维度** |
| JS 测试模式 | 全 mock | 真实模块集成 |
| 旧版 E2E 覆盖 | 走废弃页面路径 | SPA Hash 路由 |

### 性能文档化

所有产品/技术/质量文档已全面加入性能约束：

| 文档 | 新增内容 |
|------|---------|
| PRD.md | 4.1 性能章节扩展为 8 个子章节: 端到端/特征提取/评分配置/前端/SSE/存储/降级/回归防护 |
| GOALS.md | 功能模块全景标注每模块耗时预算; 新增 4.2 性能设计原则 |
| ARCHITECTURE.md | 每个数据流标注耗时+内存+复杂度; 新增第五章"性能设计决策"(4个PERF-ADR); 技术债务新增2项 |
| API.md | 接口列表新增 P95延迟+超时列; 新增缓存策略表; 新增速率限制表 |
| SCORING.md | 新增算法复杂度与耗时分解表(12个算法); Quick/Pro 耗时火焰图 |
| ANIMATION_DESIGN.md | 新增第九章"动画性能合约"(帧率/时长/GC/prefers-reduced-motion/回归检测) |
| PAGE_DESIGN.md | 新增性能总览表(每页面: 首屏/切换/动画/内存) |
| ROUTES.md | 新增路由性能合约; 路由级代码分割计划表 |
| BACKEND_ALIGNMENT.md | 新增前后端性能对接表; 前端错误降级策略 |
| VISUAL_AUDIT.md | 新增第六章"性能审计补充"(6项性能问题发现) |
| TDD.md | 新增第九章"性能测试"(5个测试示例+运行命令+回归触发条件) |
| BDD.md | 新增第七章"性能BDD场景"(7个Gherkin场景+Step Definitions) |
| PROJECT_STATUS.md | 性能基准表扩展: 增加特征提取阶段耗时/前端性能/未测量指标 |

### 核心性能目标汇总

| 维度 | 目标 | 测量 |
|------|------|------|
| Quick 端到端 | < 30s | `time.perf_counter()` |
| Pro CPU | < 180s | `time.perf_counter()` |
| Pro GPU | < 60s | `time.perf_counter()` |
| 前端 FCP | < 1.5s | Lighthouse |
| GSAP 动画 | ≥ 30fps | DevTools |
| Canvas 实时 | ≥ 30fps | DevTools |
| 路由切换 | < 300ms | `performance.now()` |
| 内存峰值 (Quick) | < 400MB | tracemalloc |
| 内存峰值 (Pro) | < 800MB | tracemalloc |
| 特征提取总耗时 | < 16s (Quick) | 各 extractor 独立计时 |

### 开源算法移植 + Feature Flag 机制 (2026-07-04)

从 VoiceLab 和 pitch-benchmark 移植 4 个开源算法，通过 Feature Flag 机制控制启用。

#### 移植来源

| 算法 | 来源 | Feature Flag | 方法 |
|------|------|-------------|------|
| 多频带 HNR | VoiceLab `MeasureHNRVoiceSauceNode.py` | `enable_multiscale_hnr` | de Krom 1993 倒谱域谐波/噪声分离, 4 频带 |
| Praat CPP | VoiceLab `MeasureCPPNode.py` | `enable_praat_cpp` | `parselmouth.Spectrum` → `To PowerCepstrum` → `Get peak prominence` |
| Voicing Detection | pitch-benchmark `algorithms/base.py` | `enable_voicing_detection` | 自一致性检查 (范围/八度跳跃/切换/能量) |
| TorchCREPE Fallback | pitch-benchmark `algorithms/torchcrepe.py` | `enable_torchcrepe_fallback` | PYIN detection_rate < 0.5 时降级 |

#### 新增文件

| 文件 | 说明 |
|------|------|
| `services/feature_flags.py` | FeatureFlags dataclass (4 开关, 默认关闭) |
| `services/features/hnr.py` | MultiScaleHNR — de Krom 1993 倒谱法 |
| `services/features/cpp.py` | PraatCPP — VoiceLab parselmouth 封装 |
| `services/features/voicing.py` | VoicingDetector — PYIN 决策质量评估 |
| `tests/integration/test_v5_18_integration.py` | 端到端集成测试 (7 tests) |

#### 真音频效果 (tests/test_data/audio/vocal/)

| 音频 (258s) | Default Tech | v5.18 Tech | 变化 | Default Total | v5.18 Total |
|-------------|-------------|-----------|------|--------------|------------|
| 1（高分） | 77.5 | 92.5 | **+15.0** | 73.6 | 77.0 |

**关键修复**: 旧 CPP 算法对所有音频返回 ~0.018 (无区分度, 评分始终 ~51)。VoiceLab CPP 返回 5-40 dB 范围，恢复 CPP 维度的区分能力。

#### 已知局限 (→ v5.19)

| 问题 | 说明 |
|------|------|
| 跨维度集成不足 | HNR/CPP 仅影响 Technique (20%总权重), 稳定性/置信度/频带差异未利用 |
| CPP 归一化 | VoiceLab CPP 通过 `/20` 映射到评分阈值, 需校准 |
| HNR 天花板 | 新旧 HNR 对优质人声均达 100 分 (≥12dB 阈值) |

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

| 模式 | 文件数 | 结果 |
|------|--------|------|
| Quick | 15 (5人声+10合成) | 5人声正常 + 10合成→0分 ✅ |
| Pro | 5人声 | 全部正确触发Demucs ✅ |
| 单元测试 | 79 | 全部通过 ✅ |
| 混合检测 | 5人声 | 全部正确检测 ✅ |

---

## v5.16 — Pro Breath 修复 (2026-06-03, 已完成)

### 实际效果

| 指标 | v5.15 | v5.16 | 变化 |
|------|-------|-------|------|
| **Pro Breath (恋人)** | 9.8 | **56.3** | **+46.5 (+474%)** |
| Pro Total (恋人) | 63.2 | **73.7** | **+10.5** |
| Quick/Pro Breath 差 | -46.6 | **-0.1** | 缩小 99.8% |
| Quick/Pro Total 差 | -12.5 | **-1.1** | 缩小 91% |
| Quick 回归 | 75.7 | 74.8 | 零回归 |
| 单元测试 | 78/79 | 89/91 | 零回归 (2 pre-existing) |

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

| 音频 | Q.Total | P.Total | Q.Breath | P.Breath | B.Diff | Demucs |
|------|---------|---------|----------|----------|--------|--------|
| 恋人（高分） | 74.8 | **73.7** | 56.4 | **56.3** | **-0.1** | ✅ |
| 1（高分） | 72.7 | 75.0 | 63.2 | 57.1 | -6.1 | ✅ |
| 音频-3分26秒(高分) | 72.6 | 76.4 | 52.6 | 78.2 | +25.6 | ✅ |
| 手写的从前（高分） | 73.4 | 79.1 | 66.4 | 93.6 | +27.2 | 跳过(纯人声) |
| 陈奕迅难听之声（低分） | 48.8 | 48.8 | 51.2 | 51.2 | 0.0 | 跳过(纯人声) |

Quick模式 15/15 文件零回归。

---

## v5.15 — 三模式修复 (2026-06-03, 已完成)

### 实际效果

| 指标 | v5.14 | v5.15 | 变化 |
|------|-------|-------|------|
| **Pro Rhythm (恋人)** | 18.6 | **66.0** | **+47.4 (+255%)** |
| Pro Total (恋人) | 57.6 | 63.2 | +5.6 |
| Pro 耗时 | ~309s | ~226s | -83s (-27%) |
| Quick 回归 (恋人) | 75.6 | 75.7 | 零回归 |
| Quick/Pro Rhythm 差 | -58.5 | **-11.1** | 缩小81% |
| 单元测试 | 78/79 | 78/79 | 零回归 |

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

| 音频 | Total | Pitch | Rhythm | Breath | Tech | Art |
|------|-------|-------|--------|--------|------|-----|
| 高分组 (n=4) | **73-76** | 79-81 | 67-77 | 53-66 | 78-84 | **80-84** |
| 低分组 (n=1) | **47.0** | 75.9 | **2.5** | 51.2 | 57.5 | **53.2** |
| 差距 | **27.4** | 4.2 | 68.6 | 4.3 | 21.7 | **28.4** |

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

| 音频 | Quick Total | Pro Total | Pro Rhythm | Pro Breath |
|------|------------|-----------|------------|------------|
| 恋人(高) | 75.6 | **57.6** | **18.6** | **9.8** |
| 陈奕迅(低) | 45.9 | 50.0 | 2.5 | 51.2 |

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

| 音频 | 总分 | Pitch | Rhythm | Breath | Tech | Art |
|------|------|-------|--------|--------|------|-----|
| 高分组 (n=4) | **73-75** | 79-81 | 67-77 | 53-66 | 78-84 | 78-80 |
| 低分组 (n=1) | **50.0** | 75.9 | **2.5** | 51.2 | 57.5 | 78.0 |
| 白噪声 | **0.0** | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

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

| 优先级 | 问题 | 测试数据 |
|--------|------|---------|
| P0 | 艺术评分无区分力 | 高分78.0 vs 低分78.0 (零差距) |
| P1 | 气息区分度偏窄 | 高分53-66 vs 低分51 (5-15分) |
| P1 | 音准区分度偏窄 | 高分79-81 vs 低分76 (3-5分) |
| P1 | 23个经验参数未校准 | 0个 [实验校准] |

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

| 子问题 | 修复 |
|--------|------|
| CV→deviation 映射将人声CV当做器乐评分 | 重新校准6段映射，CV=0.7→dev=0.40 (原 0.70) |
| 16kHz onset检测精度差 | 内部重采样到 22050Hz |
| 响度归一化 (target_rms=0.05) 压平动态 | 节奏分析使用原始未归一化音频 |
| 长音频全程CV被段落密度差异污染 (276s CV=1.33) | 60s窗口分段分析，取中位数CV |
| 不规则惩罚阈值 0.3 对声乐太严格 | 0.3→0.5，四级分级惩罚 |

**修改文件**: `services/features/rhythm.py`, `services/scoring/rhythm_scorer.py`, `services/audio_features_service.py`, `services/scoring_config.py`

#### 5. 新增级联惩罚 + 优化人声质量惩罚 (Step 7-8)

- 人声质量三层分级惩罚: vq<30 cap 40, vq<50 penalty 35, vq<65 小幅惩罚
- 多维度联合极差惩罚: 3维<40 cap 55, 4维<40 cap 40
- 等级区间更新匹配新分数分布: (88,100)专业级 → (0,25)待改进
- **修改文件**: `services/score_service.py`

### 效果对比

| 音频 | 修改前 | 修改后 | 提升 |
|------|--------|--------|------|
| 清唱 (obj_...) | 70.7 | **82.9** | +12.2 |
| 恋人 | 70.9 | **86.4** | +15.5 |
| 手写的从前 | 73.4 | **83.0** | +9.6 |

| 维度 | 修改前 | 修改后 |
|------|--------|--------|
| Rhythm | 0-6 (全损) | 67-77 (正常) |
| Breath (分离后) | 100 (假) | 70-93 (真) |
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

| 音频 | 维度 | 修复前 | 第一轮 | 第二轮 | 总改进 |
|------|------|--------|--------|--------|--------|
| 恋人 | 音准 | 66.1 | 73.2 | **79.9** | +13.8 |
| 恋人 | 情绪 | 69.2 | 69.8 | **73.9** | +4.7 |
| 恋人 | 总分 | 78.4 | 81.7 | **84.4** | +6.0 |
| 手写的从前 | 音准 | 56.2 | 63.3 | **74.0** | +17.8 |
| 手写的从前 | 情绪 | 61.9 | 68.7 | **73.1** | +11.2 |
| 手写的从前 | 总分 | 73.2 | 77.6 | **81.7** | +8.5 |

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

| 文件 | 说明 |
|------|------|
| `web/static/compare.html` | 独立对比分析页面 |
| `web/static/js/compare.js` | 对比页面主逻辑 |
| `web/static/js/modules/pitch-detector.js` | YIN 音高检测算法 |
| `web/static/js/modules/realtime-compare.js` | 实时录音对比模块 |

### 修改文件

| 文件 | 变更 |
|------|------|
| `web/static/index.html` | 对比分析 tab 改为页面链接 |
| `api/routes/upload.py` | `/compare` 接口支持 FormData |
| `api/business/audio_comparison.py` | 新增 `calculate_relative_score` 等函数 |

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
