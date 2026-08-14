"""
对比分析服务 - 使用DTW对齐引擎

整合三级DTW对齐、偏差计算、评分引擎
"""
import numpy as np
import librosa
import logging
from typing import Dict, Optional, Tuple
from dataclasses import asdict

from services.comparison.dtw_aligner import DTWAligner, MultiFeatureSequence
from services.comparison.deviation_calculator import DeviationCalculator
from services.comparison.scoring_engine import ComparisonScoringEngine
from services.comparison.benchmark_service import BenchmarkService

logger = logging.getLogger(__name__)


class ComparisonService:
    """
    对比分析服务

    整合DTW对齐、偏差计算、评分引擎
    """

    def __init__(self, sample_rate: int = 22050, hop_length: int = 512, style: str = 'pop'):
        self.sample_rate = sample_rate
        self.hop_length = hop_length
        self.aligner = DTWAligner(sample_rate, hop_length)
        self.calculator = DeviationCalculator(sample_rate, hop_length)
        self.scoring_engine = ComparisonScoringEngine(style)
        self.benchmark_service = BenchmarkService(sample_rate, hop_length)

    def compare_audio_files(
        self,
        standard_path: str,
        user_path: str,
        style: str = 'pop'
    ) -> Dict:
        """
        对比分析两个音频文件

        Args:
            standard_path: 标准音频路径
            user_path: 用户音频路径
            style: 演唱风格 (pop/classical/folk/rap)

        Returns:
            对比分析结果
        """
        logger.info(f"[ComparisonService] Starting comparison: {standard_path} vs {user_path}")

        # 1. 提取特征
        std_features = self.aligner.extract_features(standard_path)
        user_features = self.aligner.extract_features(user_path)

        return self.compare_features(std_features, user_features, style)

    def compare_features(
        self,
        std_features: MultiFeatureSequence,
        user_features: MultiFeatureSequence,
        style: str = 'pop'
    ) -> Dict:
        """
        对比分析特征序列

        Args:
            std_features: 标准音频特征
            user_features: 用户音频特征
            style: 演唱风格

        Returns:
            对比分析结果
        """
        start_time = __import__('time').time()

        # 1. DTW对齐
        alignment = self.aligner.align(std_features, user_features)
        logger.info(f"[ComparisonService] Alignment complete: confidence={alignment.confidence:.3f}")

        # 2. 计算偏差
        deviation = self.calculator.calculate(
            std_pitch=std_features.pitch,
            user_pitch=user_features.pitch,
            std_energy=std_features.energy,
            user_energy=user_features.energy,
            warp_path=alignment.warp_path,
            std_times=std_features.times,
            std_voiced=getattr(std_features, 'voiced', None),   # v7.18 P0 (O1)
            user_voiced=getattr(user_features, 'voiced', None),  # v7.18 P0 (O1)
        )

        # 3. 评分
        self.scoring_engine.style = style
        self.scoring_engine.weights = self.scoring_engine.STYLE_WEIGHTS.get(
            style, self.scoring_engine.DEFAULT_WEIGHTS
        )
        score_result = self.scoring_engine.score(
            deviation,
            confidence=alignment.confidence,
            total_frames=len(deviation.frames)
        )

        compute_time = (__import__('time').time() - start_time) * 1000

        # 4. 构建结果
        result = {
            'success': True,
            'score': score_result.overall_score,
            'level': score_result.level,
            'confidence': alignment.confidence,
            'dimensions': {
                'pitch': {
                    'score': score_result.dimensions['pitch'].score,
                    'avg_deviation': score_result.dimensions['pitch'].avg_deviation,
                    'max_deviation': score_result.dimensions['pitch'].max_deviation
                },
                'rhythm': {
                    'score': score_result.dimensions['rhythm'].score,
                    'avg_deviation': score_result.dimensions['rhythm'].avg_deviation
                },
                'volume': {
                    'score': score_result.dimensions['volume'].score,
                    'avg_deviation': score_result.dimensions['volume'].avg_deviation
                },
                'breath': {
                    'score': score_result.dimensions['breath'].score,
                    'stability': score_result.dimensions['breath'].details.get('avg_stability', 0)
                }
            },
            'pitch_match_rate': self._calculate_match_rate(score_result.dimensions['pitch'].score),
            'rhythm_match_rate': self._calculate_match_rate(score_result.dimensions['rhythm'].score),
            'avg_cents_error': deviation.avg_pitch_cents,
            'suggestions': score_result.suggestions,
            'problem_summary': score_result.problem_summary,
            'diagnosis': self._generate_diagnosis(score_result, deviation),
            'compute_time_ms': compute_time,
            'method': alignment.method,
            # v7.18 P1: 八度错误率 + 整体速度比 (F2/F1 独立信号, 供诊断)
            'octave_error_rate': getattr(deviation, 'octave_error_rate', 0.0),
            'tempo_ratio': getattr(deviation, 'tempo_ratio', 1.0),
        }

        logger.info(f"[ComparisonService] Comparison complete: score={result['score']}, level={result['level']}")

        return result

    def compare_with_benchmark(
        self,
        benchmark_id: str,
        user_path: str,
        style: str = 'pop'
    ) -> Dict:
        """
        使用预加工的基准库进行对比分析

        Args:
            benchmark_id: 基准库ID
            user_path: 用户音频路径
            style: 演唱风格

        Returns:
            对比分析结果
        """
        # 加载基准库
        benchmark = self.benchmark_service.load_benchmark(benchmark_id)
        if benchmark is None:
            return {
                'success': False,
                'error': f'基准库 {benchmark_id} 不存在'
            }

        # 构建特征对象
        std_features = MultiFeatureSequence(
            pitch=benchmark.pitch_frames,
            energy=benchmark.energy_frames,
            zcr=np.zeros(len(benchmark.pitch_frames)),  # 基准库没有ZCR
            times=np.arange(len(benchmark.pitch_frames)) * benchmark.hop_length / benchmark.sample_rate,
            sample_rate=benchmark.sample_rate,
            hop_length=benchmark.hop_length
        )

        # 提取用户特征
        user_features = self.aligner.extract_features(user_path)

        return self.compare_features(std_features, user_features, style)

    def _calculate_match_rate(self, score: float) -> float:
        """将评分转换为匹配率"""
        # 评分和匹配率的转换
        # 100分 = 100%匹配
        # 75分 = 75%匹配
        return round(score, 1)

    def _generate_diagnosis(self, score_result, deviation) -> list:
        """生成诊断信息"""
        diagnosis = []

        # 音准诊断
        pitch_score = score_result.dimensions['pitch'].score
        avg_cents = deviation.avg_pitch_cents

        if pitch_score >= 90:
            diagnosis.append('音准表现优秀，与标准音频高度匹配')
        elif pitch_score >= 75:
            diagnosis.append(f'音准整体良好，平均偏差{avg_cents:.1f}音分')
        elif pitch_score >= 60:
            diagnosis.append(f'音准需要提高，建议多听标准音频找准音高')
        else:
            diagnosis.append('音准偏差较大，建议先练习音阶建立音准感')

        # 节奏诊断
        rhythm_score = score_result.dimensions['rhythm'].score
        if rhythm_score >= 85:
            diagnosis.append('节奏把握准确，与标准音频同步良好')
        elif rhythm_score >= 70:
            diagnosis.append('节奏基本正确，注意不要抢拍或拖拍')
        else:
            diagnosis.append('节奏需要加强，建议跟着节拍器练习')

        # 气息诊断
        breath_score = score_result.dimensions['breath'].score
        if breath_score < 70:
            diagnosis.append('气息稳定性不足，建议练习腹式呼吸')

        # v7.18 P1 (F2): 八度错误提示 — 音级对但跨八度 (非走调)
        octave_rate = getattr(deviation, 'octave_error_rate', 0.0)
        if octave_rate > 0.3:
            diagnosis.append(f'检测到较多跨八度演唱 ({octave_rate*100:.0f}% 帧), 音级正确但音域/八度与原唱不同 (属正常翻唱)')

        # v7.18 P1 (F1): 整体速度提示 — tempo 已从节奏分剥离, 独立报告
        tempo = getattr(deviation, 'tempo_ratio', 1.0)
        if tempo > 1.08:
            diagnosis.append(f'整体速度比原唱快约 {(tempo-1)*100:.0f}%')
        elif tempo < 0.92:
            diagnosis.append(f'整体速度比原唱慢约 {(1-tempo)*100:.0f}%')

        # 整体诊断
        if score_result.overall_score >= 90:
            diagnosis.append('整体表现优秀，继续保持练习！')
        elif score_result.overall_score >= 75:
            diagnosis.append('表现良好，部分细节可以进一步完善')

        return diagnosis


def compare_with_dtw(standard_path: str, user_path: str, style: str = 'pop') -> Dict:
    """
    使用DTW对齐进行对比分析（便捷函数）

    Args:
        standard_path: 标准音频路径
        user_path: 用户音频路径
        style: 演唱风格

    Returns:
        对比分析结果
    """
    service = ComparisonService(style=style)
    return service.compare_audio_files(standard_path, user_path, style)