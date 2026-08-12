"""
JsonHistoryRepository — 删除/淘汰同步清理上传文件 (v7.15 P2-14)

DEEP_REVIEW E4/V8: uploads/ 永不清理。根因之一是历史记录删除/淘汰时
不解除引用 — 记录移除后其 filepath 指向的上传文件沦为孤儿永久残留。

修复 (TDD RED→GREEN):
  - delete() / delete_batch() / save() 淘汰分支 → 同步清理被移除记录的文件
  - 仅当构造传入 upload_dir 时启用 (向后兼容: 默认 None 不清理)
  - 安全约束: 只删 uploads 目录内文件; 仍被其他记录引用的共享文件不删
"""
from __future__ import annotations

from repositories.history_repository import JsonHistoryRepository


class TestHistoryRepositoryUnlink:
    def _repo(self, tmp_path, max_records=50, upload_dir=True):
        history = tmp_path / "history.json"
        ud = tmp_path / "uploads"
        ud.mkdir()
        repo = JsonHistoryRepository(
            history,
            max_records=max_records,
            upload_dir=(ud if upload_dir else None),
        )
        return repo, ud

    def test_delete_unlinks_record_file(self, tmp_path):
        repo, ud = self._repo(tmp_path)
        f = ud / "a.wav"
        f.write_bytes(b"data")
        rec = repo.save({"filepath": str(f)})
        assert f.exists()
        assert repo.delete(rec["id"]) is True
        assert not f.exists()

    def test_delete_without_upload_dir_keeps_file(self, tmp_path):
        """向后兼容: 未传 upload_dir 时保持旧行为 — 不清理文件."""
        repo, ud = self._repo(tmp_path, upload_dir=False)
        f = ud / "a.wav"
        f.write_bytes(b"data")
        rec = repo.save({"filepath": str(f)})
        repo.delete(rec["id"])
        assert f.exists()

    def test_delete_shared_file_still_referenced_kept(self, tmp_path):
        """同一文件被两条记录引用时, 删一条不误删文件 (另一条仍引用)."""
        repo, ud = self._repo(tmp_path)
        f = ud / "shared.wav"
        f.write_bytes(b"data")
        r1 = repo.save({"filepath": str(f)})
        r2 = repo.save({"filepath": str(f)})
        repo.delete(r1["id"])
        assert f.exists()

    def test_delete_batch_unlinks_each(self, tmp_path):
        repo, ud = self._repo(tmp_path)
        files, recs = [], []
        for i in range(3):
            f = ud / f"{i}.wav"
            f.write_bytes(b"d")
            files.append(f)
            recs.append(repo.save({"filepath": str(f)}))
        assert repo.delete_batch([r["id"] for r in recs]) == 3
        for f in files:
            assert not f.exists()

    def test_save_eviction_unlinks_evicted_files(self, tmp_path):
        repo, ud = self._repo(tmp_path, max_records=2)
        evicted = ud / "r0.wav"
        evicted.write_bytes(b"d")
        repo.save({"filepath": str(evicted)})
        keep = []
        for i in (1, 2):
            f = ud / f"r{i}.wav"
            f.write_bytes(b"d")
            keep.append(f)
            repo.save({"filepath": str(f)})
        # max_records=2 → 第 1 条 (r0) 被淘汰, 其上传文件应被清理
        assert not evicted.exists()
        for f in keep:
            assert f.exists()

    def test_save_eviction_does_not_unlink_outside_upload_dir(self, tmp_path):
        """被淘汰记录指向 uploads 目录外文件 (如测试音频) → 防御不删."""
        repo, ud = self._repo(tmp_path, max_records=1)
        outside = tmp_path / "outside.wav"
        outside.write_bytes(b"d")
        inside = ud / "new.wav"
        inside.write_bytes(b"d")
        repo.save({"filepath": str(outside)})
        repo.save({"filepath": str(inside)})
        # 第 1 条 (outside) 被淘汰 — 但文件不在 uploads 内 → 保留
        assert outside.exists()
        assert inside.exists()
