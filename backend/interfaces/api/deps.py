"""
FastAPI 依赖注入容器

使用 Depends() 实现构造函数注入，所有服务延迟初始化。
绞杀者模式: 委托到现有 Flask business 层。
"""

from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import sys
import os

# 确保项目根目录可导入旧模块
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from backend.infrastructure.config import Settings
from backend.shared.event_bus import EventBus
from backend.domain.assessment.services import ScoringDomainService


# ===== 单例 (lifespan 初始化) =====
_event_bus = EventBus()


@lru_cache()
def get_settings() -> Settings:
    """配置单例 — Pydantic Settings, 支持 VAS_* 环境变量"""
    return Settings()


def get_event_bus() -> EventBus:
    """EventBus 单例"""
    return _event_bus


def get_scoring_service() -> ScoringDomainService:
    """评分领域服务 — 注入 EventBus (Phase 1 实现)"""
    return ScoringDomainService(event_bus=_event_bus)


# ===== 旧模块延迟导入 — 绞杀者模式委托到现有 business 层 =====

def get_history_repo():
    """JSON 历史记录仓储 — 委托到旧 repositories 模块

    v7.15 P2-14: 传入 upload_dir, 记录删除/淘汰时同步清理其上传文件 (防孤儿残留)。
    """
    from repositories import JsonHistoryRepository
    from config import config as flask_config
    return JsonHistoryRepository(
        flask_config.HISTORY_FILE,
        flask_config.HISTORY_MAX_RECORDS,
        upload_dir=flask_config.UPLOAD_FOLDER,
    )


def get_separation_service():
    """人声分离服务 — 委托到旧 services 模块"""
    from services import SeparationService
    from config import config as flask_config
    return SeparationService(flask_config.SEPARATED_DIR)


def get_report_service():
    """报告生成服务 — 委托到旧 services 模块"""
    from services import ReportService
    from config import config as flask_config
    return ReportService(flask_config.REPORTS_DIR)


def get_flask_config():
    """旧 Flask 配置 — 兼容现有业务逻辑"""
    from config import config as flask_config
    return flask_config


@lru_cache()
def get_song_repo():
    """歌曲仓储 — SQLite 实现 (VAS_SONGS_DB 环境变量可覆盖).

    v7.14 审查 C3: @lru_cache() 共享单连接 — 此前 get_song_service() 与
    get_auto_match_use_case() 各自 connect 同一 songs.db (双连接写锁冲突)。
    """
    from backend.infrastructure.persistence.sqlite_song_repo import SqliteSongRepository
    return SqliteSongRepository(db_path=get_settings().songs_db)


@lru_cache()
def get_song_service():
    """标准曲库应用服务单例"""
    from backend.application.songs.song_library_service import SongLibraryService
    return SongLibraryService(get_song_repo())


@lru_cache()
def get_pitch_cache():
    """歌曲音高缓存 — 内存实现 (进程内常驻单例)"""
    from backend.infrastructure.persistence.in_memory_pitch_cache import InMemoryPitchCacheRepository
    return InMemoryPitchCacheRepository()


def get_song_pitch_usecase():
    """歌曲参考音高用例 — v7.13"""
    from backend.application.songs_pitch.get_song_pitch import GetSongPitchUseCase
    from backend.domain.songs_pitch.services import PitchExtractionService
    return GetSongPitchUseCase(repo=get_pitch_cache(), extractor=PitchExtractionService)


# ===== v7.14: 上传音频自动匹配标准歌曲 =====

@lru_cache()
def get_song_match_profile_repo():
    """歌曲匹配特征 profile 仓储单例 — 与歌曲库同一数据库"""
    from backend.infrastructure.persistence.sqlite_song_match_profile_repo import (
        SqliteSongMatchProfileRepository,
    )
    return SqliteSongMatchProfileRepository(db_path=get_settings().songs_db)


@lru_cache()
def get_auto_match_use_case():
    """自动匹配用例单例 — v7.14"""
    from backend.application.song_match.auto_match_use_case import AutoMatchUseCase
    return AutoMatchUseCase(
        song_repo=get_song_repo(),
        profile_repo=get_song_match_profile_repo(),
    )
