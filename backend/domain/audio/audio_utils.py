"""
音频工具函数 — v7.1.3 Phase 2

从 services/features/acoustic.py (AcousticAnalyzer) 内移到 DDD domain 层。
纯函数, 零副作用, 独立可测。

内移函数:
  - normalize_loudness()        — RMS 响度归一化
  - find_vocal_segments()       — VAD 人声分段检测
  - filter_audio_to_vocal_segments() — 提取并拼接人声段
"""
from __future__ import annotations
import numpy as np


def normalize_loudness(audio_data: np.ndarray, target_rms: float = 0.05) -> np.ndarray:
    """
    响度归一化 v5.10 — 内移自 AcousticAnalyzer.normalize_loudness

    使用RMS归一化减少录音条件差异（麦克风距离/增益/房间声学）。
    目标RMS值 0.05 对应约 -23 LUFS 的典型语音/歌唱水平。

    注意：只做增益调整，不改变动态范围。

    Args:
        audio_data: 音频数据
        target_rms: 目标RMS值（默认0.05，经验值）

    Returns:
        归一化后的音频数据
    """
    rms = np.sqrt(np.mean(audio_data ** 2))
    if rms > 1e-10:
        gain = target_rms / rms
        # 限制增益范围避免过度放大噪声或压缩强信号
        gain = np.clip(gain, 0.1, 10.0)
        return audio_data * gain
    return audio_data


def find_vocal_segments(
    f0: np.ndarray,
    hop_length: int = 512,
    sample_rate: int = 22050,
    min_segment_sec: float = 0.5,
    max_gap_sec: float = 1.0,
) -> list:
    """
    VAD 人声分段 v5.10 — 内移自 AcousticAnalyzer.find_vocal_segments

    使用基频检测标记有声段，过滤掉前奏/间奏/尾奏(纯器乐段)。
    只保留包含人声基频的连续段，避免纯器乐段被当作"没有音高的演唱"。

    Args:
        f0: 基频序列
        hop_length: 帧移
        sample_rate: 采样率
        min_segment_sec: 最小声段时长(秒)，短于此的视为噪声
        max_gap_sec: 最大间隔(秒)，小于此的间断会被合并

    Returns:
        [(start_frame, end_frame), ...] 人声段列表
    """
    voiced = ~np.isnan(f0) & (f0 > 65) & (f0 < 1047)

    min_frames = int(min_segment_sec * sample_rate / hop_length)
    max_gap_frames = int(max_gap_sec * sample_rate / hop_length)

    segments = []
    start = None
    gap_start = None

    for i, is_voiced in enumerate(voiced):
        if is_voiced:
            if start is None:
                start = i
            gap_start = None
        else:
            if start is not None:
                if gap_start is None:
                    gap_start = i
                if (i - gap_start) >= max_gap_frames:
                    segment_len = gap_start - start
                    if segment_len >= min_frames:
                        segments.append((start, gap_start))
                    start = None
                    gap_start = None

    # 末尾段
    if start is not None:
        segment_len = len(voiced) - start
        if segment_len >= min_frames:
            segments.append((start, len(voiced)))

    return segments


def filter_audio_to_vocal_segments(
    audio_data: np.ndarray,
    vocal_segments: list,
    hop_length: int = 512,
) -> np.ndarray:
    """
    提取音频中的人声段，拼接为连续数组 v5.10 — 内移自 AcousticAnalyzer.filter_audio_to_vocal_segments

    用于从包含前奏/间奏的混合音频中只提取人声部分进行特征计算。

    Args:
        audio_data: 完整音频数据
        vocal_segments: 人声段列表 [(start_frame, end_frame), ...]
        hop_length: 帧移

    Returns:
        人声段拼接后的音频数据（若无有效段则返回原音频）
    """
    if not vocal_segments:
        return audio_data

    vocal_parts = []
    for start_frame, end_frame in vocal_segments:
        start_sample = start_frame * hop_length
        end_sample = min(end_frame * hop_length, len(audio_data))
        if end_sample > start_sample:
            vocal_parts.append(audio_data[start_sample:end_sample])

    if not vocal_parts:
        return audio_data

    return np.concatenate(vocal_parts)
