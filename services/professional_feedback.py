"""
专业模式详细反馈生成器 v1.0

为专业评估模式生成详细、有价值的反馈
包含：
1. 问题定位：精确指出问题所在的时间段
2. 原因分析：解释问题产生的原因
3. 改进建议：具体的练习建议
4. 参考标准：专业级别的参考指标
"""

import numpy as np
import librosa
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class ProblemSegment:
    """问题片段"""
    start_time: float          # 开始时间（秒）
    end_time: float            # 结束时间（秒）
    problem_type: str          # 问题类型
    severity: str              # 严重程度 (minor, moderate, severe)
    description: str           # 问题描述
    value: float               # 实际值
    expected: float            # 期望值
    suggestion: str            # 改进建议


@dataclass
class DetailedFeedback:
    """详细反馈"""
    dimension: str             # 维度名称
    score: float               # 分数
    level: str                 # 等级
    summary: str               # 总结

    # 问题分析
    problems: List[ProblemSegment] = field(default_factory=list)
    problem_count: int = 0

    # 优点分析
    strengths: List[str] = field(default_factory=list)

    # 改进建议
    suggestions: List[str] = field(default_factory=list)

    # 参考指标
    reference_metrics: Dict[str, Tuple[float, float]] = field(default_factory=dict)

    # 练习建议
    practice_exercises: List[str] = field(default_factory=list)


class ProfessionalFeedbackGenerator:
    """
    专业模式详细反馈生成器

    生成详细、有价值的反馈，帮助用户：
    1. 理解评分依据
    2. 定位具体问题
    3. 获得改进方向
    """

    # 专业级别的参考标准
    PROFESSIONAL_STANDARDS = {
        'pitch': {
            'excellent': 10,      # 音分偏差
            'good': 25,
            'pass': 45,
            'description': '音准偏差（音分）'
        },
        'rhythm': {
            'excellent': 0.10,    # 拍长偏差比例
            'good': 0.20,
            'pass': 0.35,
            'description': '节奏偏差比例'
        },
        'breath': {
            'excellent': 0.15,    # RMS波动系数
            'good': 0.25,
            'pass': 0.40,
            'description': '气息波动系数'
        },
        'hnr': {
            'excellent': 20,      # 谐波噪声比 (dB)
            'good': 12,
            'pass': 6,
            'description': '谐波噪声比 (dB)'
        },
        'cpp': {
            'excellent': 2.0,     # 倒谱峰值
            'good': 1.0,
            'pass': 0.5,
            'description': '倒谱峰值显著性'
        }
    }

    # 练习建议库
    PRACTICE_EXERCISES = {
        'pitch': {
            'minor': [
                '跟着钢琴弹奏的音阶练习，注意听自己的音高是否与钢琴一致',
                '使用调音器APP实时监测音准偏差'
            ],
            'moderate': [
                '每天进行15分钟音阶练习，从慢速开始逐渐加速',
                '录制自己的演唱并与原曲对比，找出偏差位置',
                '练习半音阶，提高音高敏感度'
            ],
            'severe': [
                '建议找专业声乐老师进行一对一指导',
                '从基础音阶开始练习，建立音高概念',
                '每天听辨训练，提高音高辨别能力'
            ]
        },
        'rhythm': {
            'minor': [
                '跟着节拍器练习，保持稳定速度',
                '注意歌曲的节拍重音，在重音处踩点'
            ],
            'moderate': [
                '使用节拍器从慢速开始练习，逐步提高速度',
                '练习打拍子，先用手打拍子再演唱',
                '注意歌曲的速度变化，提前预判'
            ],
            'severe': [
                '建议先不唱歌，只跟着节拍器打拍子',
                '练习简单的节奏型，如四分音符、八分音符',
                '找专业老师指导节奏训练'
            ]
        },
        'breath': {
            'minor': [
                '练习腹式呼吸，吸气时腹部扩张',
                '长音练习，保持稳定的气息输出'
            ],
            'moderate': [
                '每天进行呼吸练习：吸气4秒，保持4秒，呼气8秒',
                '练习"嘶"音长音，保持音量稳定',
                '注意换气点，提前规划换气位置'
            ],
            'severe': [
                '建议进行专门的呼吸训练',
                '练习横膈膜控制，感受气息支撑',
                '找专业老师指导呼吸方法'
            ]
        },
        'technique': {
            'minor': [
                '练习开喉演唱，保持喉咙放松',
                '注意咬字清晰，不要含糊'
            ],
            'moderate': [
                '练习唇颤音（打嘟噜），放松喉部肌肉',
                '练习不同元音的转换，保持音色一致',
                '注意避免挤卡，保持自然发声'
            ],
            'severe': [
                '建议找专业声乐老师进行发声训练',
                '从基础发声练习开始，建立正确的发声习惯',
                '避免大声喊叫，保护嗓子'
            ]
        },
        'artistry': {
            'minor': [
                '注意歌曲的情感表达，理解歌词含义',
                '练习强弱变化，增加演唱层次感'
            ],
            'moderate': [
                '分析歌曲的情感走向，设计演唱处理',
                '练习颤音技巧，增加音色丰富度',
                '注意乐句的起承转合，有感情地演唱'
            ],
            'severe': [
                '多听优秀歌手的演唱，学习情感表达',
                '练习用不同的情绪演唱同一首歌',
                '找专业老师指导艺术表现'
            ]
        }
    }

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate

    def generate_pitch_feedback(
        self,
        f0: np.ndarray,
        score: float,
        hop_length: int = 160
    ) -> DetailedFeedback:
        """生成音准详细反馈"""
        feedback = DetailedFeedback(
            dimension='音准',
            score=score,
            level=self._get_level(score),
            summary=self._generate_summary('pitch', score)
        )

        problems = self._analyze_pitch_problems(f0, hop_length)
        feedback.problems = problems
        feedback.problem_count = len(problems)
        feedback.strengths = self._analyze_pitch_strengths(f0, score)

        severity = self._get_overall_severity(problems)
        feedback.suggestions = self._generate_suggestions('pitch', severity, score)

        standards = self.PROFESSIONAL_STANDARDS['pitch']
        feedback.reference_metrics = {
            '专业级': (0, standards['excellent']),
            '良好': (standards['excellent'], standards['good']),
            '合格': (standards['good'], standards['pass']),
        }

        feedback.practice_exercises = self.PRACTICE_EXERCISES['pitch'].get(severity, [])

        return feedback

    def generate_rhythm_feedback(
        self,
        audio: np.ndarray,
        score: float
    ) -> DetailedFeedback:
        """生成节奏详细反馈"""
        feedback = DetailedFeedback(
            dimension='节奏',
            score=score,
            level=self._get_level(score),
            summary=self._generate_summary('rhythm', score)
        )

        problems = self._analyze_rhythm_problems(audio)
        feedback.problems = problems
        feedback.problem_count = len(problems)
        feedback.strengths = self._analyze_rhythm_strengths(audio, score)

        severity = self._get_overall_severity(problems)
        feedback.suggestions = self._generate_suggestions('rhythm', severity, score)

        standards = self.PROFESSIONAL_STANDARDS['rhythm']
        feedback.reference_metrics = {
            '专业级': (0, standards['excellent']),
            '良好': (standards['excellent'], standards['good']),
            '合格': (standards['good'], standards['pass']),
        }

        feedback.practice_exercises = self.PRACTICE_EXERCISES['rhythm'].get(severity, [])

        return feedback

    def generate_breath_feedback(
        self,
        audio: np.ndarray,
        rms: np.ndarray,
        score: float
    ) -> DetailedFeedback:
        """生成气息详细反馈"""
        feedback = DetailedFeedback(
            dimension='气息',
            score=score,
            level=self._get_level(score),
            summary=self._generate_summary('breath', score)
        )

        problems = self._analyze_breath_problems(audio, rms)
        feedback.problems = problems
        feedback.problem_count = len(problems)
        feedback.strengths = self._analyze_breath_strengths(rms, score)

        severity = self._get_overall_severity(problems)
        feedback.suggestions = self._generate_suggestions('breath', severity, score)

        standards = self.PROFESSIONAL_STANDARDS['breath']
        feedback.reference_metrics = {
            '专业级': (0, standards['excellent']),
            '良好': (standards['excellent'], standards['good']),
            '合格': (standards['good'], standards['pass']),
        }

        feedback.practice_exercises = self.PRACTICE_EXERCISES['breath'].get(severity, [])

        return feedback

    def generate_technique_feedback(
        self,
        hnr: float,
        cpp: float,
        score: float
    ) -> DetailedFeedback:
        """生成技术详细反馈"""
        feedback = DetailedFeedback(
            dimension='发声技术',
            score=score,
            level=self._get_level(score),
            summary=self._generate_summary('technique', score)
        )

        problems = []

        hnr_standards = self.PROFESSIONAL_STANDARDS['hnr']
        if hnr < hnr_standards['pass']:
            severity = 'severe' if hnr < hnr_standards['good'] else 'moderate'
            problems.append(ProblemSegment(
                start_time=0,
                end_time=0,
                problem_type='hnr_low',
                severity=severity,
                description=f'谐波噪声比偏低 ({hnr:.1f}dB)',
                value=hnr,
                expected=hnr_standards['good'],
                suggestion='注意发声位置，避免挤压喉咙'
            ))

        cpp_standards = self.PROFESSIONAL_STANDARDS['cpp']
        if cpp < cpp_standards['pass']:
            severity = 'severe' if cpp < cpp_standards['good'] else 'moderate'
            problems.append(ProblemSegment(
                start_time=0,
                end_time=0,
                problem_type='cpp_low',
                severity=severity,
                description=f'倒谱峰值偏低 ({cpp:.2f})',
                value=cpp,
                expected=cpp_standards['good'],
                suggestion='注意气息支撑，增强声音穿透力'
            ))

        feedback.problems = problems
        feedback.problem_count = len(problems)

        if hnr >= hnr_standards['good']:
            feedback.strengths.append(f'谐波噪声比良好 ({hnr:.1f}dB)，声音清晰')
        if cpp >= cpp_standards['good']:
            feedback.strengths.append(f'倒谱峰值良好 ({cpp:.2f})，声音有穿透力')

        severity = self._get_overall_severity(problems)
        feedback.suggestions = self._generate_suggestions('technique', severity, score)

        feedback.reference_metrics = {
            'HNR专业级': (hnr_standards['excellent'], 30),
            'HNR良好': (hnr_standards['good'], hnr_standards['excellent']),
            'CPP专业级': (cpp_standards['excellent'], 5),
            'CPP良好': (cpp_standards['good'], cpp_standards['excellent']),
        }

        feedback.practice_exercises = self.PRACTICE_EXERCISES['technique'].get(severity, [])

        return feedback

    def generate_artistry_feedback(
        self,
        emotions: Dict[str, float],
        score: float
    ) -> DetailedFeedback:
        """生成艺术表现详细反馈"""
        feedback = DetailedFeedback(
            dimension='艺术表现',
            score=score,
            level=self._get_level(score),
            summary=self._generate_summary('artistry', score)
        )

        dominant_emotion = max(emotions, key=emotions.get) if emotions else 'neutral'
        emotion_confidence = emotions.get(dominant_emotion, 0) if emotions else 0

        if emotion_confidence > 0.7:
            feedback.strengths.append(f'情绪表达明确，以{self._emotion_cn(dominant_emotion)}为主')
        elif emotion_confidence > 0.5:
            feedback.strengths.append(f'有一定的情绪表达')
        else:
            feedback.problems.append(ProblemSegment(
                start_time=0,
                end_time=0,
                problem_type='emotion_weak',
                severity='minor',
                description='情绪表达不够明显',
                value=emotion_confidence,
                expected=0.7,
                suggestion='注意歌曲情感，用声音表达情绪'
            ))

        severity = 'minor' if score >= 70 else ('moderate' if score >= 50 else 'severe')
        feedback.suggestions = self._generate_suggestions('artistry', severity, score)

        feedback.practice_exercises = self.PRACTICE_EXERCISES['artistry'].get(severity, [])

        return feedback

    def _analyze_pitch_problems(
        self,
        f0: np.ndarray,
        hop_length: int
    ) -> List[ProblemSegment]:
        """分析音准问题"""
        problems = []

        if f0 is None or len(f0) == 0:
            return problems

        try:
            valid_mask = ~np.isnan(f0)
            valid_f0 = f0[valid_mask]

            if len(valid_f0) < 10:
                return problems

            diff = np.diff(valid_f0)
            threshold = np.mean(np.abs(diff)) + 2 * np.std(np.abs(diff))

            jump_indices = np.where(np.abs(diff) > threshold)[0]

            for idx in jump_indices[:5]:
                time = idx * hop_length / self.sample_rate
                problems.append(ProblemSegment(
                    start_time=time - 0.5,
                    end_time=time + 0.5,
                    problem_type='pitch_jump',
                    severity='moderate',
                    description=f'音高突然变化 ({abs(diff[idx]):.0f}Hz)',
                    value=abs(diff[idx]),
                    expected=threshold,
                    suggestion='注意音高过渡，避免突然跳变'
                ))

        except Exception as e:
            logger.warning(f"Pitch problem analysis failed: {e}")

        return problems

    def _analyze_rhythm_problems(self, audio: np.ndarray) -> List[ProblemSegment]:
        """分析节奏问题"""
        problems = []

        try:
            onset_env = librosa.onset.onset_strength(y=audio, sr=self.sample_rate)
            onset_frames = librosa.onset.onset_detect(
                onset_envelope=onset_env,
                sr=self.sample_rate
            )

            if len(onset_frames) < 3:
                return problems

            intervals = np.diff(onset_frames)
            mean_interval = np.mean(intervals)
            std_interval = np.std(intervals)

            if std_interval / mean_interval > 0.3:
                problems.append(ProblemSegment(
                    start_time=0,
                    end_time=len(audio) / self.sample_rate,
                    problem_type='rhythm_unstable',
                    severity='moderate',
                    description='节奏不够稳定',
                    value=std_interval / mean_interval,
                    expected=0.2,
                    suggestion='跟着节拍器练习，保持稳定速度'
                ))

        except Exception as e:
            logger.warning(f"Rhythm problem analysis failed: {e}")

        return problems

    def _analyze_breath_problems(
        self,
        audio: np.ndarray,
        rms: np.ndarray
    ) -> List[ProblemSegment]:
        """分析气息问题"""
        problems = []

        try:
            rms_std = np.std(rms)
            rms_mean = np.mean(rms)
            fluctuation = rms_std / (rms_mean + 1e-10)

            if fluctuation > 0.4:
                problems.append(ProblemSegment(
                    start_time=0,
                    end_time=len(audio) / self.sample_rate,
                    problem_type='breath_unstable',
                    severity='moderate' if fluctuation < 0.6 else 'severe',
                    description=f'气息波动较大 ({fluctuation:.2f})',
                    value=fluctuation,
                    expected=0.3,
                    suggestion='练习气息控制，保持稳定的气息输出'
                ))

        except Exception as e:
            logger.warning(f"Breath problem analysis failed: {e}")

        return problems

    def _analyze_pitch_strengths(self, f0: np.ndarray, score: float) -> List[str]:
        """分析音准优点"""
        strengths = []

        if score >= 80:
            strengths.append('音准整体准确，偏差控制在合理范围内')
        elif score >= 70:
            strengths.append('音准基本准确，有少量偏差')

        if f0 is not None and len(f0) > 0:
            valid_f0 = f0[~np.isnan(f0)]
            if len(valid_f0) > 10:
                diff = np.diff(valid_f0)
                if np.std(diff) > 5 and np.std(diff) < 30:
                    strengths.append('有自然的颤音，增加音色表现力')

        return strengths

    def _analyze_rhythm_strengths(self, audio: np.ndarray, score: float) -> List[str]:
        """分析节奏优点"""
        strengths = []

        if score >= 80:
            strengths.append('节奏稳定，拍点准确')
        elif score >= 70:
            strengths.append('节奏基本稳定')

        return strengths

    def _analyze_breath_strengths(self, rms: np.ndarray, score: float) -> List[str]:
        """分析气息优点"""
        strengths = []

        if score >= 80:
            strengths.append('气息控制良好，音量稳定')
        elif score >= 70:
            strengths.append('气息基本稳定')

        if rms is not None and len(rms) > 0:
            dynamic_range = np.percentile(rms, 95) - np.percentile(rms, 5)
            if dynamic_range > 0.1:
                strengths.append('有适当的强弱变化，增加演唱层次')

        return strengths

    def _generate_summary(self, dimension: str, score: float) -> str:
        """生成总结"""
        if score >= 85:
            return f'{self._dimension_cn(dimension)}表现优秀，达到专业水准'
        elif score >= 75:
            return f'{self._dimension_cn(dimension)}表现良好，继续保持'
        elif score >= 65:
            return f'{self._dimension_cn(dimension)}表现中等，有提升空间'
        elif score >= 55:
            return f'{self._dimension_cn(dimension)}表现一般，需要加强练习'
        else:
            return f'{self._dimension_cn(dimension)}表现欠佳，建议重点练习'

    def _generate_suggestions(
        self,
        dimension: str,
        severity: str,
        score: float
    ) -> List[str]:
        """生成改进建议"""
        suggestions = []

        if severity == 'severe':
            suggestions.append(f'{self._dimension_cn(dimension)}问题较明显，建议优先解决')
        elif severity == 'moderate':
            suggestions.append(f'{self._dimension_cn(dimension)}有改进空间，建议针对性练习')
        else:
            suggestions.append(f'{self._dimension_cn(dimension)}表现不错，可以继续精进')

        return suggestions

    def _get_level(self, score: float) -> str:
        """获取等级"""
        if score >= 85:
            return "优秀"
        elif score >= 75:
            return "良好"
        elif score >= 65:
            return "中等"
        elif score >= 55:
            return "及格"
        else:
            return "待改进"

    def _get_overall_severity(self, problems: List[ProblemSegment]) -> str:
        """获取整体严重程度"""
        if not problems:
            return 'minor'

        severities = [p.severity for p in problems]
        if 'severe' in severities:
            return 'severe'
        elif 'moderate' in severities:
            return 'moderate'
        else:
            return 'minor'

    def _dimension_cn(self, dimension: str) -> str:
        """维度中文名"""
        mapping = {
            'pitch': '音准',
            'rhythm': '节奏',
            'breath': '气息',
            'technique': '发声技术',
            'artistry': '艺术表现'
        }
        return mapping.get(dimension, dimension)

    def _emotion_cn(self, emotion: str) -> str:
        """情绪中文名"""
        mapping = {
            'happy': '欢快',
            'sad': '悲伤',
            'angry': '愤怒',
            'neutral': '平静',
            'surprised': '惊讶'
        }
        return mapping.get(emotion, emotion)
