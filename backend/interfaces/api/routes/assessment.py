"""
评估路由 v7.0 — 上传/分析/音高提取/人声分离/报告/对比

CPU 密集型操作通过 asyncio.to_thread() 避免阻塞 event loop。
"""

from __future__ import annotations
import asyncio
import re
import time
import unicodedata
from pathlib import Path
from datetime import datetime
import uuid
import logging

from fastapi import APIRouter, Depends, UploadFile, File, Form, Request, HTTPException
from fastapi.responses import FileResponse

from backend.interfaces.api.deps import (
    get_separation_service, get_report_service, get_history_repo,
    get_flask_config, get_auto_match_use_case,
)
from backend.interfaces.api.schemas.assessment import (
    UploadResponse, AnalyzeRequest, PitchExtractResponse,
    SeparateRequest, SeparateResponse, ReportRequest, ReportResponse,
    CompareRequest, CompareResponse,
)
from backend.domain.songs_pitch.services import PitchExtractionService, TARGET_SR

logger = logging.getLogger(__name__)
router = APIRouter()

# 404 错误消息常量
_FILE_NOT_FOUND = "文件不存在"
_INVALID_PATH = "无效的文件路径"
_FORBIDDEN_PATH = "无权访问此文件"


def _recover_garbled_name(name: str) -> str:
    """GBK 字节被误按 Latin-1 解码的乱码往返恢复 (P2-14)

    历史编码 bug 残留: `1£¨¸ß·Ö£©` 实为 `1（高分）` 的 GBK 字节
    (0xA3A8...) 被误按 Latin-1 解码。恢复 = latin-1 编码回原字节,
    再按 GBK 解码。仅当往返成功且结果含 CJK 才接受, 否则原样返回
    (不误伤合法 Latin-1 文件名如 `café`)。
    """
    try:
        recovered = name.encode("latin-1").decode("gbk")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return name
    if recovered == name:
        return name
    # CJK 统一表意文字基本区 + 扩展 A (U+3400-U+4DBF) + 兼容表意文字 (U+F900-U+FAFF)
    if not any(
        "㐀" <= ch <= "鿿" or "豈" <= ch <= "﫿" for ch in recovered
    ):
        return name
    return recovered


def sanitize_filename(filename: str) -> str:
    """安全处理文件名，保留中文字符

    处理顺序: GBK 乱码往返恢复 → Unicode NFC 规范化 (macOS NFD/Windows NFC
    落盘字节统一) → 剥离 Windows 非法字符 → 去首尾空白/点 (防 `..` 裸点
    stem 解析为父目录) → 空名回退。
    Path.stem 语义保留: `/` `\\` 视为路径分隔符取 basename (防路径穿越)。
    """
    name_part = Path(filename).stem
    ext_part = Path(filename).suffix
    name_part = _recover_garbled_name(name_part)
    name_part = unicodedata.normalize("NFC", name_part)
    safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name_part)
    safe_name = safe_name.strip().strip(".")
    if not safe_name:
        safe_name = f"audio_{int(time.time())}"
    return safe_name + ext_part


def validate_filepath(filepath: str, config) -> Path:
    """验证文件路径安全性"""
    if '..' in filepath or '~' in filepath:
        raise HTTPException(status_code=403, detail=_FORBIDDEN_PATH)
    if re.search(r'[\x00-\x1f\x7f]', filepath):
        raise HTTPException(status_code=403, detail=_FORBIDDEN_PATH)

    filepath_obj = Path(filepath)
    if filepath_obj.suffix.lower() not in config.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=403, detail="不支持的文件格式")

    try:
        filepath_obj = filepath_obj.resolve()
    except Exception:
        raise HTTPException(status_code=403, detail=_INVALID_PATH)

    upload_dir = config.UPLOAD_FOLDER.resolve()
    test_dir = (config.PROJECT_ROOT / "tests" / "test_data" / "audio").resolve()
    filepath_str = str(filepath_obj)

    if not (filepath_str.startswith(str(upload_dir)) or filepath_str.startswith(str(test_dir))):
        raise HTTPException(status_code=403, detail=_FORBIDDEN_PATH)
    if not filepath_obj.exists() or not filepath_obj.is_file():
        raise HTTPException(status_code=404, detail=_FILE_NOT_FOUND)

    return filepath_obj


def _serialize_compare_pitch(path: str, tag: str) -> list[dict]:
    """WAV → [{time, frequency, confidence}] — v7.13 Phase 5 双轨曲线序列化。

    提取失败返回空列表 (优雅降级, 不阻塞对比评分)。
    """
    try:
        curve = PitchExtractionService.extract(path, song_id=tag)
        return [
            {"time": float(t), "frequency": float(f), "confidence": float(c)}
            for t, f, c in zip(curve.times, curve.frequencies, curve.confidence)
        ]
    except Exception:
        logger.warning("Pitch extraction failed for %s, omitting curve", tag, exc_info=True)
        return []


def _save_history(result: dict, filepath: str, analysis_id: str, repo) -> None:
    """保存分析结果到历史记录 (v7.2: 存储完整六维字段 + analysis_id)"""
    try:
        basic_info = result.get("basic_info", {}) or {}
        record = {
            "analysis_id": analysis_id,
            "filename": basic_info.get("filename", Path(filepath).name),
            "filepath": filepath,
            "total_score": result.get("total_score", 0),
            "scores": result.get("scores", {}),
            "level": result.get("level", ""),
            "grade": result.get("grade", ""),
            "advice": result.get("advice", []),
            "mode": result.get("mode", "quick"),
            "timbre_adjustment": result.get("timbre_adjustment", 0),
            "heuristic_dimensions": result.get("heuristic_dimensions", []),
            "normalization": result.get("normalization"),
            "basic_info": basic_info,
            "duration": basic_info.get("duration_seconds", 0),
            "is_voice": result.get("is_voice", True),
            "created_at": datetime.now().isoformat(),
        }
        repo.save(record)
    except Exception:
        logger.exception("Failed to save history record")


# ===== POST /api/v1/upload =====
@router.post("/upload", response_model=UploadResponse)
async def upload_audio(
    file: UploadFile = File(...),
    mode: str = Form(default="quick"),
    reference_file: UploadFile | None = File(default=None),
    auto_match: bool = Form(default=False),
    config=Depends(get_flask_config),
    repo=Depends(get_history_repo),
    match_usecase=Depends(get_auto_match_use_case),
):
    """上传并分析音频文件"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="没有选择文件")
    if not config.is_allowed_extension(file.filename):
        raise HTTPException(status_code=400, detail="不支持的文件格式")
    if mode not in ('quick', 'professional'):
        raise HTTPException(status_code=400, detail=f"无效的评估模式: {mode}，仅支持 quick 或 professional")

    safe_name = sanitize_filename(file.filename)
    filepath = config.get_upload_path(safe_name)

    content = await file.read()
    filepath.write_bytes(content)

    # 可选参考音频 (v7.16 Phase 5.3: analyze_and_score 不再消费 reference_path, 上传保留向后兼容)
    if reference_file and reference_file.filename and config.is_allowed_extension(reference_file.filename):
        ref_safe = sanitize_filename(reference_file.filename)
        ref_path = config.get_upload_path(ref_safe)
        ref_content = await reference_file.read()
        ref_path.write_bytes(ref_content)

    try:
        from api.business import analyze_and_score
        from services.feature_flags import FeatureFlags

        result = await asyncio.to_thread(
            analyze_and_score,
            str(filepath),
            mode=mode,
            feature_flags=FeatureFlags.for_quick() if mode == 'quick' else FeatureFlags.for_professional(),
        )
    except Exception:
        logger.exception("Analysis failed")
        raise HTTPException(status_code=500, detail="分析失败，请稍后重试")

    # 生成分析 ID (前端路由 /report/:id 需要) — 必须在 _save_history 之前生成
    analysis_id = str(uuid.uuid4())[:12]
    # 派生 grade (旧版评分管线可能未填充 grade 字段)
    grade = result.get("grade", "")
    if not grade and result.get("level"):
        from backend.shared.domain_types import ScoreLevel
        grade = ScoreLevel.from_score(result.get("total_score", 0)).grade
    result["grade"] = grade
    result["analysis_id"] = analysis_id

    if result.get("success"):
        _save_history(result, str(filepath), analysis_id, repo)

    # 构建归一化信息
    norm_data = result.get("normalization")
    if isinstance(norm_data, dict):
        normalization = {"applied": norm_data.get("applied", True), "note": norm_data.get("note", "")}
    else:
        normalization = {"applied": True, "note": ""}

    # v7.14: 可选自动匹配标准歌曲 — 失败优雅降级, 不阻塞主分析
    matched_song = None
    matched_candidates: list[dict] = []
    fallback_reason = ""
    if auto_match:
        try:
            match_result = await asyncio.to_thread(match_usecase.execute, str(filepath))
            matched_song = match_result.matched_song
            matched_candidates = [c.to_dict() for c in match_result.candidates]
            fallback_reason = match_result.fallback_reason
        except Exception:
            logger.warning("Auto-match failed for upload, degraded gracefully", exc_info=True)

    return UploadResponse(
        success=result.get("success", False),
        analysis_id=analysis_id,
        total_score=result.get("total_score", 0),
        scores=result.get("scores", {}),
        timbre_adjustment=result.get("timbre_adjustment", 0),
        level=result.get("level", ""),
        grade=grade,
        advice=result.get("advice", []),
        mode=result.get("mode", "quick"),
        is_voice=result.get("is_voice", True),
        filepath=str(filepath),
        basic_info=result.get("basic_info"),
        heuristic_dimensions=result.get("heuristic_dimensions", []),
        scoring_warnings=result.get("scoring_warnings", []),
        normalization=normalization,
        duration=result.get("duration_seconds"),
        duration_display=result.get("duration", ""),
        matched_song=matched_song,
        matched_candidates=matched_candidates,
        fallback_reason=fallback_reason,
    )


# ===== POST /api/v1/analyze =====
@router.post("/analyze", response_model=UploadResponse)
async def analyze_file(
    body: AnalyzeRequest,
    config=Depends(get_flask_config),
    repo=Depends(get_history_repo),
):
    """分析已存在的音频文件"""
    filepath_obj = validate_filepath(body.filepath, config)

    # v7.16 Phase 5.3: analyze_and_score 不再消费 reference_filepath (body 字段保留向后兼容)
    try:
        from api.business import analyze_and_score
        from services.feature_flags import FeatureFlags

        result = await asyncio.to_thread(
            analyze_and_score,
            str(filepath_obj),
            mode=body.mode,
            feature_flags=FeatureFlags.for_quick() if body.mode == 'quick' else FeatureFlags.for_professional(),
        )
    except Exception:
        logger.exception("Analysis failed")
        raise HTTPException(status_code=500, detail="分析失败，请稍后重试")

    # 生成 analysis_id
    analysis_id = str(uuid.uuid4())[:12]
    grade = result.get("grade", "")
    if not grade and result.get("level"):
        from backend.shared.domain_types import ScoreLevel
        grade = ScoreLevel.from_score(result.get("total_score", 0)).grade
    result["grade"] = grade
    result["analysis_id"] = analysis_id

    if result.get("success"):
        _save_history(result, str(filepath_obj), analysis_id, repo)

    # 构建 NormalizationInfo
    norm_data = result.get("normalization")
    if isinstance(norm_data, dict):
        normalization = {"applied": norm_data.get("applied", True), "note": norm_data.get("note", "")}
    else:
        normalization = {"applied": True, "note": ""}

    return UploadResponse(
        success=result.get("success", False),
        analysis_id=analysis_id,
        total_score=result.get("total_score", 0),
        scores=result.get("scores", {}),
        timbre_adjustment=result.get("timbre_adjustment", 0),
        level=result.get("level", ""),
        grade=grade,
        advice=result.get("advice", []),
        mode=result.get("mode", "quick"),
        is_voice=result.get("is_voice", True),
        filepath=str(filepath_obj),
        basic_info=result.get("basic_info"),
        heuristic_dimensions=result.get("heuristic_dimensions", []),
        scoring_warnings=result.get("scoring_warnings", []),
        normalization=normalization,
        duration=result.get("duration_seconds"),
        duration_display=result.get("duration", ""),
    )


# ===== POST /api/v1/extract-pitch =====
@router.post("/extract-pitch")
async def extract_pitch(
    file: UploadFile | None = File(default=None),
    config=Depends(get_flask_config),
):
    """提取音高曲线"""
    import librosa
    import numpy as np

    if file and file.filename:
        if not config.is_allowed_extension(file.filename):
            raise HTTPException(status_code=400, detail="不支持的文件格式")
        safe_name = sanitize_filename(file.filename)
        filepath = config.get_upload_path(safe_name)
        content = await file.read()
        filepath.write_bytes(content)
        filepath_str = str(filepath)
    else:
        raise HTTPException(status_code=400, detail="需要上传音频文件")

    try:
        # P2-11: 一步加载到 TARGET_SR (原 sr=None 原生加载再两次重采样, 峰值内存 ~2.7x)
        y, sr = await asyncio.to_thread(librosa.load, filepath_str, sr=TARGET_SR, mono=True)

        hop_length = 512
        f0 = librosa.yin(y, fmin=65.0, fmax=1047.0, sr=sr, hop_length=hop_length)
        times = librosa.times_like(f0, sr=sr, hop_length=hop_length)
        confidence = (~np.isnan(f0)).astype(float)

        return PitchExtractResponse(
            success=True,
            data={
                "duration": float(len(y) / sr),
                "sample_rate": sr,
                "hop_length": hop_length,
                "frequencies": [float(np.nan_to_num(f, nan=0.0)) for f in f0],
                "times": times.tolist(),
                "confidence": confidence.tolist(),
                "frame_count": len(f0),
            },
        )
    except Exception:
        logger.exception("Pitch extraction failed")
        return PitchExtractResponse(success=False, error="音高提取失败，请稍后重试")


# ===== POST /api/v1/separate =====
@router.post("/separate", response_model=SeparateResponse)
async def separate_audio(
    body: SeparateRequest,
    sep_service=Depends(get_separation_service),
    config=Depends(get_flask_config),
):
    """人声分离 (Demucs)"""
    # 路径安全验证 (修复: C-1 path traversal)
    validate_filepath(body.filepath, config)
    if not Path(body.filepath).exists():
        raise HTTPException(status_code=404, detail=_FILE_NOT_FOUND)

    try:
        result = await asyncio.to_thread(
            sep_service.separate,
            audio_path=body.filepath,
            model=body.model,
            two_stems=body.two_stems,
            output_format="mp3",
        )
    except Exception:
        logger.exception("Audio separation failed")
        raise HTTPException(status_code=500, detail="人声分离失败，请稍后重试")

    return SeparateResponse(
        success=result.success,
        vocals_path=result.vocals_path,
        accompaniment_path=result.accompaniment_path,
        drums_path=result.drums_path,
        bass_path=result.bass_path,
        other_path=result.other_path,
        duration=result.duration,
        model_used=result.model_used,
        error=result.error_message,
    )


# ===== GET /api/v1/separate/models =====
@router.get("/separate/models")
async def get_separation_models(sep_service=Depends(get_separation_service)):
    """获取可用的分离模型列表"""
    return {"models": sep_service.get_available_models()}


# ===== POST /api/v1/report =====
@router.post("/report", response_model=ReportResponse)
async def generate_report(
    body: ReportRequest,
    report_service=Depends(get_report_service),
):
    """生成评估报告 (PDF/图片)"""
    try:
        if body.format == "pdf":
            result = await asyncio.to_thread(
                report_service.generate_pdf_report,
                body.analysis_result, body.filename,
            )
        else:
            result = await asyncio.to_thread(
                report_service.generate_image_report,
                body.analysis_result, body.filename,
            )
    except Exception:
        logger.exception("Report generation failed")
        raise HTTPException(status_code=500, detail="报告生成失败，请稍后重试")

    return ReportResponse(
        success=result.success,
        pdf_path=result.pdf_path,
        image_path=result.image_path,
        error=result.error_message,
    )


# ===== POST /api/v1/compare =====
@router.post("/compare", response_model=CompareResponse)
async def compare_audio(
    request: Request,
    config=Depends(get_flask_config),
):
    """对比分析两个音频文件 (支持 JSON 和 FormData)"""
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        form = await request.form()
        user_file = form.get("user_file")
        standard_file = form.get("standard_file")

        if not user_file or not standard_file or not hasattr(user_file, 'filename'):
            raise HTTPException(status_code=400, detail="缺少音频文件")

        if not config.is_allowed_extension(user_file.filename):
            raise HTTPException(status_code=400, detail="不支持的用户音频格式")
        if not config.is_allowed_extension(standard_file.filename):
            raise HTTPException(status_code=400, detail="不支持的标准音频格式")

        user_safe = sanitize_filename(user_file.filename)
        std_safe = sanitize_filename(standard_file.filename)
        user_path = config.get_upload_path(user_safe)
        std_path = config.get_upload_path(std_safe)

        user_path.write_bytes(await user_file.read())
        std_path.write_bytes(await standard_file.read())

        filepath_std = str(std_path)
        filepath_user = str(user_path)
        style = form.get("style", "pop")
    else:
        body = await request.json()
        # v7.3: 使用 Pydantic 模型验证 JSON 输入
        compare_req = CompareRequest(**body)
        filepath_std = compare_req.standard_filepath
        filepath_user = compare_req.user_filepath
        style = compare_req.style

        if not filepath_std or not filepath_user:
            raise HTTPException(status_code=400, detail="缺少文件路径")
        validate_filepath(filepath_std, config)
        validate_filepath(filepath_user, config)

    try:
        from api.business import compare_with_dtw, analyze_and_score
        from services.feature_flags import FeatureFlags

        # v7.3: 尝试 DDD comparison 路径, 失败时回退到旧路径
        dtw_result = None
        try:
            from backend.application.comparison.compare_audio import CompareAudioUseCase
            usecase = CompareAudioUseCase()
            dto = usecase.execute_lightweight(filepath_std, filepath_user, style=style)
            # 将 DDD DTO 映射为旧格式 (保持 response 兼容)
            dtw_result = {
                "success": True,
                "score": dto["score"],
                "level": dto["level"],
                "confidence": dto["confidence"],
                "pitch_match_rate": dto["pitch_match_rate"],
                "rhythm_match_rate": dto["rhythm_match_rate"],
                "avg_cents_error": dto["avg_cents_error"],
                "diagnosis": dto["diagnosis"],
                "suggestions": dto["suggestions"],
                "method": dto["method"],
                "dimensions": {},  # DDD lightweight 模式暂不返回 dimensions
            }
        except Exception:
            logger.warning("DDD comparison path failed, falling back to legacy")
            dtw_result = await asyncio.to_thread(
                compare_with_dtw, filepath_std, filepath_user, style=style
            )

        if not dtw_result or not dtw_result.get("success"):
            raise HTTPException(status_code=500, detail="DTW对比分析失败")

        # v7.13 Phase 5: 双轨音高曲线 (与选歌参考同管线, 前端时间戳对齐)
        standard_pitch = await asyncio.to_thread(
            _serialize_compare_pitch, filepath_std, "compare_standard"
        )
        user_pitch = await asyncio.to_thread(
            _serialize_compare_pitch, filepath_user, "compare_user"
        )

        # 低对齐置信度段落 (DTW 整体置信度 < 0.5 → 整段标记, 前端灰色虚线 + 统计排除)
        low_alignment: list[dict] = []
        if dtw_result.get("confidence", 1.0) < 0.5 and standard_pitch:
            low_alignment = [{
                "start": 0.0,
                "end": standard_pitch[-1]["time"],
                "avg_confidence": dtw_result["confidence"],
            }]

        # 审查 P4/P1-7: 用 quick 标志而非默认 Pro (FeatureFlags() 全部 True → Demucs 串行 ~310s)
        standard_result = await asyncio.to_thread(
            analyze_and_score, filepath_std, feature_flags=FeatureFlags.for_quick()
        )
        user_result = await asyncio.to_thread(
            analyze_and_score, filepath_user, feature_flags=FeatureFlags.for_quick()
        )

        dtw_dims = dtw_result.get("dimensions", {})
        comparison = {
            "pitch_diff": round(abs(dtw_dims.get("pitch", {}).get("score", 50) - 50), 1),
            "rhythm_diff": round(abs(dtw_dims.get("rhythm", {}).get("score", 50) - 50), 1),
            "total_diff": round(abs(dtw_result.get("score", 50) - 50), 1),
            "std_total": 100.0,
            "user_total": dtw_result.get("score", 50),
            "pitch_match_rate": dtw_result.get("pitch_match_rate", 50),
            "suggestions": dtw_result.get("suggestions", []),
        }

        return CompareResponse(
            success=True,
            data={
                "score": dtw_result["score"],
                "level": dtw_result["level"],
                "confidence": dtw_result["confidence"],
                "pitch_match_rate": dtw_result["pitch_match_rate"],
                "rhythm_match_rate": dtw_result["rhythm_match_rate"],
                "avg_cents_error": dtw_result["avg_cents_error"],
                "diagnosis": dtw_result["diagnosis"],
                "suggestions": dtw_result["suggestions"],
                "dimensions": dtw_dims,
                "method": dtw_result.get("method", "three_level_dtw"),
                "standard": standard_result if standard_result.get("success") else None,
                "user": user_result if user_result.get("success") else None,
                "comparison": comparison,
                "standard_pitch": standard_pitch,
                "user_pitch": user_pitch,
                "low_alignment_segments": low_alignment,
            },
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Compare analysis failed")
        raise HTTPException(status_code=500, detail="对比分析失败，请稍后重试")
