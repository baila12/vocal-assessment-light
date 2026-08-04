"""
Feature Flags API — v7.7

GET /api/v1/flags — 返回当前算法开关、GPU状态、模型可用性。
用于前端 Settings 面板展示算法状态。
"""

from fastapi import APIRouter
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/flags")
async def get_feature_flags():
    """返回当前 Feature Flag 状态和设备信息"""

    # ---- GPU 检测 ----
    try:
        from backend.main import _detect_gpu
        gpu_info = _detect_gpu()
    except Exception:
        gpu_info = {"available": False, "device": "error", "name": None}

    # ---- audiofeat 可用性 ----
    audiofeat_available = False
    try:
        import audiofeat
        audiofeat_available = True
    except ImportError:
        pass

    # ---- timbral_models 可用性 ----
    timbral_models_available = False
    try:
        import timbral_models
        timbral_models_available = True
    except ImportError:
        pass

    # ---- DL 模型状态 ----
    from pathlib import Path
    _project_root = Path(__file__).parent.parent.parent.parent.parent
    models_dir = _project_root / "models"
    models_status = {
        "style_classifier": (models_dir / "style_classifier" / "model.onnx").exists(),
        "vad": (models_dir / "voice_quality" / "silero_vad.onnx").exists(),
        "emotion": (models_dir / "emotion" / "wav2vec2.ckpt").exists(),
        "demucs": True,  # demucs 通过 pip 安装, 不依赖本地模型文件
    }

    # ---- Dimension Weights (v7.11: 单一数据来源 ScoringWeights) ----
    from backend.domain.assessment.scoring_weights import ScoringWeights
    _default_weights = ScoringWeights.default()
    dimension_weights = {
        "pitch": round(_default_weights.pitch * 100),
        "rhythm": round(_default_weights.rhythm * 100),
        "breath": round(_default_weights.breath * 100),
        "technique": round(_default_weights.technique * 100),
        "muscle_strength": round(_default_weights.muscle * 100),
        "artistry": round(_default_weights.artistry * 100),
    }

    # ---- Feature Flags ----
    try:
        # v7.8: 通过桥接层反映运行时 FeatureFlags 配置,
        # 修复 audiofeat 等开关显示为领域层类默认值 (enable_audiofeat=False) 的问题
        from services.feature_flags import FeatureFlags
        from backend.shared.flag_bridge import to_dimension_flags
        flags = to_dimension_flags(FeatureFlags())
        enhancements = {
            "audiofeat": flags.enable_audiofeat,
            "multiscale_hnr": flags.enable_multiscale_hnr,
            "praat_cpp": flags.enable_praat_cpp,
            "voicing_detection": flags.enable_voicing_detection,
            "torchcrepe_fallback": flags.enable_torchcrepe_fallback,
            "cross_dimension_modifiers": flags.enable_cross_dimension_modifiers,
            "reverb_compensation": flags.enable_reverb_compensation,
            "praat_voice_quality": flags.enable_praat_voice_quality,
        }
        dimensions = {
            "pitch": flags.enable_pitch,
            "rhythm": flags.enable_rhythm,
            "breath": flags.enable_breath,
            "technique": flags.enable_technique,
            "muscle_strength": flags.enable_muscle_strength,
            "artistry": flags.enable_artistry,
            "timbre_adjustment": flags.enable_timbre_adjustment,
        }
    except Exception:
        enhancements = {}
        dimensions = {}

    return {
        "success": True,
        "data": {
            "dimensions": dimensions,
            "enhancements": enhancements,
            "experimental": {
                "audiofeat_installed": audiofeat_available,
                "timbral_models_installed": timbral_models_available,
                "fcpe": False,  # FCPE 默认未启用
            },
            "gpu": gpu_info,
            "models": models_status,
            "dimension_weights": dimension_weights,
        },
    }
