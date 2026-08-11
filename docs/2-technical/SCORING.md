# 评分算法文档 v7.14

> 更新: 2026-08-10 | DDD 唯一评分路径 | 714 tests collected GREEN (unit 575 + 集成 118 + 扩展 21)
>
> **关联文档**: [ARCHITECTURE.md](ARCHITECTURE.md) | [TECH_RESEARCH.md](TECH_RESEARCH.md) | [改进计划](SCORING_ALGORITHM_IMPROVEMENT_PLAN.md) | [PROJECT_STATUS.md](../4-process/PROJECT_STATUS.md)

---

## 一、六维权重 (v7.4+, v7.5 保持)

| 维度 | 权重 | 子维度 | 文献级别 |
|------|:---:|------|:------:|
| Pitch (音准) | **13%** | MAE指数衰减(40%) + RPA(25%) + RCA(10%) + Gross Error(15%) + Smoothness(5%) + Octave(5%) | A |
| Rhythm (节奏) | **12%** | Onset间隔CV + irregularity惩罚 + is_clean_vocal重校准 | B |
| Breath (气息) | **22%** | 长音支撑(40%) + 动态控制(25%) + 气口设计(20%) + 气声技巧(15%) | B |
| Technique (技术) | **25%** | 咬字清晰度(50%) + 气声比(50%), CPPS主特征 + ZCR/Centroid增强 + HNR单调 + 实谱HF | B |
| Muscle (肌肉) ⚠️ | **15%** | 身体力量(50%) + 面部力量(50%) + 五维代理(MPT/Crest/SPR/F1F2/Alpha) + 校准formant/overtone | C |
| Artistry (艺术) | **13%** | 颤音品质(30%) + 动态控制(30%) + 乐句表现力(25%) + 音高变化(15%), 无颤音fallback + **真实F0 CV** | D |
| **Total** | **100%** | | |
| Timbre (音色) ⚠️ | **±3~-5** | 加减分项, 不占权重, clamp[0,100], 双源置信度 + **八维剖面**(需audiofeat) | B |

> v7.4 权重新分配: muscle 从 25%→15% (双文献建议), 释放 10% 分配给 pitch(+3%)/rhythm(+2%)/breath(+2%)/artistry(+3%)
>
> v7.5 增强: Technique HNR 单调化 + 实谱 HF 解耦, Muscle formant/overtone 校准, Artistry 真实 F0 CV, Timbre 八维剖面
>
> v7.11: 权重收敛为单一数据来源 `ScoringWeights` 值对象 (见下节)
>
> ⚠️ = 启发式代理指标。详见 [改进计划](SCORING_ALGORITHM_IMPROVEMENT_PLAN.md)。

### 权重单一来源 — ScoringWeights (v7.11)

权重不再硬编码在 6 个 `Score.weighted()` 方法, 收敛为 `backend/domain/assessment/scoring_weights.py`:

- `ScoringWeights.default()` — v7.4 定稿 13/12/22/25/15/13
- 4 风格预设 (`pop`/`bel_canto`/`ethnic`/`rap`): 按 `scoring-config.feature` 原 5 维比例 ×0.85 + muscle 默认 15%
- `validate()` — 总和=100% + 单维 ∈[0,50%] (系统边界 from_dict/API 校验)
- `calculate_total(..., weights=None)` — 注入自定义权重计算 (风格预设/用户自定义/系统推荐)

| 预设 | Pitch | Rhythm | Breath | Technique | Muscle | Artistry | 说明 |
|------|:---:|:---:|:---:|:---:|:---:|:---:|------|
| 流行 | 21% | 17% | 13% | 17% | 15% | 17% | 均衡, 艺术表现较高 |
| 美声 | 25% | 13% | 21% | 17% | 15% | 9% | 偏重音准和气息 |
| 民族 | 24% | 15% | 15% | 15% | 15% | 16% | 五维均衡 |
| 说唱 | 8% | 30% | 9% | 13% | 15% | 25% | 节奏+艺术表现核心 |

### 等级划分

| 分数 | 等级 | 星级 |
|------|------|:--:|
| 88-100 | 专业级 | ★★★ |
| 78-88 | 优秀 | ★★☆ |
| 62-78 | 良好 | ★★ |
| 45-62 | 中等 | ★☆ |
| 25-45 | 及格 | ★ |
| 0-25 | 待改进 | ☆ |

---

## 二、特征提取管线

### DDD 原生路径 (唯一生产路径)

```
Raw Audio (y, sr)
  │
  ├─ normalize_loudness()          # RMS → 0.05, gain clamp [0.1, 10.0]
  │
  ├─ L0: Acoustic Foundation       # HNR/CPP/HPSS/Voicing/Mixed
  │
  ├─ L1: Pitch + Rhythm            # 可并行 (互不依赖)
  │
  ├─ L2: Breath + Technique + Timbre  # 依赖 L0 Acoustic
  │
  ├─ L3: Muscle + Artistry         # 依赖 L1+L2
  │
  └─ [Optional] Audiofeat          # 130+ 特征, flag 门控 (生产默认启用, services/feature_flags.enable_audiofeat=True)
```

### 提取器清单 (13/13 自包含)

| 层级 | 提取器 | 核心输出 |
|:--:|------|------|
| L0 | `AcousticExtractor` | HNR, CPP, HPSS harmonic ratio, voicing confidence, spectral tilt |
| L1 | `PitchExtractor` | MAE (cents), RPA, RCA, gross error rate, octave error rate, smoothness |
| L1 | `RhythmExtractor` | Onset CV, irregularity, off-beat segment count |
| L2 | `BreathExtractor` | 长音支撑, 动态控制, 气口设计, 气声技巧, decay rate, harmonic stability |
| L2 | `TechniqueExtractor` | Vibrato quality/rate, slides, falsetto, staccato, legato |
| L2 | `TimbreExtractor` | Spectral centroid deviation, MFCC distance/purity, harmonic richness, nasality |
| L3 | `MuscleExtractor` | max_db, low_freq_ratio, rms_decay, singers_formant, formant_cluster, overtone |
| L3 | `ArtistryExtractor` | Vibrato quality, dynamic range, phrase coherence, pitch CV |

---

## 三、各维度算法

### 3.1 音准 (Pitch) — 六指标加权

**文献**: Wager et al. (2022), Cao et al. (2008), de Cheveigne & Kawahara (2002)

| 指标 | 权重 | 公式 |
|------|:---:|------|
| MAE 指数衰减 | 40% | `100 × exp(−mae / 40)` τ=40音分 |
| RPA (原始音高准确率) | 25% | `rpa × 100` — \|cents\|<50 帧比例 |
| RCA (原始色度准确率) | 10% | `rca × 100` — 八度折叠准确率 |
| Gross Error 惩罚 | 15% | rate>0.05 时 `100 − min(100, (rate−0.05)×200)` |
| Smoothness | 5% | `max(0, 100 − (cv−1.0)×50)` |
| Octave Error 惩罚 | 5% | `max(0, 100 − rate×200)` |

**惩罚项**:
- 检测率 < 50%: `penalty = (0.5 − rate) × 30`
- Pitch breaks: YIN 校准 ÷3.5 校正因子, 仅 >5% 真实率触发 (上限 15 分)
- Pitch wobble > 10 音分: `penalty = min(10, (wobble − 10) × 0.3)`

### 3.2 节奏 (Rhythm) — Onset CV

**文献**: Bohm et al. (2017), Gupta et al. (2021)

| 偏差比例 | 分数 | 说明 |
|---------|:---:|------|
| ≤ 10% 拍长 | 100 | 节拍精准 |
| ≤ 20% | 80~100 | 基本对齐 |
| ≤ 30% | 50~80 | 有一定偏差 |
| > 30% | 20~50 | 偏差明显 |

**Irregularity 惩罚** (CV-based):
- irr > 1.2: `min(25, 10 + (irr−1.2)×15)`
- irr > 0.8: `min(15, (irr−0.5)×25)`
- irr > 0.5: `(irr−0.5)×15`

### 3.3 气息 (Breath) — 四子维度

**文献**: Samlan & Story (2013), Sundberg (1987)

| 子维度 | 权重 | 内容 |
|------|:---:|------|
| 长音支撑 | 40% | ≥3s 连续高能量段、基频/泛音稳定性 |
| 动态控制 | 25% | 弱唱质量、渐强渐弱平滑度、动态范围 |
| 气口设计 | 20% | 干净换气点数量、乐句连贯性 |
| 气声技巧 | 15% | 风格适配 HNR 区间 (可控气声 vs 无效漏气) |

**v7.3 audiofeat 增强** (flag 门控):
- GNE < 0.4 + HNR < 10 → 不可控漏气扣分 (≤8)
- GNE > 0.8 + CPPS > 8 → 优秀声门控制加分 (≤3)
- CPPS < 3 → 声门闭合弱扣分 (≤3)

**纯净人声校准** (Demucs 分离后):
- 非艺术波动惩罚放宽 (0.25→0.35, 60→30)
- 总分补偿 ×1.8
- 等级阈值放宽 (85→73, 70→58, 55→43)

### 3.4 发声技术 (Technique) — 咬字 + 气声比

**文献**: Rathi & Hsu (2021), Hecker (1974), Barsties v. Latoszek (2023), Michaelis et al. (1997), Samlan & Story (2013), Buckley et al. (2023)

**咬字清晰度** (50%, v7.4 文献对齐):
```
score = SpectralCentroid(30%) + SpectralFlux(15%) + ZCR(15%)
      + AttackSlope(15%) + C-V能量比(10%) + OnsetDensity(10%)
```
- Rathi & Hsu 2:1:1 比例: Centroid:Flux:ZCR = 1.0:0.5:0.5
- Attack slope (v7.6): 起音 RMS 上升速率 → 投射力和清晰度
- Fallback: ZCR=0 且 Centroid=0 时回退到旧 consonant_clarity 路径

**气声比** (50%, v7.4 CPPS 主特征):
```
score = CPPS(40%) + HNR(25%) + SpectralTilt(20%) + HF_Energy(15%)
```
- CPPS ≥ 9.0 → +40 (v7.6: 声学 CPP ×100 校准), 歌声阈值 (Buckley 2023)
- HNR graduated: ≥25→满分, 18-25→70%, 10-18→30% (v7.6: 歌声特定)
- CPPS=0 时 HNR fallback 至 45%
- Spectral tilt < -5 → `penalty = min(20, abs(tilt+5)×4)`

**v7.3-v7.9 audiofeat 增强** (在 `_apply_audiofeat_enhancement()` 中, v7.7 起生产默认启用):
| 特征 | 条件 | 效果 | 影响维度 | 版本 |
|------|------|------|---------|:--:|
| Jitter | < 0.5% | +5 | 咬字 | v7.3 |
| Jitter | > 3.0% | -10 | 咬字 | v7.3 |
| Shimmer | < 0.1 dB | +3 | 气声比 | v7.3 |
| Shimmer | > 0.5 dB | -5 | 气声比 | v7.3 |
| Closed Quotient | 0.4-0.6 | +3 | 气声比 | v7.3 |
| Closed Quotient | < 0.2 | -5 | 气声比 | v7.3 |
| **GNE** | **> 0.8** | **+5** | **气声比** | **v7.8** |
| **GNE** | **< 0.4** | **-8** | **气声比** | **v7.8** |
- GNE (AROC=0.886, Michaelis 1997): 声门-噪声激励比，最强气声单一判别指标
- GNE 阈值与 BreathScorer 一致 (0.4/0.8)，确保评分体系一致性
- 所有值为 0 (audiofeat 不可用) → 跳过所有增强

### 3.5 肌肉力量 (Muscle) — 启发式代理 ⚠️

**文献**: Griffin et al. (1995), Thorpe et al. (2001), McQuade (2016), Aura et al. (2019)

**身体力量** (50%):
```
body = max_db_score(40%) + low_freq_score(35%) + decay_score(25%)
```
- max_db: [-30, 0] dB 线性映射
- low_freq: >0.40→100, >0.20→60, 分段线性
- rms_decay: <0.5→100, 3.0→10, 分段线性

**面部力量** (50%):
```
facial = singers_formant(40%) + formant_cluster(35%) + overtone(25%)
```
- singers_formant: >0.15→100, 分段线性
- formant_cluster: 0-100 直接映射
- overtone: >8→100, 分段线性

> ⚠️ **已知问题**: ✅ 权重已修正 (v7.4: 25%→15%)。仍需五维代理增强 (MPT, SPR, Crest Factor, F1/F2 元音空间)。详见 [改进计划](SCORING_ALGORITHM_IMPROVEMENT_PLAN.md#七p1-1-肌肉力量五维代理重构)。

### 3.6 艺术表现 (Artistry) — 四子维度

**文献**: Sundberg (1987), Canazza et al. (2014)

| 子维度 | 权重 | 计算 |
|------|:---:|------|
| 颤音品质 | 30% | `quality×0.80 + min(20, count×2)`. count==0 → 0 |
| 动态控制 | 30% | `min(60, dynamic_range×2) + crescendo_quality×0.40` |
| 乐句处理 | 25% | `coherence×0.70 + 30(artistic?) + min(10, notes×2)` |
| 音高变化 | 15% | 双峰映射: 低→升, 中→平台, 高→降 |

> ⚠️ **已知问题**: 无颤音 → 0 分 (流行/R&B/说唱受歧视)。区分度仅 1.9 分。详见 [P0 修复](SCORING_ALGORITHM_IMPROVEMENT_PLAN.md#五p0-3-艺术表现无颤音-fallback)。

### 3.7 音色 (Timbre) — 加减分 ⚠️

**文献**: 音色文献 research-summary §1.1-1.2

**两条路径**:

| 路径 | 子维度 | 权重 |
|------|------|:--:|
| 启发式 (v7.0) | brightness + warmth + nasality | 30/30/40 |
| audiofeat 增强 (v7.3) | brightness + warmth + nasality + roughness | 25/25/25/25 |

**不对称调整**:
| Quality | Adjustment |
|---------|:--:|
| ≥ 80 | +3 |
| 60-80 | +1 |
| 40-60 | 0 |
| 20-40 | -2 |
| 10-20 | -3 |
| < 10 | -5 |

**置信度门控**: `mfcc_cluster_purity < 0.6` → adjustment = 0

> ⚠️ **已知问题**: 无 audiofeat 时, 旧 CPP ~0.018 → mfcc_cluster_purity = 0.003 < 0.6 → 音色始终归零。详见 [P1 修复](SCORING_ALGORITHM_IMPROVEMENT_PLAN.md#八p1-2-音色八维剖面增强)。

---

## 四、Quick vs Professional 模式

| 特性 | Quick (~20s) | Professional (~155s CPU / ~55s GPU) |
|------|:-----------:|:----------------------------------:|
| 基础特征 (音量/音高/节奏/颤音) | ✅ | ✅ |
| Demucs 人声分离 | ❌ | ✅ (混合音频时, 120s CPU / 25s GPU) |
| DL 模型 (VAD/分类/DTW/风格) | ❌ | ✅ (~3s) |
| 评分算法 | 相同 | 相同 |
| 跨维度修正 | ✅ | ✅ |
| 唱法自适应权重 | ❌ (无 style_profile) | ✅ (来自 DL 唱法分类) |
| 可视化生成 | ❌ | ✅ (8s) |
| 音色分析 | ❌ | ✅ (2s) |
| 逐句评分 | ❌ | ✅ (5s) |

### 分数差异来源

Quick 和 Pro 使用**完全相同的评分算法**。差异仅来自:
1. Pro 通过 Demucs 获得更纯净的人声 → f0/HNR/CPP 更准确
2. Pro 通过 DL 唱法分类 → StyleAwareScorer 调整五维权重
3. 特征质量差异 (非算法差异)

---

## 五、跨维度修正 & 底线规则

### 跨维度修正

| 修正 | 触发条件 | 幅度 |
|------|---------|:--:|
| HNR 多频带 CV → 气息 | HNR CV > 0.15 | ≤15% |
| Voicing 置信度 → 音准 | confidence < 0.6 | 标记(不改分) |
| 频谱倾斜 → 气声技巧 | tilt > -10 (艺术) / tilt < -14 (漏气) | ≤15% |
| 气息-音准耦合 | wobble > 40 + CV > 0.20 | ≤15 分 |

### 底线规则

| 规则 | 条件 | 惩罚 |
|------|------|------|
| 连续跑调 | ≥5 个连续音符偏差 > 50 音分 | 总分 -20 |
| 脱离节拍 | 脱拍比例 > 40% | 总分上限 70 |
| 严重漏气 | HNR < 3 dB | 总分上限 50 |

### 人声质量惩罚

- VQ < 30 → 总分上限 40
- VQ < 50 → `penalty = (50 − VQ) / 50 × 35`

---

## 六、DTW 对比评分

**架构决策** (ADR-7): DTW 降级为特征提供者, 不打分。

```
Compare 流程:
  standard audio + user audio
    │
    ├─ analyze_and_score(standard)  → standard scores
    ├─ analyze_and_score(user)      → user scores
    └─ DTW alignment:
         ├─ dtw_pitch_cents         → PitchScorer 加权融合 (DTW ≤ 70%)
         ├─ dtw_rhythm_offset       → RhythmScorer 加权融合 (DTW ≤ 50%)
         └─ alignment_confidence     → 置信度 < 0.3 时 DTW 权重 = 0
```

**文献依据**: Bohm 2017 — DTW+声学融合 r=0.87 vs 纯 DTW r=0.52。DTW 仅用于音准/节奏对齐, 气息/技术/艺术维度完全不参与。

---

## 七、Feature Flags

每个维度可独立开关 (`DimensionFlags`):

| Flag | 默认 | 关闭时 |
|------|:---:|------|
| `enable_pitch` | True | 中性分 0 |
| `enable_rhythm` | True | 中性分 0 |
| `enable_breath` | True | 中性分 0 |
| `enable_technique` | True | 中性分 0 |
| `enable_muscle_strength` | True | 中性分 0 |
| `enable_artistry` | True | 中性分 0 |
| `enable_timbre_adjustment` | True | adjustment = 0 |
| `enable_audiofeat` | **True*** | 生产默认启用 130+ 特征 (CPPS/GNE/ABI/Jitter/Shimmer); 领域层默认 False, 由 services/feature_flags.py 桥接覆盖为 True |
| `enable_ddd_feature_extraction` | True | 回退旧 AudioFeaturesService |

---

## 八、DDD vs Legacy 对齐验证

以 melody.wav 为对齐基准 (DDD 原生 vs Legacy 适配器):

| 维度 | DDD | Legacy | Δ |
|------|:---:|:---:|:---:|
| Pitch | 90.3 | 90.0 | +0.3 |
| Rhythm | 100.0 | 100.0 | 0.0 |
| Breath | 34.2 | 35.5 | -1.3 |
| Technique | 50.3 | 46.9 | +3.4 |
| Muscle | 73.3 | 75.0 | -1.7 |
| Artistry | 54.6 | 56.4 | -1.8 |
| **Total** | **62.2** | **60.2** | **+2.0** |

---

## 九、真实音频评分 (v7.3 Quick, DDD 唯一路径)

| 音频 | Total | Pitch | Rhythm | Breath | Tech | Muscle | Art | Timbre |
|------|:-----:|:-----:|:------:|:------:|:----:|:------:|:---:|:------:|
| 恋人 (高分) | **65.7** | 67 | 66 | 92 | 25 | 80 | 76 | 0 |
| 手写的从前 (高分) | **61.7** | 70 | 42 | 94 | 19 | 76 | 77 | 0 |
| 1 (高分) | **65.7** | 71 | 71 | 97 | 20 | 78 | 76 | 0 |
| 陈奕迅难听之声 (低分) | **52.8** | 66 | 5 | 84 | 16 | 70 | 74 | 0 |

> **说明**: Technique 系统性偏低 (~20 vs 其他维度 ~70) 已在 [改进计划](SCORING_ALGORITHM_IMPROVEMENT_PLAN.md) 中诊断。Timbre=0 因置信度门控在生产中失效。

---

## 十、参考

| 文档 | 说明 |
|------|------|
| [TECH_RESEARCH.md](TECH_RESEARCH.md) | 五维度算法文献验证 + 实施路线 |
| [SCORING_ALGORITHM_IMPROVEMENT_PLAN.md](SCORING_ALGORITHM_IMPROVEMENT_PLAN.md) | 12 项问题诊断 + P0-P2 修复方案 |
| [PERFORMANCE_ANALYSIS_AND_OPTIMIZATION.md](PERFORMANCE_ANALYSIS_AND_OPTIMIZATION.md) | 性能瓶颈 + 11 项优化方案 |
| [PROJECT_STATUS.md](../4-process/PROJECT_STATUS.md) | 当前版本状态 |
| [CHANGELOG.md](../4-process/CHANGELOG.md) | 历史版本变更 |
