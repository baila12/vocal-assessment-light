# v7.0 全栈重构计划: FastAPI + Vue 3 + Element Plus + Electron + 六维评分

> ✅ **迁移已全部完成 (v7.11, 2026-08-04)**。本文档保留作为架构决策记录 (ADR) 和历史参考。
>
> Phase 0-5 ✅ (v7.0) | 绞杀者内移 ✅ (v7.1.3) | 死代码清理 ✅ (v7.1.4) | 特征提取清理 ✅ (v7.1.5) | audiofeat ✅ (v7.2.0) | 代码审查 ✅ (v7.2.1) | audiofeat 评分 ✅ (v7.3.0) | 安全加固 ✅ (v7.3.1) | 权重调整 ✅ (v7.4) | 音色8维 ✅ (v7.5) | ABI+rubato+attack_slope ✅ (v7.6) | Flag桥接+DDD特征统一 ✅ (v7.7) | GNE+GSAP ✅ (v7.8) | Songs CRUD+数据库BDD ✅ (v7.9) | 歌曲库前端 + 音频播放修复 ✅ (v7.10) | 评分权重可配置 + 六维权重单一来源 + BDD 基建修复 ✅ (v7.11)
>
> **当前架构文档**: [ARCHITECTURE.md](../2-technical/ARCHITECTURE.md) | **当前状态**: [PROJECT_STATUS.md](PROJECT_STATUS.md)
>
> 原始日期: 2026-07-21 | 基于 v6.3 代码库 | TDD + BDD + DDD 驱动 | 26.5 天 (Phase 0-5 计划) + 持续迭代至 v7.11

---

## 一、Context & 动机

声乐评估系统 VAS 当前为 v6.3 (Flask + Vanilla JS SPA)，需升级为 v7.0，同时实现六维评分体系重构。

| # | 问题                                                | 目标                                    |
| - | --------------------------------------------------- | --------------------------------------- |
| 1 | Flask 单线程阻塞，无法支持 WebSocket 实时评分       | FastAPI 异步 + WebSocket                |
| 2 | Vanilla JS SPA 有 162 内联样式 + 120+ emoji，难维护 | Vue 3 + Element Plus                    |
| 3 | 五维评分权重不合理 (音准 28%/节奏 20% 过高)         | 六维: 音准/节奏各 10%，新增肌肉力量 25% |
| 4 | 缺少肌肉力量维度、咬字/气声比子维度                 | 发声技术拆分 + 肌肉力量 + 音色加减分    |
| 5 | 浏览器访问，无法原生桌面体验                        | Electron + 嵌入式 Python 运行时         |

**目标架构**: DDD 四层分离 (domain/application/infrastructure/interfaces) + FastAPI 异步 + Vue 3 Composition API + Element Plus + Electron

**核心原则**: 绞杀者模式 — 每 Phase 结束时系统可独立运行，新旧代码共存。

---

## 二、架构决策记录 (ADR)

以下 8 项关键决策在 Day 1 即确定，贯穿全部 Phase。每个决策标注了**为什么这样选**、**如何应用**。

### ADR-1: 嵌入式 Python 运行时 (替代 PyInstaller)

**Why**: PyInstaller 打包后启动要解压数百 MB 依赖到临时目录 (10-15s)，篡改 `sys._MEIPASS` 导致 librosa/sndfile 路径崩溃，且无法增量更新。嵌入式 Python 方案已被 Notion、Figma 早期版本、UberEats 桌面端验证。

**How to apply**:

- Electron `resources/` 携带官方嵌入式 Python zip → 安装 pip → 修改 `python312._pth` (取消 `#import site` 注释) → pip install 依赖
- `backend/main.py` 顶部 `multiprocessing.freeze_support()` + Uvicorn `workers=1`
- **Phase 0 结束前必须跑通最小原型** (Electron 启动 → Python 打印端口 → Vue 显示)，提前验证最危险的技术栈

| 对比       | PyInstaller                                      | 嵌入式 Python                        |
| ---------- | ------------------------------------------------ | ------------------------------------ |
| 启动速度   | 10-15s (解压数百 MB)                             | <2s                                  |
| 路径可靠性 | `sys._MEIPASS` 导致 librosa/sndfile DLL 找不到 | 标准目录，零修改                     |
| 增量更新   | 重编译整个 exe (600MB+)                          | electron-updater 推送 KB 级 .py 文件 |
| 调试       | 无法直接运行 exe 看堆栈                          | 拖`python.exe main.py` 进 CMD 即可 |
| 杀毒误报   | Inno Setup exe 极易被拦截                        | electron-builder NSIS 误报率低       |
| SQLite     | spec 中手动添加 DLL                              | 嵌入式包自带`DLLs/sqlite3.dll`     |

### ADR-2: 肌肉力量 & 音色 → 启发式代理指标

**Why**: 仅凭麦克风录制的歌声，无法直接测量声门下压和身体肌肉力量 (需要 EGG 喉头仪)。Titze (1994) 和 Sundberg (1987) 的论文方法需要专门的生理测量设备。如果用户质疑分数不准，必须有技术解释权。

**How to apply**:

| 维度         | 代理指标                                                                | 置信度                         |
| ------------ | ----------------------------------------------------------------------- | ------------------------------ |
| 身体肌肉力量 | max_db_level + low_freq_energy_ratio + rms_decay_rate_held_notes        | 中                             |
| 面部肌肉力量 | singers_formant_energy + formant_clustering_quality + overtone_richness | 中                             |
| 音色评估     | spectral_centroid_deviation + mfcc_cluster_distance + harmonic_richness | 低 (MFCC 聚类纯度 <0.6 时归零) |

- 所有新特征提取器返回 `is_heuristic: bool = True`
- 前端显示 "估算值" 标签 + 可点击展开说明
- 代码注释显式标注: `# HEURISTIC: Proxy metric from microphone audio — not direct physiological measurement`

### ADR-3: 前后端类型同步 → 文件驱动 openapi.json

**Why**: URL 驱动 (`openapi-typescript http://localhost:8000/openapi.json`) 在后端未启动时中断构建，违反前后端并行开发原则。

**How to apply**:

```bash
# 后端: 导出到 shared/ 目录并提交 Git
python backend/main.py --export-openapi > shared/openapi.json

# 前端: 读取本地文件生成类型 (无需后端运行)
# package.json: "gen:api": "openapi-typescript ../shared/openapi.json --output src/api/schema.d.ts"
```

**收益**: CI/CD 无需后端即可构建、前后端并行开发互不阻塞、Git diff 追踪 API 变更。

### ADR-4: Alembic 迁移 + legacy 表隔离

**Why**: 绞杀者模式下旧 Flask 与新 FastAPI 共享数据库。如果 Alembic 执行新迁移 (增加 `muscle_strength` 列)，旧 Flask 的 SQLAlchemy 模型未同步更新 → `Unknown column` 错误。

**How to apply**:

```python
# legacy/models.py — 复制 v6.3 表定义，锁定为独立表名
class HistoryRecordV6(Base):
    __tablename__ = "history_v6"  # 独立表，不受新迁移影响
```

新 FastAPI 用新表 `history`。Phase 4 迁移完成后，数据迁移脚本 `history_v6` → `history`，删除旧表。

### ADR-5: 结构化日志 → structlog + electron-log

**Why**: 当用户反馈"评分卡住"时，需要把 session_id 输入日志解析脚本，把前后端日志按时间戳拼合成完整链路。

**How to apply**:

```python
# Python: structlog 强制 JSON 格式
import structlog
logger = structlog.get_logger()
logger.info("scoring.complete", task_id="abc123", total_score=85.3, elapsed_s=18.2)
```

```typescript
// JS: electron-log 同目录输出
import log from 'electron-log';
log.info('analysis:start', { mode: 'quick', fileSize: 3.2e6 });
```

前后端日志同目录 (`userData/logs/`)，微秒时间戳，按日切割。

### ADR-6: EventBus 最小原型 (Phase 1 即实现)

**Why**: 领域事件如果只创建不触发，等到 Phase 4 需要"评分完成时自动保存历史"时，会被迫在 API 路由里硬编码调用仓储，污染接口层。

**How to apply**:

```python
# shared/event_bus.py
class EventBus:
    _handlers: dict[Type[DomainEvent], list[Callable]] = {}

    def publish(self, event: DomainEvent):
        for handler in self._handlers.get(type(event), []):
            handler(event)

    def subscribe(self, event_type: Type[DomainEvent], handler: Callable):
        self._handlers.setdefault(event_type, []).append(handler)

# Phase 2 用例中只需 1 行:
result = scoring_service.calculate_total(...)
event_bus.publish(ScoreCalculated(result))  # 触发历史存储
```

### ADR-7: WebSocket 二进制帧边界 → 4 字节长度前缀

**Why**: WebSocket 消息不保留帧边界。客户端两个 2048-sample 帧被 TCP 合并成一个包 → `np.frombuffer` 把两个帧当成一个数组解析 → 音高数据错乱。

**How to apply**:

```
[4-byte big-endian uint32 length][Float32Array PCM data][4-byte length][PCM data]...
```

服务端循环: 读 4 字节 → 确定帧长 → 读指定字节 → `np.frombuffer` → 循环解析。即使 TCP 合并包也能正确分帧。

### ADR-8: 源码保护 → PyArmor 编译领域层

**Why**: `resources/backend/` 下明文 .py 文件，用户可随意修改评分算法权重，竞品可复制核心 IP。

**How to apply**: 仅将 `domain/assessment/*_scorer.py` 用 PyArmor 编译为 `.pyd` (Windows DLL)。应用层和接口层保持源码可热更新。核心算法被保护，应用层仍可增量更新。

---

## 三、六维评分体系

### 3.1 权重分配

> **注意 (v7.4)**: 以下为 v7.0 计划时的原始权重。v7.4 基于文献和实证反馈调整为实际权重:
> **Pitch 13% / Rhythm 12% / Breath 22% / Technique 25% / Muscle 15% / Artistry 13%**。
> 参见 [PROJECT_STATUS.md](PROJECT_STATUS.md) 六维权重章节和 `backend/domain/assessment/value_objects.py`。

| 维度                 | 旧权重 | 计划新权重     | 子维度                                                          | 算法来源                                                                                                               |
| -------------------- | ------ | -------------- | --------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| 音准 (Pitch)         | 28%    | **10%** (→13% v7.4)  | —                                                              | v6.2 多指标体系: MAE指数衰减(40%)+RPA(25%)+RCA(10%)+Gross Error(15%)+Smoothness(5%)+Octave(5%)                         |
| 节奏 (Rhythm)        | 20%    | **10%** (→12% v7.4)  | —                                                              | onset CV 分段 + irregularity 惩罚 + is_clean_vocal 重校准                                                              |
| 气息 (Breath)        | 20%    | **20%** (→22% v7.4)  | 长音支撑(40%) + 动态控制(25%) + 气口设计(20%) + 气声技巧(15%)   | 不变，v6.1 连续线性映射                                                                                                |
| 发声技术 (Technique) | 18%    | **25%**  | 咬字清晰度(50%) + 气声比(50%)                                   | **拆分**: 咬字=f(onset_density, spectral_flux, consonant_clarity)；气声比=f(HNR, spectral_tilt, hf_energy_ratio) |
| 肌肉力量 (Muscle)    | —     | **25%** (→15% v7.4)  | 身体肌肉(50%) + 面部肌肉(50%)                                   | **NEW ⚠️ 启发式**                                                                                              |
| 艺术表现 (Artistry)  | 14%    | **10%** (→13% v7.4)  | 颤音品质(30%) + 动态控制(30%) + 乐句表现力(25%) + 音高变化(15%) | 不变，v6.1 独立声学特征                                                                                                |
| **总计**       | 100%   | **100%** |                                                                 |                                                                                                                        |

### 3.2 音色加减分 (不属于六维)

- 六维加权总分计算后**独立应用**
- 最多 **+3** / 最多 **-5** (不对称设计 — 扣分比加分重)
- 最终总分 clamp 到 [0, 100]
- 低置信度 (MFCC 聚类纯度 < 0.6) 自动归零 (不加不减)

### 3.3 Feature Flag 独立开关

```python
@dataclass
class DimensionFlags:
    """六维独立开关 — 关一个不影响其余。每个维度单一职责、零依赖"""
    # 维度级
    enable_pitch: bool = True
    enable_rhythm: bool = True
    enable_breath: bool = True
    enable_technique: bool = True           # 咬字 + 气声比
    enable_muscle_strength: bool = True     # NEW ⚠️ 启发式
    enable_artistry: bool = True
    enable_timbre_adjustment: bool = True   # NEW ⚠️ 启发式
    enable_vnext_weights: bool = True       # False = 回退旧五维权重

    # 子维度级
    enable_articulation: bool = True        # 咬字清晰度
    enable_breath_voice_ratio: bool = True  # 气声比
    enable_body_muscle: bool = True         # 身体肌肉
    enable_facial_muscle: bool = True       # 面部肌肉

    # 保留 v6.2 高级算法开关 (7 个，全默认启用)
    enable_multiscale_hnr: bool = True
    enable_praat_cpp: bool = True
    enable_voicing_detection: bool = True
    enable_torchcrepe_fallback: bool = True
    enable_cross_dimension_modifiers: bool = True
    enable_reverb_compensation: bool = True
    enable_praat_voice_quality: bool = True
```

### 3.4 分数等级映射 (不变)

| 分数范围 | 等级   | 星级   | 颜色    |
| -------- | ------ | ------ | ------- |
| 88-100   | 专业级 | ★★★ | #22c55e |
| 78-88    | 优秀   | ★★☆ | #3b82f6 |
| 62-78    | 良好   | ★★   | #10b981 |
| 45-62    | 中等   | ★☆   | #f59e0b |
| 25-45    | 及格   | ★     | #f97316 |
| 0-25     | 待改进 | ☆     | #ef4444 |

### 3.5 关键业务规则 (来自 v6.2，保持不变)

1. **跨维度修正** (5 项): HNR稳定性→气息, Voicing→音准, 频谱倾斜→气声, Jitter→技术, 气息-音准耦合
2. **底线规则**: 连续跑调(>5音符) -20分, 脱拍(>40%) 上限70, 严重漏气(HNR<3dB) 上限50
3. **多维度联合惩罚**: 4维<40→上限40, 3维<40→上限55
4. **人声质量惩罚**: VQ<30→上限40, VQ<65→线性扣分
5. **DL融合**: SingMOS 已移除 (v5.15)，由自参照一致性替代

---

## 四、Phase 0: Foundation — 3.5 天

### 目标

建立 DDD 项目骨架、FastAPI + Vue 3 脚手架、四大基础设施 (Alembic + structlog + openapi-typescript + 嵌入式 Python 原型)。**绝不破坏现有功能**。

### 4.1 新目录结构 (DDD 分层)

```
vocal_assessment_light/
├── backend/                              # FastAPI 应用 (新增)
│   ├── main.py                           # 入口 + lifespan + CORS + mount /old
│   ├── domain/                           # 领域层 — 零框架依赖
│   │   ├── __init__.py
│   │   ├── assessment/                   #   评分限界上下文
│   │   │   ├── __init__.py
│   │   │   ├── entities.py               #     AssessmentResult 聚合根
│   │   │   ├── value_objects.py          #     7 个值对象 (PitchScore, RhythmScore, BreathScore,
│   │   │   │                             #       TechniqueScore, MuscleStrengthScore,
│   │   │   │                             #       ArtistryScore, TimbreAdjustment)
│   │   │   ├── services.py               #     ScoringDomainService (纯计算，零副作用)
│   │   │   ├── events.py                 #     ScoreCalculated, DimensionAnalyzed
│   │   │   ├── errors.py                 #     领域异常 (InvalidScoreError 等)
│   │   │   ├── feature_flags.py          #     DimensionFlags
│   │   │   ├── pitch_scorer.py           #     音准评分器
│   │   │   ├── rhythm_scorer.py          #     节奏评分器
│   │   │   ├── breath_scorer.py          #     气息评分器
│   │   │   ├── technique_scorer.py       #     技术评分器 (咬字+气声比)
│   │   │   ├── muscle_scorer.py          #     肌肉力量评分器 [NEW]
│   │   │   ├── artistry_scorer.py        #     艺术评分器
│   │   │   └── timbre_adjuster.py        #     音色调整器 [NEW]
│   │   ├── audio/                        #   音频处理上下文
│   │   │   ├── entities.py               #     AudioFile 聚合根
│   │   │   ├── value_objects.py          #     AudioMetadata, FeatureSet
│   │   │   └── services.py               #     FeatureExtractionDomainService
│   │   └── comparison/                   #   对比分析上下文
│   │       ├── entities.py               #     ComparisonResult 聚合根
│   │       └── services.py               #     DTWDomainService
│   ├── application/                      # 应用层 — 用例编排
│   │   ├── __init__.py
│   │   ├── assessment/                   #   评估用例
│   │   │   ├── analyze_audio.py          #     AnalyzeAudioUseCase
│   │   │   └── stream_score.py           #     StreamScoreUseCase (WebSocket)
│   │   ├── history/                      #   历史记录用例
│   │   │   └── query_history.py          #     QueryHistoryUseCase
│   │   └── comparison/                   #   对比用例
│   │       └── compare_audio.py          #     CompareAudioUseCase
│   ├── infrastructure/                   # 基础设施层 — 技术实现
│   │   ├── __init__.py
│   │   ├── config.py                     #   Pydantic BaseSettings (替代 config/default.py)
│   │   ├── persistence/                  #   仓储实现
│   │   │   ├── json_history_repo.py      #     JsonHistoryRepository
│   │   │   └── sqlite_song_repo.py       #     SqliteSongRepository
│   │   └── audio/                        #   音频处理适配器
│   │       ├── librosa_loader.py         #     LibrosaAudioLoader
│   │       ├── pyin_extractor.py         #     PYINPitchExtractor
│   │       └── demucs_separator.py       #     DemucsSeparator
│   ├── interfaces/                       # 接口层 — HTTP/WS 适配
│   │   ├── __init__.py
│   │   ├── api/                          #   REST API
│   │   │   ├── __init__.py               #     FastAPI app + lifespan
│   │   │   ├── deps.py                   #     依赖注入 (Depends)
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── assessment.py         #     /api/v1/upload, /analyze, /extract-pitch
│   │   │   │   ├── history.py            #     /api/v1/history CRUD
│   │   │   │   ├── comparison.py         #     /api/v1/compare
│   │   │   │   ├── songs.py              #     /api/v1/songs [NEW]
│   │   │   │   ├── separation.py         #     /api/v1/separate
│   │   │   │   └── health.py             #     /health
│   │   │   └── schemas/                  #   Pydantic v2 请求/响应模型
│   │   │       ├── __init__.py
│   │   │       ├── assessment.py         #     UploadResponse, AnalyzeRequest
│   │   │       ├── history.py            #     HistoryListResponse
│   │   │       ├── comparison.py         #     CompareRequest, CompareResponse
│   │   │       └── common.py             #     ApiResponse[T], ErrorResponse
│   │   └── ws/                           #   WebSocket
│   │       ├── __init__.py
│   │       ├── score_handler.py          #     /ws/v1/score 处理器
│   │       └── schemas.py                #     WS 消息 Pydantic 模型
│   ├── shared/                           # 共享内核
│   │   ├── __init__.py
│   │   ├── domain_types.py               #   PositiveFloat, ScoreValue (0-100)
│   │   ├── event_bus.py                  #   EventBus (观察者模式)
│   │   └── result.py                     #   Result[T, E] monad
│   ├── migrations/                       # Alembic 迁移
│   │   ├── env.py
│   │   └── versions/
│   └── legacy/                           # 旧 Flask 包装 (逐步删除)
│       ├── __init__.py
│       ├── flask_app.py                  # Flask app 包装为 WSGI callable
│       └── models.py                     # 旧表定义 (history_v6)
├── frontend/                             # Vue 3 + Vite (新增)
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   ├── src/
│   │   ├── main.ts                       # createApp + Element Plus + Pinia + Router
│   │   ├── App.vue                       # 根组件: <router-view> + <Transition>
│   │   ├── router/index.ts               # Vue Router 4 (hash history → history mode)
│   │   ├── stores/                       # Pinia stores
│   │   │   ├── assessment.store.ts       #   评估状态 (分析中/结果/进度)
│   │   │   ├── history.store.ts          #   历史记录 CRUD
│   │   │   └── preferences.store.ts      #   用户偏好 (主题/模式/autoPlay)
│   │   ├── api/
│   │   │   ├── client.ts                 #   HTTP 客户端 (零硬编码 URL)
│   │   │   └── schema.d.ts               #   openapi-typescript 自动生成
│   │   ├── composables/                  # Vue 组合函数
│   │   │   ├── useApi.ts                 #   API 调用封装
│   │   │   ├── useWebSocket.ts           #   WebSocket 连接 + 重连
│   │   │   ├── useGsap.ts                #   GSAP 动画 (gsap.context)
│   │   │   ├── useAudioContext.ts        #   Web Audio API 管理
│   │   │   └── useMediaRecorder.ts       #   录音控制
│   │   ├── views/                        # 页面组件
│   │   │   ├── HomeView.vue              #   上传 + 模式选择 + 抽屉(设置/曲库)
│   │   │   ├── SingView.vue              #   实时录音 + Canvas 音高
│   │   │   ├── ReportView.vue            #   评分报告 + 雷达图 + 音高曲线
│   │   │   ├── HistoryView.vue           #   历史记录列表
│   │   │   └── CompareView.vue           #   双文件对比
│   │   ├── components/                   # 共享组件
│   │   │   ├── layout/
│   │   │   │   ├── AppLayout.vue         #     ElContainer 布局
│   │   │   │   ├── TopNav.vue            #     ElMenu + ElIcon 顶导航
│   │   │   │   └── BottomNav.vue         #     移动端底导航
│   │   │   ├── ScoreCard.vue             #     评分卡片 (可复用)
│   │   │   ├── ScoreRadar.vue            #     六维雷达图 (Chart.js)
│   │   │   ├── PitchCurveCanvas.vue      #     音高曲线 Canvas
│   │   │   ├── AudioPlayer.vue           #     音频播放器 (seek+波形)
│   │   │   ├── ProgressOverlay.vue       #     分析进度条
│   │   │   └── FileUploader.vue          #     拖拽上传封装
│   │   ├── types/                        # TypeScript 类型
│   │   │   ├── api.ts                    #   API 响应类型
│   │   │   └── score.ts                  #   六维分数类型
│   │   └── styles/
│   │       ├── variables.css             #   Element Plus 主题变量
│   │       ├── element-override.scss     #   组件样式覆盖
│   │       └── global.css                #   全局样式
│   ├── electron/                         # Electron (Phase 5 实现)
│   │   ├── main.ts
│   │   └── preload.ts
│   └── tests/
│       └── unit/stores/                  # Pinia store 测试 (Vitest)
├── shared/                               # 前后端共享 (新增)
│   └── openapi.json                      # 提交 Git，前端 gen:api 读取
├── scripts/
│   └── build-python-runtime.bat          # 构建嵌入式 Python 环境
└── tests/                                # 保持现有结构 + 新增
    ├── unit/domain/                      #   六维评分器 TDD 测试
    ├── integration/                      #   FastAPI TestClient + WebSocket
    ├── tdd/                              #   现有 TDD 测试套件 (保留)
    └── e2e/                              #   Playwright
```

### 4.2 FastAPI 应用工厂

```python
# backend/main.py
import multiprocessing
multiprocessing.freeze_support()  # ⚠️ 防止嵌入式 Python 子进程递归崩溃

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: 初始化 DB 连接池, 预热模型
    logger.info("app.starting", gpu=detect_gpu())
    yield
    # shutdown: 清理资源, dispose DB
    logger.info("app.stopped")

app = FastAPI(title="VAS v7.0", version="7.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"])

# Phase 2: 注册新路由
# app.include_router(assessment.router, prefix="/api/v1")

# Phase 2: 挂载旧 Flask (绞杀者模式)
# from legacy.flask_app import flask_app
# app.mount("/old", WSGIMiddleware(flask_app))

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "7.0.0", "gpu": detect_gpu()}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 0))
    print(f"PORT={port}")  # Electron 捕获此行获取端口
    uvicorn.run(app, host="127.0.0.1", port=port, workers=1)  # ⚠️ 硬锁定 workers=1
```

### 4.3 配置管理 (Pydantic Settings)

```python
# backend/infrastructure/config.py
from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    project_root: Path = Path(__file__).parent.parent.parent
    upload_folder: Path = project_root / "uploads"
    history_file: Path = project_root / "data" / "web_history.json"
    history_max_records: int = 50
    separated_dir: Path = project_root / "web" / "static" / "separated"
    reports_dir: Path = project_root / "web" / "static" / "reports"
    max_content_length: int = 50 * 1024 * 1024  # 50MB
    allowed_extensions: set[str] = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac"}

    model_config = {"env_prefix": "VAS_", "frozen": True}
```

### 4.4 Vue 3 + Vite 初始化

```bash
npm create vite@latest frontend -- --template vue-ts
cd frontend
npm install vue-router@4 pinia@2 element-plus @element-plus/icons-vue
npm install gsap chart.js vue-chartjs
npm install -D @types/node sass unplugin-vue-components unplugin-auto-import
npm install -D vitest @vue/test-utils happy-dom
```

```typescript
// frontend/vite.config.ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

export default defineConfig({
  plugins: [
    vue(),
    AutoImport({ resolvers: [ElementPlusResolver({ importStyle: 'sass' })] }),
    Components({ resolvers: [ElementPlusResolver({ importStyle: 'sass' })] }),
  ],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/ws': { target: 'ws://127.0.0.1:8000', ws: true }
    }
  }
})
```

```typescript
// frontend/src/main.ts
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/theme-chalk/src/index.scss'
import App from './App.vue'
import router from './router'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })
app.mount('#app')
```

### 4.5 嵌入式 Python 最小原型 (Phase 0 必须完成)

```typescript
// electron/main.ts — 最小原型: 启动嵌入式 Python → 捕获端口 → 通知 Vue
import { spawn } from 'child_process'
import path from 'path'

function startBackend(): Promise<number> {
  return new Promise((resolve, reject) => {
    const pythonPath = path.join(process.resourcesPath, 'python', 'python.exe')
    const scriptPath = path.join(process.resourcesPath, 'backend', 'main.py')

    const py = spawn(pythonPath, [scriptPath, '--port=0'], {
      env: { ...process.env, PYTHONUNBUFFERED: '1' },
      stdio: ['ignore', 'pipe', 'pipe']
    })

    py.stdout.on('data', (data: Buffer) => {
      const match = data.toString().match(/PORT=(\d+)/)
      if (match) {
        const port = parseInt(match[1])
        mainWindow?.webContents.send('set-backend-url', `http://127.0.0.1:${port}`)
        resolve(port)
      }
    })

    py.stderr.on('data', (data) => log.error(`[Backend] ${data}`))
    py.on('error', reject)
  })
}
```

### 4.6 文件清单

| 操作   | 文件                                 | 说明                                     |
| ------ | ------------------------------------ | ---------------------------------------- |
| CREATE | `backend/` 完整目录结构            | 含 40+`__init__.py` + 空模块           |
| CREATE | `backend/main.py`                  | FastAPI 入口 + lifespan + freeze_support |
| CREATE | `backend/infrastructure/config.py` | Pydantic Settings                        |
| CREATE | `backend/shared/domain_types.py`   | ScoreValue, PositiveFloat                |
| CREATE | `backend/shared/event_bus.py`      | EventBus 最小原型                        |
| CREATE | `backend/shared/result.py`         | Result[T, E] monad                       |
| CREATE | `backend/legacy/flask_app.py`      | Flask app 包装为 WSGI callable           |
| CREATE | `backend/legacy/models.py`         | 旧表定义 (history_v6)                    |
| CREATE | `backend/migrations/`              | Alembic 初始化                           |
| CREATE | `frontend/`                        | Vite + Vue 3 + Element Plus 脚手架       |
| CREATE | `frontend/src/api/client.ts`       | HTTP 客户端 (零硬编码 URL)               |
| CREATE | `shared/openapi.json`              | 空文件，Phase 2 填充                     |
| CREATE | `scripts/build-python-runtime.bat` | 嵌入式 Python 构建                       |
| MODIFY | `web_app.py`                       | 提取`create_app()` 为可复用工厂        |
| MODIFY | `start.bat`                        | 增加 FastAPI + Vite 启动选项             |

### 4.7 BDD 验收

```gherkin
Feature: 基础设施健康检查
  Scenario: FastAPI 服务启动成功
    Given FastAPI app 已配置
    When 请求 GET /health
    Then 返回 200 状态码
    And 包含 "version": "7.0.0"
    And 包含 gpu 状态信息

  Scenario: 绞杀者模式共存 — 旧 Flask 端点仍可访问
    Given FastAPI 已挂载 Flask app 到 /old
    When 请求 GET /old/ (旧 SPA 首页)
    Then 返回 200

  Scenario: Vue 3 开发服务器可加载
    Given Vite 开发服务器运行中
    When 打开浏览器访问 http://localhost:5173
    Then 显示 Vue 3 渲染的空白首页
    And Element Plus 组件正常渲染

  Scenario: 嵌入式 Python 最小原型
    Given 嵌入式 Python 环境已构建
    When Electron 主进程 spawn python.exe backend/main.py --port=0
    Then stdout 输出 "PORT=xxxxx"
    And Electron 收到端口号
    And Vue 前端通过动态 URL 连接后端
```

### 4.8 Phase 0 验收

- [x] FastAPI `/health` 返回 200 (含 GPU 信息) ✅
- [x] Flask 旧应用在 `/old/` 下可访问 ✅
- [x] Vue 3 空白首页渲染成功 ✅
- [x] 嵌入式 Python 启动 → Electron 收到端口号 → Vue 显示 ✅

---

## 五、Phase 1: Domain Model (六维评分) — 5 天

### 目标

基于 TDD 实现 7 个独立可测的维度评分器 + 音色调整 + 总分协调 + EventBus。

**核心原则**:

- 每个维度单一职责、零依赖 (测 Pitch 只需跑 pitch_scorer)
- Feature Flag 独立开关 (关一个不影响其余)
- 所有新增维度 (Muscle/Timbre) 标记为启发式
- Phase 1 即实现 EventBus 并写事件触发测试

### 5.1 完整领域值对象 (7 个)

```python
# backend/domain/assessment/value_objects.py
from dataclasses import dataclass
from backend.shared.domain_types import ScoreValue

@dataclass(frozen=True)
class PitchScore:
    """音准评分 (10% 权重) — v6.2 六指标加权融合"""
    raw_score: ScoreValue          # 0-100
    mae_cents: float               # 平均音分偏差
    rpa: float                     # Raw Pitch Accuracy
    rca: float                     # Raw Chroma Accuracy
    gross_error_rate: float
    octave_error_rate: float
    smoothness_cv: float
    detection_rate: float          # PYIN 检测率
    pitch_breaks: int              # 音高断层数 (YIN 3.5x 校准)
    diagnosis: tuple[str, ...]

    def weighted(self) -> float:
        return self.raw_score * 0.10

@dataclass(frozen=True)
class RhythmScore:
    """节奏评分 (10% 权重) — onset CV + irregularity"""
    raw_score: ScoreValue
    onset_cv: float
    median_ioi_deviation: float
    irregularity_penalty: float
    is_clean_vocal: bool           # Demucs 分离后标记
    diagnosis: tuple[str, ...]

    def weighted(self) -> float:
        return self.raw_score * 0.10

@dataclass(frozen=True)
class BreathScore:
    """气息评分 (20% 权重) — 四子维度连续线性映射"""
    raw_score: ScoreValue
    long_note_support: float       # 长音支撑 (40%)
    dynamic_control: float         # 动态控制 (25%)
    breath_design: float           # 气口设计 (20%)
    breath_technique: float        # 气声技巧 (15%)
    is_clean_vocal: bool
    hnr_stability: float | None
    dynamic_range_db: float        # p95 - p5 (排除异常值)
    diagnosis: tuple[str, ...]

    def weighted(self) -> float:
        return self.raw_score * 0.20

@dataclass(frozen=True)
class TechniqueScore:
    """发声技术评分 (25% 权重) — vNext: 拆分为咬字+气声比"""
    raw_score: ScoreValue
    articulation_clarity: float    # 咬字清晰度 (50%)
    breath_voice_ratio: float      # 气声比 (50%)
    hnr_mean: float
    cpp_mean: float
    diagnosis: tuple[str, ...]

    def weighted(self) -> float:
        return self.raw_score * 0.25

@dataclass(frozen=True)
class MuscleStrengthScore:
    """肌肉力量评分 (NEW, 25% 权重) — ⚠️ 启发式代理指标"""
    raw_score: ScoreValue
    body_muscle_strength: float    # 身体肌肉 (50%): max_db + low_freq_ratio + rms_decay
    facial_muscle_strength: float  # 面部肌肉 (50%): singers_formant + formant_cluster + overtone
    is_heuristic: bool = True      # ⚠️ 非直接生理测量
    diagnosis: tuple[str, ...]

    def weighted(self) -> float:
        return self.raw_score * 0.25

@dataclass(frozen=True)
class ArtistryScore:
    """艺术表现评分 (10% 权重) — v6.1 独立声学特征"""
    raw_score: ScoreValue
    vibrato_quality: float         # 颤音品质 (30%)
    dynamic_control: float         # 动态控制 (30%)
    phrase_expression: float       # 乐句表现力 (25%)
    pitch_variation: float         # 音高变化 (15%)
    diagnosis: tuple[str, ...]

    def weighted(self) -> float:
        return self.raw_score * 0.10

@dataclass(frozen=True)
class TimbreAdjustment:
    """音色加减分 (不属于六维) — ⚠️ 启发式代理指标"""
    adjustment: float              # +3 ~ -5
    brightness_score: float        # 谱质心偏离基准
    warmth_score: float            # MFCC 低频聚类
    nasality_score: float          # 鼻音检测
    confidence: float              # MFCC 聚类纯度
    is_heuristic: bool = True      # ⚠️ 主观感知量
    diagnosis: str | None = None

    def apply(self, total: float) -> float:
        if self.confidence < 0.6:  # 低置信归零
            return max(0.0, min(100.0, total))
        return max(0.0, min(100.0, total + self.adjustment))
```

### 5.2 领域服务 + EventBus 集成

```python
# backend/domain/assessment/services.py
from backend.shared.event_bus import EventBus
from backend.domain.assessment.events import ScoreCalculated

class ScoringDomainService:
    """评分领域服务 — 纯计算，零副作用，注入 EventBus"""

    def __init__(self, event_bus: EventBus | None = None):
        self._event_bus = event_bus

    def calculate_total(
        self,
        pitch: PitchScore,
        rhythm: RhythmScore,
        breath: BreathScore,
        technique: TechniqueScore,
        muscle: MuscleStrengthScore,
        artistry: ArtistryScore,
        timbre: TimbreAdjustment | None = None,
    ) -> float:
        total = (
            pitch.weighted() +
            rhythm.weighted() +
            breath.weighted() +
            technique.weighted() +
            muscle.weighted() +
            artistry.weighted()
        )
        result = round(timbre.apply(total) if timbre else total, 1)

        # 发布领域事件 (1 行)
        if self._event_bus:
            self._event_bus.publish(ScoreCalculated(
                total_score=result,
                dimensions={
                    "pitch": pitch.raw_score, "rhythm": rhythm.raw_score,
                    "breath": breath.raw_score, "technique": technique.raw_score,
                    "muscle_strength": muscle.raw_score, "artistry": artistry.raw_score,
                },
                timbre_adjustment=timbre.adjustment if timbre else 0,
            ))
        return result

    def determine_level(self, total_score: float) -> tuple[str, str, str]:
        if total_score >= 88: return ("专业级", "S", "#22c55e")
        if total_score >= 78: return ("优秀", "A", "#3b82f6")
        if total_score >= 62: return ("良好", "B", "#10b981")
        if total_score >= 45: return ("中等", "C", "#f59e0b")
        if total_score >= 25: return ("及格", "D", "#f97316")
        return ("待改进", "E", "#ef4444")
```

### 5.3 TDD 实现顺序 (RED → GREEN → REFACTOR)

| #              | 评分器                         | 测试数       | 测试文件                                             | 实现文件                                          | 状态           |
| -------------- | ------------------------------ | ------------ | ---------------------------------------------------- | ------------------------------------------------- | -------------- |
| 1              | **PitchScorer**          | 16           | `tests/unit/domain/test_pitch_scorer.py`           | `backend/domain/assessment/pitch_scorer.py`     | 移植 v6.2      |
| 2              | **RhythmScorer**         | 12           | `tests/unit/domain/test_rhythm_scorer.py`          | `backend/domain/assessment/rhythm_scorer.py`    | 移植           |
| 3              | **BreathScorer**         | 14           | `tests/unit/domain/test_breath_scorer.py`          | `backend/domain/assessment/breath_scorer.py`    | 移植           |
| 4              | **TechniqueScorer**      | 10           | `tests/unit/domain/test_technique_scorer.py`       | `backend/domain/assessment/technique_scorer.py` | **重构** |
| 5              | **MuscleStrengthScorer** | 12           | `tests/unit/domain/test_muscle_scorer.py`          | `backend/domain/assessment/muscle_scorer.py`    | **NEW**  |
| 6              | **ArtistryScorer**       | 8            | `tests/unit/domain/test_artistry_scorer.py`        | `backend/domain/assessment/artistry_scorer.py`  | 移植           |
| 7              | **TimbreAdjuster**       | 6            | `tests/unit/domain/test_timbre_adjuster.py`        | `backend/domain/assessment/timbre_adjuster.py`  | **NEW**  |
| 8              | **ScoringDomainService** | 10           | `tests/unit/domain/test_scoring_domain_service.py` | `backend/domain/assessment/services.py`         | **重构** |
| **总计** |                                | **88** |                                                      |                                                   |                |

#### 各评分器 TDD 测试要点

**PitchScorer** (16 tests):

- MAE 指数衰减边界: 0音分→100, 40音分→36.8, 100音分→8.2
- RPA/RCA 聚合: 全部命中→100, 全部未命中→0
- gross_error 惩罚: rate=5%→100, rate=20%→70
- octave_error 检测: 相邻帧跳变 > 1000音分
- smoothness CV: CV=1.0→100, CV=3.0→0
- 检测率低惩罚: rate=0.4→扣分
- pitch_breaks YIN 校准: raw 785 → 校准后 226 (÷3.5)

**MuscleStrengthScorer** (12 tests) — **NEW**:

- 身体: 优秀呼吸支撑 (decay <0.5 dB/s) → >80分
- 身体: 弱呼吸支撑 (decay >2.0 dB/s) → <40分
- 身体: 宽动态范围 (>30dB) 加分
- 面部: 强歌手共振峰 (2.5-3.5kHz 能量 >15%) → >80分
- 面部: 弱共振峰 (能量 <5%) → <40分
- 面部: 丰富泛音加分
- 综合: 身体+面部 50/50 加权
- 综合: score clamp [0, 100]
- 综合: `is_heuristic=True` 标记验证

**TimbreAdjuster** (6 tests) — **NEW**:

- 纯净音色 (高谱质心+丰富谐波+无鼻音) → adjustment = +3
- 普通音色 → adjustment = 0
- 鼻音重 → adjustment = -2
- 严重沙哑 → adjustment = -5 (floor)
- 低置信 (<0.6) → adjustment = 0 (归零)
- clamp 验证: total=98 + adj=+3 → 100, total=3 + adj=-5 → 0

**ScoringDomainService** (10 tests) — **含事件触发**:

- 六维全部 80 分 → total = 80.0
- 六维权重和 = 100% 验证
- 音色加分 cap +3
- 音色扣分 floor -5
- 音色低置信归零
- Feature Flag: 关闭 muscle → muscle.raw_score 不影响 total
- **事件触发**: `test_scoring_service_emits_score_calculated_event` (见 5.4)
- 等级判定: total=88→专业级, total=25→及格, total=24→待改进
- total clamp [0, 100]
- 异常输入: 所有维度 None → 抛出 InvalidScoreError

### 5.4 强制事件触发测试 (驱动 EventBus 落地)

```python
# tests/unit/domain/test_scoring_domain_service.py
def test_scoring_service_emits_score_calculated_event(self):
    """确保领域事件不是摆设 — 每次评分完成必须发布 ScoreCalculated 事件"""
    events = []
    bus = EventBus()
    bus.subscribe(ScoreCalculated, lambda e: events.append(e))

    service = ScoringDomainService(event_bus=bus)
    result = service.calculate_total(
        PitchScore(raw_score=80, ...),
        RhythmScore(raw_score=80, ...),
        BreathScore(raw_score=80, ...),
        TechniqueScore(raw_score=80, ...),
        MuscleStrengthScore(raw_score=80, ...),
        ArtistryScore(raw_score=80, ...),
    )

    assert len(events) == 1
    assert events[0].total_score == result
    assert events[0].dimensions["pitch"] == 80
    assert events[0].dimensions["muscle_strength"] == 80
```

### 5.5 BDD 验收

```gherkin
Feature: 六维评分计算
  Scenario: 六个维度独立计算并加权
    Given 所有维度得分为 80 分
    When 计算总分
    Then 总分 = 80.0 (10+10+20+25+25+10 = 100%)

  Scenario: 音色加分上限 +3
    Given 六维总分 85
    And 音色评估为优秀 (adjustment=+4)
    When 应用音色调整
    Then 最终总分 = 88 (cap at +3)

  Scenario: 音色扣分下限 -5
    Given 六维总分 85
    And 音色评估为差 (adjustment=-7)
    When 应用音色调整
    Then 最终总分 = 80 (floor at -5)

  Scenario: 总分 clamp [0, 100]
    Given 六维总分 98
    And 音色加分 +3
    When 应用音色调整
    Then 最终总分 = 100 (not 101)

  Scenario: 音色低置信自动归零
    Given 六维总分 75
    And 音色评估置信度 0.3 (< 0.6)
    When 应用音色调整
    Then 最终总分 = 75 (不加不减)

  Scenario: 肌肉力量维度标记为启发式
    Given 评分引擎计算完成
    When 返回 MuscleStrengthScore
    Then is_heuristic = True
    And 前端显示 "估算值" 标签

  Scenario: 关闭一个维度不影响其余
    Given DimensionFlags(enable_breath=False)
    When 计算总分
    Then 气息维度权重归零，其余 5 维正常计算
```

### 5.6 文件清单

| 操作   | 文件                                                 | 说明                               |
| ------ | ---------------------------------------------------- | ---------------------------------- |
| CREATE | `backend/domain/__init__.py`                       | 领域层入口                         |
| CREATE | `backend/domain/assessment/value_objects.py`       | 7 个值对象                         |
| CREATE | `backend/domain/assessment/services.py`            | ScoringDomainService + EventBus    |
| CREATE | `backend/domain/assessment/events.py`              | ScoreCalculated, DimensionAnalyzed |
| CREATE | `backend/domain/assessment/errors.py`              | InvalidScoreError 等               |
| CREATE | `backend/domain/assessment/feature_flags.py`       | DimensionFlags                     |
| CREATE | `backend/domain/assessment/pitch_scorer.py`        | 移植 v6.2 多指标体系               |
| CREATE | `backend/domain/assessment/rhythm_scorer.py`       | 移植                               |
| CREATE | `backend/domain/assessment/breath_scorer.py`       | 移植                               |
| CREATE | `backend/domain/assessment/technique_scorer.py`    | 重构: 咬字+气声比                  |
| CREATE | `backend/domain/assessment/muscle_scorer.py`       | **NEW** 启发式               |
| CREATE | `backend/domain/assessment/artistry_scorer.py`     | 移植                               |
| CREATE | `backend/domain/assessment/timbre_adjuster.py`     | **NEW** 启发式               |
| CREATE | `backend/domain/audio/`                            | 音频上下文                         |
| CREATE | `backend/domain/comparison/`                       | 对比上下文                         |
| CREATE | `tests/unit/domain/test_pitch_scorer.py`           | 16 tests                           |
| CREATE | `tests/unit/domain/test_rhythm_scorer.py`          | 12 tests                           |
| CREATE | `tests/unit/domain/test_breath_scorer.py`          | 14 tests                           |
| CREATE | `tests/unit/domain/test_technique_scorer.py`       | 10 tests                           |
| CREATE | `tests/unit/domain/test_muscle_scorer.py`          | 12 tests                           |
| CREATE | `tests/unit/domain/test_artistry_scorer.py`        | 8 tests                            |
| CREATE | `tests/unit/domain/test_timbre_adjuster.py`        | 6 tests                            |
| CREATE | `tests/unit/domain/test_scoring_domain_service.py` | 10 tests (含事件)                  |

### 5.7 Phase 1 验收

- [x] 88 个新单元测试全部 GREEN ✅
- [x] 5 个真实音频回归基线 (偏差 < ±1 分 vs v6.2 ScoreServiceV4) ✅
- [x] 每个维度 Feature Flag 可独立关闭 → 该维度分数不影响 total ✅
- [x] EventBus 事件发布/订阅集成测试通过 ✅
- [x] 所有新增维度 `is_heuristic=True` 标记验证通过 ✅

---

## 六、Phase 2: FastAPI 后端迁移 — 4 天

### 目标

用 FastAPI 替代 Flask API 层，21 端点逐对迁移，绞杀者模式共存。旧 Flask 在 `/old` 下持续可用。

### 6.1 端点迁移表 (按批次)

| #     | Flask                         | FastAPI                                                                                                                     | 批                 | 说明                                   |
| ----- | ----------------------------- | --------------------------------------------------------------------------------------------------------------------------- | ------------------ | -------------------------------------- |
| 1     | `GET /health`               | `GET /health`                                                                                                             | 0 (Phase 0 已完成) |                                        |
| 2     | `GET /api/history`          | `GET /api/v1/history`                                                                                                     | 1 (I/O)            | 查询参数: date=all/today/week/month    |
| 3     | `GET /api/history/<id>`     | `GET /api/v1/history/{id}`                                                                                                | 1                  |                                        |
| 4     | `DELETE /api/history/<id>`  | `DELETE /api/v1/history/{id}`                                                                                             | 1                  |                                        |
| 5     | `DELETE /api/history/batch` | `DELETE /api/v1/history/batch`                                                                                            | 1                  | JSON body: {ids: [...]}                |
| 6     | `DELETE /api/history/all`   | `DELETE /api/v1/history/all`                                                                                              | 1                  |                                        |
| 7     | `GET /api/audio?file=...`   | `GET /api/v1/audio?file=...`                                                                                              | 1                  | 安全校验: 路径遍历 + 扩展名            |
| 8     | `GET /api/separate/models`  | `GET /api/v1/separate/models`                                                                                             | 1                  |                                        |
| 9     | `POST /api/report`          | `POST /api/v1/report`                                                                                                     | 1                  | pdf/image 导出                         |
| 10    | `POST /api/upload`          | `POST /api/v1/upload`                                                                                                     | 2 (CPU)            | FormData: file + mode + reference_file |
| 11    | `POST /api/analyze`         | `POST /api/v1/analyze`                                                                                                    | 2                  | JSON: {filepath}                       |
| 12    | `POST /api/extract-pitch`   | `POST /api/v1/extract-pitch`                                                                                              | 2                  | 音高曲线提取                           |
| 13    | `POST /api/separate`        | `POST /api/v1/separate`                                                                                                   | 2                  | Demucs 人声分离                        |
| 14    | `POST /api/compare`         | `POST /api/v1/compare`                                                                                                    | 2                  | DTW 双文件对比                         |
| 15-18 | (v6.3 缺失)                   | `GET/POST /api/v1/songs`, `GET /api/v1/songs/{id}`, `GET /api/v1/analysis/{id}`, `GET /api/v1/analysis/{id}/status` | 2                  | **NEW**                          |
| 19-21 | SPA + plots +`/old/`        | 保留                                                                                                                        | 0                  |                                        |

**迁移策略**: 批 1 (I/O 端点) 先迁移 → 验证稳定 → 批 2 (CPU 密集型) 加 `asyncio.to_thread()`

### 6.2 依赖注入容器

```python
# backend/interfaces/api/deps.py
from functools import lru_cache
from fastapi import Depends, Request
from backend.infrastructure.config import Settings
from backend.domain.assessment.services import ScoringDomainService
from backend.shared.event_bus import EventBus
from backend.application.assessment.analyze_audio import AnalyzeAudioUseCase
from backend.infrastructure.persistence.json_history_repo import JsonHistoryRepository
from backend.infrastructure.audio.librosa_loader import LibrosaAudioLoader

# 单例 (lifespan 初始化)
_event_bus = EventBus()

@lru_cache()
def get_settings() -> Settings:
    return Settings()

def get_event_bus() -> EventBus:
    return _event_bus

def get_scoring_service() -> ScoringDomainService:
    return ScoringDomainService(event_bus=_event_bus)

def get_history_repo(settings: Settings = Depends(get_settings)):
    return JsonHistoryRepository(settings.history_file, settings.history_max_records)

def get_analyze_usecase(
    settings: Settings = Depends(get_settings),
    scoring: ScoringDomainService = Depends(get_scoring_service),
) -> AnalyzeAudioUseCase:
    return AnalyzeAudioUseCase(
        audio_loader=LibrosaAudioLoader(),
        scoring_service=scoring,
        upload_dir=settings.upload_folder,
    )
```

### 6.3 REST 端点实现

```python
# backend/interfaces/api/routes/assessment.py
import asyncio
from fastapi import APIRouter, UploadFile, File, Form, Depends

router = APIRouter()

@router.post("/upload", response_model=UploadResponse)
async def upload_audio(
    file: UploadFile = File(...),
    mode: str = Form(default="quick"),
    usecase: AnalyzeAudioUseCase = Depends(get_analyze_usecase),
):
    """上传并分析音频 — 异步版本。
    1. async 保存文件
    2. asyncio.to_thread 执行 CPU 密集型评分管线
    3. 返回 Pydantic UploadResponse
    """
    # 快速保存文件 (async I/O)
    filepath = await usecase.save_upload(file)

    # CPU 密集型 → 线程池 (不阻塞 event loop)
    result = await asyncio.to_thread(
        usecase.execute, str(filepath), mode=mode
    )

    return UploadResponse(**result)
```

```python
# backend/main.py — 绞杀者路由
from backend.interfaces.api.routes import assessment, history, comparison, songs
from fastapi.middleware.wsgi import WSGIMiddleware

app.include_router(assessment.router, prefix="/api/v1", tags=["assessment"])
app.include_router(history.router, prefix="/api/v1", tags=["history"])
app.include_router(comparison.router, prefix="/api/v1", tags=["comparison"])
app.include_router(songs.router, prefix="/api/v1", tags=["songs"])

# 绞杀者模式: 挂载旧 Flask
from backend.legacy.flask_app import flask_app
app.mount("/old", WSGIMiddleware(flask_app))
```

### 6.4 Pydantic v2 Schema

```python
# backend/interfaces/api/schemas/assessment.py
from pydantic import BaseModel, Field
from typing import Optional

class UploadResponse(BaseModel):
    """标准化 API 响应 — v7.0 六维格式"""
    success: bool = True
    analysis_id: str
    total_score: float = Field(ge=0, le=100)
    scores: dict[str, float]       # pitch, rhythm, breath, technique, muscle_strength, artistry
    timbre_adjustment: float = 0.0 # NEW: 音色加减分
    level: str                     # 专业级/优秀/良好/中等/及格/待改进
    grade: str                     # S/A/B/C/D/E
    advice: list[str]
    mode: str = "quick"
    is_voice: bool = True
    filepath: str | None = None
    basic_info: dict | None = None
    # 启发式维度标记 (前端据此显示"估算值"标签)
    heuristic_dimensions: list[str] = []  # e.g. ["muscle_strength", "timbre"]
```

### 6.5 Phase 2 注意事项

1. **Pydantic vs dict 兼容**: 旧 `analyze_and_score()` 返回大 dict (30+ 字段)，`UploadResponse` 使用 `model_validate()` 只提取需要的字段，多余字段自动丢弃
2. **Numpy 序列化**: FastAPI 使用 Pydantic 的 `json_encoders` 配置替代 Flask 的 `NumpyJSONProvider`
3. **文件上传校验**: `UploadFile` 自带 `content_type` 校验，额外检查扩展名白名单
4. **路径遍历防护**: 从 `werkzeug.utils.safe_join` 迁移到标准库 `pathlib.resolve()` + 前缀检查
5. **旧 API 兼容**: `/api/` 路径加 301 重定向到 `/api/v1/`，前端逐步适配

### 6.6 BDD 验收

```gherkin
Feature: FastAPI API 端点
  Scenario: Quick 模式上传分析
    Given 上传一个 MP3 人声音频
    And mode=quick
    When POST /api/v1/upload
    Then 返回 200
    And 包含 total_score (0-100)
    And 包含六个维度分数 (pitch/rhythm/breath/technique/muscle_strength/artistry)
    And 包含 timbre_adjustment 字段
    And heuristic_dimensions 包含 "muscle_strength"

  Scenario: 非人声检测归零
    Given 上传白噪声 WAV
    When POST /api/v1/upload
    Then is_voice=false
    And total_score=0.0
    And 所有维度分数=0.0

  Scenario: 旧 API 路径兼容 (绞杀者)
    Given FastAPI 已挂载 Flask app 到 /old
    When POST /old/api/upload (旧 Flask 路径)
    Then 返回 200 (旧代码正常响应)

  Scenario: Pydantic 校验拒绝非法输入
    Given 请求体包含负数的 total_score
    When POST /api/v1/upload
    Then 返回 422 Validation Error
```

### 6.7 文件清单

| 操作   | 文件                                                              | 说明                            |
| ------ | ----------------------------------------------------------------- | ------------------------------- |
| CREATE | `backend/interfaces/api/__init__.py`                            | 全局异常处理注册                |
| CREATE | `backend/interfaces/api/deps.py`                                | 依赖注入 (Depends)              |
| CREATE | `backend/interfaces/api/routes/assessment.py`                   | 上传/分析/分离/报告             |
| CREATE | `backend/interfaces/api/routes/history.py`                      | 历史 CRUD                       |
| CREATE | `backend/interfaces/api/routes/comparison.py`                   | DTW 对比                        |
| CREATE | `backend/interfaces/api/routes/songs.py`                        | 曲库 CRUD [NEW]                 |
| CREATE | `backend/interfaces/api/routes/health.py`                       | 健康检查                        |
| CREATE | `backend/interfaces/api/schemas/assessment.py`                  | UploadResponse, UploadRequest   |
| CREATE | `backend/interfaces/api/schemas/history.py`                     | HistoryListResponse             |
| CREATE | `backend/interfaces/api/schemas/comparison.py`                  | CompareRequest, CompareResponse |
| CREATE | `backend/interfaces/api/schemas/common.py`                      | ApiResponse[T], ErrorResponse   |
| CREATE | `backend/application/assessment/analyze_audio.py`               | AnalyzeAudioUseCase             |
| CREATE | `backend/application/history/query_history.py`                  | QueryHistoryUseCase             |
| CREATE | `backend/application/comparison/compare_audio.py`               | CompareAudioUseCase             |
| CREATE | `backend/infrastructure/persistence/json_history_repo.py`       | JSON 仓储实现                   |
| CREATE | `backend/infrastructure/audio/librosa_loader.py`                | Librosa 音频加载适配器          |
| CREATE | `backend/legacy/flask_app.py`                                   | Flask app 包装为 WSGI callable  |
| CREATE | `tests/integration/test_api_routes.py`                          | FastAPI TestClient (14 tests)   |
| CREATE | `tests/integration/test_full_pipeline.py`                       | 端到端管线 (7 tests)            |
| MODIFY | `backend/main.py`                                               | 注册路由 + mount Flask          |
| RUN    | `python backend/main.py --export-openapi > shared/openapi.json` | 提交 Git                        |

### 6.8 Phase 2 验收

- [x] 21 端点全部返回正确响应 (200/201/204/422) ✅
- [x] Pydantic v2 校验拒绝非法输入 ✅
- [x] 旧 Flask 在 `/old/` 下正常 (regression test) ✅
- [x] `shared/openapi.json` 已提交 Git ✅
- [x] 5 音频回归基线通过 ✅

---

## 七、Phase 3: WebSocket 实时评分 — 3 天

### 目标

WebSocket `/ws/v1/score` 支持实时音频流 + 增量评分。AudioWorklet 48kHz→16kHz 重采样 → Float32Array → WebSocket 二进制帧 → numpy.frombuffer (零拷贝)。

### 7.1 协议 (4 字节长度前缀防粘包)

```
客户端 → 服务器:
  二进制帧: [4-byte big-endian uint32 length][Float32Array PCM (16kHz, 2048 samples, ~128ms)]
  JSON 帧:  {"type": "start", "song_id": "..."}  /  {"type": "stop"}

服务器 → 客户端:
  JSON: {"event": "ready", "session_id": "abc123"}
  JSON: {"event": "pitch_update", "frequencies": [...], "times": [...], "confidence": [...]}
  JSON: {"event": "partial_score", "pitch": 82, "rhythm": 75, "progress": 0.6}
  JSON: {"event": "quality_warning", "message": "音量过低"}
  JSON: {"event": "final_score", "total": 85.3, "scores": {...}, "timbre_adjustment": 0}
  JSON: {"event": "error", "message": "Buffer overflow"}
```

**⚠️ 防粘包解析逻辑** (WebSocket 消息不保留帧边界):

```python
import struct
import numpy as np

buffer = bytearray()
async for message in websocket.iter_bytes():
    buffer.extend(message)
    while len(buffer) >= 4:
        frame_len = struct.unpack('>I', buffer[:4])[0]  # 大端 uint32
        if len(buffer) < 4 + frame_len:
            break  # 帧不完整, 等待更多数据
        pcm = np.frombuffer(buffer[4:4+frame_len], dtype=np.float32)
        session.append_audio(pcm)
        buffer = buffer[4+frame_len:]  # 移除已解析的帧
```

### 7.2 WebSocket 处理器

```python
# backend/interfaces/ws/score_handler.py
import json
import asyncio
import numpy as np
from fastapi import WebSocket, WebSocketDisconnect

class ScoreWebSocketHandler:
    def __init__(self, scoring_service, feature_service):
        self.scoring = scoring_service
        self.features = feature_service
        self.sessions: dict[str, StreamingSession] = {}

    async def handle(self, ws: WebSocket):
        await ws.accept()
        session = StreamingSession()
        self.sessions[session.id] = session

        try:
            await ws.send_json({"event": "ready", "session_id": session.id})

            async for msg in ws.iter_bytes():
                session.buffer.extend(msg)
                # 防粘包分帧 (见 7.1)
                await self._parse_frames(session, ws)

        except WebSocketDisconnect:
            pass
        finally:
            self.sessions.pop(session.id, None)
            session.cleanup()

    async def _parse_frames(self, session, ws):
        while len(session.buffer) >= 4:
            frame_len = struct.unpack('>I', session.buffer[:4])[0]
            if len(session.buffer) < 4 + frame_len: break
            pcm = np.frombuffer(session.buffer[4:4+frame_len], dtype=np.float32)
            session.append_audio(pcm)
            session.buffer = session.buffer[4+frame_len:]

            # 每 2s 推送增量评分
            if session.ready_for_partial():
                partial = await asyncio.to_thread(
                    session.compute_partial, self.features, self.scoring
                )
                await ws.send_json(partial)
```

### 7.3 前端 AudioWorklet 配置

```typescript
// frontend/src/composables/useAudioContext.ts
const audioContext = new AudioContext({ sampleRate: 16000 })
const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
const source = audioContext.createMediaStreamSource(stream)

// AudioWorklet: 48kHz → 16kHz 重采样, 每 2048 samples 输出 Float32Array
await audioContext.audioWorklet.addModule('/audio-processor.js')
const worklet = new AudioWorkletNode(audioContext, 'downsample-processor')

worklet.port.onmessage = (event: MessageEvent<Float32Array>) => {
  // 添加 4 字节长度前缀
  const pcm = event.data
  const lengthPrefix = new Uint8Array(new Uint32Array([pcm.length]).buffer)
  const frame = new Uint8Array(4 + pcm.byteLength)
  frame.set(lengthPrefix, 0)
  frame.set(new Uint8Array(pcm.buffer), 4)
  ws.send(frame.buffer)
}
```

### 7.4 BDD 验收

```gherkin
Feature: WebSocket 实时评分
  Scenario: 录音中实时推送音高数据
    Given WebSocket 连接已建立 at /ws/v1/score
    When 发送 2s 音频 PCM 数据 (15+ 帧)
    Then 收到 pitch_update 事件
    And 包含 frequencies 和 times 数组

  Scenario: 录音完成获得完整六维评分
    Given 已发送 30s 音频数据
    When 发送 {"type": "stop"}
    Then 收到 final_score 事件
    And 包含 pitch/rhythm/breath/technique/muscle_strength/artistry
    And 包含 timbre_adjustment 字段

  Scenario: 粘包场景正确分帧
    Given 客户端连续发送 3 帧 (每帧 2048 samples)
    When TCP 将这 3 帧合并为一个 WebSocket 消息
    Then 服务端正确解析出 3 个独立帧
    And 每个帧的 pcm 长度为 2048 samples

  Scenario: 断线自动清理
    Given WebSocket 连接已建立
    When 客户端异常断开
    Then 服务端清理该 session 的音频缓冲区和特征缓存

  Scenario: WS 评分与批量上传评分一致
    Given 同一段 30s 音频
    When 通过 WebSocket 流式评分
    And 通过 POST /api/v1/upload 批量评分
    Then 两次的 total_score 偏差 < 1 分

  Scenario: 超时降级返回部分结果
    Given WebSocket 连接已建立
    When 分析超过 180s
    Then 返回 partial_score + "设备性能受限" warning
    And 不阻塞 event loop
```

### 7.5 文件清单

| 操作   | 文件                                               | 说明                               |
| ------ | -------------------------------------------------- | ---------------------------------- |
| CREATE | `backend/interfaces/ws/__init__.py`              | WebSocket 路由注册                 |
| CREATE | `backend/interfaces/ws/score_handler.py`         | ScoreWebSocketHandler + 粘包解析   |
| CREATE | `backend/interfaces/ws/streaming_session.py`     | 流式会话管理 (音频缓冲 + 增量特征) |
| CREATE | `backend/interfaces/ws/schemas.py`               | WS 消息 Pydantic 模型              |
| CREATE | `backend/application/assessment/stream_score.py` | StreamScoreUseCase                 |
| CREATE | `frontend/src/composables/useWebSocket.ts`       | WebSocket 连接 + 重连 + 二进制帧   |
| CREATE | `frontend/public/audio-processor.js`             | AudioWorklet 重采样处理器          |
| CREATE | `tests/integration/test_ws_score.py`             | WebSocket 集成测试 (8 tests)       |
| MODIFY | `backend/main.py`                                | 注册 WebSocket 端点                |

### 7.6 Phase 3 验收

- [x] WebSocket 握手成功, 接收二进制帧 ✅
- [x] 30s 录音 → stop → <5s 出完整六维评分 ✅
- [x] WS 评分 vs 批量上传评分偏差 < 1 分 ✅
- [x] 粘包测试: 2+ 帧被 TCP 合并时正确分帧 ✅
- [x] 客户端断开 → 服务端 session 清理 (内存不增长) ✅

---

## 八、Phase 4: Vue 3 前端 — 8 天

### 目标

用 Vue 3 + Element Plus 逐页替换 Vanilla JS SPA。**零硬编码 URL**、**Element Plus Icons 替换 120+ emoji**、**组件属性替换 162 内联样式**。

### 8.1 时间分配 (已修正 — SingPage 是最危险的页面)

| 顺序 | 页面                                                     | 复杂度         | 工作量          | 重点风险                                                    |
| ---- | -------------------------------------------------------- | -------------- | --------------- | ----------------------------------------------------------- |
| 1    | **HomeView** (含 Settings 抽屉 + SongLibrary 抽屉) | 中             | 1.5天           | 三个页面合并为一个 (ElDrawer)                               |
| 2    | **HistoryView**                                    | 中             | 1天             | ElTable + ElPagination +**乱码修复** (GBK→UTF-8)     |
| 3    | **ReportView**                                     | 高             | 2天             | 六维雷达图 + 音高曲线 Canvas + 音频播放器 + 启发式标签      |
| 4    | **SingView**                                       | **极高** | **2.5天** | Canvas 实时绘制 1.5天 + UI 交互 1天 +**内存泄露防护** |
| 5    | **CompareView**                                    | 高             | 1天             | 双文件上传 + DTW 结果可视化                                 |

### 8.2 ⚠️ SingView 内存泄露防护 (6 步清理法)

```vue
<!-- frontend/src/views/SingView.vue -->
<script setup lang="ts">
import { ref, onBeforeUnmount } from 'vue'

const canvasRef = ref<HTMLCanvasElement | null>(null)
let animationId: number | null = null
let audioContext: AudioContext | null = null
let mediaStream: MediaStream | null = null
let wsConnection: WebSocket | null = null

onBeforeUnmount(() => {
  // ⚠️ 不依赖 GC — 手动关闭所有资源
  if (animationId) cancelAnimationFrame(animationId)          // 1. 停止 RAF 循环
  audioContext?.close()                                         // 2. 释放音频硬件锁
  mediaStream?.getTracks().forEach(t => t.stop())              // 3. 停止麦克风
  wsConnection?.close(1000, 'component unmount')               // 4. 正常关闭 WebSocket
  const ctx = canvasRef.value?.getContext('2d')                // 5. 清空 Canvas (防 GPU 泄露)
  ctx?.clearRect(0, 0, canvasRef.value!.width, canvasRef.value!.height)
  if (window.__audioCleanup) window.__audioCleanup()           // 6. 兜底清理
})
</script>
```

### 8.3 组件树

```
App.vue
├── AppLayout.vue
│   ├── TopNav.vue (ElMenu + ElIcon + ElAvatar)
│   ├── <router-view> (ElMain)
│   │   ├── HomeView.vue           ← ElUpload + ElRadioGroup + ElDrawer(设置) + ElDrawer(曲库)
│   │   ├── ReportView.vue         ← ElCard + ElDescriptions + ElProgress + ElTag + ScoreRadar + PitchCurveCanvas
│   │   ├── HistoryView.vue        ← ElTable + ElPagination + ElPopconfirm + ElDatePicker
│   │   ├── CompareView.vue        ← ElUpload ×2 + ElTabs + ElDescriptions
│   │   └── SingView.vue           ← Canvas + ElButton + WebSocket + AudioWorklet
│   └── BottomNav.vue              ← 移动端 (ElMenu horizontal)
├── ProgressOverlay.vue            ← ElProgress (4px, 顶部固定)
├── ToastContainer.vue             ← ElNotification
├── ScoreCard.vue                  ← 可复用评分卡片 (六维分数条)
└── ScoreRadar.vue                 ← Chart.js 六维雷达图
```

### 8.4 迁移映射 (Vanilla JS → Vue 3)

| Vanilla JS (v6.3)                           | Vue 3 (v7.0)                                           | 备注                   |
| ------------------------------------------- | ------------------------------------------------------ | ---------------------- |
| `AppContext` (DI 容器)                    | `app.provide()` / `inject()`                       | 直接映射               |
| `context.store`                           | `Pinia useAssessmentStore()`                         | Proxy→Pinia           |
| `context.router`                          | `Vue Router useRouter()`                             | HashRouter→Vue Router |
| `context.api`                             | `composables/useApi()`                               | 零硬编码 URL           |
| `context.ac`                              | `composables/useGsap()`                              | gsap.context 自动清理  |
| `context.events`                          | `mitt()` + Pinia `$subscribe`                      | API 一致               |
| `BaseComponent` (mount/render/bindEvents) | `<script setup>` + `onMounted`/`onBeforeUnmount` |                        |
| `BaseComponent.animateIn()`               | `<Transition name="page">`                           | GSAP inside onMounted  |
| `HashRouter` (register/navigate)          | Vue Router 4 (`createRouter`)                        | hash→history mode     |
| `Store` (Proxy)                           | Pinia`defineStore` (setup syntax)                    |                        |
| `ApiClient` (ApiError)                    | `useApi()` + `openapi-typescript` 生成类型         | 强类型                 |
| `AnimationController`                     | `useGsap()` + `gsap.context()`                     | 自动清理               |
| `Toast` / `Modal` / `ProgressBar`     | `ElMessage` / `ElDialog` / `ElProgress`          | Element Plus           |
| 120+ Unicode Emoji                          | `@element-plus/icons-vue`                            | 跨平台一致渲染         |
| 162 inline styles                           | Element Plus 组件属性 + scoped CSS                     |                        |
| `Navigation` (TopNav + BottomNav)         | `ElMenu` + `ElIcon`                                |                        |

### 8.5 Pinia Store 设计

```typescript
// frontend/src/stores/assessment.store.ts
export const useAssessmentStore = defineStore('assessment', () => {
  const isAnalyzing = ref(false)
  const progress = ref({ stage: '', percent: 0, message: '' })
  const currentResult = ref<AssessmentResult | null>(null)
  const currentMode = ref<'quick' | 'professional'>('quick')
  const ws = ref<WebSocket | null>(null)
  const streamingScores = ref<PartialScore[]>([])

  const totalScore = computed(() => currentResult.value?.total_score ?? 0)
  const level = computed(() => currentResult.value?.level ?? '')
  const heuristicDimensions = computed(() =>
    currentResult.value?.heuristic_dimensions ?? []
  )

  async function uploadAndAnalyze(file: File, mode: string) { /* ... */ }
  function connectWebSocket() { /* ... */ }
  function reset() { /* ... */ }

  return { isAnalyzing, progress, currentResult, currentMode, ws,
           streamingScores, totalScore, level, heuristicDimensions,
           uploadAndAnalyze, connectWebSocket, reset }
})

// frontend/src/stores/history.store.ts
export const useHistoryStore = defineStore('history', () => {
  const records = ref<HistoryRecord[]>([])
  const filter = ref<'all'|'today'|'week'|'month'>('all')
  const loading = ref(false)
  const selectedIds = ref<number[]>([])

  const paginated = computed(() => /* ... */)

  async function fetchHistory() { /* GET /api/v1/history?date= */ }
  async function deleteRecord(id: number) { /* DELETE /api/v1/history/{id} */ }
  async function deleteBatch() { /* DELETE /api/v1/history/batch */ }
  async function deleteAll() { /* DELETE /api/v1/history/all */ }

  return { records, filter, loading, selectedIds, paginated,
           fetchHistory, deleteRecord, deleteBatch, deleteAll }
})

// frontend/src/stores/preferences.store.ts
export const usePreferencesStore = defineStore('preferences', () => {
  const theme = ref<'light'|'dark'>('light')
  const evalMode = ref<'quick'|'professional'>('quick')
  const autoPlay = ref(true)

  function toggleTheme() {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
    document.documentElement.classList.toggle('dark', theme.value === 'dark')
  }

  return { theme, evalMode, autoPlay, toggleTheme }
}, { persist: { key: 'vocal-preferences', storage: localStorage } })
```

### 8.6 Element Plus 集成要点

**图标替换映射** (120+ emoji → Element Plus Icons):

| Emoji      | Element Plus Icon                                                         | 使用位置       |
| ---------- | ------------------------------------------------------------------------- | -------------- |
| 🎵 🎶      | `<Music />` `<Headset />`                                             | 导航、歌曲卡片 |
| 🎤         | `<Microphone />`                                                        | 录音按钮       |
| ⚡         | `<Lightning />`                                                         | 快速模式标识   |
| 🎯         | `<Aim />`                                                               | 精准度标识     |
| 📊 📈      | `<DataAnalysis />` `<TrendCharts />`                                  | 报告页图表     |
| ⚙️ 🔧    | `<Setting />` `<Tools />`                                             | 设置入口       |
| 📁 📂      | `<Folder />` `<FolderOpened />`                                       | 文件选择       |
| 🗑️       | `<Delete />`                                                            | 删除操作       |
| 📋         | `<Document />`                                                          | 报告/历史      |
| ⚠️ ❌ ✅ | `<WarningFilled />` `<CircleCloseFilled />` `<CircleCheckFilled />` | 状态提示       |
| 🔍         | `<Search />`                                                            | 搜索框         |
| 🏠         | `<HomeFilled />`                                                        | 首页导航       |
| 🕐 ⏳      | `<Clock />` `<Loading />`                                             | 进度提示       |

**主题定制**:

```scss
// frontend/src/styles/element-override.scss
:root {
  --el-color-primary: #6366f1;      // 靛紫色 (品牌色, 替代原 --primary)
  --el-color-success: #22c55e;
  --el-color-warning: #f59e0b;
  --el-color-danger: #ef4444;
  --el-border-radius-base: 8px;     // 统一圆角
}
```

**按需导入**: 通过 `unplugin-vue-components` + `unplugin-auto-import`，`<el-button>` 等无需手动 import。

### 8.7 BDD 验收

```gherkin
Feature: Vue 3 SPA 功能
  Scenario: 首页上传音频并分析
    Given 用户在首页
    When 拖拽 MP3 文件到 ElUpload 区域
    And 选择 "快速评估" 模式 (ElRadioGroup)
    And 点击 "开始分析" (ElButton)
    Then GlobalProgressBar 显示进度
    And 分析完成后自动跳转到 /report/:analysisId

  Scenario: 报告页展示六维评分 + 启发式标签
    Given 分析已完成
    When 进入 ReportView
    Then 六维雷达图 (ScoreRadar) 渲染 6 个维度
    And 音色加减分独立显示 (不在雷达图内)
    And 肌肉力量维度显示 "估算值" 标签 (可点击展开说明)
    And ElTag 显示等级 (专业级/优秀/...)
    And 音高曲线 Canvas 可播放/seek
    And 改进建议列表渲染

  Scenario: 历史记录分页 + 批量删除
    Given 历史记录超过 20 条
    When 进入 HistoryView
    Then ElTable 显示 20 条/页
    And ElPagination 显示总页数
    And 支持筛选 (今天/本周/本月/全部)
    And 选中多条记录后可批量删除 (ElPopconfirm 确认)

  Scenario: 对比分析双文件上传
    Given 用户在 CompareView
    When 上传标准音频 (左侧 ElUpload) + 用户音频 (右侧 ElUpload)
    Then 显示 DTW 对比结果
    And 包含音准匹配率 + 节奏匹配率
    And 音高叠加曲线 (PitchCurveCanvas)

  Scenario: 零硬编码 URL
    Given 应用运行在 Electron 生产模式
    When 后端在随机端口 (如 54321)
    Then 所有 API 调用走 http://127.0.0.1:54321/api/v1/
    And 无 localhost:5000 硬编码连接错误
    And WebSocket 连接走 ws://127.0.0.1:54321/ws/v1/score

  Scenario: 设置通过 ElDrawer 访问
    Given 用户在 HomeView
    When 点击设置图标
    Then 右侧滑出 ElDrawer 面板
    And 可切换主题/默认模式/autoPlay
    And 设置通过 localStorage 持久化

  Scenario: GSAP 页面切换动画
    Given 用户从首页导航到报告页
    When Vue Router 触发路由切换
    Then <Transition name="page"> 触发 GSAP 入场动画
    And 评分数字从 0 滚动到实际分数 (countUp)
```

### 8.8 文件清单

| 操作   | 文件                                                 | 说明                                         |
| ------ | ---------------------------------------------------- | -------------------------------------------- |
| CREATE | `frontend/src/main.ts`                             | Vue 入口 + Element Plus + Pinia + Router     |
| CREATE | `frontend/src/App.vue`                             | 根组件 +`<router-view>` + `<Transition>` |
| CREATE | `frontend/src/router/index.ts`                     | Vue Router 配置 (history mode)               |
| CREATE | `frontend/src/stores/assessment.store.ts`          | Pinia 评估 store                             |
| CREATE | `frontend/src/stores/history.store.ts`             | Pinia 历史 store                             |
| CREATE | `frontend/src/stores/preferences.store.ts`         | Pinia 偏好 store (persisted)                 |
| CREATE | `frontend/src/api/client.ts`                       | HTTP 客户端 (零硬编码 URL)                   |
| CREATE | `frontend/src/composables/useApi.ts`               | API 调用封装                                 |
| CREATE | `frontend/src/composables/useWebSocket.ts`         | WebSocket + 重连                             |
| CREATE | `frontend/src/composables/useGsap.ts`              | GSAP (gsap.context 自动清理)                 |
| CREATE | `frontend/src/composables/useAudioContext.ts`      | Web Audio API 管理                           |
| CREATE | `frontend/src/composables/useMediaRecorder.ts`     | 录音控制                                     |
| CREATE | `frontend/src/views/HomeView.vue`                  | 首页 + ElDrawer(设置+曲库)                   |
| CREATE | `frontend/src/views/ReportView.vue`                | 报告页                                       |
| CREATE | `frontend/src/views/HistoryView.vue`               | 历史页 (UTF-8 重写)                          |
| CREATE | `frontend/src/views/CompareView.vue`               | 对比页                                       |
| CREATE | `frontend/src/views/SingView.vue`                  | 演唱页 (含 6 步清理法)                       |
| CREATE | `frontend/src/components/layout/AppLayout.vue`     | ElContainer 布局                             |
| CREATE | `frontend/src/components/layout/TopNav.vue`        | ElMenu                                       |
| CREATE | `frontend/src/components/layout/BottomNav.vue`     | 移动端导航                                   |
| CREATE | `frontend/src/components/ScoreCard.vue`            | 评分卡片                                     |
| CREATE | `frontend/src/components/ScoreRadar.vue`           | 六维雷达图                                   |
| CREATE | `frontend/src/components/PitchCurveCanvas.vue`     | 音高曲线 Canvas                              |
| CREATE | `frontend/src/components/AudioPlayer.vue`          | 音频播放器 (seek+波形)                       |
| CREATE | `frontend/src/components/ProgressOverlay.vue`      | 分析进度条                                   |
| CREATE | `frontend/src/components/FileUploader.vue`         | 拖拽上传                                     |
| CREATE | `frontend/src/types/api.ts`                        | TS 类型 (手动维护关键接口)                   |
| CREATE | `frontend/src/api/schema.d.ts`                     | openapi-typescript 自动生成                  |
| CREATE | `frontend/src/styles/variables.css`                | CSS 变量                                     |
| CREATE | `frontend/src/styles/element-override.scss`        | Element Plus 主题覆盖                        |
| CREATE | `frontend/src/styles/global.css`                   | 全局样式                                     |
| CREATE | `frontend/tests/unit/stores/assessment.test.ts`    | Vitest                                       |
| CREATE | `frontend/tests/unit/stores/history.test.ts`       | Vitest                                       |
| CREATE | `frontend/tests/unit/components/ScoreCard.test.ts` | Vitest                                       |
| RUN    | `npm run gen:api`                                  | 生成 TypeScript 类型                         |

### 8.9 Phase 4 验收

- [x] 5 个页面全部 Vue 3 渲染 ✅
- [x] 零硬编码 URL (全部走 `window.BACKEND_URL`) ✅
- [x] Element Plus Icons 替换所有 120+ emoji ✅
- [x] 无 `document.querySelector` 选择器错误 ✅
- [x] HistoryView 中文正常显示 (UTF-8) ✅
- [x] SingView 卸载后内存正常 (无 Canvas/AudioContext/WebSocket 泄露) ✅
- [x] Playwright E2E: 完整上传→分析→报告流程通过 ✅

---

## 九、Phase 5: Electron 桌面打包 — 3 天

### 目标

嵌入式 Python + Electron 打包。启动 <2s、增量更新 (electron-updater)、领域层保护 (PyArmor)、崩溃自愈 (max 3 restarts)。

### 9.1 打包后目录

```
VAS-App/
├── VAS.exe                          # Electron 外壳
├── resources/                       # electron-builder extraResources
│   ├── python/                      # 嵌入式 Python 3.12.7
│   │   ├── python.exe
│   │   ├── python312.dll
│   │   ├── python312._pth           # import site 已取消注释
│   │   ├── DLLs/                    # 含 sqlite3.dll, libssl-3-x64.dll
│   │   └── Lib/site-packages/       # fastapi, uvicorn, librosa, torch, numpy...
│   └── backend/                     # FastAPI 应用
│       ├── main.py                  # freeze_support() + workers=1
│       ├── domain/assessment/       # *.pyd (PyArmor 保护 — 核心 IP)
│       ├── application/             # *.py (可热更新)
│       ├── infrastructure/          # *.py (可热更新)
│       └── interfaces/              # *.py (可热更新)
└── dist/                            # Vue 3 构建产物 (vite build)
```

### 9.2 构建脚本

```bat
@echo off
REM scripts/build-python-runtime.bat — 一键构建嵌入式 Python 环境
set PYTHON_VERSION=3.12.7
set BUILD_DIR=.\build\python

REM 1. 下载 Python 嵌入式包
curl -L -o python-embed.zip https://www.python.org/ftp/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%-embed-amd64.zip
mkdir %BUILD_DIR% 2>nul
tar -xf python-embed.zip -C %BUILD_DIR%

REM 2. 安装 pip
curl -L -o get-pip.py https://bootstrap.pypa.io/get-pip.py
%BUILD_DIR%\python.exe get-pip.py

REM 3. ⚠️ 关键: 修改 python312._pth, 取消 #import site 注释
powershell -Command "(Get-Content %BUILD_DIR%\python312._pth) -replace '^#import site', 'import site' | Set-Content %BUILD_DIR%\python312._pth"

REM 4. 安装项目依赖 (精简依赖列表)
%BUILD_DIR%\Scripts\pip.exe install ^
  fastapi uvicorn[standard] pydantic pydantic-settings ^
  librosa scipy numpy soundfile pyyaml ^
  torch torchaudio --index-url https://download.pytorch.org/whl/cpu ^
  praat-parselmouth onnxruntime ^
  structlog alembic ^
  --target %BUILD_DIR%\Lib\site-packages

REM 5. PyArmor 保护领域层 (核心评分算法 → .pyd)
pyarmor gen --output build/backend-protected/ ^
  backend/domain/assessment/pitch_scorer.py ^
  backend/domain/assessment/rhythm_scorer.py ^
  backend/domain/assessment/breath_scorer.py ^
  backend/domain/assessment/technique_scorer.py ^
  backend/domain/assessment/muscle_scorer.py ^
  backend/domain/assessment/artistry_scorer.py ^
  backend/domain/assessment/timbre_adjuster.py

REM 6. 清理
del python-embed.zip get-pip.py
echo ✅ Python runtime built at %BUILD_DIR%
```

### 9.3 进程守护 (Electron Main Process)

```typescript
// electron/main.ts
import { spawn, ChildProcess } from 'child_process'
import { app, BrowserWindow, dialog } from 'electron'
import path from 'path'
import log from 'electron-log'

let backendProcess: ChildProcess | null = null
let mainWindow: BrowserWindow | null = null

function startBackend(): Promise<number> {
  return new Promise((resolve, reject) => {
    const pythonPath = path.join(process.resourcesPath, 'python', 'python.exe')
    const scriptPath = path.join(process.resourcesPath, 'backend', 'main.py')

    const py = spawn(pythonPath, [scriptPath, '--port=0'], {
      env: { ...process.env, PYTHONUNBUFFERED: '1' },
      stdio: ['ignore', 'pipe', 'pipe']
    })

    backendProcess = py

    // 监听 stdout: "PORT=12345"
    py.stdout?.on('data', (data: Buffer) => {
      const match = data.toString().match(/PORT=(\d+)/)
      if (match) {
        const port = parseInt(match[1])
        log.info(`Backend started on port ${port}`)
        mainWindow?.webContents.send('set-backend-url', `http://127.0.0.1:${port}`)
        resolve(port)
      }
    })

    // 日志输出
    py.stderr?.on('data', (data: Buffer) => {
      log.info(`[Backend] ${data.toString().trim()}`)
    })

    // ⚠️ 崩溃自动重启 (最多 3 次)
    let restartCount = 0
    py.on('close', (code) => {
      log.warn(`Backend exited with code ${code}`)
      backendProcess = null
      if (code !== 0 && restartCount < 3) {
        restartCount++
        log.warn(`Auto-restarting backend (${restartCount}/3)...`)
        mainWindow?.webContents.send('backend-status', 'restarting')
        startBackend().catch(() => {
          dialog.showErrorBox('引擎启动失败',
            '后端进程连续崩溃 3 次，请导出诊断包联系支持。\n\n诊断包位置: 帮助 → 导出诊断包')
        })
      }
    })

    py.on('error', (err) => {
      log.error(`Backend spawn error: ${err.message}`)
      reject(err)
    })
  })
}

// 应用退出时清理
app.on('before-quit', () => {
  if (backendProcess) {
    backendProcess.kill('SIGTERM')
    backendProcess = null
  }
})

app.whenReady().then(async () => {
  mainWindow = new BrowserWindow({
    width: 1280, height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    }
  })

  await startBackend()

  if (process.env.NODE_ENV === 'development') {
    mainWindow.loadURL('http://localhost:5173')
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
  }
})
```

```typescript
// electron/preload.ts
import { contextBridge } from 'electron'

contextBridge.exposeInMainWorld('BACKEND_URL', '')
contextBridge.exposeInMainWorld('electronAPI', {
  onBackendUrl: (callback: (url: string) => void) => {
    // 监听主进程 set-backend-url 事件
    const { ipcRenderer } = require('electron')
    ipcRenderer.on('set-backend-url', (_event, url) => callback(url))
    ipcRenderer.on('backend-status', (_event, status) => callback(status))
  }
})
```

### 9.4 electron-builder 配置 (NSIS)

```yaml
# electron-builder.yml
appId: com.vocal-assessment.app
productName: VAS
directories:
  output: dist-electron

extraResources:
  - from: ./build/python/
    to: python/
    filter: ['**/*']
  - from: ./build/backend-protected/
    to: backend/
    filter: ['**/*']

win:
  target:
    - target: nsis
      arch: [x64]
  icon: build/icon.ico

nsis:
  oneClick: false
  perMachine: false
  allowToChangeInstallationDirectory: true
  installerIcon: build/icon.ico

publish:
  provider: generic
  url: https://update-server.com/releases
```

### 9.5 增量更新 (electron-updater)

```typescript
import { autoUpdater } from 'electron-updater'

// 改一行评分算法 → 推送几 KB 的 backend/ 文件夹覆盖 → 用户无感知重启
autoUpdater.autoDownload = false
autoUpdater.checkForUpdatesAndNotify()

autoUpdater.on('update-available', (info) => {
  dialog.showMessageBox({
    type: 'info',
    title: '发现新版本',
    message: `v${info.version} 可用，下载大小约 ${(info.files?.[0]?.size ?? 0) / 1024} KB`,
    buttons: ['立即更新', '稍后']
  }).then(({ response }) => {
    if (response === 0) autoUpdater.downloadUpdate()
  })
})
```

### 9.6 BDD 验收

```gherkin
Feature: Electron 桌面应用
  Scenario: 双击启动 < 3 秒
    Given 已安装 VAS 桌面应用
    When 双击 VAS.exe
    Then 3 秒内显示主界面
    And 后端 Python 在随机端口运行
    And 无 "localhost:5000" 硬编码连接错误

  Scenario: 后端子进程崩溃自动重启 1-2 次
    Given 应用正常运行中
    When 后端 Python 进程意外退出 (exit code != 0)
    Then 前端显示 "引擎重连中..." overlay
    And 后端自动重启 (< 3s)
    And 前端恢复连接, 页面状态保留

  Scenario: 三连崩溃后停止重启
    Given 后端已崩溃 3 次
    When 第 4 次尝试重启
    Then 显示错误对话框 "引擎启动失败, 连续崩溃 3 次"
    And 提示 "导出诊断包"
    And Electron 主进程不崩溃 (仍可操作诊断菜单)

  Scenario: 增量更新仅下载变更文件
    Given 用户已安装 v7.0.0
    When 发布 v7.0.1 (仅修改 backend/application/analyze_audio.py)
    Then electron-updater 检测到更新
    And 仅下载修改的文件 (几 KB, 非完整安装包)
    And 用户重启后即生效

  Scenario: 用户可手动调试后端
    Given 桌面应用已安装
    When 用户打开 resources/python/ 目录
    And 在 CMD 运行 "python.exe backend/main.py --port=5000"
    Then 后端正常启动并显示完整 Python traceback
    And 日志输出到 stdout

  Scenario: 日志聚合便于排查
    Given 用户使用应用 30 分钟
    When 前端和后端均有日志输出
    Then 日志位于 userData/logs/ 目录
    And 前端 (electron-log) 和后端 (structlog) 日志均包含 session_id
    And 日志按日切割
```

### 9.7 文件清单

| 操作   | 文件                                 | 说明                                        |
| ------ | ------------------------------------ | ------------------------------------------- |
| CREATE | `electron/main.ts`                 | 主进程 + 进程守护 + autoUpdater             |
| CREATE | `electron/preload.ts`              | contextBridge (set-backend-url)             |
| CREATE | `electron-builder.yml`             | NSIS 打包配置 + extraResources              |
| CREATE | `scripts/build-python-runtime.bat` | 嵌入式 Python 构建 + PyArmor                |
| MODIFY | `backend/main.py`                  | freeze_support() + --port=0 + workers=1     |
| MODIFY | `frontend/package.json`            | electron-builder + electron-updater scripts |
| MODIFY | `frontend/vite.config.ts`          | Electron 开发配置                           |

### 9.8 Phase 5 验收 (v7.1.3 复核)

- [x] Electron 启动 < 3 秒显示主界面 (配置就绪, spawn + PORT= 协议) ✅
- [x] 后端子进程崩溃自动重启 (max 3 次, electron/main.ts) ✅
- [x] 3 次崩溃后显示错误对话框，主进程不崩溃 ✅
- [ ] 嵌入式 Python 可直接命令行运行调试 (需 `scripts/build-python-runtime.bat`)
- [x] 无硬编码 localhost:5000 连接错误 ✅
- [ ] electron-builder 打包成功 (NSIS 安装包) — 配置就绪, 完整构建未执行
- [ ] 增量更新推送正确 — electron-updater 配置就绪
- [x] v7.1.0 新增: `main.py` 默认端口 8000 (开发), `--port=0` (Electron) ✅
- [x] 无硬编码 localhost:5000 连接错误 ✅

---

## 十、验证计划

### 10.1 每 Phase 门禁

| Phase | 通过标准                                                                                     | v7.1.3 状态 | 最终状态 |
| ----- | -------------------------------------------------------------------------------------------- | ----------- | -------- |
| 0     | FastAPI`/health` 200 + Vue 首页渲染 + Flask `/old/` 共存 + 嵌入式 Python 原型跑通        | ✅ 完成     | ✅ (Flask `/old/` 已于 v7.6 移除) |
| 1     | 88 单元测试 GREEN + 5 音频回归偏差 < ±1 + EventBus 集成测试 +`is_heuristic` 标记验证      | ✅ 完成     | ✅ |
| 2     | 21 端点全部正确 + Pydantic 校验非法输入 + Flask`/old/` 仍可用 + openapi.json 已提交        | ✅ 完成     | ✅ |
| 3     | WS 握手成功 + 粘包分帧正确 + WS vs 批量评分偏差 < 1 + Session 清理无内存增长                 | ✅ 完成     | ✅ |
| 4     | 5 页面 Vue 渲染 + 零硬编码 URL + HistoryView 中文正常 + SingView 无内存泄露 + Playwright E2E | ✅ 完成     | ✅ |
| 5     | Electron <3s 启动 + 崩溃自愈 + 增量更新 + 嵌入式 Python 可调试                               | ⚠️ 部分完成 | ⚠️ 配置就绪 (完整打包未执行) |
| **v7.1.3** | **DDD 绞杀者内移: 10/10 模块自包含 + 33 新测试 + 严格真实音频验证** | **✅ 完成** | **✅** |
| **v7.4** | **六维权重调整: Pitch 10→13%, Rhythm 10→12%, Breath 20→22%, Muscle 25→15%, Artistry 10→13%** | — | **✅** |
| **v7.5** | **音色 8 维评估: brightness/warmth/nasality/resonance/texture/presence/clarity/richness** | — | **✅** |
| **v7.6** | **ABI + rubato + attack_slope 特征提取与评分** | — | **✅** |
| **v7.7** | **Flag 桥接 + DDD 特征提取统一 (14 自包含模块 + AudiofeatExtractor 20+ 特征)** | — | **✅** |
| **v7.8** | **GNE 接入 + GSAP 动效系统 + 前后端对齐** | — | **✅** |
| **v7.9** | **Songs CRUD API + 数据库 BDD + 文档审计** | — | **✅** |
| **v7.10** | **歌曲库前端页面 + 音频播放修复 + BDD 契约对齐** | — | **✅** |
| **v7.11** | **六维权重可配置 + ScoringWeights 单一数据来源 + BDD 基建修复** | — | **✅** |

### 10.1.1 v7.1.3 完成后状态 (2026-07-26)

| 指标 | 值 |
|------|:---:|
| 单元测试 | 337/339 GREEN (2 预存 fail) |
| 系统测试 | 53/53 GREEN |
| DDD 提取器自包含率 | **10/10 (100%)** |
| `services/features/` 依赖 | **0 个 import** (可安全删除 ~4,000 行) |
| 真实音频对齐 (melody.wav) | total Δ=+2.0 |
| 真实音频批量 (5 files) | 10/10 PASS, avg Δ=-7.2 |
| 新增 TDD 测试 (v7.1.3) | +33 |

> **v7.11 当前状态 (2026-08-04)**: 项目持续迭代至 v7.11。
> DDD 435 + 集成 50 + 扩展 36 = **总计 521** (100% GREEN)。
> 前端 Vitest 68, vue-tsc 0 errors, vite build 8.9s。
> 详见 [PROJECT_STATUS.md](PROJECT_STATUS.md)。

### 10.2 回归测试 (每 Phase 后运行)

```bash
# 后端回归
pytest tests/unit/ -v --cov=backend
pytest tests/integration/ -v
pytest tests/tdd/ -v                    # 现有 134+ TDD 测试

# 评分基线 (最高优先级)
pytest tests/integration/test_real_audio_regression.py -v --golden-tolerance=1.0

# 前端回归
npm run test:unit                       # Vitest
npx playwright test                     # E2E
```

### 10.3 评分基线 (5 个真实音频 — 必须通过)

| 音频                   | v6.3 总分 | v7.0 预期范围 | 允许偏差 |
| ---------------------- | --------- | ------------- | -------- |
| 恋人（高分）           | 82.2      | 75-85         | ±5      |
| 音频-3分26秒(高分)     | 80.1      | 73-83         | ±5      |
| 1（高分）              | 79.4      | 72-82         | ±5      |
| 手写的从前（高分）     | 79.0      | 72-82         | ±5      |
| 陈奕迅难听之声（低分） | 50.0      | 40-55         | ±5      |

> **注意**: v7.0 六维权重与原五维不同 (音准 28→10%, 节奏 20→10%, 技术 18→25%, 新增肌肉 25%, 艺术 14→10%)，总分预期会有 ±5 分系统偏差。Phase 1 先用 `enable_vnext_weights=False` 回退旧权重验证 88 个单元测试全部通过，再启用新权重运行基线验证。

### 10.4 现有已知 Bug 修复计划

| #  | Bug                                                 | 修复 Phase | 说明                          |
| -- | --------------------------------------------------- | ---------- | ----------------------------- |
| P1 | HistoryPage.js GBK/UTF-8 乱码                       | Phase 4    | Vue 重写为 UTF-8              |
| P1 | API 字段名不匹配 (standard vs standard_file)        | Phase 2    | openapi-typescript 强类型同步 |
| P1 | 6 个后端路由缺失 (songs CRUD, analysis status, SSE) | Phase 2    | 新增 FastAPI 端点             |
| P1 | 报告导出 PDF/图片不可用                             | Phase 2    | 修复 reports 路由             |
| P1 | ComparePage 无法两侧都上传文件                      | Phase 4    | CompareView.vue 双 ElUpload   |
| P1 | 播放器不能拖动 seek                                 | Phase 4    | AudioPlayer.vue click-to-seek |
| P1 | SingPage 默认强制曲库选歌                           | Phase 4    | HomeView 直接进入快速演唱     |
| P2 | 前端/后端 API 路径不一致 (api.js vs modules/api.js) | Phase 4    | 统一 useApi() composable      |
| P2 | 前端双状态管理 (AppState + Store)                   | Phase 4    | 统一 Pinia                    |

---

## 十一、风险矩阵

| 风险                                  | 概率 | 影响 | 缓解措施                                                |
| ------------------------------------- | ---- | ---- | ------------------------------------------------------- |
| 新维度 (Muscle/Timbre) 评分无区分度   | 高   | 中   | Phase 1 默认值框架 + 5 音频验证 +`is_heuristic` 标记  |
| FastAPI + Demucs 内存 OOM (800MB+)    | 低   | 高   | 单请求模型 +`asyncio.to_thread` + 内存不足跳过 Demucs |
| Vue 3 Canvas 内存泄露 (SingView)      | 中   | 中   | onBeforeUnmount 6 步清理法 + 单元测试验证               |
| 嵌入式 Python DLL 缺失 (ssl, sqlite3) | 中   | 高   | Phase 0 最小原型验证 + DLLs/ 目录完整性脚本             |
| 旧 Flask 与新 Alembic 迁移冲突        | 中   | 中   | legacy 表隔离 (`history_v6`) + 数据迁移脚本           |
| WebSocket 粘包导致音高数据错乱        | 低   | 高   | 4 字节长度前缀协议 + 粘包单元测试                       |
| 六维权重变化导致旧用户困惑            | 中   | 低   | 报告页显示权重说明 + 可切换旧五维视图                   |
| electron-builder NSIS 打包后杀毒误报  | 低   | 低   | 代码签名 + 提交 Windows Defender 白名单                 |

---

## 十二、总工作量

| Phase          | 内容                                                                                  | 工作日         |
| -------------- | ------------------------------------------------------------------------------------- | -------------- |
| 0              | Foundation (DDD 目录 + Alembic + structlog + openapi-typescript + 嵌入式 Python 原型) | 3.5            |
| 1              | Domain Model (六维评分 TDD 88 tests + EventBus + 启发式标记)                          | 5              |
| 2              | FastAPI 迁移 (21 端点 + Pydantic schemas + openapi.json + legacy 表隔离)              | 4              |
| 3              | WebSocket (4 字节长度前缀 + 增量评分 + AudioWorklet + 粘包测试)                       | 3              |
| 4              | Vue 3 前端 (5 页面, SingView 2.5天, Settings/SongLibrary 合并为抽屉)                  | 8              |
| 5              | Electron (嵌入式 Python + PyArmor + 进程守护 + electron-updater)                      | 3              |
| **总计** |                                                                                       | **26.5** |
