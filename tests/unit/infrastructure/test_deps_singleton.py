"""DI 容器单例测试 — P0-2 (审查 C3): get_song_repo 连接复用

get_song_repo() 曾被 get_song_service() 与 get_auto_match_use_case()
各自调用 → 同一 songs.db 上两个独立 SQLite 连接, 默认 rollback journal
模式下同文件只允许单写者 → 并发死锁/SQLITE_BUSY。
修复: get_song_repo() 加 @lru_cache() 共享单连接。
"""

def test_get_song_repo_is_cached_singleton(monkeypatch, tmp_path):
    """两次调用返回同一连接实例 — 消除双连接"""
    monkeypatch.setenv('VAS_SONGS_DB', str(tmp_path / 'songs.db'))
    from backend.interfaces.api import deps

    deps.get_settings.cache_clear()
    deps.get_song_repo.cache_clear()
    try:
        first = deps.get_song_repo()
        second = deps.get_song_repo()
        assert first is second, 'get_song_repo() 应返回同一连接实例 (双连接 → 并发写锁冲突)'
    finally:
        deps.get_song_repo.cache_clear()
        deps.get_settings.cache_clear()


def test_song_service_and_auto_match_share_repo(monkeypatch, tmp_path):
    """歌曲服务与自动匹配用例共享同一仓储连接 (C3 双连接根因)"""
    monkeypatch.setenv('VAS_SONGS_DB', str(tmp_path / 'songs.db'))
    from backend.interfaces.api import deps

    deps.get_settings.cache_clear()
    deps.get_song_repo.cache_clear()
    deps.get_song_service.cache_clear()
    deps.get_auto_match_use_case.cache_clear()
    try:
        service = deps.get_song_service()
        use_case = deps.get_auto_match_use_case()
        # 通过单例缓存共享 get_song_repo → 两处连接同一对象
        assert service._repo is deps.get_song_repo()
        assert use_case._song_repo is deps.get_song_repo()
    finally:
        deps.get_song_service.cache_clear()
        deps.get_auto_match_use_case.cache_clear()
        deps.get_song_repo.cache_clear()
        deps.get_settings.cache_clear()
