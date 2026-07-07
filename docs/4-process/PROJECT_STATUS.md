# 项目状态

> 更新: 2026-07-07 | 当前版本: **v6.2-dev** (评分算法重构 — 多指标音准 + 跨维度修正 + 频谱倾斜 + Praat 声质) | 分支: `feat/v6.2-scoring-improvements`

---

## v6.2: 评分算法重构 (进行中, 2026-07-07)

### 已完成 (commit: edfc50c)

| # | 模块 | 变更 | 文献 |
|---|------|------|------|
| 1 | `pitch_scorer.py` | 多指标体系: MAE指数衰减 + RPA(25%) + RCA(10%) + gross_error(15%) + smoothness(10%) + octave(5%) | Wager 2022, Cao et al. 2008 |
| 2 | `breath.py` | 质量门控: breath_design 权重 20%→5% (基础控制不足时) | Titze 1994 |
| 3 | `score_modifiers.py` | 跨维度修正: HNR稳定→气息, Voicing→音准, 频谱倾斜→气声, 气息-音准耦合 | de Krom 1993, Sundberg 1987, Titze 1994 |
| 4 | `feature_flags.py` | 6 个已验证算法默认启用 + for_quick()/for_professional()/safe_baseline() | — |
| 5 | `acoustic.py` | 频谱倾斜 (LTAS slope via Welch PSD) | Sundberg 1987 |
| 6 | `voice_quality_praat.py` (新) | Praat 声质: jitter/shimmer/formants/singer's formant/Praat HNR | Baken & Orlikoff 2000 |
| 7 | `technique.py` | 技巧检测扩展 3→5: +staccato +legato | Sundberg 1987 |
| 8 | `audio_features_service.py` | HPSS 缓存 + spectral_tilt + Praat VQ 接入 | — |

### 评分效果

| 指标 | v6.1 | v6.2 | 改进 |
|------|------|------|------|
| 音准区分度 | 4.2 | **39.8** | +35.6 (9.5x) |
| 高分音准 | ~80.1 | 82.1 | +2.0 |
| 低分音准 | ~75.9 | 42.4 | -33.5 |
| jitter/shimmer 修正 | 无 | 最大 ±8% 技术分 | 新增 |
| 频谱倾斜修正 | 无 | 气声 vs 漏气区分 | 新增 |

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

| 模式 | 触发方式 | CPU 耗时 | GPU 耗时 | 适用场景 |
|------|---------|----------|----------|---------|
| **Quick** | `/api/upload?mode=quick` | ~15-20s | ~15-20s | 快速练习反馈 |
| **Professional** | `/api/upload?mode=professional` | ~130-170s | ~30-50s | 详细问题诊断 |
| **Compare (DTW)** | `/api/compare` 或自动搜索 | ~45s | ~45s | 参考对比评分 |

> ✅ PyTorch 2.6.0+cu124 (CUDA 12.4), GPU 加速已就绪。Demucs Pro 模式 GPU 耗时 ~30-50s。`/health` 端点可查看 GPU 状态。

---

## 真实音频测试结果

### Quick 模式基线 (v5.17)

| 音频 | 总分 | 音准 | 节奏 | 气息 | 技巧 | 艺术 |
|------|------|------|------|------|------|------|
| 恋人（高分） | **74.8** | 79.6 | 77.1 | 56.4 | 84.0 | 75.9 |
| 手写的从前（高分） | **73.4** | 80.8 | 66.6 | 66.4 | 77.6 | 73.2 |
| 1（高分） | **72.7** | 80.7 | 66.8 | 63.2 | 77.5 | 72.6 |
| 音频-3分26秒(高分) | **72.6** | 79.3 | 71.9 | 52.6 | 84.0 | 73.8 |
| 陈奕迅难听之声（低分） | **48.8** | 75.9 | **2.5** | 51.2 | 57.5 | 46.2 |
| 白噪声 | **0.0** | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

**高分均值 73.4 vs 低分 48.8 — 区分度 24.6 分。**

### Quick vs Pro 一致性 (v5.17)

| 音频 | Quick | Pro | 差距 | Pro Demucs |
|------|-------|-----|------|-----------|
| 恋人（高分） | 74.8 | 73.7 | -1.1 | ✅ |
| 1（高分） | 72.7 | 75.0 | +2.3 | ✅ |
| 手写的从前（高分） | 73.4 | 79.1 | +5.7 | 跳过(纯人声) |
| 音频-3分26秒(高分) | 72.6 | 76.4 | +3.8 | ✅ |
| 陈奕迅（低分） | 48.8 | 48.8 | 0.0 | 跳过(纯人声) |

**Quick/Pro 总分离散 < 6 分 — 一致性良好。**

---

## 已完成功能 (按版本)

| 版本 | 日期 | 核心变更 |
|------|------|---------|
| v5.19 | 07-04 | 评分区分度修复: 气息基线40→10, 音准MAE扩展, HNR/CPP天花板, 音量独立 |
| v5.18 | 07-04 | 开源算法移植 (HNR/CPP/Voicing) + Feature Flag + 代码审查20项修复 |
| v5.17 | 06-04 | 混合音频检测修复 (阈值0.35→0.25) + GPU加速 + 合成音频归零验证 |
| v5.16 | 06-03 | Pro Breath 修复: is_clean_vocal标记传递链 → 9.8→56.3 (+474%) |
| v5.15 | 06-03 | Pro Rhythm CV重校准 + SingMOS移除 + DTW自动搜索 + 自参照一致性 |
| v5.14 | 06-03 | 音准多指标体系 + 艺术评分重构 (区分度 0.3→28.4) |
| v5.13 | 06-03 | Sigmoid+硬上限移除 → 区分度恢复 + Demucs CV映射修复 |
| v5.12 | 06-03 | 安全加固 + DL清理(-654行) + 评分统一 + 算法校准 + 魔法数字集中化 |
| v5.11 | 06-02 | 评分区分度(0-100全范围) + Demucs管线修复 + 节奏CV分段 |
| v5.10 | 05-26 | DTW参考评分融合 + 自参照DTW + 响度归一化 |

详细变更见 [CHANGELOG.md](CHANGELOG.md)。

---

## 已知问题

### P0 (严重) — 全部已修复 ✅

| 问题 | 版本 | 效果 |
|------|------|------|
| Pro 节奏崩塌 (18.6 vs Quick 77.1) | ✅ v5.15 | 18.6→66.0 (+255%) |
| SingMOS 严重跨域 (低分>高分) | ✅ v5.15 | 移除，自参照一致性替代 |
| DTW 参考评分未默认化 | ✅ v5.15 | 独立上传自动搜索 |
| Pro Breath 崩塌 (9.8 vs Quick 56.4) | ✅ v5.16 | 9.8→56.3 (+474%) |

### P1 (功能缺陷) — 4 项 (v6.0 已改进 2 项, 待 v6.1 校准)

| 问题 | 说明 | 状态 |
|------|------|------|
| **气息评分区分度偏窄** | v5.17: 53-66 vs 51 (15分差) → v5.19: 67-88 vs 80 (21分差) | ⚠️ 改善但低分仍偏高 |
| **音准评分区分度偏窄** | v5.17: 79-81 vs 76 (5分差) → v5.19: 69-76 (7分差) | ⚠️ 改善, 目标 ≥10 |
| ~~23 个经验参数未校准~~ | → v6.1 校准数据集 (优先: Breath/Technique/Artistry) | 📋 |
| **Pro 模式耗时过长** | CPU ~130-170s (Demucs 占 ~80%) | ✅ GPU 加速已就绪 |

### P2 (优化) — 4 项 (v6.0: 3 项已修复)

| 问题 | 说明 | 状态 |
|------|------|------|
| f0 节奏路径待恢复 | v5.13 回退到 f0=None，需校准验证后启用 | 📋 v6.1 |
| 技巧检测仅 3 种 | 颤音/滑音/假声 vs 论文 7-15 种 | 📋 |
| ~~无混响补偿~~ | ✅ v6.0: `ReverbCompensator` 已接入 `AudioFeaturesService` | ✅ 已修复 |
| ~~音量维度未独立~~ | ~~与 Breath 合并~~ → v5.19 基于 dynamic_range 独立计算 | ✅ 已修复 |
| ~~混合音频检测误判~~ | ✅ v6.0: 五特征融合, 纯人声 0 误判 | ✅ 已修复 |
| 核心/服务层代码重叠 | legacy 模块待清理 | 📋 |

### ✅ P0 (前端) — SPA 导航跳转 Bug (已修复)

| 问题 | 说明 | 状态 |
|------|------|------|
| **SPA 导航不跳转** | 点击导航按钮后 URL hash 改变, 但页面内容不更新 | ✅ v5.20 已修复 |

**根因**: 三重 Bug 叠加导致路由器 `#transition()` 死锁:

1. `AnimationController._execute()` — `onComplete` 被从 GSAP vars 中丢弃
2. `AnimationController._track()` — 覆盖而非链式调用已有 `onComplete`, 且 getter 对刚创建的 tween 返回 `undefined` 时未回退到 `vars.onComplete`
3. `HashRouter.#handleRoute()` — `killAll()` 在 `#navPending` 检查之前执行, 单次点击触发的 popstate 事件杀掉了 hashchange 事件的 leave 动画

**修复文件**: `web/static/js/animation/Controller.js` (3 处), `web/static/js/components/BaseComponent.js` (1 处), `web/static/router.js` (1 处)

### 🆕 P1 (前端) — 其他已修复的 SPA 问题 (v5.20)

| 问题 | 状态 |
|------|------|
| API 路径 `/api/audio/analyze` 不存在 (404) → `/api/upload` | ✅ 已修复 |
| API 路径 `/api/history/batch-delete` 路径+方法错误 | ✅ 已修复 |
| HistoryPage.js 全部中文乱码 (mojibake) + `ac is not defined` | ✅ 已修复 |
| ComparePage Modal 弹窗无法关闭 (双重 overlay) | ✅ 已修复 |
| 全部页面 `const ac = this.ac` 编码/作用域问题 | ✅ 已修复 |
| 路由 `#transition()` 无错误恢复 | ✅ 已修复 |

---

## v6.0: 混响补偿管线接入 + 混合音频检测文献驱动重构 (2026-07-06, 已完成)

### 混响补偿接入评分管线 (P2→✅)

| # | 文件 | 变更 |
|---|------|------|
| 1 | `services/feature_flags.py` | 新增 `enable_reverb_compensation` flag |
| 2 | `services/audio_features_service.py` | 集成 `ReverbCompensator`, HNR/CPP 计算前可选补偿 |
| 3 | `services/features/acoustic.py` | `analyze()` 适配新返回格式 |

**管线流程**: `audio_data` → `ReverbCompensator.process()` (HPSS+谱减法) → 补偿后音频 → HNR/CPP 计算
**控制**: `FeatureFlags.enable_reverb_compensation = True` 启用, 默认关闭

### 混合音频检测文献驱动重构 (P2→✅)

基于以下文献重新设计检测算法:

| 论文 | 关键贡献 | 应用 |
|------|---------|------|
| Fitzgerald (2010). DAFx | HPSS 中值滤波分离 | 特征1: HPSS 谐波比 |
| Driedger et al. (2014). ISMIR | HPSS 三元分解 H+P+R, 歌声在残差区 | HPSS 门控阈值 0.88/0.72 |
| Lehner et al. (2018). TASLP | 子带频谱平坦度 (1.5-3kHz) 最可靠 | 特征2: 子带平坦度 (替代低频能量) |

**v5.17 → v6.0 改进**:

| 指标 | v5.17 | v6.0 |
|------|-------|------|
| 特征数量 | 2 (低频能量+全频平坦度) | 5 (HPSS+子带平坦度+高频+谐波度+全频平坦度) |
| 纯人声误判率 | 75% (3/4) | **0%** (0/4) |
| 文献依据 | 经验阈值 | Fitzgerald+Driedger+Lehner |

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

| # | 文件 | 变更 |
|---|------|------|
| 1 | `services/features/technique.py` | technique_score 基线 50→0, 仅检测到的技巧加分 |
| 2 | `services/features/breath.py` | 四子维度步进加分→连续线性映射, 基线 10→0 |
| 3 | `services/scoring/technique_scorer.py` | HNR/CPP 高技巧阈值 70→35 |
| 4 | `services/scoring_config.py` | 所有基线参数更新 |

### Artistry 独立评分

`services/scoring/artistry_scorer.py` 完全重构:
- **旧**: `pitch*0.20 + rhythm*0.25 + breath*0.20 + technique*0.35`
- **新**: 4 个独立声学特征子维度 (颤音品质/动态控制/乐句处理/音高变化)
- 不再依赖其他维度分数

### Bug 修复

| 严重度 | 问题 | 文件 |
|--------|------|------|
| CRITICAL | `detect_mixed_audio()` 返回值 4→3, 2 个调用者静默失败 | `audio_service.py`, `dtw_aligner.py` |
| MEDIUM | E2E 测试 3 处 collection error | `test_e2e.py` 等 |

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

| # | 文件 | 修复 |
|---|------|------|
| 1 | `web/static/js/animation/Controller.js` | `_execute()`: onComplete 传入 GSAP toVars; `_track()`: 链式回调 (cleanup + 原有), 双来源检查; `leave()`: 安全超时 |
| 2 | `web/static/js/components/BaseComponent.js` | `beforeUnmount()`: 硬编码 'page-leave' 预设 |
| 3 | `web/static/router.js` | `#navPending` 检查移到 `killAll()` 之前 |

### 🏗️ 架构升级 — v7.0 Vue 迁移衔接 (3 文件新增, 3 文件重构)

| # | 文件 | 说明 | v7.0 目标 |
|---|------|------|----------|
| 1 | `web/static/js/AppContext.js` 🆕 | 依赖注入容器 (store/router/api/ac/events) | Vue `provide/inject` |
| 2 | `web/static/js/EventBus.js` 🆕 | 事件总线 (on/once/off/emit) | `mitt()` |
| 3 | `web/static/js/components/BaseComponent.js` v3.0 | context 注入, Vue 生命周期对齐 | `<script setup>` |
| 4 | `web/static/app.js` v3.0 | createApp 模式入口, context 组装 | `createApp()` |
| 5 | `web/static/router.js` v3.0 | `useContext(context)` 注入 | Vue Router `createRouter` |

### 前端 SPA Bug 修复 (6 类, 12 文件) — 基础修复, 见 CHANGELOG |

### 后端改进

| # | 模块 | 文件 | 依据 |
|---|------|------|------|
| 1 | 混响补偿 | `services/features/reverb.py` 🆕 | Fitzgerald 2010, Boll 1979, Berouti 1979 |
| 2 | 混合音频检测重构 | `services/features/acoustic.py` | HPSS + 多特征融合, 采样率自适应 |
| 3 | CPP 测试修复 | `tests/tdd/test_future_features.py` | 安装 parselmouth 0.4.7 |

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

| # | 任务 | 来源 | 文件 | Feature Flag |
|---|------|------|------|-------------|
| 1 | 多频带 HNR (de Krom 1993 倒谱分离法, 4频带) | VoiceLab | `services/features/hnr.py` | `enable_multiscale_hnr` |
| 2 | Praat CPP (parselmouth PowerCepstrum) | VoiceLab | `services/features/cpp.py` | `enable_praat_cpp` |
| 3 | Voicing detection 评估 (自一致性检查) | pitch-benchmark | `services/features/voicing.py` | `enable_voicing_detection` |
| 4 | TorchCREPE 备选接入 (PYIN 降级时) | pitch-benchmark | `services/audio_features_service.py` + `audio_service.py` | `enable_torchcrepe_fallback` |
| 5 | Feature Flag 机制 | — | `services/feature_flags.py` | — |
| 6 | DL 辅助方法提取 | — | `services/audio_dl_helpers.py` (🆕) | — |
| 7 | 端到端集成测试 | — | `tests/integration/test_v5_18_integration.py` (7 tests) | — |

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

| 维度 | 旧实现 | 新实现 (flag 开启时) |
|------|--------|---------------------|
| HNR | HPSS 谐波/冲击分离 | de Krom 1993 倒谱域分离, 4 频带 (500/1500/2500/3500Hz), 边界检测已修复 |
| CPP | 手动 FFT 倒谱 (peak - mean) | VoiceLab `parselmouth.Spectrum` → `To PowerCepstrum` → `Get peak prominence`, 归一化 `/6.0` |
| f0 提取 | librosa.yin | PYIN + TorchCREPE 降级 (detection_rate < 0.5 时), 已集成到生产管线 |
| voicing | 无 | 自一致性评估 (范围/八度跳跃/切换一致性/能量一致性), 矢量优化 |

### 真音频效果 (tests/test_data/audio/vocal)

> **测试准则**: 优先使用 `tests/test_data/audio/vocal/` 中的 5 首真实人声音频获取反馈。
> 该目录包含 4 首高分 + 1 首低分演唱，文件名即标签。

| 音频 (258s) | Default | v5.18 (全开) | 变化 | 说明 |
|-------------|---------|-------------|------|------|
| 1（高分） Tech | 77.5 | 92.5 | **+15.0** | CPP 从失效(51分)恢复到正常(85分) |
| 1（高分） Total | 73.6 | 77.0 | +3.4 | Tech 权重仅 20%, 限制了总影响力 |

**关键发现**: 旧 CPP 算法对所有音频返回 ~0.018 (几乎无区分度)，VoiceLab CPP 返回 5-40 dB 范围，恢复了 CPP 维度的评分能力。

### 已知局限 (v5.19 → v6.1)

| 问题 | 说明 | 计划 |
|------|------|------|
| **跨维度集成待启用** | Feature Flag + 基础设施已就绪, HNR/Voicing 数据待反馈到评分 | v6.0 校准后启用 |
| CPP 归一化因子 | VoiceLab CPP 通过 `/6` 映射到评分阈值, 未校准 | v6.0 校准数据集 |
| ~~HNR 天花板效应~~ | ✅ v5.19: 流行 12→22dB, 美声 20→28dB, CPP 1.0→2.5 | 已修复 |
| ~~Voicing 诊断未入评分~~ | ✅ v5.19: `_voicing_detection` 字段已预留, 集成路径已标注 | 基础设施就绪 |
| **气息评分低分偏高** | 差歌手呼吸 ~80 分 (接近好歌手 67-88), 因 breath_design 子指标与演唱质量弱相关 | v6.0 校准 + 质量门控 |

---

## 后续路线图

### ✅ v5.19: 评分区分度修复 (已完成 2026-07-04)

| 任务 | 说明 | 状态 |
|------|------|------|
| HNR/CPP 天花板重校准 | 流行 HNR 12→22dB, CPP 1.0→2.5 | ✅ 完成 |
| 气息基线降低 | 四子维度基线 40→10, 加分扩大 | ✅ 完成 |
| 音准阈值扩展 | MAE 8/45/65 + 斜率 *10→*30 | ✅ 完成 |
| 音量维度独立 | volume = f(dynamic_range) 替代 =breath_score | ✅ 完成 |
| 跨维度 Feature Flag | `enable_cross_dimension_modifiers` + 集成点标注 | ✅ 基础设施就绪 |
| HNR 稳定性 → Breath 修正 | 跨频带 CV 高 → 气息不稳惩罚 | 📋 v6.0 (需校准) |
| Voicing 置信度 → Pitch 可信度 | 低置信度降低音准权重 | 📋 v6.0 (需校准) |

### v6.1: 校准数据集 + 六维评分完善 + 算法增强

| 任务 | 优先级 | 工作量 |
|------|--------|--------|
| 3×3 对照数据集 (3首歌 × 3水平) | P0 | 2天 |
| 校准工具脚本 + 校准报告 | P0 | 2天 |
| 优先校准: CV断点, Breath基线, Artistry上限 | P0 | 1天 |
| 六维评分配置完善 | P1 | 1天 |
| f0 节奏路径恢复 (校准验证后) | P1 | 1天 |
| Technique baseline 重构 (移除硬编码50分地板) | P0 | 1天 |
| Breath 子维度评分连续化 (替换步进加分) | P0 | 1天 |
| 跨维度集成启用 (HNR稳定性→Breath, Voicing→Pitch) | P1 | 2天 |

### v6.1: 算法增强 + 混响补偿管线接入

| 任务 | 优先级 |
|------|--------|
| 混响补偿接入评分管线 (ReverbCompensator → HNR/CPP 修正) | P1 |
| SVQTD 7属性分类器接入 | P2 |
| ECAPA-TDNN 音色分析 (明亮度/厚度) | P2 |
| 歌曲模板系统 | P2 |

### v7.0: Electron 桌面应用 + Vue 3 前端重构

> 详见 [PRD.md §9](../1-product/PRD.md#9--v70--electron-桌面应用--vue-3-前端重构-规划中)

| 任务 | 优先级 | 工作量 |
|------|--------|--------|
| Vite + Vue 3 项目初始化 + Electron 集成 | P0 | 3 天 |
| Flask 子进程管理 (Electron 主进程) | P0 | 2 天 |
| 核心页面 Vue 重构 (首页 + 报告页) | P0 | 5 天 |
| 完整页面迁移 (历史/对比/演唱/设置/曲库) | P0 | 5 天 |
| 原生增强 (系统托盘/菜单/文件关联/自动更新) | P1 | 3 天 |
| electron-builder + PyInstaller 打包配置 | P0 | 3 天 |
| 全量测试 + 跨平台验证 | P0 | 3 天 |

---

## 性能基准

### 端到端模式性能

| 指标 | v5.15 | v5.16 | v5.17 | v5.18 目标 |
|------|-------|-------|-------|-----------|
| Quick 耗时 | ~40s | ~15-20s | ~15-20s | < 30s ✅ |
| Pro 耗时 (CPU) | ~226s | ~130-170s | ~130-170s | < 180s (已达) |
| Pro 耗时 (GPU) | — | — | ~30-50s | < 60s ✅ |
| 内存峰值 (Quick) | ~800MB | ~800MB | ~800MB | < 400MB |
| 内存峰值 (Pro) | ~1.2GB | ~1.2GB | ~1.2GB | < 800MB |
| 首次启动 | ~8s | ~8s | ~8s | < 10s ✅ |

### 特征提取阶段耗时 (3min 音频, 44.1kHz)

| 特征提取器 | v5.17 实际 | 预算 | 状态 |
|-----------|-----------|------|------|
| voice_quality | ~1.5s | < 2s | ✅ |
| PYIN f0 | ~5-7s | < 8s | ✅ |
| onset strength | ~2-3s | < 3s | ✅ |
| HNR + CPP | ~2-3s | < 3s | ✅ |
| RMS + breath 四维度 | ~1-2s | < 2s | ✅ |
| technique 检测 | ~2-3s | < 3s | ✅ |
| acoustic 混合检测 | ~0.5s | < 1s | ✅ |
| 自参照一致性 | ~0.5s | < 1s | ✅ |
| 评分计算 | ~0.5s | < 1s | ✅ |
| Phrase 逐句 | ~3-5s | < 5s | ✅ |
| Visualization | ~6-8s | < 10s | ✅ |
| Demucs (CPU) | ~100-130s | < 140s | ✅ |
| Demucs (GPU) | — (无GPU) | < 30s | ⏳ 需重装 CUDA 版 PyTorch |

### 前端性能

| 指标 | v5.17 实际 | 目标 | 状态 |
|------|-----------|------|------|
| FCP (首屏) | ~1.8s (未优化) | < 1.5s | ⏳ |
| TBT | ~300ms (inline styles) | < 200ms | ⏳ |
| 路由切换 | ~200ms (含旧 CSS 动画) | < 300ms (含 GSAP) | ✅ |
| GSAP 动画帧率 | — (未测量) | ≥ 30fps | ⏳ 待测量 |
| Canvas 实时绘制 | — (未启用) | ≥ 30fps | ⏳ v6.0 |
| JS Bundle | ~280KB (未 gzip) | < 300KB gzip | ⚠️ 需确认 |
| CSS 总体积 | ~45KB (含 inline) | < 50KB gzip | ⚠️ inline style 过多 |

### 模式一致性

| 指标 | v5.15 | v5.16 | v5.17 | 目标 |
|------|-------|-------|-------|------|
| Quick/Pro Rhythm 差 | -11.1 | -4.4 | -4.4 | < 5 ✅ |
| Quick/Pro Breath 差 | -46.6 | **-0.1** | **-0.1** | < 5 ✅ |
| Quick/Pro Total 差 | -12.5 | -1.1 | -1.1 | < 10% ✅ |
| 单元+集成测试 | 89/91 (98%) | **128/128 (100%)** | ✅ 超额达标 |
| TDD RED 测试 | — | **13 xfail** | 🆕 引导 v5.18+ |
| 真实音频回归 | — | **5 文件基线** | 🆕 防止评分退化 |
| JS 集成测试 | 30 mock | **16 真实模块** | 🆕 不再全 mock |

### 未测量指标 (v5.18 待建立)

| 指标 | 计划测量方式 |
|------|------------|
| 内存泄漏 (连续 10 次 Pro) | `tracemalloc` diff |
| DTW 对齐耗时 vs 音频长度 | 基准音频 × 3 个长度 |
| 文件上传吞吐 | 50MB 文件计时 |
| 历史记录查询 (1000条) | JSON 反序列化计时 |
| 报告 PDF 生成 (含图表) | `time.perf_counter()` |
| 前端动画帧率 | Chrome DevTools Performance |
| 长时间使用内存 | 30min + 50次页面切换 |

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
⏳ 跨维度集成 (HNR稳定性→Breath, Voicing→Pitch) (v5.19)
⏳ 气息区分度 ≥ 20 (需校准数据集)
⏳ 音准区分度 ≥ 10 (DTW + 校准)
⏳ HNR/CPP 天花板重校准 (v5.19)
✅ SPA 导航死锁修复 — 三重 Bug, 3 文件 (v5.20)
✅ 前端架构升级 — AppContext + EventBus + Vue 对齐 (v5.20)
```

---

## 参考文档

| 文档 | 路径 |
|------|------|
| 产品需求文档 | [PRD.md](../1-product/PRD.md) |
| 产品目标 | [GOALS.md](../1-product/GOALS.md) |
| 系统架构 | [ARCHITECTURE.md](../2-technical/ARCHITECTURE.md) |
| 评分算法 | [SCORING.md](../2-technical/SCORING.md) |
| TDD 规范 | [TDD.md](../3-quality/TDD.md) |
| BDD 规范 | [BDD.md](../3-quality/BDD.md) |
| 变更日志 | [CHANGELOG.md](CHANGELOG.md) |
