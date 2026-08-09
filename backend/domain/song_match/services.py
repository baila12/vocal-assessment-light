"""
song_match 匹配服务 — v7.14 上传音频自动匹配标准歌曲

KeyDetector: Krumhansl-Schmuckler 24 键调性检测 (Pearson 相关, 纯 stdlib)。
AutoMatchService: 确定性置信度匹配 — 加权 bpm/chroma/key/duration,
chroma 用 12 旋转最大余弦实现转调不变, 超时返回 partial 不阻塞整体评分。

匹配置信度公式 (与计划一致, 供单元测试确定性构造):
    confidence = 0.30*bpm + 0.40*chroma + 0.15*key + 0.15*duration
    bpm_score    = 1/(1 + (|Δbpm| / max(user, profile)) / 0.10)
    chroma_score = max over 12 rotations(cosine(user, rotate(profile)))
    key_score    = max(0, 1 - pitch_class_distance/6)
    duration_score = 1/(1 + |log2(user_dur/profile_dur)|)
"""

from __future__ import annotations

import math
import time
from typing import Sequence

from backend.domain.song_match.value_objects import (
    CHROMA_BINS,
    MatchCandidate,
    MatchFeatures,
    MatchResult,
    SongMatchProfile,
)

# 置信度权重与阈值 — 特性契约 (见计划文档)
WEIGHT_BPM = 0.30
WEIGHT_CHROMA = 0.40
WEIGHT_KEY = 0.15
WEIGHT_DURATION = 0.15
MATCH_THRESHOLD = 0.60
DEFAULT_TOP_N = 3
DEFAULT_MIN_DURATION = 3.0  # 秒 — 过短音频无法可靠提取匹配特征


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """12-bin 非负向量的余弦相似度 (∈[0,1])"""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def _pearson(a: Sequence[float], b: Sequence[float]) -> float:
    """Pearson 相关系数 — 对平移/缩放不变, 纯 stdlib"""
    n = len(a)
    ma = sum(a) / n
    mb = sum(b) / n
    da = [x - ma for x in a]
    db = [x - mb for x in b]
    sa = math.sqrt(sum(x * x for x in da))
    sb = math.sqrt(sum(y * y for y in db))
    if sa == 0.0 or sb == 0.0:
        return 0.0  # 常量向量 (如均匀 chroma) — 无调性信息
    return sum(x * y for x, y in zip(da, db)) / (sa * sb)


def _rotated(profile: Sequence[float], root: int) -> tuple[float, ...]:
    """将 profile 循环平移, 使主音 (index 0) 落在 root 半音

    candidate[i] = profile[(i - root) % 12] — 主音值 profile[0] 位于 index root。
    """
    root %= CHROMA_BINS
    return tuple(profile[(i - root) % CHROMA_BINS] for i in range(CHROMA_BINS))


class KeyDetector:
    """Krumhansl-Schmuckler 调性检测 — 24 键 (12 major + 12 minor)"""

    # Krumhansl-Kessler probe tone profiles (主音值位于 index 0)
    KS_MAJOR = (6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88)
    KS_MINOR = (6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17)

    PITCH_CLASSES = (
        'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B',
    )

    _NATURALS = {'c': 0, 'd': 2, 'e': 4, 'f': 5, 'g': 7, 'a': 9, 'b': 11}
    _MODE_SUFFIXES = ('minor', 'major', 'maj', 'min', 'scale', 'dur', 'moll')

    @classmethod
    def detect(cls, chroma: Sequence[float]) -> tuple[str, float]:
        """检测 12-bin chroma 的调性, 返回 (key, confidence 0-1)"""
        if len(chroma) != CHROMA_BINS:
            raise ValueError(f'chroma 必须为 {CHROMA_BINS} 维, 当前 {len(chroma)}')
        best_key: str = cls.PITCH_CLASSES[0]
        best_conf = 0.0
        for root in range(CHROMA_BINS):
            for name, profile in (('', cls.KS_MAJOR), ('m', cls.KS_MINOR)):
                candidate = _rotated(profile, root)
                conf = max(0.0, _pearson(chroma, candidate))
                if conf > best_conf:
                    best_conf = conf
                    best_key = cls.PITCH_CLASSES[root] + name
        return best_key, best_conf

    @staticmethod
    def pitch_class(key_str: str) -> int | None:
        """解析调性字符串 → pitch class (0-11), 无法解析返回 None

        支持: 'C'/'C#'/'Db' 等, 可选模式后缀 'm'/'minor'/'major'/'maj'/'min'。
        """
        if not key_str:
            return None
        s = key_str.strip().lower()
        if not s:
            return None
        for suffix in KeyDetector._MODE_SUFFIXES:
            if s.endswith(suffix) and len(s) > len(suffix):
                s = s[: len(s) - len(suffix)].strip()
                break
        if s.endswith('m') and len(s) > 1:
            s = s[:-1].strip()
        if not s:
            return None
        if s[0] not in KeyDetector._NATURALS:
            return None
        pitch = KeyDetector._NATURALS[s[0]]
        acc = s[1:]
        if acc == '':
            return pitch
        if acc == '#':
            return (pitch + 1) % CHROMA_BINS
        if acc == 'b':
            return (pitch - 1) % CHROMA_BINS
        if acc == '##':
            return (pitch + 2) % CHROMA_BINS
        if acc == 'bb':
            return (pitch - 2) % CHROMA_BINS
        return None

    @classmethod
    def pitch_class_distance(cls, k1: str, k2: str) -> int:
        """两调性的五度圈最小半音距 (0-6); 未知调性按最大距离 6 保守处理"""
        p1 = cls.pitch_class(k1)
        p2 = cls.pitch_class(k2)
        if p1 is None or p2 is None:
            return 6
        d = abs(p1 - p2) % CHROMA_BINS
        return min(d, CHROMA_BINS - d)


class AutoMatchService:
    """置信度匹配 — 纯函数, 无 IO, 可确定性构造验证"""

    @staticmethod
    def _bpm_score(user: MatchFeatures, profile: SongMatchProfile) -> float:
        denom = max(user.bpm, profile.bpm)
        if denom <= 0.0:
            return 1.0 if user.bpm == profile.bpm else 0.0  # 双静音视为一致
        ratio = abs(user.bpm - profile.bpm) / denom
        return 1.0 / (1.0 + ratio / 0.10)

    @staticmethod
    def _chroma_score(user: MatchFeatures, profile: SongMatchProfile) -> float:
        best = 0.0
        for r in range(CHROMA_BINS):
            best = max(best, _cosine(user.chroma, _rotated(profile.chroma, r)))
        return best

    @classmethod
    def _key_score(cls, user: MatchFeatures, profile: SongMatchProfile) -> float:
        dist = KeyDetector.pitch_class_distance(user.detected_key, profile.key)
        return max(0.0, 1.0 - dist / 6.0)

    @staticmethod
    def _duration_score(user: MatchFeatures, profile: SongMatchProfile) -> float:
        if user.duration_seconds <= 0.0 or profile.duration_seconds <= 0.0:
            return 1.0
        log_ratio = abs(math.log2(user.duration_seconds / profile.duration_seconds))
        return 1.0 / (1.0 + log_ratio)

    @classmethod
    def _confidence(cls, user: MatchFeatures, profile: SongMatchProfile) -> float:
        return (
            WEIGHT_BPM * cls._bpm_score(user, profile)
            + WEIGHT_CHROMA * cls._chroma_score(user, profile)
            + WEIGHT_KEY * cls._key_score(user, profile)
            + WEIGHT_DURATION * cls._duration_score(user, profile)
        )

    @classmethod
    def match(
        cls,
        features: MatchFeatures,
        profiles: Sequence[SongMatchProfile | None],
        *,
        top_n: int = DEFAULT_TOP_N,
        deadline: float | None = None,
        min_duration: float = DEFAULT_MIN_DURATION,
    ) -> MatchResult:
        """对用户特征在歌曲 profile 库中匹配, 返回 Top-N 候选

        Args:
            features: 用户音频匹配特征
            profiles: 歌曲 profile 库 (None/异常项跳过)
            top_n: 返回候选数
            deadline: time.monotonic() 截止时间戳; 超时返回 partial=True
            min_duration: 音频最短时长 (秒), 低于则回退 audio_too_short
        """
        start = time.monotonic()

        def _elapsed() -> float:
            return (time.monotonic() - start) * 1000.0

        if deadline is not None and time.monotonic() >= deadline:
            return MatchResult(
                matched=False, fallback_reason='timeout', partial=True,
                detected_key=features.detected_key, elapsed_ms=_elapsed(),
            )
        if features.duration_seconds < min_duration:
            return MatchResult(
                matched=False, fallback_reason='audio_too_short',
                detected_key=features.detected_key, elapsed_ms=_elapsed(),
            )
        if not profiles:
            return MatchResult(
                matched=False, fallback_reason='no_profiles',
                detected_key=features.detected_key, elapsed_ms=_elapsed(),
            )

        candidates: list[MatchCandidate] = []
        for profile in profiles:
            if deadline is not None and time.monotonic() >= deadline:
                return MatchResult(
                    matched=False, fallback_reason='timeout', partial=True,
                    detected_key=features.detected_key, elapsed_ms=_elapsed(),
                )
            if profile is None:
                continue
            try:
                confidence = cls._confidence(features, profile)
            except (ValueError, ZeroDivisionError, TypeError):
                continue  # 单个异常 profile 不阻断整体匹配
            candidates.append(MatchCandidate(
                song_id=profile.song_id,
                title=profile.title,
                artist=profile.artist,
                confidence=confidence,
                factors={
                    'bpm': cls._bpm_score(features, profile),
                    'chroma': cls._chroma_score(features, profile),
                    'key': cls._key_score(features, profile),
                    'duration': cls._duration_score(features, profile),
                },
                bpm_diff=abs(features.bpm - profile.bpm),
                key_diff_semitones=KeyDetector.pitch_class_distance(
                    features.detected_key, profile.key
                ),
                detected_key=features.detected_key,
            ))

        candidates.sort(key=lambda c: c.confidence, reverse=True)
        top = candidates[:max(0, top_n)]
        if not top:
            return MatchResult(
                matched=False, fallback_reason='no_match',
                detected_key=features.detected_key, elapsed_ms=_elapsed(),
            )

        best = top[0]
        matched = best.confidence >= MATCH_THRESHOLD
        matched_song: dict[str, float] | None = None
        if matched:
            matched_song = {
                'id': best.song_id,
                'title': best.title,
                'artist': best.artist,
                'confidence': best.confidence,
            }
        return MatchResult(
            matched=matched,
            matched_song=matched_song,
            candidates=tuple(top),
            fallback_reason='' if matched else 'no_match',
            detected_key=features.detected_key,
            elapsed_ms=_elapsed(),
        )
