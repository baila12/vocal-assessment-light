"""
音频对比分析业务逻辑

处理两个音频的对比分析、差异计算、建议生成
"""
import numpy as np
import logging

logger = logging.getLogger(__name__)


def calculate_comparison(standard: dict, user: dict) -> dict:
    """
    计算两个音频的对比结果

    Args:
        standard: 标准音频分析结果
        user: 用户音频分析结果

    Returns:
        对比结果字典
    """
    std_scores = standard.get('scores', {})
    user_scores = user.get('scores', {})

    # 各维度分数差距
    pitch_diff = abs(std_scores.get('pitch', 0) - user_scores.get('pitch', 0))
    volume_diff = abs(std_scores.get('volume', 0) - user_scores.get('volume', 0))
    rhythm_diff = abs(std_scores.get('rhythm', 0) - user_scores.get('rhythm', 0))
    breath_diff = abs(std_scores.get('breath', 0) - user_scores.get('breath', 0))
    emotion_diff = abs(std_scores.get('emotion', 0) - user_scores.get('emotion', 0))

    # 综合分数差距
    std_total = standard.get('total_score', 0)
    user_total = user.get('total_score', 0)
    total_diff = abs(std_total - user_total)

    # 音准匹配率
    pitch_match_rate = calculate_pitch_match_rate(
        standard.get('pitch_curve'),
        user.get('pitch_curve')
    )

    # 生成改进建议
    suggestions = generate_comparison_suggestions(std_scores, user_scores, std_total, user_total)

    return {
        'pitch_diff': round(pitch_diff, 1),
        'volume_diff': round(volume_diff, 1),
        'rhythm_diff': round(rhythm_diff, 1),
        'breath_diff': round(breath_diff, 1),
        'emotion_diff': round(emotion_diff, 1),
        'total_diff': round(total_diff, 1),
        'std_total': round(std_total, 1),
        'user_total': round(user_total, 1),
        'pitch_match_rate': round(pitch_match_rate, 1),
        'suggestions': suggestions
    }


def calculate_pitch_match_rate(std_pitch_curve: dict, user_pitch_curve: dict) -> float:
    """计算音准匹配率（0-100）"""
    if not std_pitch_curve or not user_pitch_curve:
        return 50.0

    std_freqs = std_pitch_curve.get('frequencies', [])
    user_freqs = user_pitch_curve.get('frequencies', [])

    if not std_freqs or not user_freqs:
        return 50.0

    std_freqs = np.array(std_freqs)
    user_freqs = np.array(user_freqs)

    # 过滤有效频率（人声范围 50-1000 Hz）
    std_valid = std_freqs[(std_freqs > 50) & (std_freqs < 1000)]
    user_valid = user_freqs[(user_freqs > 50) & (user_freqs < 1000)]

    if len(std_valid) < 10 or len(user_valid) < 10:
        return 50.0

    min_len = min(len(std_valid), len(user_valid))
    if min_len < 10:
        return 50.0

    # 使用线性插值重采样到相同长度
    std_resampled = np.interp(
        np.linspace(0, len(std_valid) - 1, min_len),
        np.arange(len(std_valid)),
        std_valid
    )
    user_resampled = np.interp(
        np.linspace(0, len(user_valid) - 1, min_len),
        np.arange(len(user_valid)),
        user_valid
    )

    # 计算音分差距
    with np.errstate(divide='ignore', invalid='ignore'):
        cents_diff = np.abs(1200 * np.log2(user_resampled / std_resampled))
        cents_diff = cents_diff[~np.isinf(cents_diff) & ~np.isnan(cents_diff)]

    if len(cents_diff) == 0:
        return 50.0

    # 音分差距小于50音分视为匹配
    match_rate = (np.sum(cents_diff < 50) / len(cents_diff)) * 100
    return float(match_rate)


def generate_comparison_suggestions(
    std_scores: dict,
    user_scores: dict,
    std_total: float,
    user_total: float
) -> list:
    """生成对比改进建议"""
    suggestions = []

    # 各维度建议配置
    dimension_configs = [
        ('pitch', '音准', '建议使用钢琴或调音器练习音阶，特别注意半音的准确度。', '注意长音的稳定性和尾音的收束。'),
        ('volume', '音量', '建议练习气息支持，保持稳定的音量输出。', '注意歌曲高潮和过渡段的音量变化。'),
        ('rhythm', '节奏', '建议跟着节拍器练习，注意不要抢拍或拖拍。', '注意休止符的时值和切分音的准确性。'),
        ('breath', '气息', '建议练习腹式呼吸，增强肺活量和气息控制能力。', '注意换气点的选择和气息的分配。'),
        ('emotion', '情感', '建议理解歌词含义，用声音传达歌曲的情感起伏。', '注意歌曲的强弱对比和情感转折。'),
    ]

    for key, name, large_gap_advice, small_gap_advice in dimension_configs:
        diff = std_scores.get(key, 0) - user_scores.get(key, 0)
        if diff > 10:
            suggestions.append({
                'dimension': name,
                'gap': round(diff, 1),
                'suggestion': f'{name}差距较大，{large_gap_advice}'
            })
        elif diff > 5:
            suggestions.append({
                'dimension': name,
                'gap': round(diff, 1),
                'suggestion': f'{name}略有不足，{small_gap_advice}'
            })

    # 综合建议
    total_diff = std_total - user_total
    if total_diff > 15:
        suggestions.append({
            'dimension': '综合',
            'gap': round(total_diff, 1),
            'suggestion': f'与标准音频相比，整体差距{round(total_diff, 1)}分。建议从音准和节奏入手，逐步提升各项技能。'
        })
    elif total_diff > 5:
        suggestions.append({
            'dimension': '综合',
            'gap': round(total_diff, 1),
            'suggestion': f'整体表现接近标准，差距仅{round(total_diff, 1)}分。继续练习，精益求精！'
        })
    else:
        suggestions.append({
            'dimension': '综合',
            'gap': round(total_diff, 1),
            'suggestion': '表现优秀！与标准音频非常接近，保持当前状态，可以尝试更高难度的歌曲。'
        })

    return suggestions
