"""
对比分析服务 - 使用DTW对齐引擎

v7.19 E1 消双轨: 仅产出偏差数据 (DTW 降级为特征提供者)。
评分统一由 DDD ComparisonScoringService 承担 (唯一评分入口)。
"""
import numpy as np
import logging
from typing import Dict

from services.comparison.dtw_aligner import DTWAligner, MultiFeatureSequence
from services.comparison.deviation_calculator import DeviationCalculator
from services.comparison.benchmark_service import BenchmarkService

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)


class ComparisonService:
    """
    对比分析服务 — 纯偏差提供者 (不再评分)

    整合DTW对齐 + 偏差计算。评分由 DDD 层负责。
    """

    def __init__(self, sample_rate: int = 22050, hop_length: int = 512, style: str = 'pop'):
        self.sample_rate = sample_rate
        self.hop_length = hop_length
        self.aligner = DTWAligner(sample_rate, hop_length)
        self.calculator = DeviationCalculator(sample_rate, hop_length)
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

        compute_time = (__import__('time').time() - start_time) * 1000

        # 3. 构建偏差数据 (E1: 不再评分 — 评分由 DDD ComparisonScoringService 承担)
        result = {
            'success': True,
            'confidence': alignment.confidence,
            'dimensions': {
                'pitch': {
                    'avg_deviation': deviation.avg_pitch_cents,
                    'max_deviation': deviation.max_pitch_cents,
                },
                'rhythm': {
                    'avg_deviation': deviation.avg_rhythm_ms,
                },
                'volume': {
                    'avg_deviation': deviation.avg_volume_percent,
                },
                'breath': {
                    'stability': deviation.avg_breath_stability,
                },
            },
            'avg_cents_error': deviation.avg_pitch_cents,
            'compute_time_ms': compute_time,
            'method': alignment.method,
            # v7.18 P1: 八度错误率 + 整体速度比 (F2/F1 独立信号, 供诊断)
            'octave_error_rate': getattr(deviation, 'octave_error_rate', 0.0),
            'tempo_ratio': getattr(deviation, 'tempo_ratio', 1.0),
        }

        logger.info(f"[ComparisonService] Comparison complete: confidence={result['confidence']}, "
                    f"method={result['method']}")

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