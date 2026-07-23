# 系统架构 v7.1.0

> 更新: 2026-07-23 | 架构: FastAPI (DDD 四层) + Flask (绞杀者) + Vue 3 SPA | 分支: `feat/v7-fastapi-vue-refactor`
>
> **v7.0 迁移计划**: [V7_MIGRATION_PLAN.md](../4-process/V7_MIGRATION_PLAN.md) — Phase 0-5 ✅
> **v7.1 重构完成**: [PROJECT_STATUS.md](../4-process/PROJECT_STATUS.md) — DDD 评分默认 + 死代码清理 + FCPE 集成
> **v7.1 技术研究**: [TECH_RESEARCH.md](TECH_RESEARCH.md) — 五维度算法验证 + 实施路线

---

## 一、架构总览 (v7.1.0 绞杀者模式)

```
                             ┌─────────────────────┐
                             │    Electron (P5)     │
                             │  main.ts + preload   │
                             │  嵌入式 Python 运行时  │
                             └──────────┬──────────┘
                                        │
                   ┌────────────────────┼────────────────────┐
                   │                    │                    │
            ┌──────▼──────┐    ┌───────▼──────┐    ┌───────▼──────┐
            │  Vue 3 SPA  │    │   FastAPI    │    │  Flask v6.3  │
            │  (生产构建)  │◄───│  v7.1 :8000  │◄───│  /old mount  │
            │  dist/      │    │  + WebSocket │    │  legacy API  │
            └─────────────┘    └──────┬───────┘    └──────────────┘
                                      │
    ┌─────────────────────────────────┼──────────────────────────┐
    │                    backend/ (DDD 四层)                      │
    │                                                             │
    │  ┌──────────────────┐  ┌───────────────────────────────┐   │
    │  │   interfaces/    │  │        application/           │   │
    │  │ api/routes/      │─►│ assessment/                   │   │
    │  │   assessment.py  │  │  ├─ scoring_orchestrator.py 🆕│   │
    │  │   history.py     │  │  ├─ feature_adapters.py    🆕│   │
    │  │ ws/score_handler │  │  └─ history_subscriber.py  🆕│   │
    │  │ schemas/         │  └───────────────────────────────┘   │
    │  │ middleware.py     │                                      │
    │  └──────────────────┘  ┌───────────────────────────────┐   │
    │                        │          domain/              │   │
    │  ┌──────────────────┐  │  assessment/                  │   │
    │  │ infrastructure/  │  │  ├─ pitch_scorer    (10%) ⭐ │   │
    │  │ audio/           │  │  ├─ rhythm_scorer   (10%) ⭐ │   │
    │  │  librosa_loader  │  │  ├─ breath_scorer   (20%) ⭐ │   │
    │  │  pyin_extractor  │  │  ├─ technique_scorer(25%) ⭐ │   │
    │  │  demucs_separator│  │  ├─ muscle_scorer   (25%) ⭐ │   │
    │  │  fcpe_extractor🆕│  │  ├─ artistry_scorer (10%) ⭐ │   │
    │  │  protocols.py 🆕 │  │  └─ timbre_adjuster       ⭐ │   │
    │  │ persistence/     │  │  audio/    (entities+services) │   │
    │  └──────────────────┘  │  comparison/ (entities+services)│   │
    │                        └───────────────────────────────┘   │
    │  ┌──────────────────────────────────────────────────┐      │
    │  │ shared/: event_bus, domain_types(ScoreLevel),    │      │
    │  │          result[T,E]                              │      │
    │  └──────────────────────────────────────────────────┘      │
    └────────────────────────────────────────────────────────────┘
                                      │
    ┌─────────────────────────────────┼──────────────────────────┐
    │              旧服务层 (绞杀者, 逐渐替换)                     │
    │  services/features/ (12 特征提取 — 生产唯一来源)            │
    │  services/scoring/  (8 旧评分器 — flag 回退路径)            │
    │  services/dl_services/ (style/VAD/DTW — 仍在使用)          │
    │  api/business/ (analyze_and_score — 关键桥梁)              │
    └────────────────────────────────────────────────────────────┘
│  │  pitch_scorer │ breath_scorer │ rhythm_scorer             │   │
│  │  technique_scorer │ artistry_scorer │ critical_rules      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              comparison/ DTW 对比引擎                      │   │
│  │  dtw_aligner → deviation_calculator → scoring_engine      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              其他服务                                      │   │
│  │  voice_quality │ visualization │ advice │ phrase │ report │   │
│  │  timbre │ style_aware_scorer │ professional_feedback      │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                   数据层 (Repositories)                           │
│  repositories/history_repository.py  — JSON 文件持久化          │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                   配置层 (Config)                                 │
│  config/default.py  │  services/scoring_config.py               │
│  - 应用配置          │  - 五维阈值 (EmpiricalThresholds)        │
│  - 路径/端口/文件    │  - 风格自适应权重                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 一-A. 架构设计准则: 七维低耦合 + 零硬编码 ★v7.0

> v7.0 迁移必须严格遵守, 每 Phase 验收时检查

### 七维低耦合

| 维度               | 原则                                    | 禁止                                           | 要求                                         |
| ------------------ | --------------------------------------- | ---------------------------------------------- | -------------------------------------------- |
| **代码耦合** | 单一职责: 每个文件只做一件事            | HTTP 解析 + 音频分析 + DB 写入混在同一类       | Route → Service → Repository 分层          |
| **数据耦合** | 跨模块传 Pydantic model, 不传裸 dict    | `func(raw_dict)` 依赖内部 key 名             | `func(UploadResponse)` 编译时类型检查      |
| **环境耦合** | 路径/端口/密钥全部从配置注入            | `Path(__file__).parent.parent / "uploads"`   | `config.UPLOAD_FOLDER` (构造函数注入)      |
| **控制耦合** | 模块间通过返回值/事件通信               | `service._internal_state = x` 直接改内部状态 | EventBus emit / Pinia action                 |
| **外部耦合** | 文件系统/DB/OS 通过接口抽象             | `open("/hardcoded/history.json")` 散落各处   | `HistoryRepo` 接口, 路径注入               |
| **时序耦合** | 异步操作显式声明依赖, 不假设顺序        | "先 A 再 B" 隐式依赖 (忘记 await)              | `result = await A(); await B(result)`      |
| **UI 耦合**  | UI 组件不直读业务状态, 通过 Pinia store | `<el-button @click="window.__score = 95">`   | `<el-button @click="store.submitScore()">` |

### 零硬编码铁律

```
❌ 禁止:  ws://localhost:5000/ws/score     // Electron 打包后端口必然变
❌ 禁止:  http://127.0.0.1:5000            // 换端口 = 改代码
❌ 禁止:  spawn("python", ["main.py"])     // 依赖系统 PATH

✅ 要求:  window.BACKEND_URL + "/ws/score"  // Electron preload 动态注入
✅ 要求:  backend.exe --port=0             // OS 自动分配空闲端口
✅ 要求:  stdout "BACKEND_PORT=12345"      // Electron 捕获端口号
```

### WebSocket 动态端口方案

```
Electron Main Process:
  1. spawn("backend.exe", ["--port=0"])      // OS 自动分配空闲端口
  2. 监听子进程 stdout 第一行输出
  3. 解析: "BACKEND_PORT=12345"
  4. preload.js: contextBridge.exposeInMainWorld("BACKEND_URL", "http://127.0.0.1:12345")

Vue 前端 (任何需要调后端的地方):
  const api = createApiClient(window.BACKEND_URL)                // 唯一 API 入口
  const ws = new WebSocket(`${window.BACKEND_URL.replace("http", "ws")}/ws/score`)

⚠️ 开发模式下 vite.config.ts proxy 可写 localhost:5000 — 但生产代码中绝不出现硬编码地址
```

---

## 一-B. v7.0 生产级保障: 7 大关键模式

> 桌面应用的血泪教训, v7.0 必须从 Day 1 就做对

### 1. 进程守护: spawn 监听 + 自动重启 3 次

```
Electron spawn → 监听 close → 异常则自动重启 (最多3次)
Vue overlay: "引擎加载中..." + 不确定进度条
3次全失败 → 弹错误框, Electron 主进程不崩溃
```

### 2. 日志聚合: loguru + electron-log → userData/logs/

```
前后端日志同目录, 微秒时间戳, 按日切割
排查音频卡顿: 比对时间线 → 定位算法慢 vs 网络慢
```

### 3. 音频资源: onBeforeUnmount 手动 close()

```
context.close() + stream.getTracks().forEach(t => t.stop())
window.__audioCleanup 兜底 — 不依赖 GC, 否则 2h 内存爆满
```

### 4. 环境变量: electron-is-dev

```
开发: Vite proxy → localhost:5000 | 生产: IPC 注入 127.0.0.1:动态端口
```

### 5. 超时降级: asyncio.timeout + GSAP 进度条

```
Quick 30s / Pro 180s → 超时返回部分结果 + "设备性能受限" warning
```

### 6. 持久化: Pinia persist → electron-store

```
store.$persist() 在 onBeforeUnmount 强制调用 → 不丢数据
```

### 7. API 版本号: /api/v1/ 前缀

```
v6.3 同步: POST /api/upload → 阻塞 15s-5min → 返回结果
v7.0 异步: POST /api/v1/upload → {task_id} (立即) → 轮询 GET /tasks/{id}/status
v7.0 实时: WebSocket /ws/v1/score → 音频帧流 → 实时评分事件
```

### 8. 三端联调热更新

```
npm run dev → concurrently:
  vite (Vue HMR) + uvicorn --reload (FastAPI) + nodemon (Electron)
一键启动三进程, 改 Python/Vue/Electron 代码均自动刷新
```

### 9. 音频二进制传输: Float32Array → WebSocket bytes

```
❌ JSON + Base64: 体积 +33%, 延迟 200ms+
✅ Float32Array.buffer → ws.send() → numpy.frombuffer 零拷贝: 延迟 <50ms
```

### 10. DB 连接池预热: @app.on_event("startup") SELECT 1

### 11. 乐观更新: 预估分先上屏 (GSAP 滚动) → WebSocket 静默推送真实分替换

### 12. 嵌入式 Python 运行时: Electron 携带绿色版 Python, 启动 <2s, 增量更新 KB 级 (详见 V7_MIGRATION_PLAN.md ADR-1)

### 13. 崩溃自愈: sys.excepthook → userData/crash/.zip → Vue 隐藏入口导出诊断包

### 音频采集策略

```
实时: AudioWorklet → PCM Float32Array → WebSocket 二进制帧 (16kHz, 2048 samples)
上传: MediaRecorder → MP3/WebM → HTTP Upload → FFmpeg → PCM
```

---

## 二、目录结构 (v5.17 实际)

```
vocal_assessment_light/
├── api/                              # API 层 — Flask 蓝图
│   ├── __init__.py                   # 蓝图注册 + /health 端点 + GPU 检测
│   ├── errors.py                     # 统一错误处理
│   ├── response_builder.py           # 响应格式构建
│   ├── schemas.py                    # 请求/响应 Schema
│   └── business/
│       └── audio_analysis.py         # 核心分析编排: analyze_and_score()
│
├── services/                         # 服务层 — 所有业务逻辑
│   ├── audio_service.py              # 音频分析主服务 (三模式入口)
│   ├── score_service.py              # 总分协调: ScoreServiceV4.calculate()
│   ├── separation_service.py         # Demucs 人声分离 + GPU 检测
│   ├── voice_quality_service.py      # 人声质量检测 (is_voice判定)
│   ├── audio_features_service.py     # 特征提取统一入口
│   ├── visualization_service.py      # 频谱/基频/能量图生成
│   ├── advice_service.py             # 改进建议生成
│   ├── phrase_service.py             # 逐句评分
│   ├── report_service.py             # PDF/图片报告导出
│   ├── timbre_service.py             # 音色分析
│   ├── style_aware_scorer.py         # 风格自适应评分
│   ├── style_config_loader.py        # 风格配置加载
│   ├── style_adjustment_strategies.py # 风格调整策略
│   ├── professional_feedback.py      # 专业模式反馈
│   ├── scoring_config.py             # ★ 所有阈值集中管理
│   │
│   ├── features/                     # 特征提取
│   │   ├── pitch.py                  # PYIN 基频提取 + 音分偏差
│   │   ├── breath.py                 # 四子维度气息分析
│   │   ├── rhythm.py                 # Onset 检测 + CV 分段 + 双路径策略
│   │   ├── technique.py             # HNR/CPP/颤音/滑音/假声
│   │   └── acoustic.py              # 混合音频检测 + 通用声学特征
│   │
│   ├── scoring/                      # 评分计算
│   │   ├── pitch_scorer.py           # 音准评分 (MAE + 惩罚项)
│   │   ├── rhythm_scorer.py          # 节奏评分 (偏差 + irregularity)
│   │   ├── breath_scorer.py          # 气息评分 (is_clean_vocal 校准)
│   │   ├── technique_scorer.py       # 技术评分 (HNR/CPP + 技巧加分)
│   │   ├── artistry_scorer.py        # 艺术评分 (四维度复合 + 声学调制)
│   │   └── critical_rules.py         # 关键规则 (硬性惩罚)
│   │
│   ├── comparison/                   # DTW 对比分析
│   │   ├── dtw_aligner.py            # 三级对齐引擎 (全局→句→音符)
│   │   ├── deviation_calculator.py   # 逐帧偏差计算
│   │   ├── scoring_engine.py         # DTW 评分引擎
│   │   ├── benchmark_service.py      # 基准音频库管理
│   │   └── comparison_service.py     # 对比分析主服务
│   │
│   ├── matching/                      # ★ v6.0 歌曲匹配引擎
│   │   ├── feature_extractor.py       # 快速特征提取 (BPM/Key/Chromaprint)
│   │   ├── similarity_scorer.py       # 多维度相似度评分
│   │   └── matcher.py                 # 匹配编排: 搜索→排序→阈值判定
│   │
│   └── dl_services/                  # 深度学习服务 (精简后)
│       ├── voice_quality_detector.py # 基于声学特征的人声判定
│       ├── singing_style_classifier.py # 演唱风格分类
│       ├── dl_quality_assessor.py    # DL 质量评估 (已禁用)
│       └── model_manager/            # 模型加载管理
│
├── repositories/                     # 数据层 — 仓储模式
│   ├── history_repository.py         # JSON 历史记录 CRUD
│   └── song_repository.py            # ★ v6.0 标准歌曲数据库 (SQLite)
│   └── history_repository.py         # JSON 文件历史记录 CRUD
│
├── config/                           # 配置管理
│   └── default.py                    # Flask + 路径 + 模型默认配置
│
├── core/                             # 核心算法 (桌面版遗留，部分被 services/ 替代)
│   ├── audio_analyzer.py             # 音频分析
│   ├── vocal_processor.py            # 人声处理
│   ├── comparison_analyzer.py        # 对比分析
│   ├── recorder.py                   # 录音控制
│   └── workers/                      # ⚠️ PyQt5 信号槽 (桌面版遗留)
│       ├── signals.py                # Qt Core QObject + Signal
│       └── manager.py                # Qt QThreadPool 线程管理
│
├── web/                              # 前端 (v5.20 架构升级)
│   ├── static/
│   │   ├── app.js                    # 应用入口 (createApp 模式)
│   │   ├── router.js                 # HashRouter (useContext 注入)
│   │   ├── index.html                # SPA HTML 入口
│   │   └── js/
│   │       ├── AppContext.js       🆕 # 依赖注入容器 (v7.0 → provide/inject)
│   │       ├── EventBus.js         🆕 # 事件总线 (v7.0 → mitt)
│   │       ├── state/store.js        # 全局状态 (v7.0 → Pinia)
│   │       ├── services/api.js       # API 客户端 (v7.0 → HTTP/IPC)
│   │       ├── animation/
│   │       │   ├── Controller.js     # GSAP 统一控制器
│   │       │   └── presets.js        # 动画预设库
│   │       ├── components/
│   │       │   ├── BaseComponent.js  # 组件基类 (context 注入, Vue 生命周期)
│   │       │   ├── Navigation.js     # TopNav + BottomNav
│   │       │   ├── Toast.js          # Toast 通知
│   │       │   ├── Modal.js          # 模态框
│   │       │   └── ProgressBar.js    # 进度条
│   │       ├── pages/                # 页面组件 (继承 BaseComponent)
│   │       │   ├── HomePage.js       # 首页
│   │       │   ├── SingPage.js       # 演唱录制
│   │       │   ├── ReportPage.js     # 评分报告
│   │       │   ├── HistoryPage.js    # 历史记录
│   │       │   ├── ComparePage.js    # 对比分析
│   │       │   ├── SettingsPage.js   # 系统设置
│   │       │   └── SongLibraryPage.js # 标准曲库
│   │       ├── modules/              # 功能模块
│   │       │   ├── state.js, api.js, audio.js, charts.js, recording.js, utils.js
│   │       └── plots/                # 生成的可视化图片
│
├── api/sse/                           # ★ v6.0 SSE 流式推送
│   ├── analysis_progress.py           # 上传分析进度推送 (8 events)
│   └── record_stream.py              # 录音实时 chunk 接收 + 分析
│
├── web_app.py                        # ★ Flask 应用工厂 + SSE 端点注册
├── main.py                           # 旧入口 (保留)
├── model_manager.py                  # Demucs 模型单例管理
├── tests/                            # 测试
└── docs/                             # 文档 (本目录)
```

---

## 三、数据流

### 3.1 Quick 模式

```
POST /api/upload?mode=quick
  │
  ▼
audio_analysis.analyze_and_score()
  │
  ├─[1] voice_quality_service.check_voice_quality()
  │     └─ 非人声? → is_voice=False, total_score=0 → 直接返回
  │
  ├─[2] audio_features_service.extract_all_features()
  │     ├─ features/reverb.py   → ReverbCompensator (v6.0, 可选, HPSS+谱减法)
  │     ├─ features/pitch.py     → PitchDeviationResult
  │     ├─ features/rhythm.py    → RhythmAlignmentResult
  │     ├─ features/breath.py    → BreathStabilityResult
  │     ├─ features/technique.py → VocalTechniqueResult
  │     └─ features/acoustic.py  → detect_mixed_audio() [v6.0 五特征融合]
  │
  ├─[3] score_service.ScoreServiceV4.calculate()
  │     ├─ scoring/pitch_scorer.py
  │     ├─ scoring/rhythm_scorer.py
  │     ├─ scoring/breath_scorer.py
  │     ├─ scoring/technique_scorer.py
  │     ├─ scoring/artistry_scorer.py (四维度复合评分)
  │     └─ _self_consistency_penalty() (自参照一致性)
  │
  └─[4] advice_service.generate_advice() → 响应 JSON
```

**耗时**: ~15-20s (特征提取 ~12s + 评分 ~3s)
**内存**: 峰值 ~400MB (音频加载 ~50MB + 特征缓冲 ~100MB + Python 开销)
**性能关键路径**: PYIN f0 提取 → 5s, onset strength → 2s, 四个特征可并行但受 GIL 限制

#### ★ v6.0 SSE 流式推送 (适用于所有上传分析模式)

```
POST /api/upload (Quick/Pro)
  │
  ├─ 返回 { task_id: "abc123" } (立即, ~100ms)
  │
  ├─ 后台异步执行分析管线
  │
  └─ Client 连接 GET /api/analysis/progress?task_id=abc123 (SSE)
       │
       ├─ event: voice_check     data: { is_voice: true, progress: 5 }
       ├─ event: feature_pitch   data: { f0_curve: [...], progress: 15 }
       │   └─ ★ 前端收到后立即渲染音准曲线 → 用户可播放查看
       ├─ event: feature_rhythm  data: { onsets: [...], progress: 30 }
       ├─ event: feature_breath  data: { hnr: 18.5, ... progress: 45 }
       ├─ event: feature_technique data: { vibrato_count: 3, ... progress: 60 }
       ├─ event: scoring         data: { partial_scores: {...}, progress: 80 }
       ├─ event: matching        data: { matched_song: {...} | null, progress: 85 }
       └─ event: complete        data: { full_result: {...}, progress: 100 }
```

> **关键体验**: feature_pitch 在 15% 进度时即推送 → 用户不必等 100% 就能看到音准曲线并开始播放。分析进度透明化, 不锁界面。

### 3.2 Professional 模式

```
POST /api/upload?mode=professional
  │
  ▼
audio_analysis.analyze_and_score()
  │
  ├─[1] voice_quality_service.check_voice_quality()
  │
  ├─[2] acoustic.detect_mixed_audio()
  │     └─ 是混合音频? → separation_service.separate() (Demucs, ~100-150s CPU)
  │                    → 否 (纯人声) → 直接使用原始音频
  │
  ├─[3] audio_features_service.extract_all_features(is_separated=...)
  │     ├─ is_clean_vocal 标记传递到 breath.py / rhythm.py
  │     ├─ breath.py: 纯净人声波动惩罚放宽 (0.25→0.35, 60→30)
  │     └─ rhythm.py: 纯净人声 CV 阈值 ×3 重校准
  │
  ├─[4] score_service.ScoreServiceV4.calculate()
  │     ├─ breath_scorer: is_clean_vocal 等级阈值放宽 (85→73/70→58/55→43)
  │     ├─ breath_scorer: 总分补偿 ×1.8
  │     └─ rhythm_scorer: 跳过 is_clean_vocal irregularity 双重惩罚
  │
  ├─[5] phrase_service.analyze_phrases() → 逐句评分
  ├─[6] visualization_service.generate_plots() → 频谱/基频/能量图
  └─[7] professional_feedback.generate() → 详细反馈
```

**耗时**: ~130-170s CPU / ~30-50s GPU (Demucs 占比 ~80%)
**内存**: 峰值 ~1.2GB (Demucs 模型 ~500MB + PyTorch 中间张量 ~300MB + 音频缓冲)
**性能降级**: GPU 不可用时自动回退 CPU; 内存不足 (< 2GB) 时跳过 Demucs 直接 Quick 评分

### 3.3 Compare 模式 ★v6.0 (DTW 降级为特征提供者)

```
POST /api/compare
  │
  ▼
comparison/comparison_service.compare()
  │
  ├─[1] audio_features_service 提取两路特征
  │     ├─ reference: pitch_curve + onset
  │     └─ user: pitch_curve + onset
  │
  ├─[2] dtw_aligner.align() — 三级对齐
  │     └─ 产出: warp_path + segment_confidences
  │
  ├─[3] deviation_calculator.calculate() — ★ 仅产出偏差数据
  │     ├─ dtw_pitch_cents: float[]    逐帧音分偏差
  │     ├─ dtw_rhythm_offset: float[]  逐帧节拍偏移 (ms)
  │     └─ alignment_confidence: float 全局置信度
  │     (不再产出 dtw_score / dtw_pitch_score / dtw_breath_score)
  │
  ├─[4] ★ ScoreServiceV4.calculate(dtw_data=...)
  │     ├─ pitch_scorer:   PYIN + dtw_pitch_cents 加权融合 (DTW≤70%)
  │     ├─ rhythm_scorer:  onset + dtw_rhythm_offset 加权融合 (DTW≤50%)
  │     ├─ breath_scorer:  四子维度独立 (DTW 不参与)
  │     ├─ technique_scorer: HNR/CPP/技巧 (DTW 不参与)
  │     ├─ artistry_scorer: 四维复合 (DTW 不参与)
  │     └─ critical_rules: 全局生效 (DTW 不参与)
  │
  └─[5] 响应: 五维评分 + dtw_metadata (偏差摘要, 用于前端可视化)
```

**耗时**: ~45s (DTW 对齐 ~40s + ScoreServiceV4 ~5s)
**复杂度**: DTW O(n×m) — 对 3 分钟音频 (~180s×100fps) 约 18000×18000 矩阵，通过三级对齐 (全局→句→音符) 降为分段 O(k×n²) 其中 k=句数
**内存**: DTW 累积矩阵 ~130MB (18000² × 4 bytes)，分段后 ~10MB/句

### 3.4 ★ v6.0 自动匹配 + 对比模式 (轨道A)

```
POST /api/upload (任意模式)
  │
  ├─[1] voice_quality_service.check_voice_quality()
  │     └─ 非人声? → 直接返回 is_voice=False
  │
  ├─[2] matching/feature_extractor.extract_quick_features()
  │     ├─ 提取: BPM, Key (chroma), Spectral fingerprint (chromaprint)
  │     └─ 耗时: ~2-3s
  │
  ├─[3] matching/matcher.search(features)
  │     ├─ song_repository.query() → 取所有预计算特征
  │     ├─ similarity_scorer.score() — 多维度加权:
  │     │   ├─ BPM 相似度 (容忍 ±15%)
  │     │   ├─ Key 相似度 (同调 / 关系调 / 邻近调)
  │     │   ├─ Chromaprint 相关度 (音频指纹)
  │     │   └─ 时长比例 (0.5x-2x)
  │     ├─ 排序 → Top-K 候选
  │     ├─ 最佳匹配置信度 > 阈值 (0.6)?
  │     │   ├─ YES → matched_song = {id, title, artist, confidence}
  │     │   └─ NO  → matched_song = null, fallback_reason = "no_match"
  │     └─ 耗时: ~2-3s (100 首歌曲)
  │
  ├─[4] 匹配成功?
  │     ├─ YES → DTW 对比路径
  │     │   └─ comparison/dtw_aligner (标准歌曲 vs 用户音频)
  │     │
  │     └─ NO  → ★ 完整绝对评分管线 (Quick/Pro)
  │              ├─ audio_features_service (特征提取)
  │              ├─ score_service.ScoreServiceV4 (五维评分)
  │              │   ├─ 所有 v5.x 算法优化生效
  │              │   ├─ Feature Flag 控制生效 (v5.18)
  │              │   └─ 校准数据集参数生效 (v6.0 轨道B)
  │              └─ advice_service (改进建议)
  │
  └─[5] 响应: matched_song + scoring_mode + 完整 scores
```

> **回退 ≠ 降级**: 匹配失败时的绝对评分走完整的五维评分管线（§3.1 Quick 或 §3.2 Pro），所有算法优化（多尺度HNR、Praat CPP、校准参数等）在回退路径中完全生效。

**匹配耗时增加**: ~5s (特征提取 2-3s + 数据库搜索 2-3s)，成功时总耗时 = 匹配 + DTW (~50s)，失败时总耗时 = 匹配 + 绝对评分 (~25s，特征提取复用匹配阶段结果)。

### 3.5 ★ v6.0 选歌 → 录音 → DTW 对比 (流式实时分析)

```
GET /api/songs → 浏览曲库 → 用户选择歌曲
  │
POST /api/record/stream (song_id?)
  │
  ├─ SSE 连接建立
  ├─ 前端 MediaRecorder 每 2s 发送一个 audio chunk
  │
  ├─[后端实时处理, 每收到 chunk]
  │   ├─ 追加到 session 音频缓冲区
  │   ├─ 实时基频提取 (YIN, 增量计算)
  │   ├─ 实时 onset 检测
  │   └─ SSE 推送: pitch_stream (基频采样点)
  │
  ├─[累积 ≥ 15s 数据后]
  │   ├─ 计算 partial_score: pitch_score + rhythm_score
  │   └─ SSE 推送: partial_score
  │
  ├─[用户点击停止录音]
  │   ├─ SSE 推送: recording_stopped
  │   ├─ 处理剩余未分析 chunks
  │   ├─ 若已选歌 → 直接 DTW 对比
  │   ├─ 若未选歌 → 曲库匹配 → 命中=DTW, 未命中=绝对评分
  │   └─ SSE 推送: final_score (完整五维评分)
  │
  └─ ★ 从停止到 final_score: <10s (2min 录音) / <3s (<30s 录音)

**Chunk 处理性能**:
- 每 chunk 独立处理时间: < 500ms (YIN 增量 + onset 检测)
- Chunk 缓冲区: 前端 ≤ 6 chunks (12s 音频) → 避免内存无限增长
- 后端 session 音频累积: 最大 10 分钟 → 自动清理策略

> **与旧流程的关键差异**: 旧流程是「录音→保存完整文件→上传→从头分析」, 需要 20-40s。
> 新流程在录音中已分析 80%+ 数据, 停止后仅需处理剩余 ~20%, 体验接近即时。

**Chunk 容错**:
- 每个 chunk 带 `sequence_index`, 后端按序重组
- 网络断开 → 前端缓存 chunks → 恢复后补发
- 最大缓存: 30s 音频数据 (~2MB)

### 3.6 选歌 → 录音 → DTW 对比 (旧版, v5.x)

---

## 四、关键设计决策 (ADR)

### ADR-001: 移除 SingMOS，用自参照一致性替代

- **日期**: 2026-06-03 (v5.15)
- **问题**: SingMOS 在 TTS 合成歌声上训练，对真人演唱严重跨域。实测低分演唱 MOS=95.9 > 高分演唱 MOS=73.9
- **决策**: 完全移除 `dl_assessor` 调用链，替换为 `_self_consistency_penalty()` — 将 f0 分 3 段计算稳定性 CV，段间 CV>0.15 时扣分 (上限 8 分)
- **效果**: Pro 耗时 -83s，消除反向评分污染

### ADR-002: CV 重校准替代原始音频回退

- **日期**: 2026-06-03 (v5.15)
- **问题**: Pro 模式 Demucs 分离后节奏 CV = 134%，原定方案"用分离前原始音频"实测发现混合音频 CV 同样偏高
- **决策**: 在 `_cv_to_deviation(is_clean_vocal=True)` 中阈值 ×3 缩放，同时 RhythmScorer 跳过 irregularity 双重惩罚
- **效果**: Pro Rhythm 18.6 → 66.0 (+255%)

### ADR-003: is_clean_vocal 标记传递链

- **日期**: 2026-06-03 (v5.16), 扩展自 ADR-002
- **问题**: v5.15 只修复了 rhythm 的 is_clean_vocal 传递，breath 管线完全缺失
- **决策**: 建立完整标记传递链: `AudioFeaturesService(is_separated)` → `BreathAnalyzer(is_clean_vocal)` → `BreathStabilityResult.is_clean_vocal` → `BreathScorer`
- **效果**: Pro Breath 9.8 → 56.3 (+474%)

### ADR-004: 歌曲匹配用多特征加权，不用 DL 嵌入 ★v6.0

- **日期**: 2026-06-05 (v6.0 设计)
- **问题**: 如何在海量标准歌曲中快速找到用户翻唱对应的原唱？DL 音频嵌入 (如 OpenL3) 需要 GPU 且跨域不可靠。
- **决策**: 多维度经典特征加权融合:
  - BPM (librosa.beat) — 权重 0.3
  - Key/Chroma (librosa.chroma_cqt) — 权重 0.25
  - Chromaprint 指纹 (acoustid) — 权重 0.35
  - 时长比例 — 权重 0.1
  - 综合阈值: ≥0.6 视为匹配成功
- **理由**: 全部特征可 CPU 实时计算，BPM+Key+指纹 三者互补，对速度/调性变化鲁棒。
- **替代方案**: DTW 暴力比对 (太慢, O(n²))、DL 嵌入 (需 GPU, 跨域风险)

### ADR-005: 配置即真相 — 不设硬编码兜底 ★v6.0

- **日期**: 2026-06-05 (v6.0 设计)
- **问题**: 传统做法是 config 加载失败时回退硬编码默认值，但这会掩盖配置错误。用户改了权重但不生效（因为配置格式错了悄悄回退了），导致评分结果与预期不一致。
- **决策**: 所有评分参数从 `config/styles.yaml` 读取，该文件是唯一真相来源 (Single Source of Truth)。文件缺失或格式错误 → 启动阶段 `ConfigError` → 拒绝服务。不设任何硬编码兜底值。
- **理由**: 静默降级是调试噩梦。启动即报错让问题立即暴露，修复成本远低于事后排查「为什么权重没生效」。
- **影响**: 评分逻辑中消除所有 `DEFAULT_WEIGHTS` 硬编码常量。`/health` 在配置正常时返回 `config_status: "ok"` + `config_fingerprint`。

### ADR-006: 评分不使用 DL 模型 (Wav2Vec2/wvmos/CREPE 已移除)

- **日期**: 2026-06-03 (v5.12-v5.15)
- **问题**: Wav2Vec2 (情绪)、wvmos (自然度)、CREPE (f0) 三个 DL 模型均存在跨域或可靠性问题
- **决策**: 全部移除。评分引擎回归经典信号处理 (PYIN + HNR + CPP + Onset Detection)，仅保留 Demucs 用于人声分离

### ADR-007: DTW 降级为特征提供者, 不打分 ★v6.0

- **日期**: 2026-06-05 (v6.0 设计)
- **问题**: 当前 DTW 对比管线中 scoring_engine.py 越界评分 — 用能量包络对齐测"气息"(实际测的是节奏同步性)，技术和艺术维度直接缺失。Bohm 2017 实验: 纯DTW评分与人工听感相关度仅 0.52，DTW+声学特征融合达 0.87。
- **决策**: 
  - `scoring_engine.py` 移除所有 `_score_*()` 方法，仅输出偏差数据 (dtw_pitch_cents, dtw_rhythm_offset, warp_path, confidence)
  - `ScoreServiceV4` 作为唯一评分入口，pitch_scorer 和 rhythm_scorer 接收 DTW 偏差数据做加权融合
  - breath/technique/artistry/critical_rules 零改动，DTW 完全不参与
  - 融合权重由对齐置信度动态调节: pitch_dtw_weight ≤ 0.70, rhythm_dtw_weight ≤ 0.50
- **效果**: 对比分析路径改走五维评分管线，DTW 回归其擅长的角色 (精确对齐工具)。代码改动 ~200 行，breath_scorer/technique_scorer/artistry_scorer/critical_rules 四个文件零改动。

---

## 五、性能设计决策 (Performance ADRs)

### PERF-001: 单请求模型 — 避免并发竞争

- **决策**: Flask 单线程处理，不引入后台队列或多 worker
- **理由**: 音频分析是 CPU/GPU 密集型，并发会导致内存翻倍 (Demucs ×2 → 2.4GB+) 和 GPU OOM。用户场景为个人练习，无并发需求
- **性能影响**: 第二个请求需排队等待，前端应显示"分析中"状态阻止重复提交
- **未来考虑**: 如需支持多用户/并发，应引入 job queue (Redis + RQ) 限制并发数为 1

### PERF-002: 特征提取串行执行

- **决策**: 特征提取按顺序 (pitch → rhythm → breath → technique → acoustic)，不并行
- **理由**: 五者共享音频数据缓冲区，并行会导致内存峰值 ×5。librosa 大部分操作已用 numpy 向量化 (SIMD)，GIL 下并行收益有限
- **性能影响**: 串行 ~12s vs 理论并行 ~5s，但内存 1.5GB vs 400MB

### PERF-003: SSE 替代 WebSocket

- **决策**: 分析进度和录音流使用 SSE (Server-Sent Events)，不使用 WebSocket
- **理由**: SSE 单向推送满足需求（客户端不需要推送数据到分析进度端点），协议更轻量，无需心跳维护，浏览器原生自动重连
- **性能影响**: SSE 重连开销 < 50ms (localhost)，无 keepalive ping 开销

### PERF-004: Canvas 低性能降级

- **决策**: 实时音高 Canvas 根据硬件自动调整渲染精度
- **触发条件**: `navigator.hardwareConcurrency < 4` 或用户手动切换
- **降级行为**: 帧率 60→30fps, 抗锯齿关闭, 偏差色带简化, 粒子效果禁用
- **恢复**: 设备性能改善时自动恢复（监听 concurrency 变化？不，只在页面加载时检测一次）

---

## 六、技术债务

| 债务 | 说明 | 优先级 |
|------|------|--------|
| core/ 与 services/ 功能重叠 | audio_analyzer / comparison_analyzer 部分功能已在 services/ 重写 | P2 |
| **core/workers/ PyQt5 信号槽** | `signals.py` 定义了 Qt 信号，`manager.py` 使用 QThreadPool。这是桌面版 (PyQt5) 遗留代码，Web 版 (Flask) 不使用。保留用于未来桌面端构建 | P2 |
| main.py 旧入口 | 功能已被 web_app.py 覆盖 | P3 |
| 23 个经验参数 | scoring_config.py 中全部 [经验估计]，0 个 [实验校准] | P1 |
| tests/tools/ 散落测试脚本 | 8 个工具脚本未纳入 pytest 标准框架 | P2 |
| **特征提取无定时监控** | 各特征提取器无独立耗时埋点，无法定位性能退化 | P2 |
| **Demucs 强制全曲分离** | 不支持仅分离人声段落（前奏/间奏 也分离），浪费 ~20% 时间 | P3 |

---

## 六、前端架构升级 — v7.0 Vue 迁移映射 (v5.20)

### 6.1 AppContext — 依赖注入容器

`web/static/js/AppContext.js` — 聚合 store / router / api / ac / events 五大服务。
```

app.js (createApp 模式)
  └─ new AppContext({ store, router, api, ac, events })
       │
       ├─ context.store   → 所有组件通过 BaseComponent.store 访问
       ├─ context.router  → 路由器通过 useContext(context) 注入
       ├─ context.api     → API 客户端
       ├─ context.ac      → 动画控制器
       └─ context.events  → 跨组件事件通信

```

**v7.0 迁移**: `AppContext` → Vue `app.provide('context', ...)` + `inject('context')`

### 6.2 EventBus — 事件总线

`web/static/js/EventBus.js` — 解耦跨组件通信, API 对齐 `mitt()`。

|| 方法 | 说明 |
||------|------|
|| `on(event, handler)` | 监听 |
|| `once(event, handler)` | 一次性监听 |
|| `off(event, handler?)` | 移除 |
|| `emit(event, ...args)` | 触发 |

**命名约定**: `domain:action` (e.g. `analysis:complete`, `route:changed`, `system:online`)

**v7.0 迁移**: `EventBus` → `mitt()`

### 6.3 Vanilla JS → Vue 3 完整映射
```

Vanilla JS (v5.20+)             Vue 3 (v7.0)
────────────────────────────    ───────────────────────
AppContext                      app.provide() + inject()
  context.store     →           Pinia createPinia() / useStore()
  context.router    →           Vue Router createRouter() / useRouter()
  context.api       →           HTTP client 或 Electron IPC bridge
  context.ac        →           useGsap() composable
  context.events    →           mitt()

BaseComponent                   
  constructor()     →           setup()
  render()          →           <template></template>
  bindEvents()      →           @click / @input 指令
  mount(params)     →           onBeforeMount() + onMounted()
  animateIn()       →           <Transition name="page"></transition>
  beforeUnmount()   →           onBeforeUnmount()
  destroy()         →           onUnmounted() (自动 GC)
  update(data)      →           watch() / computed()
  show() / hide()   →           v-if / v-show + <Transition></transition>
  createElement()   →           直接写 HTML 模板
  get store         →           useStore()
  get router        →           useRouter()
  get api           →           composable / IPC
  get ac            →           useGsap()

HashRouter                      Vue Router
  register(pattern) →           router.addRoute()
  onBeforeNavigate() →          router.beforeEach()
  navigate(hash)    →           router.push()
  start()           →           app.mount('#app')
  useContext()      →           inject('context')
  getCurrentRoute() →           useRoute()

```

### 6.4 迁移策略

| 阶段 | 内容 |
|------|------|
| **当前 (v5.20)** | AppContext + EventBus 已就绪。所有组件通过 `this.context` 访问服务, `window.*` 作回退 |
| **Phase 1 (v7.0)** | Vite + Vue 3 项目初始化。AppContext → `app.provide`。BaseComponent → `<script setup>` |
| **Phase 2 (v7.0)** | 逐页迁移: render() → `<template>`, bindEvents() → 模板指令 |
| **Phase 3 (v7.0)** | HashRouter → Vue Router。移除 `window.*` 全局回退。EventBus → mitt |

---

## 七、参考文档

### 项目文档

| 文档 | 路径 |
|------|------|
| 产品需求文档 | [PRD.md](../1-product/PRD.md) |
| 评分算法详解 | [SCORING.md](SCORING.md) |
| API 接口 | [API.md](API.md) |
| TDD 规范 | [TDD.md](../3-quality/TDD.md) |
| BDD 规范 | [BDD.md](../3-quality/BDD.md) |
| 项目状态 | [PROJECT_STATUS.md](../4-process/PROJECT_STATUS.md) |
| 变更日志 | [CHANGELOG.md](../4-process/CHANGELOG.md) |

### 参考文献 (v6.0)

> **设计原则**: 所有算法必须基于已发表文献，禁止凭空创造方法。详见 [GOALS.md §4.3](../1-product/GOALS.md#43-算法原则-critical)。
> **存储位置**: `参考论文/` (项目根目录，按主题分目录)
> **代码标注**: 每个算法模块注释中标注 `# Reference:` 指向对应论文章节

| 论文 | 应用 | 文件 |
|------|------|------|
| Fitzgerald (2010). "Harmonic/Percussive Separation Using Median Filtering." DAFx | HPSS 特征, 中值滤波分离 | [PDF](../../参考论文/HPSS谐波冲击分离/Fitzgerald_2010_HPSS_Median_Filtering_DAFx.pdf) |
| Driedger, Müller, Disch (2014). "Extending Harmonic-Percussive Separation of Audio Signals." ISMIR | HPSS 门控阈值, 三元分解 H+P+R | [PDF](../../参考论文/HPSS谐波冲击分离/Driedger_Muller_Disch_2014_Extending_HPSS_ISMIR.pdf) |
| Lehner, Schlüter, Widmer (2018). "Online, Loudness-Invariant Vocal Detection in Mixed Music Signals." TASLP 26(8) | 子带频谱平坦度, 特征选择 | [PDF](../../参考论文/歌声检测SVD/Lehner_Schluter_Widmer_2018_TASLP.pdf) |
| Driedger, Müller (2015). "Extracting Singing Voice from Music Recordings by Cascading Audio Decomposition Techniques." ICASSP | 级联分解策略 | [PDF](../../参考论文/歌声分离/Driedger_Muller_2015_Singing_Voice_Cascade_ICASSP.pdf) |
| Boll (1979). "Suppression of Acoustic Noise in Speech Using Spectral Subtraction." IEEE Trans. ASSP 27(2) | 谱减法 (ReverbCompensator) | ⚠️ IEEE 付费墙, 公式在 `services/features/reverb.py` |

---

## 第六章: v7.0 架构迁移 (FastAPI + Vue 3 + Electron)

> **完整计划**: [V7_MIGRATION_PLAN.md](../4-process/V7_MIGRATION_PLAN.md) — 绞杀者模式六阶段渐进替换, 8 项 ADR, 26.5 天
>
> 本文档仅保留架构设计准则 (一-A, 一-B) 和数据流示例。迁移策略、端点映射、Phase 划分、文件清单等详见专用计划文档。

### 技术栈变更

| 层级 | 当前 (v6.3) | 目标 (v7.0) |
|------|------------|------------|
| 后端框架 | Flask 3.0 | FastAPI (uvicorn) |
| 数据校验 | `request.get_json()` + dict | Pydantic v2 BaseModel |
| 路由 | Blueprint | APIRouter |
| 实时通信 | — | WebSocket `/ws/v1/score` |
| 异步 | Flask threaded=True | asyncio + `asyncio.to_thread()` |
| 前端框架 | Vanilla JS ES6 | Vue 3 Composition API |
| UI 组件 | 原生 HTML + 162 内联样式 | Element Plus |
| 图标 | 120+ Unicode Emoji | Element Plus Icons |
| 桌面 | 浏览器访问 | Electron 28+ |
| 数据存储 | localStorage + JSON 文件 | `app.getPath('userData')` |
| Python 分发 | conda 环境 | 嵌入式 Python 运行时 |

### 数据流 (v7.1.0 — DDD 默认)

```
[Vue 3 SPA] → FastAPI (:8000)
                ├─ /               Vue 3 SPA (SPA fallback)
                ├─ /api/v1/upload  → analyze_and_score()
                │                    → ScoringOrchestrator (DDD 默认 ⭐)
                │                      → FeatureAdapters (bridge)
                │                      → 6 DDD scorers
                │                      → ScoringDomainService
                │                      → EventBus → history_repo.save()
                │                    → advice_service.generate()
                │                    → {total_score, scores{6-dim}, heuristic_dimensions, ...}
                │
                ├─ /ws/v1/score    WebSocket 实时评分
                │                    AudioWorklet → 4字节帧 → asyncio.to_thread
                │
                └─ /old            Flask legacy (绞杀者, 同调用 analyze_and_score)

[Electron spawn] → python.exe backend/main.py --port=0
                   → stdout: "PORT=12345"
                   → preload: window.BACKEND_URL = `http://127.0.0.1:${port}`
```
