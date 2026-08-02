# 声乐评分算法 — 文献验证 & 完善计划

> 版本: v1.3 | 日期: 2026-08-02 | 基于 v7.5 源码 + 十二篇新增文献交叉验证
>
> **关联文档**: [TECH_RESEARCH.md](TECH_RESEARCH.md) | [SCORING.md](SCORING.md) | [PROJECT_STATUS.md](../4-process/PROJECT_STATUS.md)
>
> **实施状态**: P0 ✅ v7.4-v7.5 | P1 ✅ v7.6 | P2 ⏭️ 按需 (ABI 9参数 + 艺术表现重构; Flask + Legacy 代码清理已于 v7.6 完成)

---

## 目录

1. [深度验证: 每个结论的文献依据](#一深度验证)
2. [问题全景图: 严重度矩阵](#二问题全景图)
3. [P0 修复: 气声比 HNR 权重修正](#三p0-1-气声比-hnr-权重修正)
4. [P0 修复: 咬字清晰度接入 ZCR + Spectral Centroid](#四p0-2-咬字清晰度接入-zcr--spectral-centroid)
5. [P0 修复: 艺术表现无颤音 fallback](#五p0-3-艺术表现无颤音-fallback)
6. [P0 修复: 肌肉权重 25%→15%](#六p0-4-肌肉权重-调整)
7. [P1: 肌肉力量五维代理重构](#七p1-1-肌肉力量五维代理重构)
8. [P1: 音色八维剖面增强](#八p1-2-音色八维剖面增强)
9. [P2: 中长期演进方向](#九p2-中长期演进)
10. [实施路线图 &amp; 测试策略](#十实施路线图)

---

## 一、深度验证

> 每个关键结论都需要经过"文献原文 → 代码实现 → 实际评分数据"三重交叉验证。

### 1.1 HNR 与气声感知的关系

| 来源                        | 结论                                                     | 上下文                     |
| --------------------------- | -------------------------------------------------------- | -------------------------- |
| TECH_RESEARCH §3.1         | HNR 与气声相关性**r=-0.56 不显著**，跨研究一致性低 | 气声比**检测**场景   |
| 气声比 research-summary §4 | HNR P0 优先级，相关性**强 (r~0.78)**               | 通用**嗓音质量**场景 |
| Barsties v. Latoszek (2023) | GNE & CPPS 是最强单一指标                                | 临床气声评估               |

**关键区分**: HNR 与"通用嗓音质量"相关度 r~0.78，但与"气声感知"相关度仅 r=-0.56（不显著）。两者不矛盾——HNR 擅长反映声带闭合整体质量，但不擅长区分"可控气声（艺术选择）"和"不可控漏气（技术缺陷）"。

**当前代码问题** ([technique_scorer.py:174](backend/domain/assessment/technique_scorer.py#L174))：

```python
if 12 <= hnr_mean <= 22:
    score += 70.0   # HNR 贡献 70/100 = 70% 权重
```

70% 权重放在一个对气声感知"不显著"的指标上，是结构性问题。CPPS（单独解释 86.7% 感知气息感方差）仅通过 audiofeat 可选增强参与评分。

**验证通过** ✅ — 结论成立，但需补充 nuance：HNR 不应被移除，而是降权为辅助验证角色。

---

### 1.2 咬字清晰度特征对齐 Rathi & Hsu (2021)

| 来源                                                                                    | 公式                                                                              |
| --------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| 咬字 research-summary §4                                                               | `articulation = 0.5*SpectralFlux + 1.0*SpectralCentroid + 0.5*ZCR + 0*Spread`   |
| 当前代码 ([technique_scorer.py:139](backend/domain/assessment/technique_scorer.py#L139)) | `score = consonant_clarity*0.50 + onset_density_bonus − spectral_flux_penalty` |

**逐特征对比**:

| 特征              | Rathi & Hsu 权重 |       当前代码       |        状态        |
| ----------------- | :--------------: | :-------------------: | :-----------------: |
| Spectral Flux     |    0.5 (25%)    | ✅ 扣分项 (>3.0 惩罚) |    ⚠️ 方向相反    |
| Spectral Centroid |    1.0 (50%)    |      ❌ 完全缺失      |         ❌         |
| ZCR (过零率)      |    0.5 (25%)    |      ❌ 完全缺失      |         ❌         |
| Spectral Spread   |      0 (0%)      |          —          |         ✅         |
| onset_density     |        无        |     占 ~33% 权重     |   ⚠️ 无文献依据   |
| consonant_clarity |        无        |      占 50% 权重      | ⚠️ 提取链路不完整 |

**额外缺失**: C-V 能量比 (Hecker 1974, Freyman & Nerbonne 1989) — 经典语音学指标，完全未使用。

**验证通过** ✅ — 当前咬字算法与唯一直接相关文献 (Rathi & Hsu) 有系统性偏差。

---

### 1.3 无颤音 = 0 分的设计缺陷

代码 ([artistry_scorer.py:67](backend/domain/assessment/artistry_scorer.py#L67))：

```python
def _calc_vibrato(quality: float, count: int) -> float:
    if count == 0:
        return 0.0   # ← 颤音次数=0 → 整个颤音子维度=0
```

**影响链**: 颤音子维度占艺术表现 30% → 无颤音歌手的艺术表现被系统性压低 ~30 分 → 流行/R&B/说唱等不常用颤音的唱法被系统性歧视。

**文献支持**: TECH_RESEARCH §2.6 已标注此问题："无颤音歌手得0分但可能其他表现力强 (设计缺陷)"。

**验证通过** ✅ — 设计缺陷已自文档化。

---

### 1.4 音色置信度门控导致实际完全禁用

**代码追踪**:

```
1. LibrosaTimbreExtractor.extract() [timbre_extractor.py:33]:
   cpp = getattr(acoustic, 'cpp', 1.0)  → 旧 CPP 对所有音频返回 ~0.018
   
2. [timbre_extractor.py:43]:
   mfcc_cluster_purity = clamp(cpp / 6.0)  → 0.018/6.0 = 0.003

3. TimbreAdjuster.calculate() [timbre_adjuster.py:123]:
   if confidence < 0.6:  → 0.003 < 0.6 → adjustment = 0.0
```

**结论**: 在 `enable_audiofeat=False`（默认值，[feature_flags.py:36](backend/domain/assessment/feature_flags.py#L36)）时，音色加减分**永远为 0**。真实音频测试结果全部 `Timbre=0` 证实了这一点。

**验证通过** ✅ — 音色维度在实际生产中完全禁用。

---

### 1.5 肌肉权重 25% vs 文献建议 15%

| 来源                           | 建议                                              |
| ------------------------------ | ------------------------------------------------- |
| TECH_RESEARCH §3.4 (面部肌肉) | "保持 HEURISTIC 标注,**降低权重 25%→15%**" |
| TECH_RESEARCH §3.5 (身体肌肉) | "保持 HEURISTIC 标注,**降低权重 25%→15%**" |
| 综合评估 §2.4                 | "零研究从纯音频推断面部肌肉参与度"                |
| 综合评估 §2.5                 | "声门下压力从纯音频估计物理上不可行"              |

两个独立维度研究得出相同建议，且理由充分（零纯音频→肌肉验证研究、效应量跨研究波动 r=0.43→0.932）。

**验证通过** ✅ — 权重调整有双重文献建议支持。

---

### 1.6 发声技术维度结构性偏低

**真实音频数据验证** ([PROJECT_STATUS.md](../4-process/PROJECT_STATUS.md)):

| 音频                   | Total |     Tech     | 其他维度均值 |
| ---------------------- | :---: | :----------: | :----------: |
| 恋人（高分）           | 65.7 | **25** |     76.2     |
| 手写的从前（高分）     | 61.7 | **19** |     71.8     |
| 1（高分）              | 65.7 | **20** |     78.6     |
| 陈奕迅难听之声（低分） | 52.8 | **16** |     59.2     |

Technique 系统性低于其他维度 40-60 分。根因分析：

1. `consonant_clarity` 提取链路不完整 → 始终为 0
2. 气声比 HNR 占 70% → 多数歌声 HNR 不在 [12, 22] 最优区间
3. 两个子维度理论上限仅 ~55 分（无 audiofeat 增强时）

**验证通过** ✅ — 系统性偏差已通过真实数据证实。

---

## 二、问题全景图

### 严重度定义

|        级别        | 含义           | 标准                                          |
| :----------------: | -------------- | --------------------------------------------- |
| **CRITICAL** | 评分系统性错误 | 文献明确否定当前方法 + 真实数据证实系统性偏差 |
|   **HIGH**   | 评分结构性缺陷 | 文献提供更优方案 + 当前实现有已知局限         |
|  **MEDIUM**  | 评分可优化     | 文献支持的增强特征缺失                        |
|   **LOW**   | 长期演进       | 需要额外数据/训练                             |

### 问题矩阵

| #  | 问题                                      | 文件                                                    |       严重度       | 文献依据                   | 实施状态 |
| -- | ----------------------------------------- | ------------------------------------------------------- | :----------------: | -------------------------- | :------: |
| C1 | 气声比 HNR 占 70% 权重                    | `technique_scorer.py:174`                             | **CRITICAL** | Samlan 2013, Barsties 2023 | ✅ P0-1 |
| C2 | 音色置信度门控在生产中始终归零            | `timbre_extractor.py:43` + `timbre_adjuster.py:123` | **CRITICAL** | —                         | ✅ P1-2a |
| H1 | 咬字缺失 ZCR + Spectral Centroid          | `technique_scorer.py:139`                             |   **HIGH**   | Rathi & Hsu 2021           | ✅ P0-2 |
| H2 | 无颤音 = 0 分                             | `artistry_scorer.py:67`                               |   **HIGH**   | TECH_RESEARCH §2.6        | ✅ P0-3 |
| H3 | 肌肉权重 25%，文献建议 15%                | `value_objects.py:112`                                |   **HIGH**   | TECH_RESEARCH §3.4, §3.5 | ✅ P0-4 |
| H4 | 技术维度理论上限仅 ~55 分                 | `technique_scorer.py`                                 |   **HIGH**   | 代码结构分析               | ✅ P0-1 |
| M1 | 身体肌肉缺失 MPT                          | `muscle_scorer.py:99`                                 |  **MEDIUM**  | 身体肌肉文献 §2.1         | ✅ P1-1 |
| M2 | 身体肌肉缺失 Crest Factor + SPR           | `muscle_scorer.py:99`                                 |  **MEDIUM**  | 身体肌肉文献 §2.1         | ✅ P1-1 |
| M3 | 面部肌肉缺失 F1/F2 元音空间               | `muscle_scorer.py:145`                                |  **MEDIUM**  | 面部肌肉文献 §2.1         | ✅ P1-1 |
| M4 | 音色缺失 hardness/depth/sharpness/booming | `timbre_adjuster.py`                                  |  **MEDIUM**  | 音色文献 §1.1             | ⏭️ P1-2b |
| M5 | 咬字缺失 C-V 能量比                       | `technique_scorer.py:139`                             |  **MEDIUM**  | Hecker 1974                | ✅ P0-2 |
| L1 | ABI 9 参数模型                            | 新文件                                                  |   **LOW**   | Barsties 2017              | ⏭️ P2 |
| L2 | 艺术表现根本性重构                        | `artistry_scorer.py`                                  |   **LOW**   | TECH_RESEARCH §2.6        | ⏭️ P2 |

---

## 三、P0-1: 气声比 HNR 权重修正

### 问题

`TechniqueScorer._calc_breath_voice_ratio()` 中 HNR 贡献 70/100 分，但文献证明 HNR 与气声感知相关度 **r=-0.56 不显著**。CPPS（解释 86.7% 方差）仅通过可选 audiofeat 参与。

### 修改文件

[backend/domain/assessment/technique_scorer.py](backend/domain/assessment/technique_scorer.py)

### 当前代码 (L164-195)

```python
@staticmethod
def _calc_breath_voice_ratio(
    hnr_mean: float,
    spectral_tilt: float,
    hf_energy_ratio: float,
) -> float:
    score = 0.0
    # HNR: optimal 12-22 dB → +70 (占70%)
    if 12 <= hnr_mean <= 22:
        score += 70.0
    elif hnr_mean < 5:
        score += 20.0
    ...
```

### 修改方案

```python
@staticmethod
def _calc_breath_voice_ratio(
    hnr_mean: float,
    spectral_tilt: float,
    hf_energy_ratio: float,
    cpp_mean: float = 1.0,      # 🆕 CPPS 作为主特征
) -> float:
    """
    气声比 = f(CPPS主, HNR辅, spectral_tilt, hf_energy)
  
    文献依据:
    - CPPS: 单独解释 86.7% 感知气息感方差 (Samlan & Story 2013), r=-0.81
    - HNR: 通用嗓音质量 r~0.78, 但气声特异度低 r=-0.56 (Barsties 2023)
    - Spectral tilt: 区分可控气声 vs 不可控漏气 (Sundberg 1987)
    """
    score = 0.0

    # === 1. CPPS (40%) — 主特征 ===
    # 文献: 连续语音 CPPS > 8.37 dB = 正常, < 3.0 dB = 严重气息
    #      歌声阈值略低 (F0范围更宽、强度变化大)
    if cpp_mean > 0:  # 可用
        if cpp_mean >= 12.0:
            score += 40.0
        elif cpp_mean >= 8.0:
            score += 30.0 + (cpp_mean - 8.0) / 4.0 * 10.0   # 8→30, 12→40
        elif cpp_mean >= 5.0:
            score += 15.0 + (cpp_mean - 5.0) / 3.0 * 15.0   # 5→15, 8→30
        elif cpp_mean >= 3.0:
            score += 5.0 + (cpp_mean - 3.0) / 2.0 * 10.0    # 3→5, 5→15
        else:
            score += max(0.0, cpp_mean / 3.0 * 5.0)          # 0→0, 3→5
    else:
        # CPPS 不可用 → HNR 权重提升为 fallback (但仍不超过 45%)
        pass  # 见下方 HNR 回退逻辑

    # === 2. HNR (25%) — 辅助验证 ===
    # 文献: HNR 区分声带闭合整体质量，但非气声特异指标
    # 权重从 70% 降至 25%
    if cpp_mean > 0:
        hnr_weight = 25.0  # CPPS 可用时，HNR 为辅助
    else:
        hnr_weight = 45.0  # CPPS 不可用时，HNR 提升为 fallback
  
    if 12 <= hnr_mean <= 22:
        score += hnr_weight
    elif hnr_mean < 5:
        score += hnr_weight * 0.20    # 5→20% scale
    elif hnr_mean > 30:
        score += hnr_weight * 0.60    # 30→60% scale
    elif hnr_mean < 12:
        score += hnr_weight * (0.20 + (hnr_mean - 5) / 7.0 * 0.80)
    else:  # 22-30
        score += hnr_weight * (1.0 - (hnr_mean - 22) / 8.0 * 0.40)

    # === 3. Spectral tilt (20%) — 区分艺术气声 vs 漏气 ===
    # 文献: 气息音 H1-H2 = +2.08dB, 正常 = -0.60dB, 紧压 = -1.63dB
    if spectral_tilt < -5:
        penalty = min(20.0, abs(spectral_tilt + 5) * 4.0)
        score -= penalty

    # === 4. HF energy (15%) — 气声产生额外高频噪声 ===
    if hf_energy_ratio > 0.7:
        penalty = min(15.0, (hf_energy_ratio - 0.7) * 30.0)
        score -= penalty

    return max(0.0, min(100.0, score))
```

### 权重对比

| 特征          |      修改前      | 修改后 (CPPS 可用) | 文献依据                                     |
| ------------- | :---------------: | :----------------: | -------------------------------------------- |
| CPPS          | 0% (不在函数签名) |   **40%**   | Samlan & Story 2013: 86.7% 方差解释          |
| HNR           |   **70%**   |        25%        | Barsties 2023: r=-0.56 不显著 (气声特异度低) |
| Spectral Tilt |       ~15%       |        20%        | Sundberg 1987: H1-H2 区分气息类型            |
| HF Energy     |       ~15%       |        15%        | 气声产生额外 >5kHz 噪声                      |

### 特征输入变更

`TechniqueFeatures` 已有 `cpp_mean: float = 1.0` 字段 ([technique_scorer.py:28](backend/domain/assessment/technique_scorer.py#L28))，无需修改数据结构。仅需在调用方确保传入有效 CPPS 值。

### 预期效果

- Tech 维度理论最大值从 ~55 提升至 ~90
- 真实音频 Tech 分数从 16-30 范围提升至 40-70 范围
- 高低分歌手 Tech 差异增大（CPPS 区分度优于 HNR）

---

## 四、P0-2: 咬字清晰度接入 ZCR + Spectral Centroid

### 问题

当前 `_calc_articulation()` 使用 `consonant_clarity*0.50 + onset_density_bonus - spectral_flux_penalty`，而唯一直接相关文献 (Rathi & Hsu 2021) 的公式是 `0.5*Flux + 1.0*Centroid + 0.5*ZCR`。ZCR 和 Spectral Centroid 完全缺失，consonant_clarity 提取链路不完整。

### 修改文件

[backend/domain/assessment/technique_scorer.py](backend/domain/assessment/technique_scorer.py)

### 特征输入扩展

```python
@dataclass(frozen=True)
class TechniqueFeatures:
    """发声技术特征输入 (不可变)"""
    # === 咬字清晰度 (v7.4 扩展) ===
    onset_density: float = 0.0
    spectral_flux: float = 0.0
    consonant_clarity: float = 0.0
    zcr_mean: float = 0.0              # 🆕 过零率均值
    spectral_centroid: float = 0.0      # 🆕 频谱质心
    cv_energy_ratio: float = -15.0      # 🆕 C-V 能量比 (dB, 典型 -15)
  
    # === 气声比 (不变) ===
    hnr_mean: float = 15.0
    spectral_tilt: float = 0.0
    hf_energy_ratio: float = 0.5
    cpp_mean: float = 1.0
    vibrato_quality: float = 0.0
    vibrato_rate_avg: float = 5.0
```

### 修改方案

```python
@staticmethod
def _calc_articulation(
    onset_density: float,
    spectral_flux: float,
    consonant_clarity: float,
    # === v7.4 新增 ===
    zcr_mean: float = 0.0,
    spectral_centroid: float = 0.0,
    cv_energy_ratio: float = -15.0,
) -> float:
    """
    咬字清晰度 = 文献驱动加权融合
  
    文献依据:
    - Rathi & Hsu (2021): 0.5*Flux + 1.0*Centroid + 0.5*ZCR
    - Hecker (1974): C-V 能量比与可理解度的因果关系
    - Vurma et al. (2023): 歌声中元音+14.2dB, 清塞音仅+7.1dB
  
    权重设计:
    - Spectral Centroid (30%): Rathi & Hsu 最重要特征 (原始权重 1.0)
    - Spectral Flux (25%): Rathi & Hsu 权重 0.5 → 归一化后 25%
    - ZCR (25%): Rathi & Hsu 权重 0.5 → 归一化后 25%
    - C-V 能量比 (10%): 经典可理解度指标
    - Onset density (10%): 降权 (无文献特异性依据)
    """
    score = 0.0

    # === 1. Spectral Centroid (30%) — 最重要特征 ===
    # 文献: Rathi & Hsu 权重 1.0; 辅音时质心偏移，元音时稳定
    # 归一化: 典型歌声 centroid 500-3500 Hz → 映射到 0-30
    if spectral_centroid > 0:
        centroid_norm = spectral_centroid / 3500.0  # 归一化到 [0, 1]
        score += centroid_norm * 30.0

    # === 2. Spectral Flux (25%) — 频谱变化速率 ===
    # 文献: Rathi & Hsu 权重 0.5; 最重要的构音特征
    # 正常范围 1.0-3.0, >3.0 = 高度咬字活动 (歌手优势)
    if spectral_flux > 0:
        if spectral_flux <= 4.0:
            flux_score = spectral_flux / 4.0 * 25.0       # 0→0, 4.0→25
        elif spectral_flux <= 8.0:
            flux_score = 25.0 - (spectral_flux - 4.0) * 2  # 4→25, 8→17
        else:
            flux_score = max(10.0, 17.0 - (spectral_flux - 8.0))
        score += flux_score

    # === 3. ZCR (25%) — 辅音噪声检测 ===
    # 文献: Rathi & Hsu 权重 0.5; 擦音等高 ZCR
    # 典型值: 元音 0.02-0.08, 擦音 0.15-0.40
    if zcr_mean > 0:
        if zcr_mean >= 0.15:
            zcr_score = 25.0                                   # 清晰辅音
        elif zcr_mean >= 0.08:
            zcr_score = 15.0 + (zcr_mean - 0.08) / 0.07 * 10  # 0.08→15, 0.15→25
        else:
            zcr_score = zcr_mean / 0.08 * 15.0                 # 0→0, 0.08→15
        score += zcr_score

    # === 4. C-V 能量比 (10%) ===
    # 文献: 正常说话 ~-15dB; 歌声中不对称增长 (Vurma 2023)
    # 偏离 -15dB 过远 = 辅音被元音淹没 → 可理解度降低
    if cv_energy_ratio < 0:  # 负值正常
        deviation = abs(cv_energy_ratio - (-15.0))
        cv_score = max(0.0, 10.0 - deviation * 0.5)
        score += cv_score

    # === 5. Onset density (10%) — 降权保留 ===
    # 从原 25 权重降至 10 (无文献特异性依据)
    if 1.5 <= onset_density <= 5.0:
        score += 10.0
    elif onset_density > 0:
        dist = min(abs(onset_density - 1.5), abs(onset_density - 5.0))
        score += max(0.0, 10.0 - dist * 3.0)

    # === 6. consonant_clarity (fallback, 最多 +15 当新特征不可用时) ===
    if zcr_mean == 0.0 and spectral_centroid == 0.0:
        # 新特征不可用时的回退路径
        score = consonant_clarity * 0.50
        if 1.5 <= onset_density <= 5.0:
            score += 25.0
        elif onset_density > 0:
            dist = min(abs(onset_density - 1.5), abs(onset_density - 5.0))
            score += max(0.0, 25.0 - dist * 5.0)
        if spectral_flux > 3.0:
            penalty = min(25.0, (spectral_flux - 3.0) * 10.0)
            score -= penalty

    return max(0.0, min(100.0, score))
```

### 权重对比

| 特征              |    修改前    |  修改后  | 文献依据              |
| ----------------- | :----------: | :------: | --------------------- |
| Spectral Centroid | **0%** |   30%   | Rathi & Hsu: 权重 1.0 |
| Spectral Flux     |    扣分项    |   25%   | Rathi & Hsu: 权重 0.5 |
| ZCR               | **0%** |   25%   | Rathi & Hsu: 权重 0.5 |
| C-V 能量比        | **0%** |   10%   | Hecker 1974           |
| Onset density     |     ~33%     |   10%   | 降权 (无文献依据)     |
| Consonant clarity |     ~50%     | Fallback | 提取链路不完整        |

### ZCR/Centroid 提取成本

`librosa.feature.zero_crossing_rate(y)` + `librosa.feature.spectral_centroid(y=y, sr=sr)` — 两个函数调用，无需额外依赖，计算量 O(n)。

---

## 五、P0-3: 艺术表现无颤音 Fallback

### 问题

`_calc_vibrato()` 在 `count == 0` 时返回 0，导致无颤音歌手（流行/R&B/说唱）的艺术表现子维度固定为 0 分。

### 修改文件

[backend/domain/assessment/artistry_scorer.py](backend/domain/assessment/artistry_scorer.py)

### 当前代码 (L66-71)

```python
@staticmethod
def _calc_vibrato(quality: float, count: int) -> float:
    if count == 0:
        return 0.0   # ❌ 无颤音 → 0 分
    quality_score = quality * 0.80
    count_bonus = min(20.0, count * 2.0)
    return min(100.0, quality_score + count_bonus)
```

### 修改方案

```python
@staticmethod
def _calc_vibrato(
    quality: float,
    count: int,
    pitch_cv: float = 0.0,          # 🆕 fallback 特征
    dynamic_range: float = 15.0,    # 🆕 fallback 特征
) -> float:
    """
    颤音表现力 = vibrato_quality + 无颤音时的表现力 fallback
  
    文献: TECH_RESEARCH §2.6 — 无颤音歌手可能其他表现力强。
    流行/R&B/说唱唱法不以颤音为主要表现手段。
    """
    if count > 0:
        # 有颤音: 正常评分
        quality_score = quality * 0.80
        count_bonus = min(20.0, count * 2.0)
        return min(100.0, quality_score + count_bonus)
  
    # === 无颤音 fallback: 用音高变化 + 动态范围替代 ===
    # 原理: 表现力也可以通过音高多样性 (pitch_cv) 和动态对比 (dynamic_range) 体现
    # 上限 80 分 — 没有颤音的歌手不会得到颤音维度的满分
  
    # 音高变化 (pitch_cv): 0→0, 0.03→20, 0.10→50, 0.20→60
    if pitch_cv <= 0:
        pitch_score = 0.0
    elif pitch_cv < 0.03:
        pitch_score = pitch_cv / 0.03 * 20.0
    elif pitch_cv < 0.10:
        pitch_score = 20.0 + (pitch_cv - 0.03) / 0.07 * 30.0
    elif pitch_cv < 0.20:
        pitch_score = 50.0 + (pitch_cv - 0.10) / 0.10 * 10.0
    else:
        pitch_score = min(60.0, 60.0 - (pitch_cv - 0.20) * 50.0)
  
    # 动态范围 (dynamic_range): 0→0, 15→30, 30→40
    dynamic_score = min(40.0, dynamic_range * 1.33)
  
    return min(80.0, pitch_score + dynamic_score)
```

### Feature 输入变更

`ArtistryFeatures` 已有 `pitch_cv: float = 0.0` 字段 ([artistry_scorer.py:29](backend/domain/assessment/artistry_scorer.py#L29))，`ArtistryScorer.calculate()` 中已可用。仅需传入到 `_calc_vibrato()`。

---

## 六、P0-4: 肌肉权重调整

### 问题

肌肉力量维度 25% 权重对于纯启发式代理指标过高。文献两处独立建议降至 15%。

### 修改文件

[backend/domain/assessment/value_objects.py](backend/domain/assessment/value_objects.py)

### 当前代码

```python
class MuscleStrengthScore:
    def weighted(self) -> float:
        return self.raw_score * 0.25   # → 15%
```

### 修改方案

```python
class MuscleStrengthScore:
    def weighted(self) -> float:
        return self.raw_score * 0.15   # 25% → 15%
```

### 释放的 10% 权重重新分配

| 维度           |     修改前     |     修改后     | 理由                                    |
| -------------- | :------------: | :------------: | --------------------------------------- |
| Pitch          |      10%      | **13%** | 最可靠维度 (文献 A 级)                  |
| Rhythm         |      10%      | **12%** | 中等可靠 (文献 B 级)                    |
| Breath         |      20%      | **22%** | 四子维度丰富，提升气息权重              |
| Technique      |      25%      | **25%** | 保持不变 (P0-1 + P0-2 已修复结构性缺陷) |
| Muscle         | **25%** | **15%** | 文献建议                                |
| Artistry       |      10%      | **13%** | 提升以激励 P0-3 修复的效果              |
| **合计** | **100%** | **100%** | ✅                                      |

### 对应修改

```python
class PitchScore:
    def weighted(self) -> float:
        return self.raw_score * 0.13   # 0.10 → 0.13

class RhythmScore:
    def weighted(self) -> float:
        return self.raw_score * 0.12   # 0.10 → 0.12

class BreathScore:
    def weighted(self) -> float:
        return self.raw_score * 0.22   # 0.20 → 0.22

class ArtistryScore:
    def weighted(self) -> float:
        return self.raw_score * 0.13   # 0.10 → 0.13
```

---

## 七、P1-1: 肌肉力量五维代理重构

### 文献驱动的身体力量代理指标

基于 [身体肌肉力量文献](C:\Users\jack\Desktop\临时文件\声乐\参考论文\05-身体肌肉力量\research-summary.md) §2.1 特征矩阵:

| # | 特征                          | 代理的身体功能    |            文献验证            | 当前状态 |
| - | ----------------------------- | ----------------- | :-----------------------------: | :------: |
| 1 | **MPT (最长发声时间)**  | 呼吸肌耐力        | 训练效应+33%, FVC/FEV1/PEF 验证 |    ❌    |
| 2 | **RMS 衰减率**          | 膈肌/腹部稳态压力 |         保持 (当前实现)         |    ✅    |
| 3 | **Crest Factor**        | 声音投射力        |        典型人声 10-14dB        |    ❌    |
| 4 | **SPR (2-4kHz/0-2kHz)** | 声门内收+投射     |          训练歌手更高          |    ❌    |
| 5 | **动态范围**            | 腹肌强度调制      |   古典 20-40dB, 流行 10-25dB   |    ✅    |

### 文献驱动的面部力量代理指标

基于 [面部肌肉力量文献](C:\Users\jack\Desktop\临时文件\声乐\参考论文\04-面部肌肉力量\research-summary.md) §2.1-2.5:

| # | 特征                         | 代理的面部功能    |             文献验证             | 当前状态 |
| - | ---------------------------- | ----------------- | :------------------------------: | :------: |
| 1 | **歌手共振峰能量**     | 咽部扩大+面罩共鸣 |           多项研究验证           |    ✅    |
| 2 | **F1-F2 元音空间面积** | 下颌+唇部运动范围 |           MRI R²=0.96           |    ❌    |
| 3 | **泛音丰富度**         | 面部微调共鸣      |         保持 (当前实现)         |    ✅    |
| 4 | **Alpha Ratio**        | 发声努力程度      |  -10~-30dB, 流行 vs 歌剧差异大  |    ❌    |
| 5 | **频谱倾斜**           | 声门内收努力      | -6dB/oct(紧张) ~ -18dB/oct(放松) |    ❌    |

### 修改范围

涉及 3 个文件的级联修改:

```
MuscleFeatures (新增字段)
  → LibrosaMuscleExtractor (新增提取逻辑)
    → MuscleStrengthScorer (新增评分映射)
```

### MPT 提取方法

```python
def extract_mpt(y: np.ndarray, sr: int, 
                silence_threshold_db: float = -40.0,
                min_duration_s: float = 0.5) -> float:
    """
    提取最长发声时间 (Maximum Phonation Time)
  
    文献: 身体肌肉文献 §2.1
    - < 5s: 差 (呼吸肌耐力不足)
    - 5-10s: 一般
    - 10-15s: 良好
    - > 15s: 优秀
  
    方法: 检测连续高于阈值的 RMS 段，取最长段持续时间。
    """
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512).flatten()
    rms_db = 20 * np.log10(rms + 1e-10)
  
    # 找到连续高能量段
    active = rms_db > silence_threshold_db
    if not np.any(active):
        return 0.0
  
    # 计算连续段的长度
    edges = np.diff(np.concatenate([[False], active, [False]]).astype(int))
    starts = np.where(edges == 1)[0]
    ends = np.where(edges == -1)[0]
    durations = (ends - starts) * 512 / sr  # hop_length=512
  
    # 过滤过短段
    valid = durations >= min_duration_s
    if not np.any(valid):
        return 0.0
  
    return float(np.max(durations[valid]))
```

### 详细实施参见代码修改 PR，此处仅记录算法规格。

---

## 八、P1-2: 音色八维剖面增强

### 问题

1. **门控失效**: 无 audiofeat 时音色始终为零 (C2)
2. **维度不全**: 仅 3-4 维 vs timbral_models 8 维 (M4)
3. **特征粗糙**: 启发式路径使用 spectral_centroid_deviation (非直接测量)

### 修改方案

#### 8.1 修复门控失效 (P0 级别)

在 [timbre_extractor.py:43](backend/domain/audio/timbre_extractor.py#L43) 中，当旧 CPP 不可靠时使用替代置信度:

```python
# 修改前:
cluster_purity = clamp(cpp / 6.0)

# 修改后:
# CPP 区分度检测: 如果 CPP 在极窄范围内 (旧 CPP 特征)，使用替代门控
cpp_mean_val = float(getattr(acoustic, 'cpp', 1.0) or 1.0)
if 0.01 < cpp_mean_val < 0.05:
    # 旧 CPP 无区分度 → 用 harmonic_stability 作为替代门控
    # harmonic_stability 来自 BreathFeatures，是 breath 评分的一部分
    cluster_purity = clamp(harmonic_stability / 100.0)
else:
    # 有效 CPP (audiofeat 或其他来源)
    cluster_purity = clamp(cpp_mean_val / 6.0)
```

#### 8.2 八维音色剖面

| 维度                   | 声学基础              | 文献 r/准确率 | 提取方式                      |
| ---------------------- | --------------------- | :------------: | ----------------------------- |
| **Brightness**   | Spectral Centroid     |    r=0.967    | audiofeat centroid            |
| **Warmth**       | Bass Ratio + Richness |     中-高     | audiofeat richness + centroid |
| **Hardness** 🆕  | 2-5kHz 能量比         | timbral_models | audiofeat spectral crest      |
| **Depth** 🆕     | 30-200Hz 突出度       | timbral_models | 低频能量比                    |
| **Roughness**    | 16-80Hz 幅度调制      |       中       | audiofeat roughness           |
| **Nasality**     | std0-1K + 反共振峰    |    ~90% SVM    | audiofeat nasality            |
| **Sharpness** 🆕 | 高频能量集中度        | timbral_models | centroid / 4000               |
| **Booming** 🆕   | 低频共鸣+歌手共振峰   | timbral_models | low_freq × 0.6 + SF × 0.4   |

等权融合 (各 12.5%)，替代当前 25%/25%/25%/25% 或 30%/30%/40%。

---

## 九、P2: 中长期演进

### 9.1 ABI 9 参数模型

基于 Barsties v. Latoszek (2017)，将 9 个声学参数组合为单一气息感指数:
CPPS + Jitter + GNE + 高频噪声(6kHz) + HNR + H1-H2 + Shimmer + Period SD
→ 分数 0-10，AUC=0.94，跨 4 种语言验证。

### 9.2 艺术表现根本性重构

当前区分度仅 1.9 分 (高低分 82.1 vs 81.2)，需考虑:

- SongEval (A 级) 5 维美学评分中的 Musicality 维度
- QwenFeat-Vocal-Score (B 级) 4 维美学评分

### 9.3 歌声特定数据标注

**最大长期瓶颈**: CPPS/GNE/ABI 全部在病理语音上验证，歌声仅 n=2 试点。收集 100+ 歌声气声/咬字/音色标注数据是突破理论天花板的关键。

---

## 十、实施路线图

### Phase A: P0 修复 ✅ 已完成 (2026-07-28)

```
✅ P0-1: 气声比 HNR→CPPS 权重修正 — technique_scorer.py
✅ P0-2: 咬字 ZCR + Spectral Centroid + C-V — technique_scorer.py + technique_extractor.py
✅ P0-3: 无颤音 fallback — artistry_scorer.py
✅ P0-4: 权重调整 (6 个 weighted()) — value_objects.py
```

### Phase B: P1 增强 ✅ 已完成 (2026-07-29)

```
✅ P1-1: 肌肉五维代理重构 — muscle_scorer.py + muscle_extractor.py
✅ P1-2a: 音色门控修复 (双源置信度) — timbre_extractor.py + timbre_adjuster.py
✅ P1-2b: 音色八维剖面增强 (hardness/depth/sharpness/booming) — timbre_adjuster.py (v7.5)
```

### Phase B2: P0 评分异常修复 ✅ 已完成 (2026-07-29)

基于真实音频评分的深度分析 + 12 篇新增文献交叉验证:

```
✅ P0-1: Artistry pitch_cv Bug — 15% 权重完全失效 — ddd_feature_orchestrator.py + artistry_extractor.py
✅ P0-2: Technique HNR>22 惩罚 — 语音阈值不适用于歌声 — technique_scorer.py
✅ P0-3: CPPS-HF 非单调解耦 — 实谱 HF 替代 cpp/5.0 — technique_extractor.py
✅ P0-4: Muscle formant/overtone 校准 — 阈值适配实际输入范围 — muscle_scorer.py
```

新增文献:
- Buckley, Abur & Stepp (2023): 歌声 CPPS 规范值 (持续元音 13-18dB, 连续语音 6-11dB)
- Titze et al. (2024): F0 对 CPPS 的巨大非线性影响, H1 幅度对 CPPS 无显著影响
- Toles et al. (2020): 歌声 H1-H2 自然为 9.7dB (语音 4.2dB)
- Liu et al. (2025): MFCC1 (spectral tilt) 是 strain 最佳单特征判别器 (86.1%)
- Kondo, Kondoh & Fujii (2025): SPR 是唯一显著预测总评分的声学特征
- Bruder, Poeppel & Larrouy-Maestri (2024): 声学特征仅解释 r²=0.016-0.025 歌声偏好

### Phase C: P2 演进 (按需)

```
- ABI 9 参数模型 (新文件 services/features/abi.py)
- 艺术表现 SongEval 集成
- 歌声标注数据收集计划
```

### 测试策略

| Phase | 修改文件数 | 影响测试               | 策略                                                         |
| ----- | :--------: | ---------------------- | ------------------------------------------------------------ |
| A     |     4     | ~140 (DDD 领域 + 基建) | 先运行受影响测试，确保 GREEN → 修改 → 验证回归 → 更新基线 |
| B     |     6     | ~160                   | 同上 + 新增 MPT/Crest/SPR 单元测试                           |
| C     |    3-4    | 按需                   | TDD 新功能                                                   |

### 风险与缓解

| 风险                           | 影响                   | 缓解                                         |
| ------------------------------ | ---------------------- | -------------------------------------------- |
| P0-1/2 改变 Technique 分数分布 | 总分可能偏移 ±5-10 分 | 运行真实音频回归套件，更新 BASELINE          |
| 权重调整改变总分               | 历史记录不可比         | CHANGELOG + 版本标记 (v7.4 scoring formula)  |
| CPPS/ZCR 在新特征链路中缺失    | 回退到旧路径           | 保留 fallback 逻辑 (CPPS 不可用 → HNR 回退) |
| 门控修复后音色非零             | 可能产生不一致的 ±分  | 先小范围测试，验证 MFCC 纯度替代门控的有效性 |

---

## 附录: 参考文献速查

| 简称                         | 完整引用                                                                               |  影响维度  |
| ---------------------------- | -------------------------------------------------------------------------------------- | :---------: |
| Samlan & Story 2013          | "Relation of perceived breathiness to laryngeal kinematics" — CPP 解释 86.7% 气息方差 |   气声比   |
| Rathi & Hsu 2021             | "A Pilot Study for Algorithmic Diction Detection" — ZCR+Flux+Centroid 咬字检测        |    咬字    |
| Barsties v. Latoszek 2017    | "The Acoustic Breathiness Index" — ABI 9 参数 AUC=0.94                                |   气声比   |
| Barsties v. Latoszek 2023    | "Advances in Clinical Voice Quality Analysis with VOXplot" — GNE & CPPS 最强          |   气声比   |
| Michaelis et al. 1997        | "GNE — a New Measure" — GNE AROC=0.886                                               |   气声比   |
| Hecker 1974                  | "C-V Ratio and Speaker Intelligibility"                                                |    咬字    |
| Sundberg 1987                | "The Science of the Singing Voice" — 频谱倾斜/歌手共振峰                              | 气声比/面部 |
| Titze 1994                   | "Principles of Voice Production" — 发声物理建模                                       |   跨维度   |
| de Cheveigne & Kawahara 2002 | "YIN, a fundamental frequency estimator" — YIN 误差特性                               |    音准    |
| Wager et al. 2022            | pitch-benchmark — MAE 指数衰减                                                        |    音准    |
| Cao et al. 2008              | RPA/RCA 音准指标                                                                       |    音准    |
| Griffin et al. 1995          | "Physiological characteristics of the supported singing voice"                         |  身体肌肉  |
| Thorpe et al. 2001           | "Patterns of breath support in projection of the singing voice"                        |  身体肌肉  |
| McQuade 2016                 | Zygomaticus-resonance correlation (94.2% cases)                                        |  面部肌肉  |
| Aura et al. 2019             | Singer's expression mechanism (nasal dilation → pharyngeal)                           |  面部肌肉  |
| 2025 RCT                     | "Effect of Core Stabilization Exercises on Acoustic Properties" (n=27)                 |  身体肌肉  |
| Bohm et al. 2017             | DTW+acoustic fusion r=0.87 vs pure DTW 0.52                                            |  DTW 架构  |
| Santos & Masiero 2026        | "A Survey on 30+ Years of Automatic Singing Assessment"                                |    综述    |
