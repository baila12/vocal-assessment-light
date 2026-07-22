# 项目状态

> 更新: 2026-07-22 | 当前版本: **v7.0-alpha** (Phase 0-4 完成) | 分支: `feat/v7-fastapi-vue-refactor`

---

## v7.0 重构进度: FastAPI + Vue 3 + Element Plus + Electron (执行中)

> **完整计划**: [V7_MIGRATION_PLAN.md](V7_MIGRATION_PLAN.md) — 绞杀者模式六阶段渐进迁移, 8 项 ADR, 26.5 天

### 六阶段进度

| Phase | 内容         | 天数 | 状态 | 核心交付                                                              |
| ----- | ------------ | ---- | ---- | --------------------------------------------------------------------- |
| 0     | Foundation   | 3.5  | ✅   | DDD 目录 + FastAPI + Vue 3 脚手架 + Alembic + 嵌入式 Python 脚本 |
| 1     | Domain Model | 5    | ✅   | 六维评分 TDD (88 tests) + EventBus + 启发式标记 + ScoringDomainService |
| 2     | FastAPI 迁移 | 4    | ✅   | 21 端点 + Pydantic v2 + openapi.json (16 paths) + Flask `/old/` 共存 |
| 3     | WebSocket    | 3    | ✅   | `/ws/v1/score` + 4 字节长度前缀协议 + 轻量评分 + AudioWorklet |
| 4     | Vue 3 前端   | 8    | ✅   | 5 页面 + 3 Pinia stores + 6 shared components + 33 Vitest tests    |
| 5     | Electron     | 3    | ⏳   | 嵌入式 Python + PyArmor + 进程守护 + 增量更新                         |

### 测试状态 (v7.0-alpha)

| 层级 | 测试数 | 状态 |
|------|--------|------|
| v6.3 单元测试 (保留) | 121 | ✅ 零回归 |
| Phase 1 领域 TDD | 88 | ✅ 全部 GREEN |
| Phase 2 API 集成 | 20 | ✅ 全部 GREEN |
| Phase 3 WebSocket 集成 | 8 | ✅ 全部 GREEN |
| Phase 4 Vue 3 前端 | 33 | ✅ 全部 GREEN (Vitest) |
| **总计** | **270** | ✅ **全部通过** |

### 已落地的 8 项 ADR

| # | ADR | 状态 |
|---|-----|------|
| 1 | **嵌入式 Python 运行时** 替代 PyInstaller | 📋 Phase 5 执行 |
| 2 | **肌肉力量 & 音色 → 启发式代理指标** | ✅ 已实现 (is_heuristic=True + 前端估算值标签) |
| 3 | **前后端类型同步 → 文件驱动 openapi.json** | ✅ 已导出 (16 paths) + 前端 types/api.ts |
| 4 | **Alembic + legacy 表隔离** | ✅ history_v6 表已定义 |
| 5 | **structlog + electron-log** | 📋 Phase 5 执行 |
| 6 | **EventBus 最小原型** | ✅ 已实现 + 事件触发测试 |
| 7 | **WebSocket 4 字节长度前缀** | ✅ 已实现 + 粘包测试 + 前端 useWebSocket composable |
| 8 | **PyArmor 编译领域层** | 📋 Phase 5 执行 |

### Phase 4: Vue 3 前端交付 (2026-07-22)

**架构**: Vue 3 Composition API + Pinia + Element Plus + Chart.js + GSAP + Vite

| 层 | 文件 | 说明 |
|----|------|------|
| **Stores** (3) | `assessment.store.ts`, `history.store.ts`, `preferences.store.ts` | Pinia setup stores |
| **Composables** (5) | `useApi.ts`, `useGsap.ts`, `useMediaRecorder.ts`, `useWebSocket.ts`, `useAudioContext.ts` | Composable pattern |
| **Layout** (3) | `AppLayout.vue`, `TopNav.vue`, `BottomNav.vue` | ElContainer + ElMenu |
| **Shared** (6) | `ScoreCard.vue`, `ScoreRadar.vue`, `PitchCurveCanvas.vue`, `AudioPlayer.vue`, `ProgressOverlay.vue`, `FileUploader.vue` | 可复用组件 |
| **Views** (5) | `HomeView.vue`, `ReportView.vue`, `HistoryView.vue`, `CompareView.vue`, `SingView.vue` | 页面组件 |

**关键设计决策**:
- ✅ **零硬编码 URL**: `window.BACKEND_URL` + `apiClient` (Electron 动态端口)
- ✅ **Element Plus Icons**: 替代 v6.3 的 120+ Unicode emoji
- ✅ **ElDrawer 合并页面**: 设置和曲库作为抽屉 (HomeView) 替代独立页面
- ✅ **SingView 6步清理法**: `cancelAnimationFrame → audioContext.close → close WebSocket → clearRect → cleanup`
- ✅ **HistoryView UTF-8 重写**: 修复 v6.3 GBK 乱码 (P1 bug)
- ✅ **AudioPlayer click-to-seek**: 修复 v6.3 播放器不能拖动进度 (P1 bug)
- ✅ **CompareView 双 ElUpload**: 修复 v6.3 无法两侧上传 (P1 bug)
- ✅ **启发式标签**: 肌肉力量和音色维度显示 "估算值" Tag + 橙色边框
- ✅ **Pinia persist**: 用户偏好 (主题/模式/自动播放) 持久化到 localStorage
- ✅ **GSAP reduced-motion**: 尊重 `prefers-reduced-motion: reduce`

**构建验证**:
```bash
# Vitest (33 tests, 0 failures)
npm run test:unit    # ✅ 33/33 passed

# TypeScript 类型检查
npx vue-tsc --noEmit  # ✅ Zero errors

# 生产构建
npm run build         # ✅ 9.55s (所有 chunk < 350KB gzip)
```

### v7.0 新增端点

| 方法 | 路径 | 标签 |
|------|------|------|
| GET | `/health` | FastAPI 健康检查 |
| POST | `/api/v1/upload` | 上传分析 |
| POST | `/api/v1/analyze` | 分析已存在文件 |
| POST | `/api/v1/extract-pitch` | 音高曲线提取 |
| POST | `/api/v1/separate` | Demucs 人声分离 |
| GET/POST | `/api/v1/separate/models` | 分离模型列表 |
| POST | `/api/v1/report` | 报告导出 |
| POST | `/api/v1/compare` | DTW 对比 |
| GET/DELETE | `/api/v1/history` + CRUD | 历史记录 |
| GET | `/api/v1/audio` | 音频流 |
| GET | `/api/v1/songs` | 歌曲库 (stub) |
| WS | `/ws/v1/score` | WebSocket 实时评分 |

---

## v6.3: 项目重构 + 评分体系设计 (2026-07-20)

### 评分体系: 六维重构设计 ★vNext

- 音准 30%→**10%**、节奏 20%→**10%** 降权
- 发声技术拆分为: 咬字清晰度 + 气声比 (25%)
- **新增**肌肉力量: 身体肌肉 + 面部肌肉 (25%)
- **新增**音色额外加减分 +3~-5 (clamp [0,100])
- 开发原则: 维度独立可测、低耦合、Feature Flag 独立开关

### 项目结构清理

- 🗑️ PyQt5 旧代码删除: `core/`, `widgets/`, `windows/`, `styles/`, `utils/`
- 🗑️ 根目录清理: `prototype.html`, `desktop_app.py`, `main.py`, `vocal_assessment.spec`, `installer.iss`
- 🗑️ 旧页面删除: `web/static/analysis.html`, `compare.html`, `settings.html`
- 🗑️ 废弃 JS: `js/effects/` (4 stub), `js/services/sse.js`
- 📦 `model_manager.py` → `services/dl_services/emotion_manager.py`

### v7.0 前端方向

- Element Plus + Element Plus Icons (替代 emoji)
- Vue 3 Composition API + Vite + Pinia + Electron

---

## v6.2.1: FeatureFlags 激活 + SPA 修复 + 桌面打包 (2026-07-08)

### FeatureFlags 激活 (P0 修复)

**v6.2 的核心算法此前从未在线上环境执行。** `upload.py` 调用 `analyze_and_score()` 时缺少 `feature_flags=FeatureFlags()`，所有 gated 算法静默失效。

修复后激活的 7 个算法：Cross-Dimension Modifiers、Praat Voice Quality (jitter/shimmer/formants)、Multi-scale HNR (de Krom 1993)、Praat CPP、Voicing Detection、Reverb Compensation、TorchCREPE Fallback。

### SPA 前端修复 (9 项)

| 修复                 | 文件                            | 说明                                        |
| -------------------- | ------------------------------- | ------------------------------------------- |
| querySelector 选择器 | ReportPage/HistoryPage/SingPage | 11 处`_xxx` → `#xxx`                   |
| 运行时崩溃           | HistoryPage.js                  | `el.textContent` 未定义变量、HTML标签损坏 |
| 音频播放器           | ReportPage.js                   | 导入 AudioPlayer，play/pause/progress/time  |
| PitchCurve           | ReportPage.js                   | 实例化 Canvas 音高曲线                      |
| API 字段名           | HistoryPage.js                  | `res.records` → `res.history`          |
| 模拟数据替换         | ComparePage.js / SingPage.js    | 真实 API 调用                               |
| separateVocals       | api.js                          | FormData → JSON                            |
| mode 持久化          | upload.py / audio_analysis.py   | 历史记录 + 报告页                           |
| 确认对话框           | HistoryPage.js                  | 清空全部添加确认 + deleteHistoryAll         |

### 桌面应用打包

- **pywebview**: `desktop_app.py` — Flask 后台线程 + Edge WebView2 原生窗口
- **PyInstaller**: `vocal_assessment.spec` — 干净 conda 环境 + CPU PyTorch + INT8 量化模型，0.91 GB
- **Inno Setup**: `installer.iss` — Windows 安装器
- **一键启动**: `start.bat` — 自动激活环境 + 等待就绪 + 打开浏览器

### 已知问题 (更新)

### 算法路径全景 (v6.2.1)

> 详细分析见 [SCORING.md](../2-technical/SCORING.md)

| 模式                   | 评分算法       | DL 模型          | Demucs分离 | 可视化/音色/逐句 | DTW参考   | 特征增强*    |
| ---------------------- | -------------- | ---------------- | ---------- | ---------------- | --------- | ------------ |
| **Quick (上传)** | 5维标准        | ❌ 全部跳过      | ❌         | ❌               | 可选      | ✅ 全部 7 项 |
| **Quick (演唱)** | 5维标准        | ❌ 全部跳过      | ❌         | ❌               | ❌        | ✅ 全部 7 项 |
| **Pro (上传)**   | 5维 + 唱法权重 | ✅ (SingMOS失败) | ✅         | ✅               | 可选      | ✅ 全部 7 项 |
| **Compare**      | 5维 ×2 + DTW  | ✅ (双方)        | ✅         | ❌               | ✅ (核心) | ✅ 全部 7 项 |

> \* 特征增强 = 跨维度修正 + Praat声质 + 多频带HNR + PraatCPP + Voicing + 混响补偿 + TorchCREPE

**Quick 模式特征全部启用**：`upload.py` 传入 `FeatureFlags()`（全部 `True`）是正确的设计。Quick 的"快"来自跳过 DL 模型和辅助分析，而非缩减特征提取。`FeatureFlags.for_quick()` 工厂方法已过时，应移除或更新为全开。

**DL 模型启用状态**:

| 模型                          | 模式           | 状态                        |
| ----------------------------- | -------------- | --------------------------- |
| Silero VAD (ONNX)             | 仅 Pro/Compare | ✅                          |
| Style Classifier (ONNX, INT8) | 仅 Pro/Compare | ✅                          |
| Self-Referenced DTW           | 仅 Pro/Compare | ✅ (计算但不影响评分)       |
| SingMOS (PyTorch Hub)         | 仅 Pro/Compare | ❌ 缺少 s3prl → 静默返回0  |
| Wav2Vec2 Emotion              | 全部           | ❌ v5.12 移除 → 启发式替代 |

### 已知问题与限制 (v6.2.1)

#### P0 — 桌面打包

| # | 问题                   | 根因                                                                                                                                                                                                                                                     | 文件                                    | 计划                                                           |
| - | ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------- | -------------------------------------------------------------- |
| 1 | EXE 无法启动 (SSL DLL) | `vocal_assessment.spec:18-24` 硬编码了 conda `Library/bin/libssl-3-x64.dll` 的绝对路径，仅在构建机存在。运行时 PyInstaller 提取的 DLL 与 `_ssl.pyd` 版本不匹配。另：`console=True`(debug遗留)、硬编码清理路径 `c:/Users/jack/Desktop/VocalApp` | `vocal_assessment.spec:18-24,168,193` | conda 环境中的 DLL 正确嵌入；`console=False`；移除硬编码路径 |
| 2 | 无 WebView2 检测       | `desktop_app.py:235` `create_window` 依赖 Edge WebView2，目标机未安装时窗口白屏无提示                                                                                                                                                                | `desktop_app.py`                      | 添加 WebView2 运行时检测 + 提示                                |

#### P1 — 前端功能缺失/缺陷

| # | 问题                                 | 根因                                                                                                                                                                                                                                                                                                                                                            | 文件                                                                                            | 计划                                                                    |
| - | ------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| 3 | **播放器不能拖动进度**         | `_setupAudioControls()` 只做了 play/pause，progress bar 无 click-to-seek                                                                                                                                                                                                                                                                                      | `ReportPage.js:326-363`                                                                       | 给`#audioProgress` 添加 click 事件，调用 `audioElement.currentTime` |
| 4 | **播放器无跳动效果**           | 无频谱可视化、无波形动画。旧`analysis.js` 有 `drawWaveform`/`drawFrequency`                                                                                                                                                                                                                                                                               | `modules/audio.js` 已实现但未接入                                                             | 在 ReportPage 中集成`drawWaveform` Canvas                             |
| 5 | **导出 PDF/图片无实际导出**    | 后端`/api/report` 生成文件到 `reports/xxx_report.pdf`，返回服务器本地路径如 `C:\Users\...\reports\report.png`。前端 `ReportPage.js:316` 用 `<a href="C:\Users\...">` 下载 — 浏览器无法访问服务器本地路径（无 HTTP 路由 serve `reports/` 目录，不同于 `plots/` 目录有 Flask 路由）。另：PDF 需要 `reportlab` 包未在 `requirements.txt` 中声明 | `ReportPage.js:316-318`, `report_service.py:73,334`, `api/__init__.py` (reports 路由缺失) | 添加`/reports/<filename>` 路由；或改用 blob 响应直接返回文件内容      |
| 6 | **标准音乐库无法导入**         | 后端缺失`GET/POST /api/songs` 路由。`SongLibraryPage` 调用后 fallback 到 `window.__mockSongs`                                                                                                                                                                                                                                                             | `SongLibraryPage.js:134,365`, `services/api.js:287`                                         | 新增 6 个后端路由                                                       |
| 7 | **分析后无曲库比对弹窗**       | 分析流程中没有与曲库对比的步骤。DTW 仅在`/api/compare` 路由中调用，需要手动对比                                                                                                                                                                                                                                                                               | `api/routes/upload.py:101`                                                                    | 分析完成后自动搜索曲库并 DTW 比对，弹窗显示相似度                       |
| 8 | **对比页缺少直接上传标准音频** | ComparePage 左侧仅支持曲库选择 (`StandardAudioSelector`)，右侧仅支持上传。无法两侧都上传文件                                                                                                                                                                                                                                                                  | `ComparePage.js:77-95`                                                                        | 左侧添加"上传标准音频"选项                                              |

#### P1 — SingPage 演唱页

| # | 问题                           | 根因                                                                                                                                  | 文件                             | 计划                                             |
| - | ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------- | ------------------------------------------------ |
| 9 | **必须先选曲库才能演唱** | SingPage 默认显示曲库选择器，跳过按钮`#skipSongBtn` 存在但样式弱(`font-size:12px; color:var(--text-muted)`)。用户感知为"必须选歌" | `SingPage.js:149-151, 318-326` | 改为默认显示"快速演唱"模式，曲库选歌作为可选增强 |

#### P2 — 编码与数据

| #  | 问题                           | 根因                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | 文件                                                      | 计划             |
| -- | ------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- | ---------------- |
| 10 | **HistoryPage 乱码**     | 文件以错误编码保存（GBK 字节被当作 UTF-8 读取），导致中文注释和 UI 文本显示为 mojibake                                                                                                                                                                                                                                                                                                                                                                                       | `HistoryPage.js` 全文                                   | 整体重写为 UTF-8 |
| 11 | **6 个后端路由缺失**     | `GET/POST /api/songs`、`GET /api/songs/:id`、`GET /api/analysis/:id`、`GET /api/analysis/:id/status`、SSE `/api/analysis/progress`                                                                                                                                                                                                                                                                                                                                 | `api/routes/`                                           | v6.3 新增        |
| 12 | **前后端数据格式不匹配** | (a)`/api/compare` FormData: 前端 `api.js:253` 发送字段名 `standard`/`user`，后端 `upload.py:297` 检查 `file`/`standard_file` → 永远不匹配，落入 JSON 解析路径 → 400 错误; (b) `/api/compare` 响应: 后端返回 `{ data: { score, level } }`, `ComparePage.js:521` 读 `result.total_score` → `undefined`; (c) `separateVocals()` — ✅ v6.2.1 已修复; (d) history `records`→`history` — ✅ v6.2.1 已修复; (e) mode 持久化 — ✅ v6.2.1 已修复 | `api.js:253`, `upload.py:297`, `ComparePage.js:521` | v6.3 统一字段名  |

### 前端缺失功能 (SPA 迁移遗留)

| 功能            | 旧页面        | SPA        | 状态                            |
| --------------- | ------------- | ---------- | ------------------------------- |
| 音频播放器      | analysis.html | ReportPage | ✅ v6.2.1 已回归 (无 seek/频谱) |
| 音高曲线        | analysis.html | ReportPage | ✅ v6.2.1 已回归                |
| 波形可视化      | analysis.html | —         | ❌ 缺失                         |
| 频谱图/能量曲线 | analysis.html | —         | ❌ 缺失                         |
| 人声分离面板    | analysis.html | —         | ❌ 缺失                         |
| 音色分析面板    | analysis.html | —         | ❌ 缺失                         |
| 逐句评分        | analysis.html | —         | ❌ vizCard 隐藏                 |
| KTV 对比面板    | compare.html  | —         | ❌ 缺失                         |
| 曲库比对弹窗    | —            | —         | ❌ 从未实现                     |

## v6.2: 评分算法重构 + 性能优化 (2026-07-07, 已完成)

### 设计目标

1. **评分区分度**: 高分 ≥ 80, 低分 40-50, 差距 ≥ 30
2. **客观真实**: 所有改动有文献/实验数据支撑, 不做无依据的参数调整
3. **性能**: 单文件分析 < 60s (曾 ~700s)
4. **全面性**: 更多声学特征 + 更多技巧类型

### 算法变更

| #  | 模块       | 文件                            | 变更                                                                                                | 依据                                        |
| -- | ---------- | ------------------------------- | --------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| 1  | 音准评分   | `pitch_scorer.py`             | 多指标体系: MAE指数衰减(40%) + RPA(25%) + RCA(10%) + gross_error(15%) + smoothness(5%) + octave(5%) | Wager 2022, Cao et al. 2008                 |
| 2  | 音准评分   | `pitch_scorer.py`             | 断层惩罚: PYIN校准率阈值 (YIN ÷3.5 校正因子, >5%真实率触发)                                        | PYIN对比实验: YIN 785 vs PYIN 226 断层      |
| 3  | 音准评分   | `pitch.py`                    | pitch_breaks 检测: 仅连续有声帧 + 排除八度跳变 (1000-1400音分)                                      | de Cheveigne & Kawahara 2002 — YIN八度混淆 |
| 4  | 气息评分   | `breath.py`                   | 质量门控: breath_design 权重 20%→5% (基础控制不足时)                                               | Titze 1994                                  |
| 5  | 气息评分   | `breath.py`                   | dynamic_range: max/min→p95/p5 百分位 (排除近静音异常值)                                            | max/min 实测 101.9dB, 物理不可能            |
| 6  | 跨维度修正 | `score_modifiers.py` (新)     | HNR稳定→气息, Voicing→音准, 频谱倾斜→气声, 气息-音准耦合                                         | de Krom 1993, Sundberg 1987, Titze 1994     |
| 7  | 声学特征   | `acoustic.py`                 | 频谱倾斜: LTAS slope via Welch PSD + 线性回归                                                       | Sundberg 1987                               |
| 8  | 声学特征   | `acoustic.py`                 | _calc_harmonicity: np.correlate O(N²)→FFT自相关 O(N log N) [Wiener-Khinchin]                      | cProfile: 566.9s (97%总耗时)                |
| 9  | 声质特征   | `voice_quality_praat.py` (新) | Praat: jitter/shimmer/formants(F1-F4)/singer's formant/HNR                                          | Baken & Orlikoff 2000                       |
| 10 | 技巧检测   | `technique.py`                | 扩展 3→5: +staccato +legato                                                                        | Sundberg 1987, Nakano et al. 2006           |
| 11 | 特征开关   | `feature_flags.py`            | 6个已验证算法默认启用 + for_quick()/for_professional()/safe_baseline()                              | —                                          |
| 12 | 性能优化   | `audio_features_service.py`   | HPSS缓存: 预计算一次, 调用点复用 (避免 3x 重复 ~18s)                                                | 实测单次HPSS 5.9s                           |
| 13 | 性能优化   | `voice_quality_praat.py`      | Quick模式截断60s (jitter/shimmer/formant统计快速收敛)                                               | 临床标准 3-5s 元音即够                      |

### v6.2 真实音频评分基线 (Quick模式)

| Audio                  | Total          | Pitch          | Rhythm         | Breath         | Tech           | Art            | 耗时 |
| ---------------------- | -------------- | -------------- | -------------- | -------------- | -------------- | -------------- | ---- |
| 恋人（高分）           | **82.2** | 77.7           | 77.1           | 93.6           | 82.2           | 82.0           | 63s  |
| 音频-3分26秒(高分)     | **80.1** | 77.7           | 71.9           | 92.7           | 74.8           | 85.5           | 41s  |
| 1（高分）              | **79.4** | 79.3           | 66.8           | 92.3           | 76.6           | 82.9           | 63s  |
| 手写的从前（高分）     | **79.0** | 79.2           | 66.6           | 91.3           | 76.4           | 82.0           | 49s  |
| **高分均值**     | **80.2** | **78.5** | **70.6** | **92.5** | **77.5** | **83.1** | ~54s |
| 陈奕迅难听之声（低分） | **50.0** | 72.7           | **2.5**  | 84.8           | 66.2           | 81.2           | 33s  |
| **区分度**       | **30.2** | 5.8            | **68.1** | 7.7            | 11.3           | 1.9            |      |

### v5.17 → v6.2 对比

| 指标         | v5.17 | v6.2           | 变化 |
| ------------ | ----- | -------------- | ---- |
| 高分总分均值 | 73.4  | **80.2** | +6.8 |
| 低分总分     | 48.8  | 50.0           | +1.2 |
| 总分区分度   | 24.6  | **30.2** | +5.6 |
| 音准区分度   | 4.2   | 5.8            | +1.6 |
| 节奏区分度   | 68.1  | 68.1           | 不变 |
| 单文件耗时   | ~700s | **~54s** | 13x  |

### 已知问题与限制

#### P1 — 算法层面

| 问题                                 | 根因                                                                                               | 影响                        | 计划                      |
| ------------------------------------ | -------------------------------------------------------------------------------------------------- | --------------------------- | ------------------------- |
| **气息评分整体偏高 (85-94)**   | BreathAnalyzer 四子维度对各类演唱均给高分; clean_breath_count 与演唱质量弱相关                     | 高低分歌手气息差距仅 7.7 分 | v6.3: 子维度校准数据集    |
| **艺术评分无区分度 (1.9)**     | ArtistryScorer 依赖 vibrato_quality + dynamic_range + phrase_coherence; 这些特征在流行唱法中变化小 | 高低分无差异                | v6.3: 引入音色/表现力模型 |
| **音准区分度 5.8 (目标 ≥10)** | 无参考旋律时, 仅能评估"离最近的半音多远", 不能评估"唱的是不是对的音"                               | 限制了对音准的真正判断力    | v7.0: DTW 参考评分默认化  |
| **低分歌手 Pitch=72.7 (偏高)** | 该歌手音准客观上尚可 — 问题是节奏(R=2.5)不是音准。系统客观反映了此事实                            | 音准维度区分度受限          | 无需修复 (客观正确)       |

#### P2 — f0 质量

| 问题                                   | 根因                                                                            | 缓解措施                                                              |
| -------------------------------------- | ------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| **YIN @ 16kHz 产生大量帧间伪影** | librosa.yin 对非有声帧赋值随机 f0 (NaN率=0%); PYIN正确处理但慢30x (23s vs 0.7s) | pitch_breaks: 八度跳变排除 + PYIN校准因子(÷3.5); smoothness 权重减半 |
| **pitch_breaks 仍有 785+ 次**    | 排除八度跳变后剩余的是真实帧间差异; YIN低SNR下误差率升高 [de Cheveigne 2002]    | 率阈值 (校准后 >5% 才罚)                                              |

#### P2 — 性能

| 问题                 | 当前                                                                      | 目标     |
| -------------------- | ------------------------------------------------------------------------- | -------- |
| extract_all_features | ~17s                                                                      | < 10s    |
| 完整 Quick 管道      | ~54s                                                                      | < 30s    |
| 主要剩余瓶颈         | audio_service.analyze() 内多步librosa操作 (chroma/mel/onset/RMS/centroid) | 可并行化 |

### 测试

```
单元测试: 43/43 通过
TDD v6.1: 11/11 通过 (1 xfail→XPASS)
集成测试: 134/134 通过
```

## 运行

```bash
conda activate pytorch2
python web_app.py
# http://localhost:5000
```

**技术栈**: Flask 3.0 | librosa | PyTorch | Demucs | Chart.js | GSAP 3 | AppContext DI | EventBus | pytest | Playwright

---

## 三模式现状

| 模式                    | 触发方式                          | CPU 耗时  | GPU 耗时 | 适用场景     |
| ----------------------- | --------------------------------- | --------- | -------- | ------------ |
| **Quick**         | `/api/upload?mode=quick`        | ~15-20s   | ~15-20s  | 快速练习反馈 |
| **Professional**  | `/api/upload?mode=professional` | ~130-170s | ~30-50s  | 详细问题诊断 |
| **Compare (DTW)** | `/api/compare` 或自动搜索       | ~45s      | ~45s     | 参考对比评分 |

> ✅ PyTorch 2.6.0+cu124 (CUDA 12.4), GPU 加速已就绪。Demucs Pro 模式 GPU 耗时 ~30-50s。`/health` 端点可查看 GPU 状态。

---

## 真实音频测试结果

### Quick 模式基线 (v5.17)

| 音频                   | 总分           | 音准 | 节奏          | 气息 | 技巧 | 艺术 |
| ---------------------- | -------------- | ---- | ------------- | ---- | ---- | ---- |
| 恋人（高分）           | **74.8** | 79.6 | 77.1          | 56.4 | 84.0 | 75.9 |
| 手写的从前（高分）     | **73.4** | 80.8 | 66.6          | 66.4 | 77.6 | 73.2 |
| 1（高分）              | **72.7** | 80.7 | 66.8          | 63.2 | 77.5 | 72.6 |
| 音频-3分26秒(高分)     | **72.6** | 79.3 | 71.9          | 52.6 | 84.0 | 73.8 |
| 陈奕迅难听之声（低分） | **48.8** | 75.9 | **2.5** | 51.2 | 57.5 | 46.2 |
| 白噪声                 | **0.0**  | 0.0  | 0.0           | 0.0  | 0.0  | 0.0  |

**高分均值 73.4 vs 低分 48.8 — 区分度 24.6 分。**

### Quick vs Pro 一致性 (v5.17)

| 音频               | Quick | Pro  | 差距 | Pro Demucs   |
| ------------------ | ----- | ---- | ---- | ------------ |
| 恋人（高分）       | 74.8  | 73.7 | -1.1 | ✅           |
| 1（高分）          | 72.7  | 75.0 | +2.3 | ✅           |
| 手写的从前（高分） | 73.4  | 79.1 | +5.7 | 跳过(纯人声) |
| 音频-3分26秒(高分) | 72.6  | 76.4 | +3.8 | ✅           |
| 陈奕迅（低分）     | 48.8  | 48.8 | 0.0  | 跳过(纯人声) |

**Quick/Pro 总分离散 < 6 分 — 一致性良好。**

---

## 已完成功能 (按版本)

| 版本  | 日期  | 核心变更                                                             |
| ----- | ----- | -------------------------------------------------------------------- |
| v5.19 | 07-04 | 评分区分度修复: 气息基线40→10, 音准MAE扩展, HNR/CPP天花板, 音量独立 |
| v5.18 | 07-04 | 开源算法移植 (HNR/CPP/Voicing) + Feature Flag + 代码审查20项修复     |
| v5.17 | 06-04 | 混合音频检测修复 (阈值0.35→0.25) + GPU加速 + 合成音频归零验证       |
| v5.16 | 06-03 | Pro Breath 修复: is_clean_vocal标记传递链 → 9.8→56.3 (+474%)       |
| v5.15 | 06-03 | Pro Rhythm CV重校准 + SingMOS移除 + DTW自动搜索 + 自参照一致性       |
| v5.14 | 06-03 | 音准多指标体系 + 艺术评分重构 (区分度 0.3→28.4)                     |
| v5.13 | 06-03 | Sigmoid+硬上限移除 → 区分度恢复 + Demucs CV映射修复                 |
| v5.12 | 06-03 | 安全加固 + DL清理(-654行) + 评分统一 + 算法校准 + 魔法数字集中化     |
| v5.11 | 06-02 | 评分区分度(0-100全范围) + Demucs管线修复 + 节奏CV分段                |
| v5.10 | 05-26 | DTW参考评分融合 + 自参照DTW + 响度归一化                             |

详细变更见 [CHANGELOG.md](CHANGELOG.md)。

---

## 已知问题

### P0 (严重) — 全部已修复 ✅

| 问题                                | 版本     | 效果                   |
| ----------------------------------- | -------- | ---------------------- |
| Pro 节奏崩塌 (18.6 vs Quick 77.1)   | ✅ v5.15 | 18.6→66.0 (+255%)     |
| SingMOS 严重跨域 (低分>高分)        | ✅ v5.15 | 移除，自参照一致性替代 |
| DTW 参考评分未默认化                | ✅ v5.15 | 独立上传自动搜索       |
| Pro Breath 崩塌 (9.8 vs Quick 56.4) | ✅ v5.16 | 9.8→56.3 (+474%)      |

### P1 (功能缺陷) — 4 项 (v6.0 已改进 2 项, 待 v6.1 校准)

| 问题                         | 说明                                                       | 状态                  |
| ---------------------------- | ---------------------------------------------------------- | --------------------- |
| **气息评分区分度偏窄** | v5.17: 53-66 vs 51 (15分差) → v5.19: 67-88 vs 80 (21分差) | ⚠️ 改善但低分仍偏高 |
| **音准评分区分度偏窄** | v5.17: 79-81 vs 76 (5分差) → v5.19: 69-76 (7分差)         | ⚠️ 改善, 目标 ≥10  |
| ~~23 个经验参数未校准~~     | → v6.1 校准数据集 (优先: Breath/Technique/Artistry)       | 📋                    |
| **Pro 模式耗时过长**   | CPU ~130-170s (Demucs 占 ~80%)                             | ✅ GPU 加速已就绪     |

### P2 (优化) — 4 项 (v6.0: 3 项已修复)

| 问题                  | 说明                                                          | 状态      |
| --------------------- | ------------------------------------------------------------- | --------- |
| f0 节奏路径待恢复     | v5.13 回退到 f0=None，需校准验证后启用                        | 📋 v6.1   |
| 技巧检测仅 3 种       | 颤音/滑音/假声 vs 论文 7-15 种                                | 📋        |
| ~~无混响补偿~~       | ✅ v6.0:`ReverbCompensator` 已接入 `AudioFeaturesService` | ✅ 已修复 |
| ~~音量维度未独立~~   | ~~与 Breath 合并~~ → v5.19 基于 dynamic_range 独立计算      | ✅ 已修复 |
| ~~混合音频检测误判~~ | ✅ v6.0: 五特征融合, 纯人声 0 误判                            | ✅ 已修复 |
| 核心/服务层代码重叠   | legacy 模块待清理                                             | 📋        |

### ✅ P0 (前端) — SPA 导航跳转 Bug (已修复)

| 问题                     | 说明                                           | 状态            |
| ------------------------ | ---------------------------------------------- | --------------- |
| **SPA 导航不跳转** | 点击导航按钮后 URL hash 改变, 但页面内容不更新 | ✅ v5.20 已修复 |

**根因**: 三重 Bug 叠加导致路由器 `#transition()` 死锁:

1. `AnimationController._execute()` — `onComplete` 被从 GSAP vars 中丢弃
2. `AnimationController._track()` — 覆盖而非链式调用已有 `onComplete`, 且 getter 对刚创建的 tween 返回 `undefined` 时未回退到 `vars.onComplete`
3. `HashRouter.#handleRoute()` — `killAll()` 在 `#navPending` 检查之前执行, 单次点击触发的 popstate 事件杀掉了 hashchange 事件的 leave 动画

**修复文件**: `web/static/js/animation/Controller.js` (3 处), `web/static/js/components/BaseComponent.js` (1 处), `web/static/router.js` (1 处)

### 🆕 P1 (前端) — 其他已修复的 SPA 问题 (v5.20)

| 问题                                                           | 状态      |
| -------------------------------------------------------------- | --------- |
| API 路径`/api/audio/analyze` 不存在 (404) → `/api/upload` | ✅ 已修复 |
| API 路径`/api/history/batch-delete` 路径+方法错误            | ✅ 已修复 |
| HistoryPage.js 全部中文乱码 (mojibake) +`ac is not defined`  | ✅ 已修复 |
| ComparePage Modal 弹窗无法关闭 (双重 overlay)                  | ✅ 已修复 |
| 全部页面`const ac = this.ac` 编码/作用域问题                 | ✅ 已修复 |
| 路由`#transition()` 无错误恢复                               | ✅ 已修复 |

---

## v6.0: 混响补偿管线接入 + 混合音频检测文献驱动重构 (2026-07-06, 已完成)

### 混响补偿接入评分管线 (P2→✅)

| # | 文件                                   | 变更                                              |
| - | -------------------------------------- | ------------------------------------------------- |
| 1 | `services/feature_flags.py`          | 新增`enable_reverb_compensation` flag           |
| 2 | `services/audio_features_service.py` | 集成`ReverbCompensator`, HNR/CPP 计算前可选补偿 |
| 3 | `services/features/acoustic.py`      | `analyze()` 适配新返回格式                      |

**管线流程**: `audio_data` → `ReverbCompensator.process()` (HPSS+谱减法) → 补偿后音频 → HNR/CPP 计算
**控制**: `FeatureFlags.enable_reverb_compensation = True` 启用, 默认关闭

### 混合音频检测文献驱动重构 (P2→✅)

基于以下文献重新设计检测算法:

| 论文                          | 关键贡献                          | 应用                             |
| ----------------------------- | --------------------------------- | -------------------------------- |
| Fitzgerald (2010). DAFx       | HPSS 中值滤波分离                 | 特征1: HPSS 谐波比               |
| Driedger et al. (2014). ISMIR | HPSS 三元分解 H+P+R, 歌声在残差区 | HPSS 门控阈值 0.88/0.72          |
| Lehner et al. (2018). TASLP   | 子带频谱平坦度 (1.5-3kHz) 最可靠  | 特征2: 子带平坦度 (替代低频能量) |

**v5.17 → v6.0 改进**:

| 指标         | v5.17                   | v6.0                                       |
| ------------ | ----------------------- | ------------------------------------------ |
| 特征数量     | 2 (低频能量+全频平坦度) | 5 (HPSS+子带平坦度+高频+谐波度+全频平坦度) |
| 纯人声误判率 | 75% (3/4)               | **0%** (0/4)                         |
| 文献依据     | 经验阈值                | Fitzgerald+Driedger+Lehner                 |

**已知局限** (文献证实): 极轻钢琴伴奏 HPSS ratio >0.88 时信号处理无法检测。
此为 Driedger 2014 和 Lehner 2018 共同确认的理论上限, 需 LSTM 方法解决。

### 测试

```
TDD 新增: 9 个测试 (4 reverb pipeline + 5 mixed audio detection)
全部通过: 6 passed, 1 skipped (known limitation), 0 failed
混合音频检测: 合成 5/5 通过, 真音频 0 误判
```

---

## v6.1: 评分区分度修复 + Artistry 独立评分 + 测试模块化 (2026-07-06, 已完成)

### 评分区分度修复

| # | 文件                                     | 变更                                           |
| - | ---------------------------------------- | ---------------------------------------------- |
| 1 | `services/features/technique.py`       | technique_score 基线 50→0, 仅检测到的技巧加分 |
| 2 | `services/features/breath.py`          | 四子维度步进加分→连续线性映射, 基线 10→0     |
| 3 | `services/scoring/technique_scorer.py` | HNR/CPP 高技巧阈值 70→35                      |
| 4 | `services/scoring_config.py`           | 所有基线参数更新                               |

### Artistry 独立评分

`services/scoring/artistry_scorer.py` 完全重构:

- **旧**: `pitch*0.20 + rhythm*0.25 + breath*0.20 + technique*0.35`
- **新**: 4 个独立声学特征子维度 (颤音品质/动态控制/乐句处理/音高变化)
- 不再依赖其他维度分数

### Bug 修复

| 严重度   | 问题                                                     | 文件                                     |
| -------- | -------------------------------------------------------- | ---------------------------------------- |
| CRITICAL | `detect_mixed_audio()` 返回值 4→3, 2 个调用者静默失败 | `audio_service.py`, `dtw_aligner.py` |
| MEDIUM   | E2E 测试 3 处 collection error                           | `test_e2e.py` 等                       |

### 测试模块化 + 速度优化

- `test_future_features.py` → 4 个模块 + `conftest.py` (会话级缓存)
- TDD 套件: 600s+ → ~65s (消除冗余 HPSS 调用 + 短音频片段)
- 新增 `docs/2-technical/API_CONTRACT.md` (Vue 迁移)
- 新增 `docs/4-process/TEST_RESULTS.md` (测试结果记录)

### 测试

```
单元: 121 passed, 0 failed
TDD:  ~35 tests (12 acoustic + 11 mixed + 9 scoring + 5 RED/xfail)
```

---

## v5.20: 前端SPA修复 + 架构升级 + 混响补偿 + 混合音频检测重构 (2026-07-05, 已完成)

### 🔴 SPA 导航死锁修复 (P0, 3 文件)

三重 Bug 叠加 → 路由器 `#transition()` 死锁 → URL 变但页面不更新。

| # | 文件                                          | 修复                                                                                                                    |
| - | --------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| 1 | `web/static/js/animation/Controller.js`     | `_execute()`: onComplete 传入 GSAP toVars; `_track()`: 链式回调 (cleanup + 原有), 双来源检查; `leave()`: 安全超时 |
| 2 | `web/static/js/components/BaseComponent.js` | `beforeUnmount()`: 硬编码 'page-leave' 预设                                                                           |
| 3 | `web/static/router.js`                      | `#navPending` 检查移到 `killAll()` 之前                                                                             |

### 🏗️ 架构升级 — v7.0 Vue 迁移衔接 (3 文件新增, 3 文件重构)

| # | 文件                                               | 说明                                      | v7.0 目标                  |
| - | -------------------------------------------------- | ----------------------------------------- | -------------------------- |
| 1 | `web/static/js/AppContext.js` 🆕                 | 依赖注入容器 (store/router/api/ac/events) | Vue`provide/inject`      |
| 2 | `web/static/js/EventBus.js` 🆕                   | 事件总线 (on/once/off/emit)               | `mitt()`                 |
| 3 | `web/static/js/components/BaseComponent.js` v3.0 | context 注入, Vue 生命周期对齐            | `<script setup>`         |
| 4 | `web/static/app.js` v3.0                         | createApp 模式入口, context 组装          | `createApp()`            |
| 5 | `web/static/router.js` v3.0                      | `useContext(context)` 注入              | Vue Router`createRouter` |

### 前端 SPA Bug 修复 (6 类, 12 文件) — 基础修复, 见 CHANGELOG |

### 后端改进

| # | 模块             | 文件                                  | 依据                                     |
| - | ---------------- | ------------------------------------- | ---------------------------------------- |
| 1 | 混响补偿         | `services/features/reverb.py` 🆕    | Fitzgerald 2010, Boll 1979, Berouti 1979 |
| 2 | 混合音频检测重构 | `services/features/acoustic.py`     | HPSS + 多特征融合, 采样率自适应          |
| 3 | CPP 测试修复     | `tests/tdd/test_future_features.py` | 安装 parselmouth 0.4.7                   |

### 测试

```
单元+TDD: 149 passed, 0 failed, 7 xfail (v6.0)
混响补偿: 1 xfail → 1 GREEN 🆕
```

---

## v5.18: 开源算法移植 + Feature Flag + 代码审查修复 (已完成)

### 代码审查修复 (2026-07-04)

三代理并行审查（code-reviewer + security-reviewer + python-reviewer）发现 20 个问题，全部修复。详见 [CHANGELOG.md](CHANGELOG.md)。

**关键修复**:

- 🔴 de Krom 1993 谐波边界检测 Bug (hnr.py) — 倒谱谐波峰仅置零 1 bin → 正确扩展到整个谐波"山峰"
- 🔴 倒谱镜像 off-by-one (hnr.py) — 噪声倒谱对称性修复
- 🔴 Voicing 一致性 3 重 Bug (voicing.py) — 时长计算 + 边界段统计
- 🔴 TorchCREPE fallback 死代码 (audio_service.py) — `feature_flags` 现已传入 `_analyze_pitch()`
- 🔴 API traceback 泄露 (audio_analysis.py) — 移除错误响应中的完整堆栈
- 🟡 CPP 归一化校准: `/20.0` → `/6.0`
- 🟡 文件大小: `audio_service.py` 872→800 行, 提取 `audio_dl_helpers.py` (93 行)

### 完成状态 ✅

| # | 任务                                        | 来源            | 文件                                                          | Feature Flag                   |
| - | ------------------------------------------- | --------------- | ------------------------------------------------------------- | ------------------------------ |
| 1 | 多频带 HNR (de Krom 1993 倒谱分离法, 4频带) | VoiceLab        | `services/features/hnr.py`                                  | `enable_multiscale_hnr`      |
| 2 | Praat CPP (parselmouth PowerCepstrum)       | VoiceLab        | `services/features/cpp.py`                                  | `enable_praat_cpp`           |
| 3 | Voicing detection 评估 (自一致性检查)       | pitch-benchmark | `services/features/voicing.py`                              | `enable_voicing_detection`   |
| 4 | TorchCREPE 备选接入 (PYIN 降级时)           | pitch-benchmark | `services/audio_features_service.py` + `audio_service.py` | `enable_torchcrepe_fallback` |
| 5 | Feature Flag 机制                           | —              | `services/feature_flags.py`                                 | —                             |
| 6 | DL 辅助方法提取                             | —              | `services/audio_dl_helpers.py` (🆕)                         | —                             |
| 7 | 端到端集成测试                              | —              | `tests/integration/test_v5_18_integration.py` (7 tests)     | —                             |

### Feature Flag 机制

```python
# services/feature_flags.py
@dataclass
class FeatureFlags:
    enable_multiscale_hnr: bool = False        # de Krom 1993 多频带 HNR
    enable_praat_cpp: bool = False             # VoiceLab parselmouth CPP
    enable_voicing_detection: bool = False     # PYIN 决策质量评估
    enable_torchcrepe_fallback: bool = False   # CREPE f0 降级 (现通过 _analyze_pitch 集成)
```

### 算法移植细节

所有新算法通过 Feature Flag 默认关闭，开启后 1:1 替换 `AudioFeaturesService` 中的对应计算:

| 维度    | 旧实现                      | 新实现 (flag 开启时)                                                                                 |
| ------- | --------------------------- | ---------------------------------------------------------------------------------------------------- |
| HNR     | HPSS 谐波/冲击分离          | de Krom 1993 倒谱域分离, 4 频带 (500/1500/2500/3500Hz), 边界检测已修复                               |
| CPP     | 手动 FFT 倒谱 (peak - mean) | VoiceLab`parselmouth.Spectrum` → `To PowerCepstrum` → `Get peak prominence`, 归一化 `/6.0` |
| f0 提取 | librosa.yin                 | PYIN + TorchCREPE 降级 (detection_rate < 0.5 时), 已集成到生产管线                                   |
| voicing | 无                          | 自一致性评估 (范围/八度跳跃/切换一致性/能量一致性), 矢量优化                                         |

> ⚠️ **v6.2.1 重要修复**: 以上 Feature Flag 算法在 v6.2 发布后因 `upload.py` 未实例化 `FeatureFlags()` 而从未在线上执行。v6.2.1 已修复，所有算法正式激活。

### 真音频效果 (tests/test_data/audio/vocal)

> **测试准则**: 优先使用 `tests/test_data/audio/vocal/` 中的 5 首真实人声音频获取反馈。
> 该目录包含 4 首高分 + 1 首低分演唱，文件名即标签。

| 音频 (258s)     | Default | v5.18 (全开) | 变化            | 说明                             |
| --------------- | ------- | ------------ | --------------- | -------------------------------- |
| 1（高分） Tech  | 77.5    | 92.5         | **+15.0** | CPP 从失效(51分)恢复到正常(85分) |
| 1（高分） Total | 73.6    | 77.0         | +3.4            | Tech 权重仅 20%, 限制了总影响力  |

**关键发现**: 旧 CPP 算法对所有音频返回 ~0.018 (几乎无区分度)，VoiceLab CPP 返回 5-40 dB 范围，恢复了 CPP 维度的评分能力。

### 已知局限 (v5.19 → v6.1)

| 问题                       | 说明                                                                          | 计划                 |
| -------------------------- | ----------------------------------------------------------------------------- | -------------------- |
| **跨维度集成待启用** | Feature Flag + 基础设施已就绪, HNR/Voicing 数据待反馈到评分                   | v6.0 校准后启用      |
| CPP 归一化因子             | VoiceLab CPP 通过`/6` 映射到评分阈值, 未校准                                | v6.0 校准数据集      |
| ~~HNR 天花板效应~~        | ✅ v5.19: 流行 12→22dB, 美声 20→28dB, CPP 1.0→2.5                          | 已修复               |
| ~~Voicing 诊断未入评分~~  | ✅ v5.19:`_voicing_detection` 字段已预留, 集成路径已标注                    | 基础设施就绪         |
| **气息评分低分偏高** | 差歌手呼吸 ~80 分 (接近好歌手 67-88), 因 breath_design 子指标与演唱质量弱相关 | v6.0 校准 + 质量门控 |

---

## 后续路线图

### ✅ v5.19: 评分区分度修复 (已完成 2026-07-04)

| 任务                           | 说明                                              | 状态             |
| ------------------------------ | ------------------------------------------------- | ---------------- |
| HNR/CPP 天花板重校准           | 流行 HNR 12→22dB, CPP 1.0→2.5                   | ✅ 完成          |
| 气息基线降低                   | 四子维度基线 40→10, 加分扩大                     | ✅ 完成          |
| 音准阈值扩展                   | MAE 8/45/65 + 斜率 *10→*30                       | ✅ 完成          |
| 音量维度独立                   | volume = f(dynamic_range) 替代 =breath_score      | ✅ 完成          |
| 跨维度 Feature Flag            | `enable_cross_dimension_modifiers` + 集成点标注 | ✅ 基础设施就绪  |
| HNR 稳定性 → Breath 修正      | 跨频带 CV 高 → 气息不稳惩罚                      | 📋 v6.0 (需校准) |
| Voicing 置信度 → Pitch 可信度 | 低置信度降低音准权重                              | 📋 v6.0 (需校准) |

### v6.1: 校准数据集 + 六维评分完善 + 算法增强

| 任务                                               | 优先级 | 工作量 |
| -------------------------------------------------- | ------ | ------ |
| 3×3 对照数据集 (3首歌 × 3水平)                   | P0     | 2天    |
| 校准工具脚本 + 校准报告                            | P0     | 2天    |
| 优先校准: CV断点, Breath基线, Artistry上限         | P0     | 1天    |
| 六维评分配置完善                                   | P1     | 1天    |
| f0 节奏路径恢复 (校准验证后)                       | P1     | 1天    |
| Technique baseline 重构 (移除硬编码50分地板)       | P0     | 1天    |
| Breath 子维度评分连续化 (替换步进加分)             | P0     | 1天    |
| 跨维度集成启用 (HNR稳定性→Breath, Voicing→Pitch) | P1     | 2天    |

### v6.1: 算法增强 + 混响补偿管线接入

| 任务                                                     | 优先级 |
| -------------------------------------------------------- | ------ |
| 混响补偿接入评分管线 (ReverbCompensator → HNR/CPP 修正) | P1     |
| SVQTD 7属性分类器接入                                    | P2     |
| ECAPA-TDNN 音色分析 (明亮度/厚度)                        | P2     |
| 歌曲模板系统                                             | P2     |

### v7.0: Electron 桌面应用 + Vue 3 前端重构

> 详见 [PRD.md §9](../1-product/PRD.md#9--v70--electron-桌面应用--vue-3-前端重构-规划中)

| 任务                                       | 优先级 | 工作量 |
| ------------------------------------------ | ------ | ------ |
| Vite + Vue 3 项目初始化 + Electron 集成    | P0     | 3 天   |
| Flask 子进程管理 (Electron 主进程)         | P0     | 2 天   |
| 核心页面 Vue 重构 (首页 + 报告页)          | P0     | 5 天   |
| 完整页面迁移 (历史/对比/演唱/设置/曲库)    | P0     | 5 天   |
| 原生增强 (系统托盘/菜单/文件关联/自动更新) | P1     | 3 天   |
| electron-builder + PyInstaller 打包配置    | P0     | 3 天   |
| 全量测试 + 跨平台验证                      | P0     | 3 天   |

---

## 性能基准

### 端到端模式性能

| 指标             | v5.15  | v5.16     | v5.17     | v5.18 目标    |
| ---------------- | ------ | --------- | --------- | ------------- |
| Quick 耗时       | ~40s   | ~15-20s   | ~15-20s   | < 30s ✅      |
| Pro 耗时 (CPU)   | ~226s  | ~130-170s | ~130-170s | < 180s (已达) |
| Pro 耗时 (GPU)   | —     | —        | ~30-50s   | < 60s ✅      |
| 内存峰值 (Quick) | ~800MB | ~800MB    | ~800MB    | < 400MB       |
| 内存峰值 (Pro)   | ~1.2GB | ~1.2GB    | ~1.2GB    | < 800MB       |
| 首次启动         | ~8s    | ~8s       | ~8s       | < 10s ✅      |

### 特征提取阶段耗时 (3min 音频, 44.1kHz)

| 特征提取器          | v5.17 实际 | 预算   | 状态                      |
| ------------------- | ---------- | ------ | ------------------------- |
| voice_quality       | ~1.5s      | < 2s   | ✅                        |
| PYIN f0             | ~5-7s      | < 8s   | ✅                        |
| onset strength      | ~2-3s      | < 3s   | ✅                        |
| HNR + CPP           | ~2-3s      | < 3s   | ✅                        |
| RMS + breath 四维度 | ~1-2s      | < 2s   | ✅                        |
| technique 检测      | ~2-3s      | < 3s   | ✅                        |
| acoustic 混合检测   | ~0.5s      | < 1s   | ✅                        |
| 自参照一致性        | ~0.5s      | < 1s   | ✅                        |
| 评分计算            | ~0.5s      | < 1s   | ✅                        |
| Phrase 逐句         | ~3-5s      | < 5s   | ✅                        |
| Visualization       | ~6-8s      | < 10s  | ✅                        |
| Demucs (CPU)        | ~100-130s  | < 140s | ✅                        |
| Demucs (GPU)        | — (无GPU) | < 30s  | ⏳ 需重装 CUDA 版 PyTorch |

### 前端性能

| 指标            | v5.17 实际             | 目标              | 状态                   |
| --------------- | ---------------------- | ----------------- | ---------------------- |
| FCP (首屏)      | ~1.8s (未优化)         | < 1.5s            | ⏳                     |
| TBT             | ~300ms (inline styles) | < 200ms           | ⏳                     |
| 路由切换        | ~200ms (含旧 CSS 动画) | < 300ms (含 GSAP) | ✅                     |
| GSAP 动画帧率   | — (未测量)            | ≥ 30fps          | ⏳ 待测量              |
| Canvas 实时绘制 | — (未启用)            | ≥ 30fps          | ⏳ v6.0                |
| JS Bundle       | ~280KB (未 gzip)       | < 300KB gzip      | ⚠️ 需确认            |
| CSS 总体积      | ~45KB (含 inline)      | < 50KB gzip       | ⚠️ inline style 过多 |

### 模式一致性

| 指标                | v5.15       | v5.16                    | v5.17           | 目标     |
| ------------------- | ----------- | ------------------------ | --------------- | -------- |
| Quick/Pro Rhythm 差 | -11.1       | -4.4                     | -4.4            | < 5 ✅   |
| Quick/Pro Breath 差 | -46.6       | **-0.1**           | **-0.1**  | < 5 ✅   |
| Quick/Pro Total 差  | -12.5       | -1.1                     | -1.1            | < 10% ✅ |
| 单元+集成测试       | 89/91 (98%) | **128/128 (100%)** | ✅ 超额达标     |          |
| TDD RED 测试        | —          | **13 xfail**       | 🆕 引导 v5.18+  |          |
| 真实音频回归        | —          | **5 文件基线**     | 🆕 防止评分退化 |          |
| JS 集成测试         | 30 mock     | **16 真实模块**    | 🆕 不再全 mock  |          |

### 未测量指标 (v5.18 待建立)

| 指标                      | 计划测量方式                |
| ------------------------- | --------------------------- |
| 内存泄漏 (连续 10 次 Pro) | `tracemalloc` diff        |
| DTW 对齐耗时 vs 音频长度  | 基准音频 × 3 个长度        |
| 文件上传吞吐              | 50MB 文件计时               |
| 历史记录查询 (1000条)     | JSON 反序列化计时           |
| 报告 PDF 生成 (含图表)    | `time.perf_counter()`     |
| 前端动画帧率              | Chrome DevTools Performance |
| 长时间使用内存            | 30min + 50次页面切换        |

---

## 验收状态

```
✅ 非人声检测归零 (白噪声 → 0分, 10/10)
✅ 合成音频归零验证
✅ 评分区分度 0-100 全范围
✅ 艺术评分区分度 28.4 分 (v5.14)
✅ Quick/Pro Total 分差 < 10%
✅ Quick/Pro Breath 分差 < 5
✅ Quick/Pro Rhythm 分差 < 5
✅ SingMOS 完全移除 (v5.15)
✅ DTW 参考搜索默认化 (v5.15)
✅ Pro Rhythm 崩塌修复 (v5.15)
✅ Pro Breath 崩塌修复 (v5.16)
✅ 混合音频检测 (轻伴奏) (v5.17)
✅ GPU 加速支持 (v5.17)
✅ 测试体系审计与修复 (v5.18)
  ├── 141 单元/集成/TDD 测试全部通过 (0 失败)
  ├── 22 评分稳健性测试 (可重现性、边界值、分布)
  ├── 24 SPA E2E 测试 (Hash 路由、全页面渲染)
  ├── 7 v5.18 集成测试 (端到端管线, 含真音频对比) 🆕
	  ├── 13 TDD 测试 (7 v5.18 已 GREEN + 6 v6.0 xfail)
  ├── 真实音频回归基线 (5 文件 × 6 维度)
  ├── 16 JS 集成测试 (真实 Store + AnimationController)
  └── 3 旧版 E2E 文件标记 skip (等待 SPA 迁移)
✅ Feature Flag 机制 (v5.18)
✅ 多频带 HNR — de Krom 1993 (VoiceLab 移植)
✅ Praat CPP — parselmouth PowerCepstrum (VoiceLab 移植)
✅ Voicing detection 评估 (pitch-benchmark 模式)
✅ TorchCREPE 备选接入 (PYIN 降级)
✅ FeatureFlags 线上激活 — 7 算法从静默失效→正式启用 (v6.2.1)
✅ SPA querySelector 选择器修复 — 11 处 (v6.2.1)
✅ ReportPage 音频播放器回归 (v6.2.1)
✅ ReportPage PitchCurve 实例化 (v6.2.1)
✅ ComparePage/SingPage 模拟数据→真实API (v6.2.1)
✅ 桌面打包 pywebview + PyInstaller + Inno Setup (v6.2.1)
✅ 一键启动脚本 start.bat (v6.2.1)
⏳ SPA 缺失功能补全 — 波形/频谱/人声分离/音色分析/逐句评分 (v6.3)
⏳ HistoryPage 编码修复 — 文件级 GBK/UTF-8 混乱 (v6.3)
⏳ 跨维度集成 (HNR稳定性→Breath, Voicing→Pitch) (v5.19)
⏳ 气息区分度 ≥ 20 (需校准数据集)
⏳ 音准区分度 ≥ 10 (DTW + 校准)
⏳ HNR/CPP 天花板重校准 (v5.19)
✅ SPA 导航死锁修复 — 三重 Bug, 3 文件 (v5.20)
✅ 前端架构升级 — AppContext + EventBus + Vue 对齐 (v5.20)
```

---

## 参考文档

| 文档         | 路径                                             |
| ------------ | ------------------------------------------------ |
| 产品需求文档 | [PRD.md](../1-product/PRD.md)                     |
| 产品目标     | [GOALS.md](../1-product/GOALS.md)                 |
| 系统架构     | [ARCHITECTURE.md](../2-technical/ARCHITECTURE.md) |
| 评分算法     | [SCORING.md](../2-technical/SCORING.md)           |
| TDD 规范     | [TDD.md](../3-quality/TDD.md)                     |
| BDD 规范     | [BDD.md](../3-quality/BDD.md)                     |
| 变更日志     | [CHANGELOG.md](CHANGELOG.md)                      |
