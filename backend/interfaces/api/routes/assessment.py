"""
评估路由 v7.0 — 上传/分析/音高提取/人声分离/报告/对比

CPU 密集型操作通过 asyncio.to_thread() 避免阻塞 event loop。
"""

from __future__ import annotations
import asyncio
import re
import time
from pathlib import Path
import logging

from fastapi import APIRouter, Depends, UploadFile, File, Form, Request, HTTPException
from fastapi.responses import FileResponse

from backend.interfaces.api.deps import (
    get_separation_service, get_report_service, get_history_repo,
    get_flask_config,
)
from backend.interfaces.api.schemas.assessment import (
    UploadResponse, AnalyzeRequest, PitchExtractResponse,
    SeparateRequest, SeparateResponse, ReportRequest, ReportResponse,
    CompareRequest, CompareResponse,
)
import uuid

logger = logging.getLogger(__name__)
router = APIRouter()

# 404 错误消息常量
_FILE_NOT_FOUND = "文件不存在"
_INVALID_PATH = "无效的文件路径"
_FORBIDDEN_PATH = "无权访问此文件"


def sanitize_filename(filename: str) -> str:
    """安全处理文件名，保留中文字符"""
    name_part = Path(filename).stem
    ext_part = Path(filename).suffix
    safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name_part)
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


def _save_history(result: dict, filepath: str, repo) -> None:
    """保存分析结果到历史记录"""
    try:
        record = {
            "filename": result.get("basic_info", {}).get("filename", Path(filepath).name),
            "filepath": filepath,
            "total_score": result.get("total_score", 0),
            "scores": result.get("scores", {}),
            "level": result.get("level", ""),
            "advice": result.get("advice", []),
            "mode": result.get("mode", "quick"),
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
    config=Depends(get_flask_config),
    repo=Depends(get_history_repo),
):
    """上传并分析音频文件"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="没有选择文件")
    if not config.is_allowed_extension(file.filename):
        raise HTTPException(status_code=400, detail="不支持的文件格式")

    safe_name = sanitize_filename(file.filename)
    filepath = config.get_upload_path(safe_name)

    content = await file.read()
    filepath.write_bytes(content)

    # 可选参考音频
    reference_path = None
    if reference_file and reference_file.filename and config.is_allowed_extension(reference_file.filename):
        ref_safe = sanitize_filename(reference_file.filename)
        ref_path = config.get_upload_path(ref_safe)
        ref_content = await reference_file.read()
        ref_path.write_bytes(ref_content)
        reference_path = str(ref_path)

    try:
        from api.business import analyze_and_score
        from services.feature_flags import FeatureFlags

        result = await asyncio.to_thread(
            analyze_and_score,
            str(filepath),
            mode=mode,
            reference_path=reference_path,
            feature_flags=FeatureFlags(),
        )
    except Exception as e:
        logger.exception(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"分析失败: {e}")

    if result.get("success"):
        _save_history(result, str(filepath), repo)

    # 生成分析 ID (前端路由 /report/:id 需要)
    analysis_id = str(uuid.uuid4())[:12]
    # 派生 grade (旧版评分管线可能未填充 grade 字段)
    grade = result.get("grade", "")
    if not grade and result.get("level"):
        from backend.shared.domain_types import ScoreLevel
        grade = ScoreLevel.from_score(result.get("total_score", 0)).grade

    return UploadResponse(
        success=result.get("success", False),
        analysis_id=analysis_id,
        total_score=result.get("total_score", 0),
        scores=result.get("scores", {}),
        level=result.get("level", ""),
        grade=grade,
        advice=result.get("advice", []),
        mode=result.get("mode", "quick"),
        is_voice=result.get("is_voice", True),
        filepath=str(filepath),
        basic_info=result.get("basic_info"),
        heuristic_dimensions=result.get("heuristic_dimensions", []),
    )


# ===== POST /api/v1/analyze =====
@router.post("/analyze")
async def analyze_file(
    body: AnalyzeRequest,
    config=Depends(get_flask_config),
    repo=Depends(get_history_repo),
):
    """分析已存在的音频文件"""
    filepath_obj = validate_filepath(body.filepath, config)

    ref_path = None
    if body.reference_filepath:
        try:
            ref_obj = validate_filepath(body.reference_filepath, config)
            ref_path = str(ref_obj)
        except Exception:
            pass

    try:
        from api.business import analyze_and_score
        from services.feature_flags import FeatureFlags

        result = await asyncio.to_thread(
            analyze_and_score,
            str(filepath_obj),
            mode=body.mode,
            reference_path=ref_path,
            feature_flags=FeatureFlags(),
        )
    except Exception as e:
        logger.exception(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"分析失败: {e}")

    if result.get("success"):
        _save_history(result, str(filepath_obj), repo)

    return result


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
        TARGET_SR = 16000
        y, sr = await asyncio.to_thread(librosa.load, filepath_str, sr=None, mono=True)
        if sr > TARGET_SR:
            y = librosa.resample(y, orig_sr=sr, target_sr=TARGET_SR)
            sr = TARGET_SR

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
    except Exception as e:
        logger.exception(f"音高提取失败: {e}")
        return PitchExtractResponse(success=False, error=str(e))


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

    result = await asyncio.to_thread(
        sep_service.separate,
        audio_path=body.filepath,
        model=body.model,
        two_stems=body.two_stems,
        output_format="mp3",
    )

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

    return ReportResponse(
        success=result.success,
        pdf_path=result.pdf_path,
        image_path=result.image_path,
        error=result.error_message,
    )


# ===== POST /api/v1/compare =====
@router.post("/compare")
async def compare_audio(
    request: Request,
    config=Depends(get_flask_config),
):
    """对比分析两个音频文件 (支持 JSON 和 FormData)"""
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        form = await request.form()
        user_file = form.get("file")
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
        filepath_std = body.get("standard_filepath")
        filepath_user = body.get("user_filepath")
        style = body.get("style", "pop")

        if not filepath_std or not filepath_user:
            raise HTTPException(status_code=400, detail="缺少文件路径")
        validate_filepath(filepath_std, config)
        validate_filepath(filepath_user, config)

    try:
        from api.business import compare_with_dtw, analyze_and_score
        from services.feature_flags import FeatureFlags

        dtw_result = await asyncio.to_thread(
            compare_with_dtw, filepath_std, filepath_user, style=style
        )
        if not dtw_result.get("success"):
            raise HTTPException(status_code=500, detail=dtw_result.get("error", "DTW对比分析失败"))

        standard_result = await asyncio.to_thread(
            analyze_and_score, filepath_std, feature_flags=FeatureFlags()
        )
        user_result = await asyncio.to_thread(
            analyze_and_score, filepath_user, feature_flags=FeatureFlags()
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
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Compare analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"分析失败: {e}")
