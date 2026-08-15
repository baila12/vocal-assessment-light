"""ReportRequest filename 路径穿越防护 + validate_filepath is_relative_to — v7.19 整理回归

Gap 分析发现:
1. ReportRequest.filename 无校验, 直接拼入 output_dir / f'{filename}_report.pdf'
   → filename='../../evil' 可写出 output_dir (路径穿越)。
2. validate_filepath 用 str.startswith 做目录判定 — '/uploads_evil/x.mp3'
   因前缀匹配被误放行 (与 audio.py 的 is_relative_to 不一致)。
"""
import pytest

from pathlib import Path

from backend.interfaces.api.schemas.assessment import ReportRequest


class TestReportRequestFilenameSanitize:
    """ReportRequest.filename 应剥离路径分隔符/穿越片段"""

    def test_posix_traversal_stripped(self):
        r = ReportRequest(analysis_result={}, filename="../../evil")
        assert "/" not in r.filename and ".." not in r.filename
        assert Path(r.filename + "_report.pdf").is_relative_to(Path("."))

    def test_windows_traversal_stripped(self):
        r = ReportRequest(analysis_result={}, filename="..\\..\\evil")
        assert "\\" not in r.filename and ".." not in r.filename

    def test_absolute_path_stripped(self):
        r = ReportRequest(analysis_result={}, filename="/etc/passwd")
        assert "/" not in r.filename

    def test_empty_falls_back_to_report(self):
        r = ReportRequest(analysis_result={}, filename="   ")
        assert r.filename  # 非空 (回退 'report')

    def test_normal_chinese_filename_kept(self):
        r = ReportRequest(analysis_result={}, filename="歌手-歌曲")
        assert r.filename == "歌手-歌曲"

    def test_very_long_filename_truncated(self):
        r = ReportRequest(analysis_result={}, filename="x" * 200)
        assert len(r.filename) <= 64


class TestValidateFilepathDirectoryCheck:
    """validate_filepath 应使用 is_relative_to (严格目录判定), 非 startswith 前缀匹配"""

    @staticmethod
    def _config(tmp_path):
        class _Cfg:
            UPLOAD_FOLDER = tmp_path / "uploads"
            PROJECT_ROOT = tmp_path
            ALLOWED_EXTENSIONS = {".wav", ".mp3"}
        return _Cfg()

    def test_sibling_dir_prefix_rejected(self, tmp_path):
        """/uploads_evil/x.mp3 与 /uploads 前缀相同但不在其内 → 应 403"""
        from backend.interfaces.api.routes.assessment import validate_filepath
        from fastapi import HTTPException

        cfg = self._config(tmp_path)
        # 构造兄弟目录下的真实文件 (证明路径存在但不在 uploads 内)
        sibling = tmp_path / "uploads_evil"
        sibling.mkdir()
        f = sibling / "x.wav"
        f.write_bytes(b"\x00" * 4)

        with pytest.raises(HTTPException) as exc:
            validate_filepath(str(f), cfg)
        assert exc.value.status_code == 403

    def test_valid_upload_file_accepted(self, tmp_path):
        from backend.interfaces.api.routes.assessment import validate_filepath

        cfg = self._config(tmp_path)
        cfg.UPLOAD_FOLDER.mkdir(exist_ok=True)
        f = cfg.UPLOAD_FOLDER / "ok.wav"
        f.write_bytes(b"\x00" * 4)

        result = validate_filepath(str(f), cfg)
        assert result == f.resolve()

    def test_relative_escape_rejected(self, tmp_path):
        """uploads/../secret.wav 的 '..' 应被 403 拦截 (resolve 后不在 uploads 内)"""
        from backend.interfaces.api.routes.assessment import validate_filepath
        from fastapi import HTTPException

        cfg = self._config(tmp_path)
        cfg.UPLOAD_FOLDER.mkdir(exist_ok=True)
        secret = tmp_path / "secret.wav"
        secret.write_bytes(b"\x00" * 4)

        # 构造 uploads/../secret.wav (文件确实存在, resolve 后在 uploads 外)
        with pytest.raises(HTTPException) as exc:
            validate_filepath(str(cfg.UPLOAD_FOLDER / ".." / "secret.wav"), cfg)
        assert exc.value.status_code == 403
