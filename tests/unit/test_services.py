"""
单元测试 - 业务层测试
测试 services 模块的核心功能
"""
import pytest
import numpy as np
from pathlib import Path
import tempfile

from services.score_service import ScoreService, ScoreResult
from services.advice_service import AdviceService, AdviceResult
from services.audio_service import AudioAnalysisResult


class TestScoreResult:
    """评分结果 DTO 测试"""

    def test_create_score_result(self):
        """测试创建评分结果"""
        result = ScoreResult(
            volume=80.0,
            pitch=75.0,
            rhythm=70.0,
            breath=85.0,
            emotion=90.0,
            total=80.0,
            level='良好',
            stars='★★★★',
            color='#3b82f6',
            penalties={'volume_low': 5.0}
        )

        assert result.volume == 80.0
        assert result.pitch == 75.0
        assert result.level == '良好'
        assert result.penalties == {'volume_low': 5.0}

    def test_score_result_is_mutable(self):
        """测试 ScoreResult 是可变的（非 frozen）"""
        result = ScoreResult(
            volume=80.0, pitch=75.0, rhythm=70.0,
            breath=85.0, emotion=90.0, total=80.0,
            level='良好', stars='★★★★', color='#3b82f6',
            penalties={}
        )

        # ScoreResultV4 是可变的 dataclass
        result.volume = 100
        assert result.volume == 100


class TestAdviceService:
    """建议生成服务测试"""

    def setup_method(self):
        self.service = AdviceService()

    def test_generate_advice(self):
        """测试建议生成"""
        scores = ScoreResult(
            volume=50.0,  # 较低
            pitch=80.0,
            rhythm=80.0,
            breath=80.0,
            emotion=80.0,
            total=74.0,
            level='及格',
            stars='★★★',
            color='#f59e0b',
            penalties={'volume_low': 10.0}
        )

        result = self.service.generate(scores)

        assert isinstance(result, AdviceResult)
        assert isinstance(result.advice, list)
        assert len(result.advice) > 0
        # 音量最低，应该是 weakest
        assert result.weakest_dimension == 'volume'

    def test_generate_advice_high_scores(self):
        """测试高分情况的建议"""
        scores = ScoreResult(
            volume=95.0,
            pitch=95.0,
            rhythm=95.0,
            breath=95.0,
            emotion=95.0,
            total=95.0,
            level='优秀',
            stars='★★★★★',
            color='#10b981',
            penalties={}
        )

        result = self.service.generate(scores)

        assert isinstance(result, AdviceResult)
        assert len(result.advice) >= 0


class TestAudioAnalysisResult:
    """音频分析结果 DTO 测试"""

    def test_create_success_result(self):
        """测试创建成功结果"""
        result = AudioAnalysisResult(
            success=True,
            filepath='/test/audio.wav',
            filename='audio.wav',
            duration=10.0,
            sample_rate=22050,
            file_size=1000.0,
            volume_info={'mean': -20.0},
            pitch_info={'mean': 440.0},
            rhythm_info={'bpm': 120},
            _audio_data=np.array([0.1, 0.2]),
            _pitch_stability=0.8
        )

        assert result.success is True
        assert result.error is None
        assert result.filepath == '/test/audio.wav'

    def test_create_error_result(self):
        """测试创建错误结果"""
        result = AudioAnalysisResult(
            success=False,
            filepath='/test/audio.wav',
            filename='audio.wav',
            duration=0.0,
            sample_rate=0,
            file_size=0.0,
            volume_info={},
            pitch_info={},
            rhythm_info={},
            error='文件不存在'
        )

        assert result.success is False
        assert result.error == '文件不存在'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
