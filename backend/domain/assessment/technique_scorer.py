"""
发声技术评分器 v7.0 — 重构: 咬字清晰度(50%) + 气声比(50%)

v6.3 旧版: HNR(40%) + CPP(30%) + technique(30%)
v7.0 新版: 拆分为两个独立子维度，每个基于可测量的声学特征
v7.3: audiofeat 增强 — Jitter/Shimmer/Closed Quotient 用于精化技术评分
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

from backend.domain.assessment.value_objects import TechniqueScore

if TYPE_CHECKING:
    from backend.domain.audio.audiofeat_extractor import AudiofeatFeatures


@dataclass(frozen=True)
class TechniqueFeatures:
    """发声技术特征输入 (不可变)"""
    onset_density: float = 0.0       # onsets/second, 正常范围 1.5-5.0
    spectral_flux: float = 0.0       # 频谱变化率, 正常 < 3.0
    consonant_clarity: float = 0.0   # 辅音清晰度 0-100
    hnr_mean: float = 15.0           # 谐波噪声比 dB
    spectral_tilt: float = 0.0       # 频谱倾斜 (-10到+5, 负值=气声)
    hf_energy_ratio: float = 0.5     # >2kHz 能量占比
    cpp_mean: float = 1.0            # 声门闭合周期峰值
    vibrato_quality: float = 0.0     # v7.1.3: 颤音质量 0-100 (来自 TechniqueAnalyzer)
    vibrato_rate_avg: float = 5.0    # v7.1.3: 平均颤音速率 Hz (来自 TechniqueAnalyzer)
    # v7.4: 咬字清晰度增强 (Rathi & Hsu 2021)
    zcr_mean: float = 0.0            # 过零率均值 (0.02-0.08 元音, 0.15-0.40 擦音)
    spectral_centroid: float = 0.0   # 频谱质心 Hz (500-3500 典型歌声)
    cv_energy_ratio: float = -15.0   # C-V 能量比 dB (典型 -15dB, Hecker 1974)
    # v7.6: 起音斜率
    attack_slope: float = 0.0         # 起音速率 0-100 (越高越清晰/有投射力)
    # v7.17: 混音/分离标记 — 决定 HNR/CPP 是否需混音污染补偿 (A2)
    is_clean_vocal: bool = False


class TechniqueScorer:
    """发声技术评分器 — 纯计算, 零副作用

    v7.3: 可选 audiofeat 参数增强评分精度:
      - Jitter (频率微扰): 咬字稳定性
      - Shimmer (幅度微扰): 振幅控制
      - Closed Quotient (声门闭合商): 发声效率
    """

    # ---- audiofeat 阈值 (v7.3) ----
    JITTER_EXCELLENT = 0.5     # < 0.5% = 极稳定
    JITTER_HIGH = 3.0           # > 3% = 不稳定 (病理)
    SHIMMER_EXCELLENT = 0.1     # < 0.1 dB = 极稳定
    SHIMMER_HIGH = 0.5          # > 0.5 dB = 不稳定
    CQ_OPTIMAL_LOW = 0.4        # 最优闭合商下限
    CQ_OPTIMAL_HIGH = 0.6       # 最优闭合商上限
    CQ_LOW = 0.2                # < 0.2 = 闭合不足

    JITTER_BONUS = 5.0          # 极稳定加分
    JITTER_PENALTY = 10.0       # 不稳定扣分
    SHIMMER_BONUS = 3.0         # 极稳定加分
    SHIMMER_PENALTY = 5.0       # 不稳定扣分
    CQ_BONUS = 3.0              # 高效发声加分
    CQ_PENALTY = 5.0            # 闭合不足扣分

    # ---- GNE 阈值 (v7.8) ----
    # GNE: 声门-噪声激励比, AROC=0.886 为最强气声判别指标 (Michaelis 1997)
    GNE_QUALITY_THRESHOLD = 0.8  # > 0.8 = 优秀声门控制, 气声极少
    GNE_LEAK_THRESHOLD = 0.4     # < 0.4 = 噪声主导, 不可控漏气
    GNE_QUALITY_BONUS = 5.0      # 优秀声门控制最大加分
    GNE_LEAK_PENALTY = 8.0       # 不可控漏气最大扣分

    def calculate(
        self,
        features: TechniqueFeatures,
        audiofeat: 'AudiofeatFeatures | None' = None,
    ) -> TechniqueScore:
        # 1. 咬字清晰度 (50%)
        articulation = self._calc_articulation(
            features.onset_density,
            features.spectral_flux,
            features.consonant_clarity,
            features.zcr_mean,            # v7.4: Rathi & Hsu 2021
            features.spectral_centroid,    # v7.4: Rathi & Hsu 2021
            features.cv_energy_ratio,      # v7.4: Hecker 1974
            features.attack_slope,         # v7.6: 起音斜率
        )

        # 2. 气声比 (50%)
        breath_voice = self._calc_breath_voice_ratio(
            features.hnr_mean,
            features.spectral_tilt,
            features.hf_energy_ratio,
            features.cpp_mean,  # v7.4: CPPS 作为主特征
            is_clean_vocal=features.is_clean_vocal,  # v7.17 A2: 混音污染补偿
        )

        # 3. v7.3: audiofeat 增强微调
        if audiofeat is not None:
            articulation, breath_voice = self._apply_audiofeat_enhancement(
                articulation, breath_voice, audiofeat,
            )

        # 加权合成
        score = articulation * 0.50 + breath_voice * 0.50
        score = max(0.0, min(100.0, score))

        diagnosis: list[str] = []
        if articulation < 40:
            diagnosis.append("咬字清晰度偏低")
        if breath_voice < 40:
            diagnosis.append("气声比失衡")

        return TechniqueScore(
            raw_score=round(score, 1),
            articulation_clarity=round(articulation, 1),
            breath_voice_ratio=round(breath_voice, 1),
            hnr_mean=features.hnr_mean,
            cpp_mean=features.cpp_mean,
            diagnosis=tuple(diagnosis),
        )

    def _apply_audiofeat_enhancement(
        self,
        articulation: float,
        breath_voice: float,
        af: 'AudiofeatFeatures',
    ) -> tuple[float, float]:
        """v7.3: audiofeat 增强 — Jitter/Shimmer/CQ/GNE 微调子维度分数

        v7.8: 新增 GNE (声门-噪声激励比) 增强, AROC=0.886 为最强气声判别指标
        """
        jitter = af.jitter_local
        shimmer = af.shimmer_db
        cq = af.closed_quotient
        gne = af.gne_mean

        # v7.17 A3 垃圾值守卫: 越界物理范围视为无数据 (实测 audiofeat 对 MP3 输出
        # jitter=-263175 类异常值; 物理范围: jitter 0-10%, shimmer 0-5dB, cq 0-1, gne 0-1)
        if not (0.0 < jitter <= 10.0):
            jitter = 0.0
        if not (0.0 < shimmer <= 5.0):
            shimmer = 0.0
        if not (0.0 < cq <= 1.0):
            cq = 0.0
        if not (0.0 < gne <= 1.0):
            gne = 0.0

        # 所有值为 0 (默认/不可用) → 无增强
        if jitter == 0.0 and shimmer == 0.0 and cq == 0.0 and gne == 0.0:
            return articulation, breath_voice

        # Jitter: 频率稳定性 → 影响咬字清晰度
        # (v7.17 A3: 保留 >0 守卫 — 越界归零的 jitter 视为无数据, 不得触发加分)
        if 0.0 < jitter < self.JITTER_EXCELLENT:
            articulation = min(100.0, articulation + self.JITTER_BONUS)
        elif jitter > self.JITTER_HIGH:
            articulation = max(0.0, articulation - self.JITTER_PENALTY)

        # Shimmer: 振幅稳定性 → 影响气声比
        if shimmer > 0 and shimmer < self.SHIMMER_EXCELLENT:
            breath_voice = min(100.0, breath_voice + self.SHIMMER_BONUS)
        elif shimmer > self.SHIMMER_HIGH:
            breath_voice = max(0.0, breath_voice - self.SHIMMER_PENALTY)

        # Closed Quotient: 声门闭合效率 → 影响气声比
        if cq > 0:
            if self.CQ_OPTIMAL_LOW <= cq <= self.CQ_OPTIMAL_HIGH:
                breath_voice = min(100.0, breath_voice + self.CQ_BONUS)
            elif cq < self.CQ_LOW:
                breath_voice = max(0.0, breath_voice - self.CQ_PENALTY)

        # GNE: 声门-噪声激励比 → 影响气声比 (AROC=0.886, Michaelis 1997)
        # 阈值沿用 BreathScorer (0.4/0.8); 条件略宽: 气声比子维度对 GNE 单指标即可
        # 触发 (BreathScorer 需 GNE+HNR 双确认, 见 breath_scorer.py)
        if gne > 0:
            if gne < self.GNE_LEAK_THRESHOLD:
                # 不可控漏气: 线性惩罚, GNE 越低扣分越多
                leak_factor = (self.GNE_LEAK_THRESHOLD - gne) / self.GNE_LEAK_THRESHOLD
                breath_voice = max(0.0, breath_voice - leak_factor * self.GNE_LEAK_PENALTY)
            elif gne > self.GNE_QUALITY_THRESHOLD:
                # 优秀声门控制: 线性加分, GNE 越高加分越多
                quality_factor = (gne - self.GNE_QUALITY_THRESHOLD) / (1.0 - self.GNE_QUALITY_THRESHOLD)
                breath_voice = min(100.0, breath_voice + quality_factor * self.GNE_QUALITY_BONUS)

        return articulation, breath_voice

    @staticmethod
    def _calc_articulation(
        onset_density: float,
        spectral_flux: float,
        consonant_clarity: float,
        zcr_mean: float = 0.0,            # v7.4: Rathi & Hsu 2021
        spectral_centroid: float = 0.0,    # v7.4: Rathi & Hsu 2021
        cv_energy_ratio: float = -15.0,    # v7.4: Hecker 1974
        attack_slope: float = 0.0,         # v7.6: 起音斜率
    ) -> float:
        """咬字清晰度 = 文献驱动加权融合

        文献依据:
        - Rathi & Hsu (2021): 0.5*Flux + 1.0*Centroid + 0.5*ZCR
        - Hecker (1974): C-V 能量比与可理解度的因果关系
        - Sundberg (1987): 起音斜率反映投射力和清晰度

        权重设计 (v7.6, 文献对齐 Rathi & Hsu 2021):
        - Spectral Centroid (30%): 文献权重 1.0 (2× flux/zcr)
        - Spectral Flux (15%): 文献权重 0.5
        - ZCR (15%): 文献权重 0.5
        - Attack slope (15%): 起音质量 (Sundberg 1987)
        - C-V 能量比 (10%): 经典可理解度指标 (Hecker 1974)
        - Onset density (10%): 降权保留
        - Consonant clarity (fallback): 新特征缺失时回退
        """
        # 检查新特征是否可用
        has_new_features = zcr_mean > 0 or spectral_centroid > 0

        if has_new_features:
            score = 0.0

            # === 1. Spectral Centroid (30%) — 文献权重 1.0, 最重要 ===
            # v7.17: 参考 3500→2000 Hz — 实测高分真实音频 centroid 1160-1760 Hz (典型歌声),
            # 旧参考使典型歌声仅得 ~12/30。新参考: 1355Hz→20.3/30, 1760Hz→26.4/30。
            if spectral_centroid > 0:
                centroid_norm = min(1.0, spectral_centroid / 2000.0)
                score += centroid_norm * 30.0

            # === 2. Spectral Flux (15%) — 文献权重 0.5 ===
            if spectral_flux > 0:
                if spectral_flux <= 4.0:
                    flux_score = spectral_flux / 4.0 * 15.0
                elif spectral_flux <= 8.0:
                    flux_score = 15.0 - (spectral_flux - 4.0) * 2.0
                else:
                    flux_score = max(7.0, 7.0 - (spectral_flux - 8.0))
                score += flux_score

            # === 3. ZCR (15%) — 文献权重 0.5 ===
            # v7.17: 曲线上移 — 实测高分音频 zcr 0.066-0.099, 旧曲线 0.08 以下仅 ~7/15
            if zcr_mean > 0:
                if zcr_mean >= 0.12:
                    zcr_score = 15.0
                elif zcr_mean >= 0.06:
                    zcr_score = 9.0 + (zcr_mean - 0.06) / 0.06 * 6.0   # 0.06→9, 0.12→15
                elif zcr_mean >= 0.03:
                    zcr_score = 4.0 + (zcr_mean - 0.03) / 0.03 * 5.0   # 0.03→4, 0.06→9
                else:
                    zcr_score = zcr_mean / 0.03 * 4.0
                score += zcr_score

            # === 4. Attack slope (15%) — v7.6: 起音质量 ===
            if attack_slope > 0:
                score += attack_slope * 0.15

            # === 5. C-V 能量比 (10%) ===
            # v7.17: 斜率 0.5→0.3 — 实测高分音频 cv_ratio -8~-10 (接近典型 -15), 旧曲线
            # 给 7.5-8.5, 新曲线给 8-9.5 (C-V 区分度弱, 软化惩罚)
            if cv_energy_ratio < 0:
                deviation = abs(cv_energy_ratio - (-15.0))
                cv_score = max(0.0, 10.0 - deviation * 0.3)
                score += cv_score

            # === 6. Onset density (10%) — 降权保留 ===
            if 1.5 <= onset_density <= 5.0:
                score += 10.0
            elif onset_density > 0:
                dist = min(abs(onset_density - 1.5), abs(onset_density - 5.0))
                score += max(0.0, 10.0 - dist * 3.0)

            return max(0.0, min(100.0, score))

        # === Fallback: 新特征不可用时的回退路径 (保持向后兼容) ===
        score = 0.0

        # consonant_clarity: 0→0, 100→50
        score += consonant_clarity * 0.50

        # onset_density: 1.5-5.0 → +25, outside → linear decay
        if 1.5 <= onset_density <= 5.0:
            score += 25.0
        elif onset_density > 0:
            dist = min(abs(onset_density - 1.5), abs(onset_density - 5.0))
            score += max(0.0, 25.0 - dist * 5.0)

        # spectral_flux 扣分: flux > 3.0 → penalty
        if spectral_flux > 3.0:
            penalty = min(25.0, (spectral_flux - 3.0) * 10.0)
            score -= penalty

        return max(0.0, min(100.0, score))

    @staticmethod
    def _calc_breath_voice_ratio(
        hnr_mean: float,
        spectral_tilt: float,
        hf_energy_ratio: float,
        cpp_mean: float = 1.0,  # v7.4: CPPS 主特征 (40%), 文献 Samlan & Story 2013
        is_clean_vocal: bool = False,  # v7.17 A2: 混音污染补偿
    ) -> float:
        """气声比 = f(CPPS主40%, HNR辅25%, spectral_tilt 20%, hf_energy 15%)

        文献依据:
        - CPPS: 单独解释 86.7% 感知气息感方差 (Samlan & Story 2013)
        - HNR: 通用嗓音质量 r~0.78, 但气声特异度低 r=-0.56 (Barsties 2023)
        - Spectral tilt: 区分可控气声 vs 不可控漏气 (Sundberg 1987)

        v7.17 结构调整: ① 撤销 v7.17 A2 的 +8/+1.5 混音偏移 — 实测 Demucs 分离
        人声 HNR 仍 ~8dB (与混音相近), 该偏移假设("HNR 被伴奏压低")不成立,
        歌手本身即低 HNR。② spectral_tilt + hf_energy 从"只罚不奖"改为质量组件
        (干净→满分, 气声→递减) — 修复"气声比结构性封顶 65"缺陷 (旧实现 tilt/hf
        仅扣分, 完美人声也封顶 40+25=65, 不合理)。
        """
        score = 0.0

        # === 1. CPPS (40%) — 主特征 ===
        # v7.6: 阈值重标定 — 声学 CPP ×100 后范围 ~3-10 (原始 0.04-0.10)
        # 文献: Buckley et al. 2023 — 歌声 CPPS 持续元音 13-18dB
        #       (acoustic CPP ×100 ≈ 4-10 对应基本音质, 不同于 audiofeat CPPS dB)
        # v7.17: 分段上移 (9→8 满分), 5-6 斜率更陡 — 实测高分音频 cpp 5.5-7.3
        if cpp_mean > 0:
            if cpp_mean >= 8.0:
                score += 40.0                                          # 优秀
            elif cpp_mean >= 6.0:
                score += 30.0 + (cpp_mean - 6.0) / 2.0 * 10.0         # 6→30, 8→40
            elif cpp_mean >= 5.0:
                score += 20.0 + (cpp_mean - 5.0) * 10.0               # 5→20, 6→30
            elif cpp_mean >= 3.0:
                score += 10.0 + (cpp_mean - 3.0) / 2.0 * 10.0         # 3→10, 5→20
            else:
                score += max(0.0, cpp_mean / 3.0 * 10.0)              # 0→0, 3→10

        # === 2. HNR (25% CPPS 可用时 / 45% fallback) — 辅助验证 ===
        # v7.6: 歌声特定 HNR 阈值 (文献 Buckley 2023: 歌声 HNR 典型 25-35dB)
        # v7.17: 阈值下移 — 实测真实音频 (MP3 压缩/混响) librosa HNR 仅 2.8-8.3dB
        #       (librosa 自相关 HNR 在压缩/混响录制下系统性低估; 分离人声亦 ~8dB)。
        #       故 hnr 8 ≈ 良好 (18/25), hnr 14+ ≈ 满分。
        if cpp_mean > 0:
            hnr_weight = 25.0  # CPPS 可用时，HNR 为辅助
        else:
            hnr_weight = 45.0  # CPPS 不可用时，HNR 提升为 fallback

        if hnr_mean >= 14.0:
            score += hnr_weight                                        # ≥14 → 满分
        elif hnr_mean >= 8.0:
            score += hnr_weight * (0.72 + (hnr_mean - 8.0) / 6.0 * 0.28)  # 8→72%, 14→100%
        elif hnr_mean >= 4.0:
            score += hnr_weight * (0.40 + (hnr_mean - 4.0) / 4.0 * 0.32)  # 4→40%, 8→72%
        elif hnr_mean > 0:
            score += hnr_weight * (hnr_mean / 4.0 * 0.40)                 # 0→0%, 4→40%

        # === 3. Spectral tilt (20%) — 质量组件 (v7.17: 旧为只罚不奖) ===
        # 文献: 气息音 H1-H2 = +2.08dB, 正常 = -0.60dB, 紧压 = -1.63dB (Sundberg 1987)
        # 干净 (tilt ≥ -4) → 满分; 强负 (气声) → 递减。实测真实歌曲 tilt 典型 -5~-7。
        if spectral_tilt >= -4.0:
            score += 20.0
        elif spectral_tilt >= -10.0:
            score += 20.0 + (spectral_tilt + 4.0) / 6.0 * 15.0   # -4→20, -10→5
        else:
            score += max(0.0, 5.0 + (spectral_tilt + 10.0) / 10.0 * 5.0)  # -10→5, -20→0

        # === 4. HF energy (15%) — 质量组件 (v7.17: 旧为只罚不奖) ===
        # 气声产生额外高频噪声 (>5kHz); 低 hf = 干净 → 满分, 高 hf = 气声噪声 → 递减
        if hf_energy_ratio <= 0.40:
            score += 15.0
        elif hf_energy_ratio <= 0.80:
            score += 15.0 - (hf_energy_ratio - 0.40) / 0.40 * 15.0  # 0.4→15, 0.8→0
        # hf > 0.8 → 0

        return max(0.0, min(100.0, score))
