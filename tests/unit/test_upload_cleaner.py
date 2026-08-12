"""
upload_cleaner — 上传文件自动清理单元测试 (v7.15 P2-14)

DEEP_REVIEW E4/V8 (CONFIRMED): uploads/ 目录永不清理 — 36 个文件无清理,
孤儿文件 (历史记录已删/淘汰/从未引用) 永久残留, 磁盘无限增长。

修复 (TDD RED→GREEN):
  - unlink_files(upload_dir, filepaths)   — 定向删除记录文件 (仅 uploads 目录内, 防御误删)
  - collect_referenced_files(records)     — 提取仍被历史记录引用的文件集合
  - cleanup_orphans(upload_dir, refs)     — 孤儿扫描: 删除未被引用的上传文件
  - run_startup_upload_cleanup(dir, repo) — 启动时孤儿扫描入口 (无仓储则安全不删)
"""
from __future__ import annotations

from unittest.mock import Mock

from services.upload_cleaner import (
    unlink_files,
    cleanup_orphans,
    collect_referenced_files,
    run_startup_upload_cleanup,
)


class TestUnlinkFiles:
    def test_deletes_files_within_upload_dir(self, tmp_path):
        upload = tmp_path / "uploads"
        upload.mkdir()
        f = upload / "a.wav"
        f.write_bytes(b"data")
        assert unlink_files(upload, [str(f)]) == 1
        assert not f.exists()

    def test_skips_files_outside_upload_dir(self, tmp_path):
        upload = tmp_path / "uploads"
        upload.mkdir()
        outside = tmp_path / "keep.wav"
        outside.write_bytes(b"data")
        assert unlink_files(upload, [str(outside)]) == 0
        assert outside.exists()

    def test_skips_empty_entries_and_tolerates_missing(self, tmp_path):
        upload = tmp_path / "uploads"
        upload.mkdir()
        # None / "" 跳过; 不存在的文件 missing_ok 不抛错 (幂等)
        assert unlink_files(upload, [None, "", str(upload / "ghost.wav")]) == 1


class TestCleanupOrphans:
    def test_deletes_unreferenced_keeps_referenced(self, tmp_path):
        upload = tmp_path / "uploads"
        upload.mkdir()
        orphan = upload / "orphan.wav"
        used = upload / "used.wav"
        orphan.write_bytes(b"1")
        used.write_bytes(b"2")
        deleted = cleanup_orphans(upload, [str(used)])
        assert deleted == 1
        assert used.exists()
        assert not orphan.exists()

    def test_nonexistent_dir_returns_zero(self, tmp_path):
        assert cleanup_orphans(tmp_path / "nope", []) == 0

    def test_skips_subdirectories(self, tmp_path):
        upload = tmp_path / "uploads"
        sub = upload / "sub"
        sub.mkdir(parents=True)
        (sub / "inner.wav").write_bytes(b"x")
        (upload / "orphan.wav").write_bytes(b"y")
        # 仅删除顶层文件; 子目录不递归 (KISS, 无已知子目录用法)
        assert cleanup_orphans(upload, []) == 1
        assert (sub / "inner.wav").exists()


class TestCollectReferencedFiles:
    def test_collects_nonempty_filepaths(self, tmp_path):
        records = [
            {"filepath": str(tmp_path / "a.wav")},
            {"filepath": ""},
            {},
        ]
        refs = collect_referenced_files(records)
        assert refs == {str((tmp_path / "a.wav").resolve())}


class TestRunStartupUploadCleanup:
    def test_removes_orphans_keeps_referenced(self, tmp_path):
        upload = tmp_path / "uploads"
        upload.mkdir()
        used = upload / "used.wav"
        used.write_bytes(b"1")
        (upload / "orphan.wav").write_bytes(b"2")
        repo = Mock()
        repo.get_by_date.return_value = [{"filepath": str(used)}]
        assert run_startup_upload_cleanup(upload, repo) == 1
        assert used.exists()
        assert not (upload / "orphan.wav").exists()

    def test_no_repo_is_safe_noop(self, tmp_path):
        """无仓储可校验引用 → 不删除任何文件 (安全优先)."""
        upload = tmp_path / "uploads"
        upload.mkdir()
        (upload / "x.wav").write_bytes(b"x")
        assert run_startup_upload_cleanup(upload, None) == 0
        assert (upload / "x.wav").exists()
