"""
CompareAudioUseCase — v7.3 Phase 3

DDD 对比分析用例: 编排旧 DTW 引擎 + 新 DDD 评分服务
绞杀者模式: 复用 services/comparison/ 的特征提取 + DTW 对齐,
用 DDD ComparisonScoringService 替换旧评分引擎。
"""

from __future__ import annotations
import logging
import time
from typing import Dict

from backend.application.assessment.advice_generator import AdviceGenerator
from backend.domain.comparison.entities import (
    ComparisonResult, AlignmentData, DeviationData,
)
from backend.domain.comparison.services import ComparisonScoringService

logger = logging.getLogger(__name__)


class CompareAudioUseCase:
    """DDD 对比分析用例

    用法:
        usecase = CompareAudioUseCase()
        result = usecase.execute(std_path, user_path, style="pop")
        # result 是 ComparisonResult 聚合根
    """

    def __init__(self):
        self._scoring = ComparisonScoringService()

    def execute(
        self,
        standard_path: str,
        user_path: str,
        style: str = "pop",
    ) -> ComparisonResult:
        """执行完整对比分析流程"""
        start = time.time()

        # 1. 特征提取 + DTW对齐 (复用旧服务层)
        from services.comparison.comparison_service import ComparisonService
        legacy = ComparisonService(style=style)
        legacy_result = legacy.compare_audio_files(standard_path, user_path, style)

        # 2. 构建 DDD 实体
        alignment = AlignmentData(
            confidence=legacy_result.get("confidence", 1.0),
            method=legacy_result.get("method", "three_level_dtw"),
            compute_time_ms=legacy_result.get("compute_time_ms", 0),
        )

        # 从 legacy dimensions 提取偏差数据
        dims = legacy_result.get("dimensions", {})
        deviation = DeviationData(
            avg_pitch_cents=legacy_result.get("avg_cents_error", 0),
            # v7.19 整理: 补 max_pitch_cents 映射 — 旧实现遗漏, 导致
            # _score_pitch 的 max_deviation 恒 0.0 / problem_count 恒 0
            max_pitch_cents=dims.get("pitch", {}).get("max_deviation", 0),
            avg_rhythm_ms=dims.get("rhythm", {}).get("avg_deviation", 0),
            avg_volume_percent=dims.get("volume", {}).get("avg_deviation", 0),
            avg_breath_stability=dims.get("breath", {}).get("stability", 1.0),
            octave_error_rate=legacy_result.get("octave_error_rate", 0.0),  # v7.18 P1 (F2)
            tempo_ratio=legacy_result.get("tempo_ratio", 1.0),              # v7.18 P1 (F1)
        )

        # 3. DDD 评分
        scoring = self._scoring.score(deviation, confidence=alignment.confidence, style=style)

        compute_ms = (time.time() - start) * 1000

        return ComparisonResult(
            alignment=alignment,
            deviation=deviation,
            scoring=scoring,
            method=alignment.method,
            compute_time_ms=compute_ms,
        )

    def execute_lightweight(
        self,
        standard_path: str,
        user_path: str,
        style: str = "pop",
    ) -> Dict:
        """轻量模式: 仅返回前端需要的字段 (兼容旧 API)"""
        result = self.execute(standard_path, user_path, style)

        # v7.19 E5: 建议复用 DDD AdviceGenerator (四维子集), 消除 domain generate_suggestions 硬编码
        advice = AdviceGenerator().generate(
            {
                "pitch_score": result.scoring.pitch.score,
                "rhythm_score": result.scoring.rhythm.score,
                "volume_score": result.scoring.volume.score,
                "breath_score": result.scoring.breath.score,
                "total_score": result.overall_score,
                "total": result.overall_score,  # AdviceGenerator 契约: total 兼容键
            },
            dimensions=("pitch", "rhythm", "volume", "breath"),
        )

        return {
            "success": True,
            "score": result.overall_score,
            "level": result.level,
            "confidence": result.alignment.confidence,
            "pitch_match_rate": result.scoring.pitch.score,
            "rhythm_match_rate": result.scoring.rhythm.score,
            "avg_cents_error": result.deviation.avg_pitch_cents,
            "diagnosis": self._diagnosis_from_result(result),
            "suggestions": advice.advice,
            "method": result.method,
        }

    @staticmethod
    def _diagnosis_from_result(result: ComparisonResult) -> list:
        """从 ComparisonResult 生成诊断"""
        s = result.scoring
        d = result.deviation
        diagnosis = []

        if s.pitch.score >= 90:
            diagnosis.append("音准表现优秀，与标准音频高度匹配")
        elif s.pitch.score >= 75:
            diagnosis.append(f"音准整体良好，平均偏差{d.avg_pitch_cents:.1f}音分")
        elif s.pitch.score >= 60:
            diagnosis.append("音准需要提高，建议多听标准音频找准音高")
        else:
            diagnosis.append("音准偏差较大，建议先练习音阶建立音准感")

        if s.rhythm.score >= 85:
            diagnosis.append("节奏把握准确，与标准音频同步良好")
        elif s.rhythm.score >= 70:
            diagnosis.append("节奏基本正确，注意不要抢拍或拖拍")
        else:
            diagnosis.append("节奏需要加强，建议跟着节拍器练习")

        # v7.18 P1 O2: 该维度实为能量/音量波动 (非声学气息, 真气息 GNE/CPPS 见 P2)
        if s.breath.score < 70:
            diagnosis.append("音量/能量波动较大，建议保持稳定的音量输出")

        # v7.18 P1 (F2): 八度错误提示 — 音级对但跨八度 (非走调)
        if d.octave_error_rate > 0.3:
            diagnosis.append(
                f"检测到较多跨八度演唱 ({d.octave_error_rate*100:.0f}% 帧), "
                f"音级正确但音域/八度与原唱不同 (属正常翻唱)"
            )

        # v7.18 P1 (F1): 整体速度提示 — tempo 已从节奏分剥离, 独立报告
        if d.tempo_ratio > 1.08:
            diagnosis.append(f"整体速度比原唱快约 {(d.tempo_ratio-1)*100:.0f}%")
        elif d.tempo_ratio < 0.92:
            diagnosis.append(f"整体速度比原唱慢约 {(1-d.tempo_ratio)*100:.0f}%")

        return diagnosis
