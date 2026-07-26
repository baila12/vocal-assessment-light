"""
声学特征提取器 — v7.1 Batch 1: Acoustic Foundation

整合 HNR, CPP, Spectral Tilt, Voicing Detection, Mixed Audio Detection
到统一的 AcousticFeatureExtractor。

算法来源:
  - HNR: librosa HPSS harmonic/residual energy ratio
  - Multi-scale HNR: de Krom (1993) cepstral method, 4 frequency bands
  - CPP: Cepstral Peak Prominence via FFT→log→IFFT
  - Praat CPP: VoiceLab parselmouth PowerCepstrum (optional)
  - Spectral Tilt: LTAS slope dB/oct [Sundberg 1987]
  - Voicing: PYIN-based voiced/unvoiced ratio + detection confidence
  - Mixed Audio: 5-feature weighted vote (HPSS ratio, sub-band flatness, etc.)

设计原则:
  - 零副作用: 纯计算, 输入 (y, sr, f0) → 输出 AcousticFeatures
  - 独立可测: 可用合成音频验证
  - Feature Flag 门控: 高级算法可独立开关
"""
from __future__ import annotations
import logging
from typing import Optional
import numpy as np

from backend.domain.audio.feature_types import AcousticFeatures

logger = logging.getLogger(__name__)


class LibrosaAcousticExtractor:
    """
    声学基础特征提取器 (librosa 实现)

    整合 HPSS HNR, cepstral CPP, spectral tilt, voicing detection,
    mixed audio detection 于单一入口。

    用法:
        extractor = LibrosaAcousticExtractor()
        features = extractor.extract(y, sr)
        print(f"HNR={features.hnr:.1f}dB, CPP={features.cpp:.2f}")
    """

    def __init__(self, sample_rate: int = 22050, hop_length: int = 512):
        self.sample_rate = sample_rate
        self.hop_length = hop_length

    # ================================================================
    # 主入口
    # ================================================================

    def extract(
        self,
        y: np.ndarray,
        sr: int,
        enable_multiscale_hnr: bool = True,
        enable_praat_cpp: bool = True,
        enable_voicing_detection: bool = True,
        enable_reverb_compensation: bool = False,
    ) -> AcousticFeatures:
        """
        提取声学基础特征。

        Args:
            y: 音频数据 (float32, shape (n_samples,))
            sr: 采样率
            enable_multiscale_hnr: 启用 de Krom 4-band HNR (覆盖基线 HNR)
            enable_praat_cpp: 启用 Praat PowerCepstrum CPP (覆盖基线 CPP)
            enable_voicing_detection: 启用人声检测
            enable_reverb_compensation: 启用混响补偿 (实验性)

        Returns:
            AcousticFeatures: 声学基础特征
        """
        # Guard: 空/极短音频
        if y is None or len(y) < sr * 0.05:  # < 50ms
            logger.debug("Audio too short (< 50ms), returning defaults")
            return AcousticFeatures()

        # Energy check — silence guard
        rms = np.sqrt(np.mean(y ** 2))
        if rms < 1e-8:
            logger.debug("Audio is silent, returning zeros")
            return AcousticFeatures(hnr=0.0, cpp=0.0)

        # 1. HPSS decomposition (for ratio, mixed audio detection)
        hpss_harmonic, hpss_ratio = self._compute_hpss(y)

        # 2. HNR — v7.1.3: 内移自 AcousticAnalyzer.calculate_hnr (HPSS energy ratio)
        hnr = self._compute_hnr(y, hpss_harmonic=hpss_harmonic)

        # 3. CPP — v7.1.3: 内移自 AcousticAnalyzer.calculate_cpp (frame-based cepstral)
        cpp = self._compute_cpp(y)

        # 4. Spectral tilt
        spectral_tilt = self._compute_spectral_tilt(y, sr)

        # 7. Voicing detection
        voicing_ratio = 0.0
        detection_confidence = 0.0
        if enable_voicing_detection:
            voicing_ratio, detection_confidence = self._compute_voicing(y, sr)

        # 8. Mixed audio detection
        is_mixed, mixed_confidence = self._detect_mixed_audio(y, sr, hpss_ratio)

        return AcousticFeatures(
            hnr=round(float(hnr), 2),
            cpp=round(float(cpp), 4),
            spectral_tilt=round(float(spectral_tilt), 2),
            voicing_ratio=round(float(voicing_ratio), 4),
            detection_confidence=round(float(detection_confidence), 4),
            is_mixed_audio=is_mixed,
            mixed_audio_confidence=round(float(mixed_confidence), 4),
            hpss_harmonic_ratio=round(float(hpss_ratio), 4),
        )

    # ================================================================
    # HPSS
    # ================================================================

    @staticmethod
    def _compute_hpss(y: np.ndarray) -> tuple[np.ndarray, float]:
        """HPSS 分离: 谐波分量 + 谐波能量比"""
        try:
            import librosa
            harmonic, percussive = librosa.effects.hpss(y, margin=(1.0, 3.0))
            h_energy = np.sum(harmonic ** 2) + 1e-10
            p_energy = np.sum(percussive ** 2)
            total = h_energy + p_energy
            ratio = h_energy / total if total > 0 else 0.0
            return harmonic, float(ratio)
        except Exception:
            logger.warning("HPSS failed, returning raw audio with ratio=0", exc_info=True)
            return y, 0.0

    # ================================================================
    # HNR (Harmonics-to-Noise Ratio)
    # ================================================================

    def _compute_hnr(
        self,
        audio_data: np.ndarray,
        hpss_harmonic: np.ndarray | None = None,
    ) -> float:
        """
        HNR via HPSS harmonic/residual energy ratio in dB.
        v7.1.3: 内移自 AcousticAnalyzer.calculate_hnr — 逐位一致。
        支持缓存的 HPSS 谐波分量 (v6.2 perf 优化)。
        """
        try:
            if hpss_harmonic is not None and len(hpss_harmonic) == len(audio_data):
                harmonic = hpss_harmonic
            else:
                import librosa
                harmonic, _ = librosa.effects.hpss(audio_data, margin=(1.0, 3.0))
            harmonic_energy = np.sum(harmonic ** 2)
            residual_energy = np.sum((audio_data - harmonic) ** 2) + 1e-10

            if harmonic_energy > 0 and residual_energy > 0:
                hnr = 10.0 * np.log10(harmonic_energy / residual_energy)
                return float(max(0.0, min(40.0, hnr)))
            return 0.0
        except Exception:
            logger.debug("HNR calculation failed")
            return 0.0

    # ================================================================
    # Multi-scale HNR (de Krom 1993)
    # ================================================================

    @staticmethod
    def _compute_multiscale_hnr(y: np.ndarray, sr: int) -> Optional[float]:
        """
        de Krom (1993) 多频带 HNR.

        4 个频带: 0-500Hz, 500-1500Hz, 1500-2500Hz, 2500-4000Hz
        返回中频带 (0-1500Hz) 中位数 HNR — 与人声感知最相关。
        """
        try:
            n_fft = 2048
            hop_length = 512

            # STFT
            S = np.abs(np.fft.rfft(
                y[:len(y) - len(y) % hop_length].reshape(-1, hop_length),
                n=n_fft, axis=1
            ))

            # Frequency bins
            freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)

            bands = [
                (0, 500),
                (500, 1500),
                (1500, 2500),
                (2500, 4000),
            ]

            band_hnrs = []
            for flo, fhi in bands:
                mask = (freqs >= flo) & (freqs < fhi)
                if not np.any(mask):
                    continue
                band_energy = np.sum(S[mask] ** 2, axis=0)
                noise_floor = np.percentile(band_energy, 10) + 1e-10
                band_hnr = 10.0 * np.log10(np.mean(band_energy) / noise_floor)
                band_hnrs.append(max(0.0, band_hnr))

            if band_hnrs:
                # Return median of mid bands (0-1500Hz, most relevant for voice)
                mid_bands = band_hnrs[:2] if len(band_hnrs) >= 2 else band_hnrs
                return float(np.median(mid_bands))
            return None
        except Exception:
            return None

    # ================================================================
    # CPP (Cepstral Peak Prominence)
    # ================================================================

    def _compute_cpp(self, audio_data: np.ndarray) -> float:
        """
        CPP via frame-based cepstral analysis.
        v7.1.3: 内移自 AcousticAnalyzer.calculate_cpp — 逐位一致。

        Quefrency range: 2-20ms (50-500Hz fundamental period range)
        """
        try:
            import librosa
            frame_length = 2048
            frames = librosa.util.frame(
                audio_data, frame_length=frame_length, hop_length=self.hop_length
            )

            cpp_values = []
            min_quefrency = int(0.002 * self.sample_rate)
            max_quefrency = int(0.02 * self.sample_rate)

            for frame in frames.T:
                if np.max(np.abs(frame)) < 1e-6:
                    continue

                spectrum = np.abs(np.fft.rfft(frame))
                log_spectrum = np.log(spectrum + 1e-10)
                cepstrum = np.fft.ifft(log_spectrum).real

                if max_quefrency < len(cepstrum):
                    search_range = cepstrum[min_quefrency:max_quefrency]
                    if len(search_range) > 0:
                        peak = np.max(search_range)
                        baseline = np.mean(search_range)
                        cpp_values.append(float(peak - baseline))

            return float(np.mean(cpp_values)) if cpp_values else 0.0
        except Exception:
            logger.debug("CPP calculation failed")
            return 0.0

    # ================================================================
    # Praat CPP (VoiceLab parselmouth, optional)
    # ================================================================

    @staticmethod
    def _compute_praat_cpp(y: np.ndarray, sr: int) -> Optional[float]:
        """Praat PowerCepstrum CPP — 需要 parselmouth 可用"""
        try:
            import parselmouth
            sound = parselmouth.Sound(y, sampling_frequency=sr)
            cepstrum = sound.to_power_cepstrogram(
                time_step=0.01,  # 10ms
            )
            # Get mean CPP across time
            values = cepstrum.values.flatten()
            values = values[np.isfinite(values)]
            if len(values) > 0:
                return float(np.mean(values))
            return None
        except ImportError:
            logger.debug("parselmouth not available, Praat CPP disabled")
            return None
        except Exception:
            return None

    # ================================================================
    # Spectral Tilt
    # ================================================================

    @staticmethod
    def _compute_spectral_tilt(y: np.ndarray, sr: int) -> float:
        """
        LTAS (Long-Term Average Spectrum) slope in dB/octave.

        Sundberg (1987): 频谱倾斜区分气声 (负 tilt) vs 压嗓 (正 tilt).
        """
        try:
            n_fft = 2048
            # Average spectrum
            n_frames = max(1, len(y) // 512 - 1)
            spec_accum = np.zeros(n_fft // 2 + 1)
            for i in range(n_frames):
                frame = y[i * 512:i * 512 + n_fft]
                if len(frame) < n_fft:
                    break
                spec_accum += np.abs(np.fft.rfft(frame * np.hamming(len(frame))))

            spec_accum /= max(1, n_frames)
            freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)

            # Focus on 100-5000Hz (vocal range)
            mask = (freqs >= 100) & (freqs <= 5000)
            if np.sum(mask) < 10:
                return -10.0

            log_freq = np.log2(freqs[mask] + 1e-10)
            log_spec = 20.0 * np.log10(spec_accum[mask] + 1e-10)

            # Linear regression: slope in dB/octave
            if len(log_freq) > 2:
                slope, _ = np.polyfit(log_freq, log_spec, 1)
                return float(np.clip(slope, -20.0, 10.0))
            return -10.0
        except Exception:
            return -10.0

    # ================================================================
    # Voicing Detection
    # ================================================================

    @staticmethod
    def _compute_voicing(y: np.ndarray, sr: int) -> tuple[float, float]:
        """
        基于 PYIN/能量的人声检测。

        Returns:
            voicing_ratio: 有声帧比例 (0-1)
            detection_confidence: 检测置信度均值 (0-1)
        """
        try:
            import librosa

            # PYIN F0 extraction
            f0, voiced_flag, voiced_prob = librosa.pyin(
                y.astype(np.float64),
                fmin=65.0,
                fmax=1047.0,
                sr=sr,
                fill_na=0.0,
            )

            if f0 is None or len(f0) == 0:
                return 0.0, 0.0

            voiced = voiced_flag.astype(bool) if voiced_flag is not None else f0 > 0
            raw_ratio = float(np.mean(voiced))

            # Confidence: mean voiced_prob for voiced frames
            if np.any(voiced) and voiced_prob is not None:
                confidence = float(np.mean(voiced_prob[voiced]))
            else:
                confidence = 0.0

            # Low confidence → scale down voicing ratio proportionally
            # PYIN can hallucinate voiced frames on noise with very low prob
            if confidence < 0.2:
                voice_ratio = raw_ratio * (confidence / 0.2)
            else:
                voice_ratio = raw_ratio

            return voice_ratio, confidence
        except ImportError:
            # librosa fallback: energy + zero-crossing rate voicing detection
            frame_len = int(sr * 0.025)
            hop_len = frame_len // 2
            n_frames = max(1, (len(y) - frame_len) // hop_len)

            energies = np.zeros(n_frames)
            zc_rates = np.zeros(n_frames)

            for i in range(n_frames):
                frame = y[i * hop_len:i * hop_len + frame_len]
                if len(frame) < 2:
                    continue
                energies[i] = np.sqrt(np.mean(frame ** 2))
                # Zero-crossing rate: high for noise, low for voiced
                zc_rates[i] = np.mean(np.abs(np.diff(np.sign(frame)))) / 2.0

            if len(energies) < 2:
                return 0.0, 0.0

            # Energy gate
            energy_threshold = max(1e-6, np.percentile(energies, 30))
            has_energy = energies > energy_threshold

            # ZCR gate: white noise has ZCR ~0.5, voiced speech ~0.1-0.2
            zcr_threshold = 0.35  # above this is likely noise, not voice
            is_voiced_like = zc_rates < zcr_threshold

            # Combined: need both energy AND low ZCR
            voiced_frames = has_energy & is_voiced_like
            voice_ratio = float(np.mean(voiced_frames))

            # Confidence: higher when energy and ZCR agree
            if np.any(has_energy):
                confidence = float(np.mean(is_voiced_like[has_energy]))
            else:
                confidence = 0.0

            return voice_ratio, confidence
        except Exception:
            return 0.0, 0.0

    # ================================================================
    # Mixed Audio Detection
    # ================================================================

    @staticmethod
    def _detect_mixed_audio(
        y: np.ndarray, sr: int, hpss_ratio: float
    ) -> tuple[bool, float]:
        """
        混合音频检测: 5 特征加权投票。

        特征:
          1. HPSS harmonic ratio < 0.25 → likely mixed
          2. Sub-band spectral flatness > 0.4 → noise/interference
          3. High frequency energy ratio > 0.3 → percussion
          4. Harmonicity score < 0.5 → weak harmonic structure
          5. Full-band spectral flatness > 0.35 → overall noise

        Returns:
            is_mixed: 是否检测到混合音频
            confidence: 置信度 (0-1)
        """
        try:
            votes = []
            weights = []

            # 1. HPSS ratio check
            if hpss_ratio > 0:
                score_1 = max(0.0, min(1.0, (0.25 - hpss_ratio) / 0.25))
                votes.append(score_1)
                weights.append(0.30)

            # 2-5. Spectral flatness checks
            n_fft = 2048
            S = np.abs(np.fft.rfft(
                y[:len(y) - len(y) % 512].reshape(-1, 512),
                n=n_fft, axis=1
            ))

            if S.size > 0:
                freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)

                # 2. Sub-band flatness (200-800Hz vocal harmonic region)
                sub_mask = (freqs >= 200) & (freqs <= 800)
                if np.any(sub_mask):
                    sub_spec = S[sub_mask]
                    geo_mean = np.exp(np.mean(np.log(sub_spec + 1e-10)))
                    arith_mean = np.mean(sub_spec)
                    sub_flatness = float(geo_mean / (arith_mean + 1e-10))
                    score_2 = max(0.0, min(1.0, (sub_flatness - 0.3) / 0.4))
                    votes.append(score_2)
                    weights.append(0.20)

                # 3. High frequency energy (>4kHz) — percussion indicator
                hf_mask = freqs >= 4000
                if np.any(hf_mask) and np.any(~hf_mask):
                    hf_ratio = float(np.sum(S[hf_mask]) / (np.sum(S) + 1e-10))
                    score_3 = max(0.0, min(1.0, (hf_ratio - 0.15) / 0.25))
                    votes.append(score_3)
                    weights.append(0.15)

                # 4. Harmonicity: ratio of harmonic peaks to inter-harmonic valleys
                # Simplified: use HPSS ratio as proxy
                score_4 = max(0.0, min(1.0, (0.5 - hpss_ratio) / 0.3))
                votes.append(score_4)
                weights.append(0.20)

                # 5. Full-band spectral flatness
                full_geo = np.exp(np.mean(np.log(S + 1e-10)))
                full_arith = np.mean(S)
                full_flatness = float(full_geo / (full_arith + 1e-10))
                score_5 = max(0.0, min(1.0, (full_flatness - 0.2) / 0.3))
                votes.append(score_5)
                weights.append(0.15)

            if not votes:
                return False, 0.0

            # Weighted vote
            total_weight = sum(weights)
            confidence = sum(v * w for v, w in zip(votes, weights)) / total_weight

            return confidence > 0.5, float(confidence)
        except Exception:
            return False, 0.0
