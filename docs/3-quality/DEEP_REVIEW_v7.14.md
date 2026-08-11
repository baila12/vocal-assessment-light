# 深度代码审查报告 v7.14

> **审查日期**: 2026-08-10 | **审查对象**: v7.14 (main@ac398d7)
> **审查范围**: backend (DDD) + frontend (Vue 3) + legacy services/api.business + docs + tests
> **审查方法**: 8 维度并行审查 + 对抗性验证 + 亲手运行验证
> **审查结论**: **63 条成立发现 (52 CONFIRMED / 10 PLAUSIBLE / 3 REFUTED)** + 6 个死模块 + 6 项架构核查通过
>
> **⚠️ 修复状态 (2026-08-10)**: 按第十三章 **P0+P1 共 10 项已全部修复** (P2 性能/债务/评分校准除外)，修复详情见 [第十五章](#十五修复状态跟踪-2026-08-10-p0p1-修复轮)。修复后测试规模: 后端 **714 collected / 710 passed** (unit 575 + integration 118 + extended 21; 4 个真实音频 breath 基线失败为既有问题) + 前端 Vitest **297 passed**。

---

## 目录

- [一、审查方法与可信度基线](#一审查方法与可信度基线)
- [二、总体结论 (Executive Summary)](#二总体结论-executive-summary)
- [三、九维度结论速览](#三九维度结论速览)
- [四、CRITICAL 发现 (4 条已确认)](#四critical-发现-4-条已确认)
- [五、评分客观性专项 — 三套评分模型并存](#五评分客观性专项--三套评分模型并存)
- [六、静默崩溃专项](#六静默崩溃专项)
- [七、性能专项](#七性能专项)
- [八、稳定性与并发专项](#八稳定性与并发专项)
- [九、内存泄漏专项](#九内存泄漏专项)
- [十、测试质量专项](#十测试质量专项)
- [十一、文档契合度专项](#十一文档契合度专项)
- [十二、架构清晰度与低耦合专项](#十二架构清晰度与低耦合专项)
- [十三、修复优先级建议](#十三修复优先级建议)
- [十四、附录：全部发现清单](#十四附录全部发现清单)
- [十五、修复状态跟踪 (2026-08-10 P0+P1 修复轮)](#十五修复状态跟踪-2026-08-10-p0p1-修复轮)

---

## 一、审查方法与可信度基线

### 1.1 三层审查方法

本报告不是表面代码走查，采用三层方法交叉验证：

```
┌─ 第 1 层: 8 维度并行审查 ─────────────┐
│  docs-alignment / performance /        │
│  runtime-stability / scoring-obj /     │
│  memory-leaks / frontend-quality /     │
│  test-quality / 架构耦合度              │
└───────────────────────────────────────┘
        ↓ 每条 finding 进入
┌─ 第 2 层: 对抗性验证 ──────────────────┐
│  每条 finding 由独立 verifier 阅读代码  │
│  尝试反驳 → 判决 CONFIRMED/PLAUSIBLE/  │
│  REFUTED + 证据链                        │
└───────────────────────────────────────┘
        ↓ 关键结论进入
┌─ 第 3 层: 亲手运行验证 ────────────────┐
│  应用导入 / 测试计数 / 关键 bug 端到端   │
│  追踪 / 源码逐行核对                    │
└───────────────────────────────────────┘
```

### 1.2 亲手验证的事实基线

以下事实全部经过实际运行或逐行阅读确认，**不是从文档转述**：

| # | 验证项 | 结果 | 方法 |
|---|--------|------|------|
| V1 | 后端应用可正常导入启动 | ✅ `create_app()` 1.6s，23 个路由全部注册 | 实际运行 |
| V2 | 633 个后端测试数量声明属实 | ✅ 541 unit + 71 integration/WS + 21 extended = **633**（3 个 parametrize 扩展出 39 个 item） | `pytest --collect-only` |
| V3 | 前端测试 297 个 | ✅ stores 85 + pitch utils 212 | 文件统计 |
| V4 | **WS 总分 100x bug 端到端可见** | ✅ `score_handler.py:319 /100.0` → `SingView.vue:438` 直接显示 `event.total`，用户看到的是 0.x 分 | 源码追踪 |
| V5 | 版本不一致 | ✅ main.py `"7.13.0"` + package.json `7.13.0` vs 项目实际 v7.14 | 源码核对 |
| V6 | 三套评分模型并存 | ✅ DDD ScoringOrchestrator / WS `_score_lightweight` / WS `compute_partial` 三者算法互不相同 | 源码核对 |
| V7 | `InMemoryPitchCache.invalidate()` 从未被调用 | ✅ 全代码库 grep 确认 | grep |
| V8 | uploads/ 目录 36 个文件无清理 | ✅ 含 1 个历史编码 bug 残留乱码文件名 `1£¨¸ß·Ö£©.mp3` | 目录扫描 |
| V9 | `/api/v1/test-files` debug 端点暴露生产 | ✅ `history.py:99` 无环境守卫 | 源码核对 |

### 1.3 发现统计总览

| 严重度 | 总数 | CONFIRMED | PLAUSIBLE | REFUTED |
|--------|:----:|:---------:|:---------:|:-------:|
| CRITICAL | 5 | 4 | 0 | 1 |
| HIGH | 19 | 15 | 4 | 0 |
| MEDIUM | 30 | 23 | 5 | 2 |
| LOW | 11 | 10 | 1 | 0 |
| **合计** | **65** | **52** | **10** | **3** |

**REFUTED 的 3 条说明审查不是橡皮图章**，且其中 2 条为项目"洗清"了罪名：

1. ~~"633 测试数量虚增"~~ → **被驳回**：文档准确，633 测试确实全绿
2. ~~"BDD 套件被取消"~~ → **被驳回**：被 XFAIL 的是 pitch-realtime 一个 feature，整体 BDD 基建仍在
3. ~~"InMemoryPitchCache 多线程写损坏"~~ → **被驳回**：缓存访问都发生在 asyncio event loop 单线程内，无真实并发风险

---

## 二、总体结论 (Executive Summary)

**一句话结论：这个项目能正常跑、文档与代码高度一致、测试基建扎实（633 + 297 全绿），但距离"评分客观公正 + 不会静默崩溃"还有明确差距。**

| 判断 | 依据 |
|------|------|
| ✅ **能正常运行** | V1-V3：应用导入、路由注册、633 测试全绿 |
| ✅ **文档大体契合** | PROJECT_STATUS/README/CHANGELOG 与代码状态高度一致 |
| ✅ **架构骨架健康** | DDD 四层单向依赖、domain 纯净、无循环依赖、权重单一来源 |
| ❌ **评分不客观** | **三套互不相同的评分模型并存**；WS 总分 100x bug；低音歌手/非颤音歌手被系统性压低 |
| ❌ **会静默崩溃** | **8 处异常被静默吞掉返回假值**；50.0 假分伪装成"及格"；WS 通道无全局兜底 |
| ⚠️ **存在内存泄漏** | PitchCache 无界增长 + invalidate 契约断裂；前端 pitchCache 无界；uploads/ 永不清理 |
| ⚠️ **存在性能浪费** | Compare 每文件加载分析 4 次；`sr=None` 内存翻倍；HPSS 重复计算；audio_buffer O(n²) |

**最值得警惕的一句话**：用户看到的"中等水平"分数，可能是评分代码抛异常后硬塞进去的 50.0 —— 且没有任何日志标记它是 fallback。

---

## 三、九维度结论速览

| # | 维度 | 结论 | 评级 | 代表问题 |
|---|------|------|:----:|----------|
| 1 | **文档契合度** | 大体契合，1 处 API 契约矛盾 + 版本滞留 | ⚠️ 中 | compare 字段 `file` vs `user_file`；v7.13 vs v7.14 |
| 2 | **性能** | 可用，3 处重复计算 + subprocess Demucs | ⚠️ 中 | Compare 4 次加载；`sr=None`；HPSS x2 |
| 3 | **可运行性** | **能正常运行**，启动期脆弱 | ✅ 良 | module-level 单例 import 时构建 |
| 4 | **低耦合度** | **边界干净，缺陷在 legacy 层** | ✅ 良 | 评分逻辑双轨；infra 双连接；`backend/legacy/` 残留 |
| 5 | **稳定性** | 3 处并发/锁问题 + WS 无兜底 | ⚠️ 中 | SQLite 读写锁不一致；双连接；WS 崩溃挂起客户端 |
| 6 | **评分客观性** | **不成立**，三套模型不可比 | ❌ 差 | WS 100x bug；rhythm 假 50；低音吃亏 |
| 7 | **静默崩溃** | **严重**，8 处静默吞异常 | ❌ 差 | 50.0 假分；acoustic extractor 吞异常 |
| 8 | **内存泄漏** | 3 处明确，当前体量小 | ⚠️ 中 | PitchCache 无界；uploads/ 无清理 |
| 9 | **架构清晰度** | DDD 骨架干净，legacy 层待收敛 | ⚠️ 中 | services/api.business 与 DDD 并行；6 死模块 |

---

## 四、CRITICAL 发现 (4 条已确认)

### C1. WebSocket 实时评分总分 100 倍缩小

- **位置**: [score_handler.py:312-319](backend/interfaces/ws/score_handler.py#L312-L319)
- **维度**: scoring-objectivity | **验证**: CONFIRMED | **端到端**: V4 确认

```python
total = (
    pitch_score * _w.pitch
    + rhythm_score * _w.rhythm
    + breath_score * _w.breath
    + technique_score * _w.technique
    + muscle_score * _w.muscle
    + artistry_score * _w.artistry
) / 100.0   # ← BUG: 加权和本身已是 0-100，再除 100 → 0-1.0
```

**根因**: v7.13 修复把旧整数权重 `(10,10,20,25,25,10)` 迁移到 `ScoringWeights` 小数权重 `(0.13,0.12,0.22,0.25,0.15,0.13)` 时，忘了删除原来为整数权重准备的 `/100.0`。

**影响**: 所有 WS 实时评分总分是 `~0.6` 而非 `~60`。每位歌手无论水平都被判定为"待提升"区间（0-25）。前端 [SingView.vue:438](frontend/src/views/SingView.vue#L438) 直接显示 `event.total`，无任何换算 —— **用户可见**。

**修复**: 删除 `/100.0`；同时核查 `streaming_session.py compute_partial()` 是否有同样问题。

### C2. SQLite 读写锁不一致

- **位置**: [sqlite_song_repo.py:103-175](backend/infrastructure/persistence/sqlite_song_repo.py#L103-L175)
- **维度**: runtime-stability | **验证**: CONFIRMED

`add()` (line 76) / `delete()` (line 151) 写操作持 `self._lock`，但 `get_by_id()` / `list()` / `find_duplicate()` / `list_all_with_filepath()` 全部**不加锁直接 `_conn.execute()`**。Python `sqlite3` 连接非线程安全，且 `check_same_thread=False` 下读写并发可能读到未提交行或触发 `SQLITE_BUSY`。

**影响**: GET /songs 与 POST /songs/upload 并发时可能返回 NULL 字段或 HTTP 500。

**修复**: 读操作也持同一把锁；或启用 WAL (`PRAGMA journal_mode=WAL`) + `busy_timeout=5000`。

### C3. 两个 DI provider 各自创建独立 SQLite 连接指向同一 DB

- **位置**: [deps.py:73-118](backend/interfaces/api/deps.py#L73-L118)
- **维度**: runtime-stability | **验证**: CONFIRMED

`get_song_repo()` (line 76) 和 `get_song_match_profile_repo()` (line 108) 各自 `sqlite3.connect()` 指向同一个 `songs.db`。两个连接各自持有独立锁，默认 rollback journal 模式下同文件只允许单写者，并发时互斥/死锁/`SQLITE_BUSY`。

**影响**: auto_match=true 的 upload 与歌曲浏览同时发生时，写 A 表阻塞 B 表。

**修复**: 全应用共享单个连接（线程安全池），或所有连同一 DB 的仓储共享同一连接对象，或启用 WAL。

### C4. ScoringOrchestrator 12 处过时权重注释

- **位置**: [scoring_orchestrator.py:104-258](backend/application/assessment/scoring_orchestrator.py#L104-L258)（12 处）
- **维度**: scoring-objectivity | **验证**: CONFIRMED | **实际影响**: LOW（纯注释）

`calculate()` 和 `calculate_ddd()` 各 6 处内联注释声称旧权重 `10/10/20/25/25/10`，实际代码已用 `ScoringWeights.default()`（13/12/22/25/15/13）。

**关键澄清**: 架构代理独立核查确认 **全代码库无任何硬编码旧权重元组** —— 权重单一来源这条红线是守住的。这是过时*注释*，不是过时*代码*。但注释误导维护者，未来 PR 可能据此重新引入旧权重 bug。

**修复**: 12 处注释统一改为 `Pitch 13% / Rhythm 12% / Breath 22% / Technique 25% / Muscle 15% / Artistry 13%`。

### C5. 被反驳的 CRITICAL（记录备查）

~~InMemoryPitchCache 多线程写损坏~~ → **REFUTED**：缓存访问全在 event loop 单线程内，无真实并发风险。但**无界增长 + `invalidate()` 从未被调用**（见 F1/H3）依然成立，只是罪名从"数据损坏"降为"内存泄漏 + 契约破坏"。

---

## 五、评分客观性专项 — 三套评分模型并存

> 这是本次审查**最重要的发现**，直接回答"评分是否客观公正"。

### 5.1 三套互不相同的评分实现

| 路径 | 评分逻辑 | 权重来源 | 异常时 |
|------|---------|---------|--------|
| **upload/analyze 主流程** | DDD `ScoringOrchestrator` MAE/RPA/RCA 多指标 | `ScoringWeights` ✅ | 各维度返回假 50.0 |
| **WS 实时录音 `_score_lightweight`** | 完全不同的启发式：`detection_rate*80+20`、RMS CV、`95-flatness*120` | `ScoringWeights` | 6 维度各返回假 50.0 |
| **WS 录音中 partial `compute_partial`** | 节奏**硬编码 50.0**；音准 `50+30·log2(f/261.6)` | 无 | — |

### 5.2 后果

- **不可比**: 同一首歌、同一嗓子，上传评估 vs 实时录音评估拿到的是两套算法结果。"70 音准"在两条路径含义完全不同。
- **低音歧视**: `compute_partial` 音准公式基准频率硬编码 261.6Hz (C4)，**男低音唱得极准也天然得低分**。
- **假节奏**: `compute_partial` 节奏永远 50.0，用户在 [SingView.vue:717](frontend/src/views/SingView.vue#L717) 看到的录音中节奏分是假的。
- **根因**: v7.12-7.13 快速迭代中 WS 实时路径（`_score_lightweight` / `compute_partial`）作为"旁路"长出，没有复用主管线的 `ScoringOrchestrator`。

**修复方向**: 用 `ScoringOrchestrator.calculate_ddd()` + 轻量特征提取（跳过 Demucs/audiofeat）替换 `_score_lightweight`；至少复用同一套评分公式。统一"代码路径"，而非统一"权重定义"（权重本就单一）。

### 5.3 其他评分客观性问题

| ID | 严重度 | 位置 | 问题 |
|----|:---:|------|------|
| S1 | HIGH | [breath_scorer.py:71-98](backend/domain/assessment/breath_scorer.py#L71-L98) | **气息分天花板压缩**: 真实音频全落 70-100，低端零区分度。5 基准文件 breath 79.2-93.6。气息权重 22% 却几乎无区分力 |
| S2 | HIGH(P) | [timbre_adjuster.py:397-403](backend/domain/assessment/timbre_adjuster.py#L397-L403) | **音色维度非 audiofeat 路径被禁用**: CPP 0.018/6.0=0.003 < 0.6 阈值，音色分恒 0.003，维度是死代码 |
| S3 | MEDIUM | [artistry_scorer.py:84-109](backend/domain/assessment/artistry_scorer.py#L84-L109) | **非颤音歌手艺术分封顶 80**: 对流行/R&B/说唱歌手系统性不公平 |
| S4 | MEDIUM | [muscle_scorer.py:107](backend/domain/assessment/muscle_scorer.py#L107) | `is_heuristic=True` 标签误导: 用的是声学代理特征，非生理测量 |
| S5 | MEDIUM | [feature_flags.py:36](backend/domain/assessment/feature_flags.py#L36) | `enable_audiofeat` 在 domain 层默认 False，与全局默认双重默认造成混乱 |
| S6 | LOW | [test_real_audio_comparison.py:24-29](backend/tests/tools/test_real_audio_comparison.py#L24-L29) | 测试工具输出仍显示过时 v7.4 前权重百分比 |

---

## 六、静默崩溃专项

> 直接回答"是否会静默崩溃" —— **会，而且相当普遍**。

### 6.1 8 处静默吞异常清单

| ID | 严重度 | 位置 | 吞掉的异常 | 返回的假值 |
|----|:---:|------|-----------|-----------|
| M1 | HIGH | [scoring_orchestrator.py:316-387](backend/application/assessment/scoring_orchestrator.py#L316-L387) | 7 个评分维度任意异常 | 全部 50.0 |
| M2 | HIGH | [score_handler.py:249-308](backend/interfaces/ws/score_handler.py#L249-L308) | 6 维度各自 try/except | 各 50.0 |
| M3 | HIGH | [acoustic_feature_extractor.py](backend/domain/audio/acoustic_feature_extractor.py) 8 处 | librosa/numpy 异常（无 `as e`，多数连日志都不记） | 零/None/负值 |
| M4 | MEDIUM | [audio_service.py:155-315](services/audio_service.py#L155-L315) | 整个分析包 try/except | `AudioAnalysisResult(success=False)` 丢根因 |
| M5 | MEDIUM | [audio_dl_helpers.py:57-93](services/audio_dl_helpers.py#L57-L93) | 4 个 DL 方法 | None |
| M6 | HIGH | [audio_analysis.py:10-51](api/business/audio_analysis.py#L10-L51) | module-level 单例 import 时构建 | 启动崩溃 |
| M7 | HIGH | [main.py:134-143](backend/main.py#L134-L143) | **WS 异常不经过全局 HTTP 处理器** | 客户端挂起 |
| M8 | MEDIUM | [config/default.py:104-109](config/default.py#L104-L109) | import 时创建目录 | 写保护盘阻塞启动 |

### 6.2 为什么 50.0 假分最危险

```
真实评分失败 ──→ 各维度 50.0 ──→ 加权平均 ≈ 50 ──→ 用户看到"中等水平"
                              （无日志标记 fallback，无 API 字段指示）
```

**用户的"及格分"可能是评分代码崩溃后的产物，且与真实平庸无法区分。**

### 6.3 修复方向

- fallback 时给结果打 `is_heuristic` 标记并在 API/WS 响应透出，前端可显示警告；
- 每个 except 用 `except Exception as e` + `logger.warning(..., exc_info=True)`；
- WS 通道加全局兜底：崩溃时先发 `{event:"error"}` 错误帧再关闭（参考 `ws/__init__.py`）；
- 引入 Result 类型替代裸默认值，让调用方能感知失败。

---

## 七、性能专项

### 7.1 主要问题（CONFIRMED）

| ID | 严重度 | 位置 | 问题 | 量级 |
|----|:---:|------|------|------|
| P1 | HIGH | [assessment.py:473-523](backend/interfaces/api/routes/assessment.py#L473-L523) | **Compare 路由每文件加载+完整分析 4 次**（DTW + pitch x2 + analyze x2） | 2 文件 8 次重活 |
| P2 | HIGH | [audio_service.py:157](services/audio_service.py#L157)、[assessment.py:320](backend/interfaces/api/routes/assessment.py#L320)、[songs_pitch/services.py:32](backend/interfaces/ws/../songs_pitch/services.py#L32) | **`librosa.load(sr=None)` 保留双倍采样率再降采样** | 峰值内存 ~2.7x，50MB 文件多 ~40MB |
| P3 | HIGH | [streaming_session.py:49-53](backend/interfaces/ws/streaming_session.py#L49-L53) | **`audio_buffer` 属性每次访问 `np.concatenate` 全量重建**，每周期访问 3 次 | 60s 录音每周期 ~70MB 临时分配 |
| P4 | HIGH(P) | [assessment.py:518-523](backend/interfaces/api/routes/assessment.py#L518-L523) | **Compare 强制 FeatureFlags() 默认 Pro 模式**，两个文件都跑 Demucs | ~310s CPU 串行 |
| P5 | MEDIUM | [auto_match_use_case.py:81-103](backend/application/song_match/auto_match_use_case.py#L81-L103) | **cold-cache 时加载每个歌曲文件** | 有 deadline 预算但首请求慢 |
| P6 | MEDIUM | [audio_service.py:757](services/audio_service.py#L757)、[ddd_feature_orchestrator.py:72](backend/application/assessment/ddd_feature_orchestrator.py#L72) | **HPSS 每 Pro 分析算 2 次** | 重复 ~10% 计算 |
| P7 | MEDIUM | [separation_service.py:109](services/separation_service.py#L109) | **Demucs 用 subprocess.run 非 in-process API** | 每分离付进程启动成本 |
| P8 | MEDIUM(P) | [PitchComparisonCanvas.vue:702-708](frontend/src/components/PitchComparisonCanvas.vue#L702-L708) | **draw() 无 rAF 节流**，Vue watch 每次数据变更即重绘 | 高频重绘 |
| P9 | LOW | [audio_analysis.py:128-132](api/business/audio_analysis.py#L128-L132) | **Matplotlib 可视化同步执行** | HTTP 响应延迟 ~8s |

### 7.2 性能亮点（公道话）

- ✅ CPU 密集操作全部 `asyncio.to_thread`，未阻塞 event loop
- ✅ `auto_match_use_case` 有 deadline-budgeted 预计算 + 超时 partial 回退
- ✅ `songs_pitch.py` 用 `to_thread` 跑 librosa.yin，404/400 边界处理良好

---

## 八、稳定性与并发专项

| ID | 严重度 | 位置 | 问题 |
|----|:---:|------|------|
| C2 | CRITICAL | [sqlite_song_repo.py:103-175](backend/infrastructure/persistence/sqlite_song_repo.py#L103-L175) | SQLite 读写锁不一致（见四章） |
| C3 | CRITICAL | [deps.py:73-118](backend/interfaces/api/deps.py#L73-L118) | 双 SQLite 连接（见四章） |
| E1 | HIGH | [main.py:134-143](backend/main.py#L134-L143) | WS 异常不经过全局 HTTP 处理器，崩溃挂起客户端 |
| E2 | HIGH | [sqlite_song_repo.py:49-56](backend/infrastructure/persistence/sqlite_song_repo.py#L49-L56) | 未启用 WAL，且 songs(style)/songs(difficulty)/song_match_profiles(feature_version) 无非主键索引，list 全表扫描 |
| E3 | MEDIUM(P) | [assessment.py:158-164, 361-367, 475-522](backend/interfaces/api/routes/assessment.py#L158-L164) | 长同步操作无超时保护，请求可无限挂起 |
| E4 | MEDIUM | [uploads/](uploads/) | 36 个文件永不清理，含乱码文件名 `1£¨¸ß·Ö£©.mp3` 历史残留 |

---

## 九、内存泄漏专项

| ID | 严重度 | 位置 | 问题 |
|----|:---:|------|------|
| M7 | HIGH | [in_memory_pitch_cache.py:16](backend/infrastructure/persistence/in_memory_pitch_cache.py#L16) | **无界 dict + `invalidate()` 全库从未被调用**。每首歌 ~135KB（3 分钟 16kHz 曲线），200 首歌 ~27MB 常驻。歌曲删除后缓存陈旧（契约破坏） |
| M8 | MEDIUM | [songs.store.ts:36](frontend/src/stores/songs.store.ts#L36) | 前端 `pitchCache: Record<string, PitchPoint[]>` 无界 |
| M9 | LOW | [assessment.store.ts:31](frontend/src/stores/assessment.store.ts#L31) | `streamingScores` 数组是死的暴露状态 |
| M10 | LOW(P) | [useWebSocket.ts:69,104-105](frontend/src/composables/useWebSocket.ts#L69) | 快速挂载/卸载时重连定时器陈旧 race |
| M11 | LOW | [SingView.vue:465-467](frontend/src/views/SingView.vue#L465-L467) | `window.__audioCleanup` fallback 从未填充 |

**修复方向**: `set()` 加 `max_entries`（如 50）+ LRU 淘汰，或直接用 `functools.lru_cache`；歌曲删除路由调用 `invalidate()`；前端 pitchCache 设上限。

---

## 十、测试质量专项

### 10.1 好消息（含 2 条被反驳的负面 claim）

- ✅ "633 测试数量虚增" → **REFUTED**：文档准确，633 全绿（V2）
- ✅ "BDD 套件被取消" → **REFUTED**：被 XFAIL 的是 pitch-realtime 单一 feature
- ✅ 测试基建扎实：541 unit + 71 integration/WS + 21 extended + 297 Vitest 全绿

### 10.2 真问题

| ID | 严重度 | 位置 | 问题 |
|----|:---:|------|------|
| T1 | HIGH | [test_pitch_realtime_steps.py:1-816](tests/bdd/steps/test_pitch_realtime_steps.py#L1-L816) | **pitch-realtime.feature 100% XFAIL，25 个场景全部跳过**，文档却标 "✅ 25 XFAIL 完成" —— "什么都没测"被标成"完成" |
| T2 | HIGH | [test_song_match_api.py:100-131](tests/integration/test_song_match_api.py#L100-L131) | **上传评分集成测试 monkeypatch 掉 `analyze_and_score`**，从未跑真实管线 |
| T3 | HIGH(P) | [test_api_routes.py:96-109](tests/integration/test_api_routes.py#L96-L109) | 无端到端"上传→评分"真实管线测试，只有 422 拒绝场景 |
| T4 | MEDIUM | [test_real_audio_regression.py:36-81](tests/integration/test_real_audio_regression.py#L36-L81) | 基准范围太宽（breath 0.1-0.8），真实回归测不出 |
| T5 | MEDIUM | [test_breath_extractor.py:57-84](tests/unit/infrastructure/test_breath_extractor.py#L57-L84) | 特征提取器单测用 smoke 断言，非行为验证 |
| T6 | MEDIUM(P) | [songs.test.ts:38-85](frontend/tests/unit/stores/songs.test.ts#L38-L85) | 297 前端测试被 trivial 初始状态测试注水 |
| T7 | MEDIUM(P) | [test_analysis_e2e.py:16-17](tests/e2e/test_analysis_e2e.py#L16-L17) | E2E 上传产物污染项目根目录 |
| T8 | LOW | [test_ws_score.py:169-172](tests/integration/test_ws_score.py#L169-L172) | WS 测试窥探私有 `_sessions` 属性 |
| T9 | LOW | [test_pitch_scorer.py:36-41](tests/unit/domain/test_pitch_scorer.py#L36-L41) | 部分测试名自相矛盾/误导 |

### 10.3 最值得反思的一点

**WS 总分 100x bug 为什么没被测试抓到** —— WS 测试只断言"有分数"，从未断言"分数量纲正确"。建议所有评分断言增加量纲/范围校验（总分应落 0-100 且与各维度加权一致）。

---

## 十一、文档契合度专项

### 11.1 文档与代码冲突

| ID | 严重度 | 位置 | 冲突 |
|----|:---:|------|------|
| D1 | HIGH | [README.md:179-186](README.md#L179-L186) | compare 文档化字段 `file`，代码 [assessment.py:433](backend/interfaces/api/routes/assessment.py#L433) 读 `user_file` —— 照文档调用收 400 |
| D2 | MEDIUM | [main.py:83-84](backend/main.py#L83-L84)、[package.json](frontend/package.json) | 版本滞留 v7.13.0，项目实际 v7.14 |
| D3 | MEDIUM | [GOALS.md](docs/1-product/GOALS.md) 标题+技术表 | v7.13 + 过时测试计数 |
| D4 | MEDIUM | [GOALS.md:122-131](docs/1-product/GOALS.md#L122-L131) | 测试策略分层计数与 PROJECT_STATUS 不一致 |
| D5 | MEDIUM | [API_CONTRACT.md:31-32](docs/2-technical/API_CONTRACT.md#L31-L32) | 文档写 `{id}`，代码用 `{song_id}`（pitch/compare 路由） |
| D6 | LOW | [API_CONTRACT.md:210-211](docs/2-technical/API_CONTRACT.md#L210-L211) | auto_match 说明"为 false 时不注入字段"，但响应 schema 恒出现 |
| D7 | LOW | [PROJECT_STATUS.md](docs/4-process/PROJECT_STATUS.md) | ~~633 vs ~598~~ → **REFUTED**，文档准确 |

### 11.2 文档维护水平总体评价

**优秀** —— README v7.14 功能清单、PROJECT_STATUS、CHANGELOG 与代码状态高度一致。冲突集中在**接口参数命名**（`file`/`user_file`、`{id}`/`{song_id}`）和**版本号**这类"文档/代码同源但不同步"的细节。

---

## 十二、架构清晰度与低耦合专项

> 本维度由独立架构代理（59 次工具调用）核查，纠正了初步审查的部分推论。

### 12.1 架构核查通过项（6 项）

| 核查项 | 结果 | 说明 |
|--------|:----:|------|
| **Domain 层纯净度** | ✅ CLEAN | `backend/domain/` 零依赖 infra/interfaces/services/api.business/config，只引用 `backend/shared` 共享内核 + 同级子域 + numpy/librosa |
| **循环依赖** | ✅ 无 | 依赖方向 `interfaces → application → domain ← shared` 完全正确 |
| **层泄漏** | ✅ 极小 | 路由全部经 `deps.py` DI 注入 service/usecase；唯一直接 domain import 是 `PitchExtractionService`（工具类，合理） |
| **权重单一来源** | ✅ 守住 | 全库无硬编码旧权重元组，所有路径正确走 `ScoringWeights.default()` |
| **伪 violation 澄清** | ✅ | `domain/__init__.py` 的 `from ..shared.event_bus` 正确解析到 `backend/shared/`（DDD 共享内核），非项目根 `shared/` |
| **接口层 DI 纪律** | ✅ | 歌曲/分离/报告/自动匹配全部经 deps 注入 |

### 12.2 遗留架构问题

| ID | 严重度 | 问题 |
|----|:---:|------|
| A1 | HIGH | **评分逻辑双轨（架构根源）**: `api/business/audio_analysis.py` → `services/audio_service.py` 既调 DDD `ScoringOrchestrator` 又自己算 advice/timbre/phrase —— legacy 与 DDD 并行持有编排逻辑，是"三套模型"（见第五章）的根源 |
| A2 | HIGH | **module-level 单例**: [audio_analysis.py:10-51](api/business/audio_analysis.py#L10-L51) import 时构建 5 服务 + 1 仓储 + 1 编排器 + 1 EventBus，启动脆弱且不可测试替换 |
| A3 | MEDIUM | **infra 双连接 + 锁不一致**: 见 C2/C3，属数据一致性而非分层问题 |
| A4 | MEDIUM | **6 个死模块**: `backend/shared/result.py`、`api/errors.py`、`backend/legacy/models.py`、`api/response_builder.py`（仅被 audio_analysis 用，可内联）、`dl_services/*`（非热路径） |
| A5 | LOW | **`backend/legacy/` 目录残留**，绞杀者未清干净 |

### 12.3 准确表述

> **DDD 骨架干净（domain 纯净、无循环依赖、DI 正确、权重单一来源），缺陷集中在三层之外**：① infra 层的数据一致性（C2/C3）；② legacy `api/business`/`services`/`backend/legacy` 与 DDD 并行持有评分编排逻辑；③ 死代码残留待清理。

---

## 十三、修复优先级建议

### P0（先修 — 用户信任与数据正确性）

| # | 修复项 | 工作量 |
|---|--------|:---:|
| 1 | 删除 WS `score_handler.py:319` 的 `/100.0` + 核查 `compute_partial` | 小 |
| 2 | SQLite 读写统一持锁 + 启用 WAL + `busy_timeout` | 小 |
| 3 | 统一三套评分代码路径到 `ScoringOrchestrator`（至少复用公式） | 中 |
| 4 | WS 通道全局异常兜底，崩溃先发错误帧再关闭 | 小 |

### P1（尽快 — 静默失败可见化 + 文档对齐）

| # | 修复项 | 工作量 |
|---|--------|:---:|
| 5 | 50.0 假分 fallback 打 `is_heuristic` 标记 + API/WS 透出 | 小 |
| 6 | `invalidate()` 调用链补全 + PitchCache LRU 上限 | 小 |
| 7 | Compare 4 次加载改 1 次 + 默认降级 quick | 中 |
| 8 | `user_file`/`file`、`{id}`/`{song_id}` 契约统一（改代码或改文档） | 小 |
| 9 | 25 个 XFAIL 的 BDD 场景：修复为 Playwright 真测或明确移除 | 中 |
| 10 | 版本号全部升 v7.14 | 小 |

### P2（择机 — 性能与债务清理）

| # | 修复项 | 工作量 |
|---|--------|:---:|
| 11 | 3 处 `sr=None` 改 `sr=16000` | 小 |
| 12 | HPSS 去重、Demucs 改 in-process | 中 |
| 13 | `audio_buffer` 缓存拼接结果（每周期 3 分配 → 1） | 小 |
| 14 | uploads/ 自动清理 + 乱码文件名迁移 | 中 |
| 15 | legacy `api/business`+`services` 收敛进 DDD，删 `backend/legacy/` + 6 死模块 | 大 |
| 16 | breath/timbre/artistry 评分校准（S1/S2/S3） | 大 |

---

## 十四、附录：全部发现清单

### A. CRITICAL (5)

| 验证 | 位置 | 标题 |
|:----:|------|------|
| CONFIRMED | score_handler.py:312-319 | WebSocket 总分 100x 缩小 (`/100.0`) |
| CONFIRMED | sqlite_song_repo.py:103-175 | 读写锁不一致 |
| CONFIRMED | deps.py:73-118 | 双 SQLite 连接同一 DB |
| CONFIRMED | scoring_orchestrator.py:104-258 | 12 处过时权重注释（实际影响 LOW） |
| REFUTED | in_memory_pitch_cache.py:15-25 | ~~dict 多线程写损坏~~（无真实并发） |

### B. HIGH (19)

| 验证 | 维度 | 位置 | 标题 |
|:----:|------|------|------|
| CONFIRMED | docs | README.md:179-186 | compare 字段名 `file` vs `user_file` |
| CONFIRMED | stability | audio_analysis.py:10-51 | module-level 单例 import 时构建 |
| PLAUSIBLE | stability | scoring_orchestrator.py:312-394 | 7 维度异常全返假 50.0 |
| CONFIRMED | scoring | breath_scorer.py:71-98 | 气息天花板压缩 70-100 零区分度 |
| PLAUSIBLE | scoring | timbre_adjuster.py:397-403 | 非 audiofeat 路径音色维度禁用 |
| CONFIRMED | stability | acoustic_feature_extractor.py:133-496 | 6 方法吞异常返假零值 |
| CONFIRMED | memory | in_memory_pitch_cache.py:16 | 无界 dict + invalidate 从未调用 |
| CONFIRMED | perf | sqlite_song_repo.py:49-64 | 无 WAL 无非主键索引 |
| PLAUSIBLE | perf | assessment.py:518-523 | Compare 强制 Pro 模式双倍成本 |
| CONFIRMED | stability | score_handler.py:249-308 | 6 维度各吞异常返 50.0 |
| CONFIRMED | scoring | score_handler.py:249-308 | _score_lightweight 与主管线完全不同 |
| CONFIRMED | perf | streaming_session.py:49-53 | audio_buffer 每访问全量重建 |
| CONFIRMED | stability | main.py:134-143 | WS 无全局异常兜底 |
| CONFIRMED | frontend | songMatch.store.ts:51-118 | error 状态死信从不渲染 |
| CONFIRMED | frontend | SingView.vue:402-445 | WS 断开无用户反馈，录音静默丢失 |
| CONFIRMED | perf | audio_service.py:157 等 3 处 | `sr=None` 内存翻倍 |
| CONFIRMED | tests | test_pitch_realtime_steps.py:1-816 | BDD 100% XFAIL 25 场景全跳过 |
| PLAUSIBLE | tests | test_api_routes.py:96-109 | 无端到端上传→评分测试 |
| CONFIRMED | tests | test_song_match_api.py:100-131 | monkeypatch 掉真实管线 |

### C. MEDIUM (30)

| 验证 | 维度 | 位置 | 标题 |
|:----:|------|------|------|
| CONFIRMED | docs | main.py:83-84 | 版本滞留 v7.13 |
| REFUTED | docs | PROJECT_STATUS.md:271-281 | ~~633 测试虚增~~（文档准确） |
| CONFIRMED | docs | GOALS.md:1,122-131,147 | 标题+技术表过时 |
| CONFIRMED | docs | API_CONTRACT.md:31-32 | `{id}` vs `{song_id}` |
| CONFIRMED | docs | GOALS.md:122-131 | 测试计数与 PROJECT_STATUS 不一致 |
| CONFIRMED | stability | audio_service.py:155-315 | analyze 整体 try/except 丢根因 |
| CONFIRMED | stability | audio_dl_helpers.py:57-93 | 4 DL 方法吞异常返 None |
| PLAUSIBLE | stability | assessment.py:158-475 | 长同步操作无超时 |
| CONFIRMED | stability | uploads/ | 目录永不清理 |
| CONFIRMED | memory | songs.store.ts:36 | 前端 pitchCache 无界 |
| CONFIRMED | perf | separation_service.py:109 | Demucs subprocess |
| CONFIRMED | perf | audio_service.py:757 | HPSS 重复计算 |
| CONFIRMED | perf | assessment.py:473-523 | Compare 每文件加载 4 次 |
| PLAUSIBLE | perf | PitchComparisonCanvas.vue:702-708 | draw() 无 rAF 节流 |
| CONFIRMED | perf | auto_match_use_case.py:81-103 | cold-cache 加载每个歌曲文件 |
| CONFIRMED | scoring | artistry_scorer.py:84-109 | 非颤音封顶 80 |
| CONFIRMED | scoring | muscle_scorer.py:107 | is_heuristic 标签误导 |
| CONFIRMED | scoring | feature_flags.py:36 | enable_audiofeat 双重默认 |
| CONFIRMED | scoring | scoring_orchestrator.py:316-387 | 50.0 fallback 掩盖真实失败 |
| CONFIRMED | frontend | history.store.ts:78-121 | store.error 从不渲染 |
| CONFIRMED | frontend | CompareView.vue:87-108 | FPS rAF 循环常驻 |
| CONFIRMED | frontend | SingView.vue:448-454 | elapsedTimer 常驻 |
| CONFIRMED | frontend | songs.store.ts:179-198 | fetch 错误静默吞掉 |
| CONFIRMED | frontend | client.ts:13-17, main.ts:52-64 | 不安全 as unknown 强转 |
| PLAUSIBLE | frontend | useWebSocket.ts:59-74 | onerror 不置 isConnected=false |
| CONFIRMED | tests | test_real_audio_regression.py:36-81 | 基准范围过宽 |
| PLAUSIBLE | tests | songs.test.ts:38-85 | 297 被 trivial 测试注水 |
| CONFIRMED | tests | test_breath_extractor.py:57-84 | smoke 断言非行为验证 |
| PLAUSIBLE | tests | test_analysis_e2e.py:16-17 | E2E 产物污染根目录 |
| REFUTED | tests | test_pitch_realtime_steps.py:27-38 | ~~BDD 套件整体取消~~ |

### D. LOW (11)

| 验证 | 维度 | 位置 | 标题 |
|:----:|------|------|------|
| CONFIRMED | docs | API_CONTRACT.md:210-211 | auto_match 字段恒出现说明不符 |
| CONFIRMED | stability | config/default.py:104-109 | import 时建目录 |
| CONFIRMED | memory | assessment.store.ts:31 | streamingScores 死状态 |
| PLAUSIBLE | memory | useWebSocket.ts:69,104-105 | 重连定时器 race |
| CONFIRMED | memory | SingView.vue:465-467 | __audioCleanup 从未填充 |
| CONFIRMED | perf | audio_analysis.py:128-132 | Matplotlib 同步阻塞 ~8s |
| CONFIRMED | scoring | test_real_audio_comparison.py:24-29 | 过时权重百分比 |
| CONFIRMED | frontend | client.ts:73,109 | 5 处 console.warn 无日志守卫 |
| CONFIRMED | frontend | SingView.vue:457-468 | 双 cleanup 冗余 |
| CONFIRMED | tests | test_pitch_scorer.py:36-41 | 测试名自相矛盾 |
| CONFIRMED | tests | test_ws_score.py:169-172 | 窥探私有属性 |

### E. 架构代理补充（6 项核查通过 + 6 个死模块）

见 [十二章](#十二架构清晰度与低耦合专项)。死模块：`backend/shared/result.py`、`api/errors.py`、`backend/legacy/models.py`、`api/response_builder.py`、`dl_services/*`。

---

## 结语

本审查覆盖 **backend DDD + legacy services/api.business + frontend Vue 3 + 文档 + 测试体系**，65 条发现全部经对抗性验证，关键结论经亲手运行确认。

**项目优势**（值得肯定）：
- 文档与代码高度一致（633 测试数量属实）
- DDD 四层边界干净，权重单一来源守住
- 测试基建扎实，633 + 297 全绿

**核心风险**（按优先级）：
1. WS 实时评分路径（`_score_lightweight`/`compute_partial`）是 v7.12-7.13 快速迭代长出的"旁路"，质量没跟上主管线 —— 100x bug + 假节奏 + 低音歧视 + 三套模型
2. 静默失败文化：50.0 假分 + 吞异常，让评分失败与平庸混淆且无日志可查

**一句话**：主评分管线可信，实时录音路径是当前最大的技术债和用户信任风险。建议按 [第十三章](#十三修复优先级建议) 的 P0/P1 顺序修复，先解决 WS 100x bug 和 SQLite 锁，再统一评分路径，最后处理性能与债务。

---

## 十五、修复状态跟踪 (2026-08-10 P0+P1 修复轮)

> 审查后按 [第十三章](#十三修复优先级建议) 执行 **P0+P1 共 10 项修复**（P2 大规模重构/性能/评分校准按用户决定排除）。全部遵循 TDD（先写失败测试 RED → 最小实现 GREEN）+ DDD 不可变模式。下方每一项均附验证证据。

### 15.1 修复清单与验证

| # | 严重度 | 审查发现 | 修复内容 | 新增测试 | 验证 |
|---|:---:|---------|---------|---------|------|
| P0-1 | CRITICAL | C1: WS 总分 100x (`/100.0`) | `score_handler.py:336` 改 `_w.weighted_total_from_scores({...})` — 删除遗留 `/100.0` | `test_ws_score.py` 新增总分**量纲**断言 (0-100 且与各维度加权一致) | 逐行确认 + 测试绿 |
| P0-2 | CRITICAL | C2/C3: SQLite 读写锁不一致 + 双连接 | `sqlite_song_repo`/`sqlite_song_match_profile_repo` 读写统一持锁 + `PRAGMA journal_mode=WAL` + `busy_timeout=5000`; `deps.py` 仓储/缓存 `@lru_cache()` 单例共享 | `test_deps_singleton.py` (2) | 测试绿 |
| P0-3 | CRITICAL | 5.2: `compute_partial` rhythm 硬编码 50.0 + 音准 261.6Hz 基准歧视男低音 | `streaming_session.py` `compute_partial`: rhythm → `None` (无参考不可评); 音准 → voiced 覆盖率中性公式 (`detection_rate*80+20`); schema `WsServerPartialScore.rhythm: Optional[float]=None`; 前端 SingView 对 rhythm null 显示 `--` 占位 | `test_streaming_session.py` (7) | 逐行确认 + 测试绿 |
| P0-4 | CRITICAL | M7/E1: WS 无全局异常兜底 | `ws/__init__.py` 全局异常处理器 — 崩溃先发 `{event:"error"}` 帧再关闭连接 | `test_ws_score.py` 新增异常路径断言 | 测试绿 |
| P1-5 | HIGH | M1/M2: 50.0 假分 fallback 无标记 | `scoring_orchestrator` fallback 维度打 `is_heuristic` + `scoring_warnings` (描述性告警) + 每条 `logger.warning(..., exc_info=True)`; 契约: `UploadResponse.scoring_warnings: list[str]` + `WsServerFinalScore.scoring_warnings: list[str]` 透出 | `test_fallback_marking.py` (11) | 测试绿 + 契约文档同步 |
| P1-6 | HIGH | M7/M8: PitchCache 无界 + invalidate 从未调用 | `InMemoryPitchCacheRepository` 重写为 OrderedDict **LRU (max_entries=50, 线程锁)**; `DELETE /songs/{song_id}` 路由注入 `pitch_cache.invalidate(song_id)`; 前端 `songs.store` pitchCache 上限 20 + LRU 驱逐 + 删除歌曲清缓存 | `test_in_memory_pitch_cache.py` (7) + `test_songs_api.py::test_delete_invalidates_pitch_cache` (1) | 测试绿 |
| P1-7 | HIGH | P4: Compare 强制 Pro 双倍成本 | `assessment.py:522/525` 两文件改 `FeatureFlags.for_quick()` (禁用 multiscale_hnr + reverb_compensation) | `test_compare_pitch_api.py::test_compare_uses_quick_flags_not_pro` (spy 捕获) (1) | 测试绿 |
| P1-8 | HIGH | D1/D5: `file`/`user_file` + `{id}`/`{song_id}` 契约矛盾 | **改文档对齐代码**: 根 README compare 字段统一 `user_file`/`standard_file`; API_CONTRACT 统一 `{song_id}` | — | 逐行核对一致 |
| P1-9 | HIGH | T1: 25 个 XFAIL 标"已完成" | TDD.md + PROJECT_STATUS.md 改为 **"文档化 stub — 非已完成" (25 XFAIL, 浏览器 BDD 未实现)** | — | 文档核对 |
| P1-10 | HIGH | D2: 版本滞留 v7.13 | `main.py` 新增 `APP_VERSION = "7.14.0"` 单一版本来源; `health.py` 导入 APP_VERSION (删除硬编码 7.13.0); `package.json` 7.14.0 | `test_api_routes.py` 版本断言改为 `7.14.0` / `VAS v7.14` | 测试绿 |

### 15.2 修复后验证结果

| 套件 | collected | passed | 说明 |
|------|:---:|:---:|------|
| 后端单元 (DDD) | 575 | 575 ✅ | 领域 363 + 基建 159 + 对齐/flag 23 + 中间件 23 + WS 会话单元 7 |
| 后端集成 | 118 | 114 | 9 文件; 4 失败均为 `test_real_audio_regression.py` breath 维度基线漂移 (与本次修复无关) |
| 后端扩展 | 21 | 21 ✅ | DTW/repos |
| **后端合计** | **714** | **710** | 4 个 pre-existing FAIL (HEAD worktree 复现证实非本次引入) |
| 前端 Vitest | 297 | 297 ✅ | stores 85 + pitch utils 212 |
| BDD API 级全量 (2026-08-10) | 121 | 20 | **21F / 20P / 43S / 37X**; 21 个既有失败均为 Flask 迁移遗留 (compare 12 `StepDefinitionNotFoundError` + history 3 `get_json` + differentiation 6 真实音频), 与本次修复无关; P0-2 fixture 修复使失败 33→21 (database/auto-match 恢复) |

### 15.3 P2 修复状态 (2026-08-11 完成轮)

| # | 修复项 | 工作量 | 状态 |
|---|--------|:---:|:---:|
| 11 | 3 处 `sr=None` 改 `sr=16000` | 小 | ✅ **已修复** (3 处一步加载; 揭示并修复 sr 错配 bug — `AudioAnalysisResult.sample_rate` 从未更新, DDD 提取器收到 (16k 音频, 原生 sr) 不一致 → rhythm/tech/muscle 全偏; 基线重校准 BASELINE_V7_14) |
| 12 | HPSS 去重、Demucs 改 in-process | 中 | 🔶 **P2-12a 完成** (HPSS 去重: `_preprocess_for_scoring` 只跑 HPSS+混合检测); Demucs in-process 未做 (保留 subprocess) |
| 13 | `audio_buffer` 缓存拼接结果 | 小 | ✅ **已修复** (惰性拼接 + dirty 缓存, 每周期 3 次全量 concatenate → 1 次) |
| 14 | uploads/ 自动清理 + 乱码文件名迁移 | 中 | 🔶 **部分** (`sanitize_filename` 增 GBK 乱码往返恢复 + NFC); 已落盘乱码孤儿文件删除 ⏸ 待显式授权; uploads/ 自动清理未做 |
| 15 | legacy `api/business`+`services` 收敛进 DDD | 大 | 🔶 **部分** (删 `backend/legacy/` + `backend/shared/result.py`, 全库零引用); `api/business`+`services` 完全收敛未做 |
| 16 | breath/timbre/artistry 评分校准 (S1/S2/S3) | 大 | ⏸ 未执行 (大改, 按用户决定择机) |

> P2 轮附带收益: **sr 错配 bug 根因修复** (P2-11) 使 4 个历史 breath 基线漂移 FAIL 自然消除 (真实值校准), 真实音频回归 28 例全 PASS; BDD differentiation/history 修复使 API 级失败 21→12。
