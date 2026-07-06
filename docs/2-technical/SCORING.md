# 评分算法文档

> 更新日期: 2026-07-06 | v6.1 — Technique 基线归零 + Breath 连续映射 + Artistry 独立评分

---

## 五维评分体系

### 权重分配

| 维度 | 默认权重 | 说明 |
|------|---------|------|
| 音准 (Pitch) | 30% | 核心维度 — 音分偏差 MAE |
| 节奏 (Rhythm) | 20% | 核心维度 — 节拍对齐偏差 |
| 气息 (Breath) | 20% | 辅助维度 — 四子维度专业评估 |
| 发声技术 (Technique) | 20% | 核心维度 — HNR/CPP/技巧检测 |
| 艺术表现 (Artistry) | 10% | 高级维度 — 情绪+技巧多样性 |

> 相关文档: [PRD](../1-product/PRD.md) | [架构](ARCHITECTURE.md) | [TDD](../3-quality/TDD.md) | [BDD](../3-quality/BDD.md)

### 权重配置机制 ★v6.0

#### 四层优先级 (高→低)

| 优先级 | 来源 | 存储位置 | 适用场景 |
|--------|------|---------|---------|
| 1 | 请求参数 `scoring_weights` | 请求体 | 对比分析手动调参 |
| 2 | 歌曲关联配置 | 曲库 `scoring_config` 字段 | 录入歌曲时保存 |
| 3 | 用户本地预设 | 前端 `localStorage` / JSON 文件 | 个人偏好 |
| 4 | 风格预设 | `config/styles.yaml` | 自动检测或手动选择 |

> **没有硬编码兜底**: 配置文件缺失或格式错误时，系统启动即报错 (`ConfigError`)，不静默降级。配置文件是唯一的真相来源 (Single Source of Truth)。

#### 风格预设权重表

| 风格 | Pitch | Rhythm | Breath | Tech | Art | 联动阈值调整 |
|------|-------|--------|--------|------|-----|------------|
| 流行 (默认) | 30% | 20% | 20% | 20% | 10% | 标准阈值, 与 config/default.py 一致 |
| 美声 | 30% | 15% | 25% | 20% | 10% | Pitch MAE≤10, Breath≥5s, Rhythm≤15% |
| 民族 | 28% | 18% | 18% | 18% | 18% | 滑音不计入跑调 |
| 说唱 | 10% | 35% | 10% | 15% | 30% | Pitch MAE放宽至≤25, 节奏权重加倍 |

#### 系统推荐算法

系统分析标准音频的 5 个维度的声学特征，按规则给出权重调整建议：

| 分析维度 | 检测方法 | 推荐规则 |
|---------|---------|---------|
| 音域 | 基频 min/max (半音) | 跨度 > 24 → Pitch +5% |
| 节奏 | BPM变异系数 + onset密度 | CV > 0.3 → Rhythm +5% |
| 长音 | ≥2s 连续高能量段占比 | > 30% → Breath +3% |
| 技巧 | 颤音+滑音+假声检测密度 | > 5处/分钟 → Technique +3% |
| 动态 | RMS标准差 (dB) | > 20dB → Artistry +5% |

> 推荐结果含每项调整的文字理由。用户可一键应用或微调后保存为自定义预设。详见 BDD: [scoring-config.feature](../../tests/bdd/features/scoring-config.feature)。

#### 有参考时的双轨评分

```
五维绝对评分 (always)          DTW 对比指标 (有参考时)
├─ total_score (五维加权)       ├─ dtw_score (0-100)
├─ scores.pitch/rhythm/...      ├─ pitch_match_rate (%)
├─ level + stars                ├─ rhythm_match_rate (%)
├─ advice (基于五维弱项)        ├─ problem_segments
└─ voice_quality                └─ alignment_confidence

两者互补, DTW 不替代五维。DTW 置信度低时以五维为准。
```

### 等级划分

| 分数区间 | 等级 | 星级 |
|---------|------|------|
| 90-100 | 专业级 | ★★★ |
| 80-90 | 优秀 | ★★☆ |
| 70-80 | 良好 | ★★ |
| 60-70 | 中等 | ★☆ |
| 50-60 | 及格 | ★ |
| 0-50 | 待改进 | ☆ |

---

## v6.1 评分公式变更 (2026-07-06)

### Technique: 基线归零

```
v5.x:  technique_score = 50 + vibrato 加分 + slide 加分
v6.1:  technique_score = 0  + vibrato 加分 + slide 加分 + falsetto 加分
```

HNR(40%) + CPP(30%) + technique_score(30%) = 技术维度总分。
技术维度仍由声带闭合质量主导; technique_score 仅反映技巧运用程度。

### Breath: 连续线性映射

```
v5.x:  if pitch_stability > 80:  score += 20  (步进加分)
v6.1:  score += pitch_stability * 0.40        (连续映射)

v5.x:  for each long_note: score += min(30, dur_s * 2.0)  (单句累加)
v6.1:  total_dur = sum(all long notes); score += min(30, total_dur * 2.0)  (总计)
```

所有子维度 (长音支撑/动态控制/气口设计/气声技巧) 从步进改为连续。

### Artistry: 独立声学信号

```
v5.14: artistry = pitch*0.20 + rhythm*0.25 + breath*0.20 + technique*0.35 + modulation(±10)
v6.1:  artistry = vibrato_expressiveness*0.30 + dynamic_expressiveness*0.30
                + phrase_expressiveness*0.25 + pitch_variation*0.15
```

每个子维度基于真实声学测量, 不再依赖其他维度分数。

---

## 各维度算法详解

### 1. 音准评分

**特征提取** (`services/features/pitch.py`):
- F0 → MIDI (12 * log2(f0/440) + 69)
- 计算到最近标准半音的音分偏差: `cents = (midi - round(midi)) * 100`
- 统计指标: MAE (平均绝对音分偏差)、max、连续跑调、音高断层 (>200音分跳变)、长音波动

**评分** (`services/scoring/pitch_scorer.py`):
- 基础分: 分段线性插值 (excellent≤12 → 100, good≤35 → 90-100, pass≤60 → 70-90)
- 惩罚项: 检测率<50% 扣分、音高断层>3处 扣分、长音波动>30音分 扣分

**阈值** (`services/scoring_config.py`):

| 级别 | MAE 音分 | 说明 |
|------|---------|------|
| 专业级 | ≤12 | 人耳几乎不可辨 |
| 良好 | ≤35 | 轻微偏差 |
| 合格 | ≤60 | 可接受范围 |

### 2. 节奏评分

**特征提取** (`services/features/rhythm.py`):
- 双路径策略:
  1. 优先: 基频变化 onset 检测 (>100音分跳变视为音符起始)
  2. 降级: librosa onset_strength + beat_track
- 计算 onset 与最近节拍点的归一化偏差 (偏差/拍间隔)
- 统计: 平均偏差比、最大偏差比、脱离节拍段数、节奏不规则度 (beat intervals CV)

**评分** (`services/scoring/rhythm_scorer.py`):
- 基础分: 分段线性 (excellent≤0.12 → 100, good≤0.25, pass≤0.38)
- 惩罚: 不规则度>0.3 扣分、BPS 异常 (<0.5 或 >5)

**阈值**:

| 级别 | 偏差比例 | 说明 |
|------|---------|------|
| 专业级 | ≤12% 拍长 | 节拍精准 |
| 良好 | ≤25% 拍长 | 基本对齐 |
| 合格 | ≤38% 拍长 | 有一定偏差 |

### 3. 气息评分 (v5.16 纯净人声校准)

**特征提取** (`services/features/breath.py`):
- 四子维度评估体系:

| 子维度 | 权重 | 评估内容 |
|--------|------|---------|
| 长音支撑 | 40% | ≥3秒连续高能量段的数量和基频/泛音稳定性 |
| 动态控制 | 25% | 弱唱质量、渐强渐弱平滑度、动态范围 |
| 气口设计 | 20% | 干净换气点数量、乐句连贯性 |
| 气声技巧 | 15% | 风格适配 HNR 区间 (可控气声 vs 无效漏气) |

- 艺术化波动检测: RMS自相关 + 基频-能量相关性 → 区分有规律起伏 vs 随机抖动

**评分** (`services/scoring/breath_scorer.py`):
- 使用 `professional_breath_score` (加权综合 + 艺术化判定 + 奖励分)
- 正向加分为主: 长音优秀+5、弱唱优秀+5
- 严重问题才惩罚: 气息断层>3处 扣分

**v5.16 纯净人声校准** (Demucs分离后):
- 非艺术波动惩罚: 阈值 0.25→0.35, 惩罚系数 60→30 (纯净人声RMS波动天然更大, 无伴奏平滑)
- 总分补偿: ×1.8 (Demucs后四子维度RMS/HNR/CPP系统性降解)
- 等级阈值放宽: 专业级85→73, 良好70→58, 合格55→43
- 标记: `BreathStabilityResult.is_clean_vocal` → `BreathAnalyzer` → `BreathScorer`
- 效果: Pro Breath 9.8→56.3 (+474%), Quick/Pro Breath差 -46.6→-0.1

**HNR 风格阈值**:

| 风格 | 优秀区间 | 可接受最低 |
|------|---------|-----------|
| 流行 | 8-15 dB | 5 dB |
| 美声 | 20-30 dB | 15 dB |
| 民族 | 15-25 dB | 10 dB |
| 说唱 | 5-12 dB | 3 dB |

### 4. 发声技术评分

**特征提取** (`services/features/technique.py`):
- 颤音检测: FFT频谱分析 detrended f0 → 检测 4.5-8Hz 周期性调制
- 滑音检测: 连续对数 f0 变化 >0.02
- 假声检测: 频谱质心 >3500Hz
- HNR (谐波噪声比): 反映声带闭合质量
- CPP (倒谱峰值突出): 声门闭合周期峰值

**评分** (`services/scoring/technique_scorer.py`):
- 三因素加权: HNR(40%) + CPP(30%) + 技巧完成度(30%)
- 风格感知阈值: 美声HNR>20dB满分, 流行实声>12dB满分, 气声>8dB正常
- 混合音频检测: 识别伴奏 → HNR应用1.5x修正系数
- 高技巧分 + 低HNR → 可能是艺术化气声选择，不惩罚

### 5. 艺术表现评分 (v5.14 重构)

**评分** (`services/scoring/artistry_scorer.py`):
- v5.14 复合评分: 从音准/节奏/气息/技术四维度加权合成 (Pitch×0.20 + Rhythm×0.25 + Breath×0.20 + Tech×0.35)
- 声学调制: 动态对比度(log range) + 音高多样性(unique notes ratio)
- 情绪置信度 `emotion_confidence` 来自启发式声学分析 (v5.12 已移除 Wav2Vec2 情绪模型)
- 效果: Artistry 区分度 0.3→28.4 (v5.14)

---

## 底线规则

| 规则 | 条件 | 惩罚 |
|------|------|------|
| 连续跑调 | ≥5个连续音符偏差>50音分 | 总分-20 |
| 脱离节拍 | 脱拍比例>40% | 总分上限70 |
| 严重漏气 | HNR<3dB | 总分上限50 |

实现: `services/scoring/critical_rules.py`

---

## DL 融合 (v5.15 已禁用)

- SingMOS 在 v5.15 完全移除 — 跨域反评分已铁证确认 (TTS 合成歌声自然度模型不适用于真人演唱)
- `_apply_dl_fusion()` → pass-through (始终返回原总分)
- `_assess_with_dl()` → 始终返回零值
- 替代方案: `_self_consistency_penalty()` 自参照分段一致性 (v5.15)
- 实现: `services/score_service.py:_apply_dl_fusion()` (保留为扩展点)

---

## 双评估模式

| 特性 | 快速评估 | 专业评估 |
|------|---------|---------|
| 耗时 | ~15-20s (CPU) | ~130-170s (CPU) / ~30-50s (GPU) |
| 阈值 | 标准 (与专业模式相同) | 标准 (0-100分) |
| 逐句评分 | ✗ | ✓ |
| 音色分析 | ✗ | ✓ |
| 可视化图表 | ✗ | ✓ |
| DL 质量评估 | ✗ (v5.15 已全局移除) | ✗ (v5.15 已全局移除) |
| 自参照一致性 | ✓ | ✓ |

### 算法复杂度与耗时分解

> 以 3 分钟 44.1kHz 单声道音频为基准 (~30MB WAV)。所有耗时在 16GB RAM + SSD 环境下测量。

| 算法 | 库 | 复杂度 | Quick 耗时 | Pro 耗时 | 内存 |
|------|-----|--------|-----------|---------|------|
| **Silero VAD** | PyTorch | O(n) 逐帧 | < 1s | < 1s | ~50MB (模型) |
| **PYIN f0** | librosa | O(n × fmin_eggs) | ~5s | ~8s | ~80MB |
| **Onset Strength** | librosa | O(n × n_fft) | ~2s | ~3s | ~40MB |
| **RMS 能量** | numpy | O(n) 向量化 | < 0.5s | < 1s | ~10MB |
| **HNR** (自相关法) | scipy | O(n × lag_max) | ~2s | ~3s | ~30MB |
| **CPP** (倒谱法) | numpy | O(n × n_fft × log(n_fft)) | ~1s | ~2s | ~30MB |
| **Chromaprint** | acoustid | O(n × n_fft) | 跳过 | 跳过 (仅匹配用) | — |
| **Demucs htdemucs_ft** | PyTorch | O(n × model_params) | 跳过 | ~120s CPU / ~25s GPU | ~800MB |
| **DTW** (全局) | scipy/numpy | O(m × n) | 跳过 | 跳过 (仅对比) | ~130MB |
| **自参照一致性** | numpy | O(n) 向量化 | < 1s | < 1s | ~5MB |
| **评分计算** (五维) | numpy | O(1) 聚合 | < 0.5s | < 1s | ~2MB |
| **可视化渲染** | matplotlib | O(n) 采样 | 跳过 | ~8s | ~50MB |

### Quick 模式耗时火焰图

```
VAD check       ██ 1s
PYIN f0         ██████████ 5s         ← 最大瓶颈 (31%)
Onset strength  ████ 2s
HNR + CPP       ██████ 3s
RMS + breath    ██ 1s
Technique       ██ 1s
Acoustic check  █ 0.5s
Scoring calc    █ 0.5s
Advice gen      █ 0.5s
Self-consistency █ 0.5s
────────────────────────────────
Total           ████████████████████████████ 15-20s
```

### Pro 模式耗时火焰图 (CPU)

```
VAD check       █ 1s
Mixed detection █ 0.5s
Demucs separate ████████████████████████████████████████████████████████████ 120s ← 70%
PYIN f0         ████ 8s
Onset strength  ██ 3s
HNR + CPP       ███ 4s
RMS + breath    █ 1s
Technique       ██ 2s
Phrase scoring  ██ 5s
Visualization   █████ 8s
Scoring calc    █ 1s
Advice gen      █ 1s
Self-consistency █ 0.5s
────────────────────────────────────────────────────────────────────────
Total           ████████████████████████████████████████████████████████████████████████ 155-170s
```

> **核心瓶颈**: Demucs 占 70-78% 总耗时。GPU 加速是最有效的优化手段 (120s → 25s)。
> 其次为 PYIN f0 (8s) → 可考虑 TorchCREPE 备选或降低 hop_length。
> 可视化 (8s) 可通过降低 DPI 或异步生成优化。

---

## 算法评估 (v5.9 审计 → v5.17 状态)

> 原始审计: [算法审计报告](ALGORITHM_AUDIT.md) (v5.9, 审计结论 6/10)

### 已修复 (v5.11-v5.17)

| 问题 (v5.9) | 修复版本 | 方案 |
|------|------|------|
| [P0-1] 未先做人声分离 | v5.11 | Demucs 接入评分主流程 |
| [P0-2] DTW 未默认化 | v5.15 | `_find_reference_audio()` 自动搜索 |
| [P1-1] librosa beat_track 节奏 | v5.15 | CV 重校准 + 标记传递链 |
| [P1-2] Wav2Vec2 域不匹配 | v5.12 | 移除 + v5.14 复合评分替代 |
| 魔法数字散落 | v5.12 | `EmpiricalThresholds` +14 字段 |

### 仍待解决

| 问题 | 影响 | 状态 |
|------|------|------|
| 23 个经验参数未校准 | 全局一致性 | 🟡 v6.1 计划 |
| ~~无混响补偿~~ | ✅ v6.0: `ReverbCompensator` 已接入管线 | ✅ 已修复 |
| 未跳过纯器乐段 (前奏/间奏) | 拖低评分 | 🟡 Silero VAD 已集成 |
| 古典/戏曲风格无效 | Rubato/微分音 | 🟡 低优先级 |
| ~~混合音频检测误判~~ | ✅ v6.0: 文献驱动五特征融合, 0 误判 | ✅ 已修复 |

### 混合音频检测: 文献驱动重构 ★v6.0

#### 算法 (`services/features/acoustic.py:detect_mixed_audio`)

基于以下论文重新设计, 五特征加权投票:

| 特征 | 理论来源 | 权重 | 说明 |
|------|---------|------|------|
| HPSS 谐波能量比 | Fitzgerald (2010). DAFx | 0.25 | 中值滤波分离谐波/冲击成分 |
| 子带频谱平坦度 (1.5-3kHz) | Lehner et al. (2018). TASLP §4 | 0.30 | 文献证明最可靠的单特征 |
| 高频能量 (>5kHz) | — | 0.20 | 镲片/弦乐泛音指示 |
| 谐波度 (Harmonicity) | Lehner et al. (2018) | 0.15 | f0 整数倍能量集中度 (自相关法) |
| 全频带频谱平坦度 | — | 0.10 | 辅助特征 |

移除: 低频能量 (<300Hz) — Lehner 2018 证明受录音/房间/声部影响过大

**HPSS 门控** [Driedger et al. 2014 §3]:
- `hpss_ratio > 0.88`: 跳过 (极纯谐波 → 纯人声)
- `0.72-0.88`: 五特征加权评分
- `< 0.72`: 显著非谐波内容指示伴奏

**决策阈值**:
- `mixed_score > 0.55` → 高置信混合
- `mixed_score > 0.40` → 中置信混合
- `mixed_score > 0.30` → 灰区 (触发分离, 低置信)
- `≤ 0.30` → 纯人声

#### 真音频验证 (30s 片段, 前 30s 足以建立频谱统计)

| 音频 | HPSS | 子带平坦度 | 谐波度 | 判定 | 预期 |
|------|------|-----------|--------|------|------|
| 1（高分） | 0.799 | 0.159 | 0.277 | ✅ CLEAN | CLEAN |
| 恋人（高分） | 0.866 | 0.126 | 0.241 | ✅ CLEAN | CLEAN |
| 手写的从前（高分） | 0.883 | 0.102 | 0.173 | ⚠️ CLEAN | MIXED |

**已知局限**: 手写的从前(轻钢琴抒情歌) 前 30s HPSS ratio 0.883 > 0.88 门控阈值。
轻钢琴伴奏自身高度谐波, HPSS 无法将其与人声区分 [Driedger 2014 §3]。
此为信号处理方法的理论上限, Lehner 2018 最终转向 LSTM 解决此问题。全曲分析可能因后续段落不同而产生不同判定。

#### v5.17 → v6.0 改进

| 指标 | v5.17 | v6.0 |
|------|-------|------|
| 特征数量 | 2 (低频能量+全频平坦度) | 5 (HPSS+子带平坦度+高频+谐波度+全频平坦度) |
| 纯人声误判率 | 75% (3/4) | **0%** (0/4) |
| 文献依据 | 经验阈值 | Fitzgerald+Driedger+Lehner |

---

---

## DTW 角色: 特征提供者, 非评分引擎 ★v6.0

### 设计决策 (基于学术文献)

| 论文 | 结论 |
|------|------|
| Bohm 2017 (IJCNN) | DTW+声学特征融合 → 与人工听感相关度 0.87, 纯DTW仅 0.52 |
| Gupta 2021 (APSIPA) | DTW对齐后节奏评分相关度从 0.53 → 0.78, 但仅限节奏 |
| Santos & Masiero 2026 (arXiv) | 综述: DTW仅适用于音准对齐和节奏对齐, 其他维度无效 |

**核心结论**: DTW 只擅长两件事 — 音准对齐和节奏对齐。气息/技术/艺术给它打分是"用错了工具"。

### 架构: DTW 降级为偏差数据提供者

```
标准音频 ─┐
          ├─ DTW 三级对齐 → 仅产出偏差数据:
用户音频 ─┘    ├─ dtw_pitch_cents: [...]    逐帧音分偏差
               ├─ dtw_rhythm_offset: [...]  逐帧节拍偏移 (ms)
               ├─ dtw_warp_path: [...]      对齐路径
               └─ alignment_confidence: float  全局置信度
                                   │
                                   ▼
                          ScoreServiceV4 (唯一评分入口)
               ├─ pitch_scorer:  PYIN + dtw_pitch_cents 加权融合
               ├─ rhythm_scorer: onset + dtw_rhythm_offset (代替CV估算)
               ├─ breath_scorer:  RMS/HNR/CPP/长音/弱唱 (DTW不参与)
               ├─ technique_scorer: HNR/CPP/颤音/滑音 (DTW不参与)
               ├─ artistry_scorer: 四维复合 (DTW不参与)
               └─ critical_rules:  全局生效 (DTW不参与)
```

### 各维度融合公式

#### 音准: PYIN + DTW 加权

```
pitch_final = pitch_pyin × (1 - dtw_weight) + pitch_dtw × dtw_weight
dtw_weight  = alignment_confidence × 0.70   (上限 70%)
```

- PYIN 始终保有 ≥30% 权重 (绝对音准不被 DTW 完全覆盖)
- confidence < 0.3 → dtw_weight = 0 → 纯 PYIN

#### 节奏: Onset + DTW 加权

```
rhythm_final = rhythm_onset × (1 - dtw_weight) + rhythm_dtw × dtw_weight
dtw_weight   = alignment_confidence × 0.50   (上限 50%)
```

- 有 DTW 偏移时, 跳过 CV 估算 + irregularity 惩罚
- 无 DTW 时回退到现有 onset + CV 路径 (行为不变)

#### 气息/技术/艺术: DTW 不参与

| 维度 | 评估方法 | DTW 状态 |
|------|---------|---------|
| 气息 | 四子维度 (长音/动态/气口/气声) | ❌ 不参与 |
| 技术 | HNR/CPP/颤音/滑音/假声 | ❌ 不参与 |
| 艺术 | 四维复合 + 声学调制 | ❌ 不参与 |
| 关键规则 | 连续跑调/脱离节拍/严重漏气 | ❌ 不参与 (全局生效) |

### 改动范围

| 文件 | 改动 | 行数 |
|------|------|------|
| `services/comparison/scoring_engine.py` | 移除 _score_pitch/_score_rhythm/_score_breath/_score_volume | -120 |
| `services/scoring/pitch_scorer.py` | 新增 dtw_pitch_cents 可选参数 + 加权融合 | +35 |
| `services/scoring/rhythm_scorer.py` | 新增 dtw_rhythm_offset 可选参数 + 加权融合 | +30 |
| `api/business/audio_analysis.py` | compare 端点改调 ScoreServiceV4 | +15 |

### 不改动的文件 (四个文件零改动)

`breath_scorer.py`, `technique_scorer.py`, `artistry_scorer.py`, `critical_rules.py` — DTW 降级不涉及这四个文件, 逻辑和测试完全不变。仅 `pitch_scorer.py` 和 `rhythm_scorer.py` 新增 DTW 可选参数。
