"""
音频对比分析业务逻辑

处理两个音频的对比分析、差异计算、建议生成
"""
import numpy as np
import logging

logger = logging.getLogger(__name__)


def calculate_relative_score(standard: dict, user: dict) -> dict:
    """
    基于标准音频计算相对评分

    类似全民K歌的评分方式：
    - 音准匹配率：用户音高与标准音高的匹配程度
    - 节奏匹配率：用户节奏与标准节奏的对齐程度
    - 综合评分：加权计算

    Args:
        standard: 标准音频分析结果
        user: 用户音频分析结果

    Returns:
        {
            'pitch_match_rate': 85.0,  # 音准匹配率
            'rhythm_match_rate': 90.0, # 节奏匹配率
            'overall_score': 87.5,     # 综合评分
            'level': '优秀',
            'avg_cents_error': 15.2,   # 平均音分偏差
            'diagnosis': [...]         # 详细诊断
        }
    """
    # 计算音准匹配率
    pitch_match_rate = calculate_pitch_match_rate(
        standard.get('pitch_curve'),
        user.get('pitch_curve')
    )

    # 计算平均音分偏差
    avg_cents_error = calculate_avg_cents_error(
        standard.get('pitch_curve'),
        user.get('pitch_curve')
    )

    # 计算节奏匹配率
    rhythm_match_rate = calculate_rhythm_match_rate(
        standard.get('rhythm_curve'),
        user.get('rhythm_curve')
    )

    # 综合评分计算（音准权重60%，节奏权重40%）
    overall_score = pitch_match_rate * 0.6 + rhythm_match_rate * 0.4

    # 等级评定
    if overall_score >= 90:
        level = '优秀'
    elif overall_score >= 80:
        level = '良好'
    elif overall_score >= 70:
        level = '中等'
    elif overall_score >= 60:
        level = '及格'
    else:
        level = '需改进'

    # 生成诊断信息
    diagnosis = generate_diagnosis(
        pitch_match_rate,
        rhythm_match_rate,
        avg_cents_error,
        standard.get('pitch_curve'),
        user.get('pitch_curve')
    )

    return {
        'pitch_match_rate': round(pitch_match_rate, 1),
        'rhythm_match_rate': round(rhythm_match_rate, 1),
        'overall_score': round(overall_score, 1),
        'level': level,
        'avg_cents_error': round(avg_cents_error, 1),
        'diagnosis': diagnosis
    }


def calculate_avg_cents_error(std_pitch_curve: dict, user_pitch_curve: dict) -> float:
    """计算平均音分偏差"""
    if not std_pitch_curve or not user_pitch_curve:
        return 50.0

    std_freqs = std_pitch_curve.get('frequencies', [])
    user_freqs = user_pitch_curve.get('frequencies', [])

    if not std_freqs or not user_freqs:
        return 50.0

    std_freqs = np.array(std_freqs)
    user_freqs = np.array(user_freqs)

    # 过滤有效频率
    std_valid = std_freqs[(std_freqs > 50) & (std_freqs < 1000)]
    user_valid = user_freqs[(user_freqs > 50) & (user_freqs < 1000)]

    if len(std_valid) < 10 or len(user_valid) < 10:
        return 50.0

    min_len = min(len(std_valid), len(user_valid))

    # 重采样
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

    return float(np.mean(cents_diff))


def calculate_rhythm_match_rate(std_rhythm_curve: dict, user_rhythm_curve: dict) -> float:
    """计算节奏匹配率（基于能量包络相似度）"""
    if not std_rhythm_curve or not user_rhythm_curve:
        return 70.0  # 默认值

    std_energy = std_rhythm_curve.get('energy', [])
    user_energy = user_rhythm_curve.get('energy', [])

    if not std_energy or not user_energy:
        return 70.0

    std_energy = np.array(std_energy)
    user_energy = np.array(user_energy)

    if len(std_energy) < 10 or len(user_energy) < 10:
        return 70.0

    min_len = min(len(std_energy), len(user_energy))

    # 重采样到相同长度
    std_resampled = np.interp(
        np.linspace(0, len(std_energy) - 1, min_len),
        np.arange(len(std_energy)),
        std_energy
    )
    user_resampled = np.interp(
        np.linspace(0, len(user_energy) - 1, min_len),
        np.arange(len(user_energy)),
        user_energy
    )

    # 归一化
    std_norm = (std_resampled - np.min(std_resampled)) / (np.max(std_resampled) - np.min(std_resampled) + 1e-6)
    user_norm = (user_resampled - np.min(user_resampled)) / (np.max(user_resampled) - np.min(user_resampled) + 1e-6)

    # 计算相关性
    correlation = np.corrcoef(std_norm, user_norm)[0, 1]

    if np.isnan(correlation):
        return 70.0

    # 将相关性转换为匹配率 (0-100)
    match_rate = max(0, min(100, (correlation + 1) * 50))

    return float(match_rate)


def generate_diagnosis(
    pitch_match_rate: float,
    rhythm_match_rate: float,
    avg_cents_error: float,
    std_pitch_curve: dict,
    user_pitch_curve: dict
) -> list:
    """生成诊断信息"""
    diagnosis = []

    # 音准诊断
    if pitch_match_rate >= 90:
        diagnosis.append('音准表现优秀，与标准音频高度匹配')
    elif pitch_match_rate >= 80:
        diagnosis.append('音准整体良好，部分段落略有偏差')
    elif pitch_match_rate >= 70:
        diagnosis.append('音准需要提高，建议多听标准音频找准音高')
    else:
        diagnosis.append('音准偏差较大，建议先练习音阶建立音准感')

    # 音分偏差诊断
    if avg_cents_error < 20:
        diagnosis.append('音高控制精准，音分误差很小')
    elif avg_cents_error < 40:
        diagnosis.append('音高控制尚可，注意微调')
    elif avg_cents_error < 60:
        diagnosis.append('音高偏差明显，需要加强音准训练')

    # 节奏诊断
    if rhythm_match_rate >= 85:
        diagnosis.append('节奏把握准确，与标准音频同步良好')
    elif rhythm_match_rate >= 70:
        diagnosis.append('节奏基本正确，注意不要抢拍或拖拍')
    else:
        diagnosis.append('节奏需要加强，建议跟着节拍器练习')

    # 分析偏高/偏低趋势
    if std_pitch_curve and user_pitch_curve:
        std_freqs = np.array(std_pitch_curve.get('frequencies', []))
        user_freqs = np.array(user_pitch_curve.get('frequencies', []))

        if len(std_freqs) > 10 and len(user_freqs) > 10:
            min_len = min(len(std_freqs), len(user_freqs))
            std_resampled = np.interp(
                np.linspace(0, len(std_freqs) - 1, min_len),
                np.arange(len(std_freqs)),
                std_freqs
            )
            user_resampled = np.interp(
                np.linspace(0, len(user_freqs) - 1, min_len),
                np.arange(len(user_freqs)),
                user_freqs
            )

            # 过滤有效值
            valid_mask = (std_resampled > 50) & (std_resampled < 1000) & (user_resampled > 50) & (user_resampled < 1000)
            if np.sum(valid_mask) > 10:
                cents_diff = 1200 * np.log2(user_resampled[valid_mask] / std_resampled[valid_mask])
                positive_count = np.sum(cents_diff > 10)
                negative_count = np.sum(cents_diff < -10)

                if positive_count > negative_count * 2:
                    diagnosis.append('整体偏高，注意控制气息不要过于用力')
                elif negative_count > positive_count * 2:
                    diagnosis.append('整体偏低，注意加强气息支撑')

    return diagnosis


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
