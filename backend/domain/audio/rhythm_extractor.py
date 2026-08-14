"""
节奏特征提取器 — v7.1.3 自包含版

v7.1.3: 内移 RhythmAnalyzer._calculate_rhythm_traditional 算法,
移除对 services/features/rhythm.py 的依赖。算法逐位一致。

算法: onset 密度 + 间隔变异系数 (CV) + 不规则段检测。
适用: 无伴奏独唱、弹性速度、非西方节奏体系、传统流行乐。
"""
from __future__ import annotations
import logging
import numpy as np

from backend.domain.assessment.rhythm_scorer import RhythmFeatures

logger = logging.getLogger(__name__)

_RHYTHM_SR = 22050  # resample target for onset detection
_VOICE_FMIN, _VOICE_FMAX = 65.0, 1047.0


class LibrosaRhythmExtractor:
    """节奏特征提取器 — Level 1, v7.1.3 算法自包含"""

    def __init__(self, sample_rate: int = 22050, hop_length: int = 512):
        self.sample_rate = sample_rate
        self.hop_length = hop_length

    def extract(
        self,
        y: np.ndarray,
        sr: int,
        f0: np.ndarray | None = None,
        voiced_flags: np.ndarray | None = None,
        is_clean_vocal: bool = False,
        accompaniment: np.ndarray | None = None,
        accompaniment_sr: int | None = None,
    ) -> RhythmFeatures:
        """提取节奏特征 —— v7.1.3 内移自 RhythmAnalyzer, pitch-based + traditional 双路径。

        v7.17: 可选节拍锚定路径 — 传伴奏轨 (分离后) 时, 用伴奏节拍作基准 + 人声 vocal onset,
        测歌手音符对节拍的偏差 (修复 pro 分离后 rhythm 崩坍)。伴奏不可用则回退混音路径。
        """
        try:
            import librosa

            # v7.17: 节拍锚定路径 (pro 分离模式, 伴奏轨可用)
            if accompaniment is not None and accompaniment_sr:
                anchored = self._extract_beat_anchored(y, sr, accompaniment, accompaniment_sr)
                if anchored is not None:
                    return anchored
                logger.debug("Beat-anchored rhythm unavailable, falling back to mixed path")

            # Resample to 22kHz for better onset detection
            if sr != _RHYTHM_SR:
                audio_data = librosa.resample(y, orig_sr=sr, target_sr=_RHYTHM_SR)
                eff_sr = _RHYTHM_SR
            else:
                audio_data = y
                eff_sr = sr

            total_duration = len(audio_data) / eff_sr

            # Long audio: segment-based analysis (60s windows, 30s overlap)
            segment_dur = 60.0
            segment_hop = 30.0

            if total_duration > segment_dur * 1.5:
                segment_cvs = []
                segment_devs = []
                total_onsets = 0
                total_off_beat = 0
                max_bps = 0.0

                for start_t in np.arange(0, total_duration - segment_dur, segment_hop):
                    end_t = min(start_t + segment_dur, total_duration)
                    start_sample = int(start_t * eff_sr)
                    end_sample = int(end_t * eff_sr)
                    segment = audio_data[start_sample:end_sample]

                    if len(segment) < eff_sr * 3:
                        continue

                    seg_onset_env = librosa.onset.onset_strength(
                        y=segment, sr=eff_sr, hop_length=self.hop_length,
                    )
                    seg_onset_frames = librosa.onset.onset_detect(
                        onset_envelope=seg_onset_env, sr=eff_sr, hop_length=self.hop_length,
                    )

                    if len(seg_onset_frames) < 3:
                        continue

                    seg_times = librosa.frames_to_time(
                        seg_onset_frames, sr=eff_sr, hop_length=self.hop_length,
                    )
                    seg_ioi = np.diff(seg_times)
                    seg_mean = np.mean(seg_ioi)
                    if seg_mean > 0:
                        seg_cv = float(np.std(seg_ioi) / seg_mean)
                        segment_cvs.append(seg_cv)
                        segment_devs.append(_cv_to_deviation(seg_cv, is_clean_vocal))
                        total_onsets += len(seg_onset_frames)
                        total_off_beat += _count_irregular_segments(seg_ioi, seg_mean)
                        seg_bps = (
                            len(seg_onset_frames) / (seg_times[-1] - seg_times[0])
                            if seg_times[-1] > seg_times[0] else 0.0
                        )
                        max_bps = max(max_bps, seg_bps)

                if segment_cvs:
                    irregularity = float(np.median(segment_cvs))
                    avg_deviation_ratio = float(np.median(segment_devs))
                    onset_count = total_onsets
                    beats_per_second = max_bps
                    off_beat_segments = total_off_beat
                    return RhythmFeatures(
                        avg_deviation_ratio=round(avg_deviation_ratio, 4),
                        irregularity=round(irregularity, 4),
                        onset_density=max(0.5, round(beats_per_second, 2)),
                        onset_count=int(onset_count),
                        off_beat_segments=int(off_beat_segments),
                        is_clean_vocal=is_clean_vocal,
                    )

            # Short audio: direct analysis
            onset_env = librosa.onset.onset_strength(
                y=audio_data, sr=eff_sr, hop_length=self.hop_length,
            )
            onset_frames = librosa.onset.onset_detect(
                onset_envelope=onset_env, sr=eff_sr, hop_length=self.hop_length,
            )
            onset_count = len(onset_frames)

            if onset_count < 2:
                return RhythmFeatures(
                    avg_deviation_ratio=0.0, irregularity=0.0,
                    onset_density=0.5, onset_count=0,
                    off_beat_segments=0, is_clean_vocal=is_clean_vocal,
                )

            onset_times = librosa.frames_to_time(
                onset_frames, sr=eff_sr, hop_length=self.hop_length,
            )
            ioi = np.diff(onset_times)
            mean_ioi = np.mean(ioi)

            if mean_ioi > 0:
                total_dur = onset_times[-1] - onset_times[0]
                beats_per_second = (
                    onset_count / total_dur if total_dur > 0 else 0.0
                )
                irregularity = float(np.std(ioi) / mean_ioi)
                avg_dev = _cv_to_deviation(irregularity, is_clean_vocal)
                off_beat = _count_irregular_segments(ioi, mean_ioi)
            else:
                beats_per_second = 0.0
                irregularity = 0.0
                avg_dev = 0.0
                off_beat = 0

            return RhythmFeatures(
                avg_deviation_ratio=round(avg_dev, 4),
                irregularity=round(irregularity, 4),
                onset_density=max(0.5, round(beats_per_second, 2)),
                onset_count=int(onset_count),
                off_beat_segments=int(off_beat),
                is_clean_vocal=is_clean_vocal,
            )
        except Exception:
            logger.warning("Rhythm extraction failed, returning defaults", exc_info=True)
            return RhythmFeatures(
                avg_deviation_ratio=0.0, irregularity=0.0,
                onset_density=0.5, onset_count=0,
                off_beat_segments=0, is_clean_vocal=is_clean_vocal,
            )


    def _extract_beat_anchored(
        self,
        y_vocal: np.ndarray,
        sr_vocal: int,
        y_accomp: np.ndarray,
        sr_accomp: int,
    ) -> RhythmFeatures | None:
        """节拍锚定节奏 — 用伴奏轨节拍作基准, 测歌手 vocal onset 对节拍的偏差。

        v7.17: 修复 pro 模式分离后 rhythm 崩坍 (纯人声失去伴奏节拍锚定 → CV 1.32 无意义)。
        伴奏轨含节拍 (鼓/贝斯/和弦), 人声轨含歌手音符起始点:
          avg_deviation_ratio = 每个 vocal onset 到最近节拍的距离 (归一化到节拍周期) 的中位数
            - ~0.1 (10% 拍距) = 跟得很准 → 高分; ~0.5 (半拍) = 脱拍 → 低分
          irregularity = 偏差的 CV (忽快忽慢额外惩罚)
        数据不足 (无节拍/无 onset) 返回 None → 调用方回退混音路径。
        """
        import librosa
        try:
            # 1. 伴奏轨节拍网格
            _, beat_frames = librosa.beat.beat_track(
                y=y_accomp, sr=sr_accomp, hop_length=self.hop_length,
            )
            if len(beat_frames) < 4:
                return None
            beat_times = librosa.frames_to_time(
                beat_frames, sr=sr_accomp, hop_length=self.hop_length,
            )
            beat_period = float(np.median(np.diff(beat_times))) if len(beat_times) > 2 else 0.0
            if beat_period <= 0:
                return None

            # 2. 人声轨 vocal onset
            onset_env = librosa.onset.onset_strength(
                y=y_vocal, sr=sr_vocal, hop_length=self.hop_length,
            )
            onset_frames = librosa.onset.onset_detect(
                onset_envelope=onset_env, sr=sr_vocal, hop_length=self.hop_length,
            )
            if len(onset_frames) < 2:
                return None
            onset_times = librosa.frames_to_time(
                onset_frames, sr=sr_vocal, hop_length=self.hop_length,
            )

            # 3. 每个 vocal onset → 最近节拍偏差 (归一化到节拍周期)
            devs = np.array([min(abs(t - b) for b in beat_times) for t in onset_times])
            norm_devs = devs / beat_period
            avg_dev = float(np.median(norm_devs))

            # 4. 一致性 — 稳健离散度 (p75-p50)/p50, 对 Demucs 伪 onset 不敏感
            #    旧 CV (std/mean) 被伪 onset 拉到 3.0 → 25 分惩罚 (实测失真);
            #    p75-p50 反映上 25% 离散, 好歌手 ~0.3-0.6 (轻微惩罚), 脱拍 >1.0
            p75 = float(np.percentile(norm_devs, 75))
            irregularity = (p75 - avg_dev) / (avg_dev + 1e-6) if avg_dev > 0 else 0.0

            # 5. 脱拍段数: deviation > 半拍
            off_beat = int(np.sum(norm_devs > 0.5))

            span = onset_times[-1] - onset_times[0]
            onset_density = len(onset_times) / max(0.001, span)

            return RhythmFeatures(
                avg_deviation_ratio=round(min(1.0, avg_dev), 4),
                irregularity=round(min(3.0, irregularity), 4),
                onset_density=max(0.5, round(onset_density, 2)),
                onset_count=int(len(onset_times)),
                off_beat_segments=off_beat,
                is_clean_vocal=True,
            )
        except Exception:
            logger.warning("Beat-anchored rhythm extraction failed, returning None", exc_info=True)
            return None


def _cv_to_deviation(cv: float, is_clean_vocal: bool = False) -> float:
    """
    CV（变异系数）→ deviation_ratio (0-1) v5.13.
    内移自 RhythmAnalyzer._cv_to_deviation, 逐位一致。

    纯净人声的 onset 间隔分布与混合音频完全不同，
    因此使用不同的阈值映射。

    v7.17 混音分支重校准 (A1 失真修复): 实测 5 个真实音频 (Quick, 未分离) 显示
    PYIN voiced_flags 全程 100% voiced (伴奏被连续跟踪), HPSS 谐波 onset 亦无可靠改善
    (CV 未显著降低) — 混音下 onset CV 天然被伴奏抬到 0.5-1.0。旧映射把 CV 0.6 判为
    deviation 0.32 → 基础分 45 (过严)。新映射将 CV 0.6 判为 0.22 → 基础分 ~73,
    而 CV ≥1.2 (真实脱拍) 仍判 deviation ≥0.57 → 基础分 20, 保持区分度。
    """
    if is_clean_vocal:
        if cv < 0.5:
            return cv * 0.35
        elif cv < 0.8:
            return 0.175 + (cv - 0.5) * 0.5
        elif cv < 1.2:
            return 0.325 + (cv - 0.8) * 0.6
        elif cv < 1.8:
            return 0.565 + (cv - 1.2) * 0.5
        else:
            return min(1.0, 0.865 + (cv - 1.8) * 0.2)
    else:
        if cv < 0.3:
            return cv * 0.35
        elif cv < 0.5:
            return 0.105 + (cv - 0.3) * 0.45      # 0.3→0.105, 0.5→0.195
        elif cv < 0.8:
            return 0.195 + (cv - 0.5) * 0.25      # 0.5→0.195, 0.8→0.270
        elif cv < 1.2:
            return 0.27 + (cv - 0.8) * 0.75       # 0.8→0.27, 1.2→0.57
        else:
            return min(1.0, 0.57 + (cv - 1.2) * 0.5)


def _count_irregular_segments(ioi: np.ndarray, mean_ioi: float) -> int:
    """
    检测节奏不规则段。
    内移自 RhythmAnalyzer._count_irregular_segments, 逐位一致。
    """
    if len(ioi) < 3 or mean_ioi <= 0:
        return 0

    irregular_mask = np.abs(ioi - mean_ioi) > mean_ioi * 0.5

    segments = []
    start = None
    for i, val in enumerate(irregular_mask):
        if val and start is None:
            start = i
        elif not val and start is not None:
            if i - start >= 2:
                segments.append((start, i))
            start = None
    if start is not None and len(irregular_mask) - start >= 2:
        segments.append((start, len(irregular_mask)))

    return len(segments)
