"""
建议生成服务
负责根据评分生成改进建议

设计原则：
- 单一职责：只负责建议生成
- 无状态：纯函数
- 可扩展：新增建议规则只需修改此模块
"""
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class AdviceResult:
    """建议结果 DTO"""
    advice: List[str]
    strongest_dimension: str
    weakest_dimension: str


class AdviceService:
    """
    建议生成服务

    职责：
    - 根据评分结果生成改进建议
    - 识别强项和弱项

    扩展方式：
    - 新增建议模板只需修改 _TIPS 和 _PRAISE 字典
    - 不影响其他模块
    """

    # 维度名称映射
    DIMENSION_NAMES = {
        'volume': '音量',
        'pitch': '音准',
        'rhythm': '节奏',
        'breath': '气息',
        'emotion': '情绪',
        'technique': '技术',
        'muscle_strength': '肌肉力量',
        'artistry': '艺术表现',
    }

    # 改进建议模板
    _TIPS = {
        'volume': "练习腹式呼吸，保持稳定气息支撑。注意强弱的对比变化，增强音乐表现力。",
        'pitch': "每天跟唱音阶10分钟，使用调音器校准。多听标准音高，培养音准感觉。",
        'rhythm': "跟着节拍器练习，从慢速开始。注意切分音和休止符的准确性。",
        'breath': "练习长音保持，每天做呼吸操。注意换气点的选择，保持气息稳定。",
        'emotion': "理解歌词含义，多听优秀歌手演绎。尝试用肢体语言辅助情感表达。",
        'technique': "练习咬字清晰度，注意气声比例的平衡。多做元音和辅音的发声练习。",
        'muscle_strength': "加强腹式呼吸和核心力量训练，提升声音的穿透力和稳定性。",
        'artistry': "注重颤音技巧和动态变化，增强乐句表现力。多听不同风格的音乐作品。",
    }

    # 表扬模板
    _PRAISE = {
        'volume': "音量控制精准，动态表现丰富！",
        'pitch': "音准极佳，旋律线条清晰！",
        'rhythm': "节奏感出色，律动感强！",
        'breath': "气息控制稳定，颤音运用得当！",
        'emotion': "情感表达丰富，感染力强！",
        'technique': "发声技术扎实，咬字清晰，气声比控制得当！",
        'muscle_strength': "声音穿透力强，共鸣丰富，肌肉支撑稳定！",
        'artistry': "艺术表现力出色，乐句处理细腻！",
    }

    def generate(self, scores: dict) -> 'AdviceResult':
        """
        生成改进建议 (v7.1.4: DDD orchestrator 产生 dict)

        Args:
            scores: 评分结果 (dict)

        Returns:
            AdviceResult: 建议结果
        """
        def _s(key, default=0.0):
            return scores.get(key, default) if isinstance(scores, dict) else getattr(scores, key, default)

        # v7.1.4: DDD orchestrator 产生六维评分 dict (字段名以 _score 结尾)
        score_dict = {
            'pitch': _s('pitch_score'),
            'rhythm': _s('rhythm_score'),
            'breath': _s('breath_score'),
            'technique': _s('technique_score'),
            'muscle_strength': _s('muscle_strength_score'),
            'artistry': _s('artistry_score'),
            'total': _s('total_score'),
        }

        # 排序找出最强和最弱维度
        sorted_scores = sorted(score_dict.items(), key=lambda x: x[1], reverse=True)
        strongest = sorted_scores[0]
        weakest = sorted_scores[-1]

        advice = []

        # 总体评价
        advice.append(self._get_overall_comment(strongest, _s('total')))

        # 针对最弱维度的建议
        if weakest[1] < 75:
            advice.append(self._get_improvement_tip(weakest))

        # 针对较强维度的鼓励
        if strongest[1] >= 90:
            advice.append(self._get_praise(strongest))

        return AdviceResult(
            advice=advice,
            strongest_dimension=strongest[0],
            weakest_dimension=weakest[0]
        )

    def _get_overall_comment(
        self,
        strongest: tuple,
        total_score: float
    ) -> str:
        """生成总体评价"""
        dim_name = self.DIMENSION_NAMES[strongest[0]]

        if total_score >= 90:
            return f"优秀表现！{dim_name}控制出色，专业水准！"
        elif total_score >= 85:
            return f"整体良好，{dim_name}表现突出，接近专业水平。"
        elif total_score >= 80:
            return f"整体表现良好，{dim_name}表现较好。"
        elif total_score >= 70:
            return "水平中等，有进步空间。"
        elif total_score >= 60:
            dim_name = self.DIMENSION_NAMES[strongest[0]]
            return f"基础尚可，建议重点提升{dim_name}。"
        else:
            dim_name = self.DIMENSION_NAMES[strongest[0]]
            return f"需要加强练习，重点关注{dim_name}。"

    def _get_improvement_tip(self, weakest: tuple) -> str:
        """生成改进建议"""
        dim_name = self.DIMENSION_NAMES[weakest[0]]
        tip = self._TIPS.get(weakest[0], "")
        return f"{dim_name}建议：{tip}"

    def _get_praise(self, strongest: tuple) -> str:
        """生成表扬"""
        return self._PRAISE.get(strongest[0], "")