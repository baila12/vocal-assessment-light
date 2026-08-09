"""
AutoMatchUseCase — v7.14 上传音频自动匹配标准歌曲 (应用层编排)

加载用户音频 → 提取匹配特征 → 预算式预计算缺失歌曲 profile (存 SQLite) →
按 deadline 匹配 (超时返回 partial, 不阻塞整体评分)。
依赖 SongRepository / SongMatchProfileRepository / MatchFeatureExtractor /
AutoMatchService 抽象, 与存储/提取实现解耦。
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

from backend.domain.song_match.feature_extractor import DEFAULT_SR, MatchFeatureExtractor
from backend.domain.song_match.repository import SongMatchProfileRepository
from backend.domain.song_match.services import AutoMatchService
from backend.domain.song_match.value_objects import (
    FEATURE_VERSION,
    MatchFeatures,
    MatchResult,
    SongMatchProfile,
)
from backend.domain.songs.repository import SongRepository


class AutoMatchUseCase:
    """上传音频自动匹配用例 — 预算式特征预计算 + 确定性匹配"""

    def __init__(
        self,
        song_repo: SongRepository,
        profile_repo: SongMatchProfileRepository,
        extractor: MatchFeatureExtractor | type[MatchFeatureExtractor] = MatchFeatureExtractor,
        matcher: AutoMatchService | type[AutoMatchService] = AutoMatchService,
    ) -> None:
        self._song_repo = song_repo
        self._profile_repo = profile_repo
        self._extractor = extractor
        self._matcher = matcher

    def execute(
        self,
        audio_path: str | Path,
        *,
        top_n: int = 3,
        timeout_s: float = 10.0,
    ) -> MatchResult:
        """执行匹配

        Args:
            audio_path: 用户音频文件路径
            top_n: 返回候选数
            timeout_s: 整体超时秒数; 超时返回 partial=True

        Returns:
            MatchResult — matched/matched_song/candidates/fallback_reason/partial
        """
        import librosa

        # 1. 用户音频 → 匹配特征
        y, sr = librosa.load(str(audio_path), sr=DEFAULT_SR, mono=True)
        features: MatchFeatures = self._extractor.extract(y, sr)

        deadline = time.monotonic() + max(0.0, timeout_s)

        # 2. 预算式预计算缺失歌曲 profile (提取失败跳过, 不阻断)
        self._ensure_profiles(deadline)

        # 3. 确定性匹配 (deadline 传递, 超时 partial)
        profiles = self._profile_repo.list_all()
        return self._matcher.match(
            features, profiles, top_n=top_n, deadline=deadline,
        )

    def _ensure_profiles(self, deadline: float) -> None:
        """为缺少 profile 的歌曲预算式提取并持久化, 超时立即停止"""
        import librosa

        for song in self._song_repo.list_all_with_filepath():
            if time.monotonic() >= deadline:
                break  # 预算耗尽, 用现有 profiles 继续
            if self._profile_repo.get(song.id) is not None:
                continue
            try:
                y, sr = librosa.load(song.filepath, sr=DEFAULT_SR, mono=True)
                song_features = self._extractor.extract(y, sr)
            except (OSError, ValueError, RuntimeError):
                continue  # 单个歌曲提取失败跳过, 不阻断整体匹配

            profile = SongMatchProfile(
                song_id=song.id,
                title=song.metadata.title,
                artist=song.metadata.artist,
                bpm=song_features.bpm,
                key=song_features.detected_key,
                chroma=song_features.chroma,
                duration_seconds=song_features.duration_seconds,
                feature_version=FEATURE_VERSION,
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
            self._profile_repo.save(profile)
