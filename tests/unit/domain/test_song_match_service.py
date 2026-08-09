"""
song_match 匹配服务单元测试 — TDD RED (v7.14 auto-match)

KeyDetector (Krumhansl-Schmuckler 24 键检测) + AutoMatchService (置信度匹配)。
确定性构造 MatchFeatures/SongMatchProfile, 验证特性契约:
精确匹配≥0.7 / BPM±9%≥0.6 / Key+2半音鲁棒 / Top-3 排序 / no_match 回退 / 超时 partial。
"""
import time

import pytest

from backend.domain.song_match.services import AutoMatchService, KeyDetector
from backend.domain.song_match.value_objects import MatchFeatures, SongMatchProfile

# 单一 pitch class (C) 集中于 index 0 — 便于确定性验证旋转/调性
CHROMA_C = (1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
# 均匀 chroma — 无清晰和声中心, 用于确定性验证 no_match
CHROMA_UNIFORM = (1 / 12,) * 12


def _rot(v: tuple[float, ...], r: int) -> tuple[float, ...]:
    """chroma 向量向右循环平移 r 半音"""
    r %= 12
    return tuple(v[r:] + v[:r])


def _profile(
    song_id: str = 's1',
    title: str = '月亮代表我的心',
    artist: str = '邓丽君',
    bpm: float = 78.0,
    key: str = 'C',
    chroma: tuple[float, ...] = CHROMA_C,
    duration: float = 180.0,
) -> SongMatchProfile:
    return SongMatchProfile(
        song_id=song_id, title=title, artist=artist,
        bpm=bpm, key=key, chroma=chroma, duration_seconds=duration,
    )


def _features(
    bpm: float = 78.0,
    key: str = 'C',
    chroma: tuple[float, ...] = CHROMA_C,
    duration: float = 180.0,
    key_conf: float = 0.8,
) -> MatchFeatures:
    return MatchFeatures(
        bpm=bpm, detected_key=key, key_confidence=key_conf,
        chroma=chroma, duration_seconds=duration,
    )


class TestKeyDetector:
    """Krumhansl-Schmuckler 调性检测"""

    def test_detect_c_major(self):
        chroma = tuple(KeyDetector.KS_MAJOR)
        key, conf = KeyDetector.detect(chroma)
        assert key == 'C'
        assert conf > 0.5

    def test_detect_c_minor(self):
        """KS_MINOR 主音值 (6.33) 位于 index 0 = C 小调"""
        chroma = tuple(KeyDetector.KS_MINOR)
        key, conf = KeyDetector.detect(chroma)
        assert key == 'Cm'
        assert conf > 0.5

    @pytest.mark.parametrize('root,mode', [
        (r, m) for r in range(12) for m in ('major', 'minor')
    ])
    def test_all_24_keys_detectable(self, root, mode):
        """每个键用自己的 K-S profile 构造 chroma → 检测回自身"""
        profile = KeyDetector.KS_MAJOR if mode == 'major' else KeyDetector.KS_MINOR
        chroma = tuple(profile[(pc - root) % 12] for pc in range(12))
        key, conf = KeyDetector.detect(chroma)
        expected = KeyDetector.PITCH_CLASSES[root] + ('' if mode == 'major' else 'm')
        assert key == expected
        assert conf > 0.9

    def test_uniform_chroma_low_confidence(self):
        chroma = tuple([1 / 12] * 12)
        key, conf = KeyDetector.detect(chroma)
        assert conf < 0.3

    def test_chroma_length_must_be_12(self):
        with pytest.raises(ValueError):
            KeyDetector.detect((1.0, 0.0))

    @pytest.mark.parametrize('key_str,expected', [
        ('C', 0), ('C Major', 0), ('C#', 1), ('Db', 1),
        ('D', 2), ('G#m', 8), ('Ab minor', 8), ('B', 11), ('Bb', 10),
    ])
    def test_pitch_class_parsing(self, key_str, expected):
        assert KeyDetector.pitch_class(key_str) == expected

    def test_pitch_class_unparseable(self):
        assert KeyDetector.pitch_class('XX') is None
        assert KeyDetector.pitch_class('') is None

    @pytest.mark.parametrize('k1,k2,expected', [
        ('C', 'C', 0), ('C', 'D', 2), ('C', 'Db', 1),
        ('C', 'F#', 6), ('C', 'G#', 4), ('Am', 'A', 0),
    ])
    def test_pitch_class_distance(self, k1, k2, expected):
        assert KeyDetector.pitch_class_distance(k1, k2) == expected


class TestAutoMatchConfidence:
    """置信度算法 — 确定性验证特性契约"""

    def test_exact_match_high_confidence(self):
        result = AutoMatchService.match(_features(), [_profile()])
        assert result.matched is True
        assert result.matched_song == {
            'id': 's1', 'title': '月亮代表我的心',
            'artist': '邓丽君', 'confidence': result.matched_song['confidence'],
        }
        assert result.matched_song['confidence'] >= 0.7

    def test_bpm_9percent_robust(self):
        """BPM +9% (85 vs 78) 仍匹配, 置信度 ≥ 0.6"""
        user = _features(bpm=78 * 1.09)
        result = AutoMatchService.match(user, [_profile(bpm=78.0)])
        assert result.matched is True
        assert result.matched_song['confidence'] >= 0.6

    def test_key_plus_2_semitones_robust(self):
        """调性 +2 半音 (D vs C) 仍匹配, 标注 key_diff_semitones"""
        user = _features(key='D', chroma=_rot(CHROMA_C, 2))
        result = AutoMatchService.match(user, [_profile(key='C')])
        assert result.matched is True
        assert result.candidates[0].key_diff_semitones == 2
        assert result.candidates[0].detected_key == 'D'

    def test_confidence_stays_high_after_transposition(self):
        """转调后 chroma 旋转匹配 — 置信度不低于同曲未转调太远"""
        exact = AutoMatchService.match(_features(), [_profile()])
        transposed = AutoMatchService.match(
            _features(key='D', chroma=_rot(CHROMA_C, 2)), [_profile(key='C')]
        )
        assert transposed.matched_song['confidence'] >= exact.matched_song['confidence'] - 0.2

    def test_no_match_below_threshold(self):
        """完全不同的歌 (快BPM + 远调 + 无清晰旋律) → 置信度 < 0.6 → no_match 回退"""
        user = _features(bpm=160.0, key='F#', chroma=CHROMA_UNIFORM)
        result = AutoMatchService.match(user, [_profile(bpm=78.0, key='C')])
        assert result.matched is False
        assert result.matched_song is None
        assert result.fallback_reason == 'no_match'

    def test_top3_candidates_sorted_desc(self):
        """多候选 → Top-3 按置信度降序, 第一名最接近"""
        user = _features()
        profiles = [
            _profile('p_exact', '原唱', '甲', bpm=78.0),
            _profile('p_bpm90', '翻唱1', '乙', bpm=90.0),
            _profile('p_bpm100', '翻唱2', '丙', bpm=100.0),
            _profile('p_bpm120', '翻唱3', '丁', bpm=120.0),
        ]
        result = AutoMatchService.match(user, profiles)
        assert len(result.candidates) == 3
        confs = [c.confidence for c in result.candidates]
        assert confs == sorted(confs, reverse=True)
        assert result.candidates[0].song_id == 'p_exact'

    def test_empty_profiles_returns_no_profiles(self):
        result = AutoMatchService.match(_features(), [])
        assert result.matched is False
        assert result.fallback_reason == 'no_profiles'

    def test_short_audio_falls_back(self):
        result = AutoMatchService.match(_features(duration=2.0), [_profile()])
        assert result.matched is False
        assert result.fallback_reason == 'audio_too_short'

    def test_deadline_exceeded_returns_partial(self):
        """deadline 已过 → partial=True (不阻塞整体评分)"""
        result = AutoMatchService.match(
            _features(), [_profile()] * 5,
            deadline=time.monotonic() - 0.001,
        )
        assert result.partial is True

    def test_bad_profile_does_not_break_match(self):
        """单个异常 profile 跳过, 其余正常匹配"""
        result = AutoMatchService.match(_features(), [_profile('ok'), None])  # type: ignore[list-item]
        assert result.matched is True
        assert result.candidates[0].song_id == 'ok'
