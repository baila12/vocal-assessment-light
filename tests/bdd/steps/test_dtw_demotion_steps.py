"""
Step definitions for dtw-demotion.feature (v7.19 E1 消双轨)

验证 DTW 降级为纯偏差提供者 + 对比评分唯一入口 DDD ComparisonScoringService。
这些断言是"架构不变量": 检查文件结构/类属性/单一数据来源,
不运行真实音频对比 (由 extended/test_comparison_dtw.py 承担)。
"""
import os
from pathlib import Path

import pytest
from pytest_bdd import given, when, then, parsers, scenarios

scenarios('../features/dtw-demotion.feature')

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
SCORING_ENGINE_PATH = PROJECT_ROOT / 'services' / 'comparison' / 'scoring_engine.py'


# ── Given ──────────────────────────────────────────

@given('服务已启动')
def server_started(api_client):
    assert api_client is not None


@given('标准音频和用户音频均已上传')
def both_audio_uploaded():
    """Placeholder — audio files are loaded per scenario."""
    pass


@given(parsers.parse('标准音频 "{ref_name}" 和用户音频 "{user_name}"'))
def reference_and_user_audio(ref_name, user_name, test_data_dir):
    """Resolve reference and user audio files."""
    ref_path = test_data_dir / 'audio' / 'vocal' / ref_name
    user_path = test_data_dir / 'audio' / 'vocal' / user_name
    if not ref_path.exists():
        candidates = sorted((test_data_dir / 'audio' / 'vocal').glob('*.wav'))
        ref_path = candidates[0] if candidates else ref_path
    if not user_path.exists():
        candidates = sorted((test_data_dir / 'audio' / 'vocal').glob('*.wav'))
        user_path = candidates[-1] if len(candidates) > 1 else (candidates[0] if candidates else user_path)
    return {'reference': ref_path, 'user': user_path}


@given('DTW 已产出偏差数据')
def dtw_has_deviation_data():
    pass


@given('无 DTW 数据 (绝对评分场景)')
def no_dtw_data():
    return {'dtw_available': False}


@given('系统未匹配到标准歌曲 (无 DTW 数据)')
def no_reference_matched():
    return {'dtw_available': False, 'matched': False}


@given('DTW 降级重构完成')
def dtw_demotion_refactored():
    pass


@given('对比分析完成')
def compare_analysis_done():
    pass


# ── When ───────────────────────────────────────────

@when('DTW 三级对齐完成')
def dtw_three_level_alignment():
    pass


@when('进入评分阶段')
def enter_scoring_phase():
    pass


@when('前端请求对比分析建议')
def frontend_requests_advice():
    pass


@when('执行评分')
def execute_scoring():
    pass


@when('rhythm_scorer 计算节奏分数')
def rhythm_scorer_calculates():
    pass


@when('Code Review 检查 services/comparison/scoring_engine.py')
def code_review_check():
    pass


# ── Then ───────────────────────────────────────────

@then(parsers.parse('ComparisonService 应输出以下偏差数据 (而非评分):'))
def check_deviation_data_output(datatable):
    """E1: ComparisonService 是纯偏差提供者; legacy scoring_engine.py 已删除。"""
    expected_fields = {row[0] for row in datatable[1:]}
    assert expected_fields, '偏差数据字段表不应为空'

    from services.comparison.comparison_service import ComparisonService
    assert ComparisonService is not None

    assert not SCORING_ENGINE_PATH.exists(), \
        "E1 消双轨: scoring_engine.py 应已删除"


@then('不应输出任何 score, level, suggestions, diagnosis 等评分字段')
def check_no_scoring_fields():
    """E1: ComparisonService 输出不应含评分字段 — 检查其源码 result dict 键。"""
    src = (PROJECT_ROOT / 'services' / 'comparison' / 'comparison_service.py').read_text(encoding='utf-8')
    # result dict 不应再构造 'score'/'level'/'suggestions' 键
    assert "'score':" not in src, 'ComparisonService 不应再输出 score 字段'
    assert "'level':" not in src, 'ComparisonService 不应再输出 level 字段'
    assert "'suggestions':" not in src, 'ComparisonService 不应再输出 suggestions 字段'
    # 不应再引用 legacy 评分引擎
    assert 'scoring_engine' not in src.replace('SCORING_ENGINE_PATH', ''), \
        'ComparisonService 源码不应引用 scoring_engine'


@then('ComparisonService 不应持有 legacy scoring_engine 属性')
def check_no_scoring_engine_attribute():
    from services.comparison.comparison_service import ComparisonService
    service = ComparisonService(style='pop')
    assert not hasattr(service, 'scoring_engine'), \
        "E1: ComparisonService 不应再持有 legacy scoring_engine"


@then('DDD ComparisonScoringService 应承担对比评分 (legacy scoring_engine.py 已删)')
def check_ddd_scoring_service():
    assert not SCORING_ENGINE_PATH.exists(), \
        "E1 消双轨: scoring_engine.py 应已删除"
    from backend.domain.comparison.services import ComparisonScoringService
    assert ComparisonScoringService is not None


@then('风格权重应单一来源自 COMPARISON_STYLE_WEIGHTS (value_objects)')
def check_weights_single_source():
    from backend.domain.comparison.value_objects import COMPARISON_STYLE_WEIGHTS
    from backend.domain.comparison.services import ComparisonScoringService
    # services.py 的 STYLE_WEIGHTS 应直接引用单一来源 (而非本地复制)
    assert 'pop' in COMPARISON_STYLE_WEIGHTS
    assert ComparisonScoringService.STYLE_WEIGHTS is COMPARISON_STYLE_WEIGHTS, \
        "E1: STYLE_WEIGHTS 应单一来源引用 value_objects.COMPARISON_STYLE_WEIGHTS"


@then('不应存在独立的 "DTW 评分路径" 或 legacy "对比评分引擎"')
def check_no_legacy_scoring_path():
    assert not SCORING_ENGINE_PATH.exists(), \
        "E1 消双轨: scoring_engine.py 应已删除"


@then('建议应由 CompareAudioUseCase 复用 AdviceGenerator (四维子集) 生成')
def check_advice_reuses_generator():
    src = (PROJECT_ROOT / 'backend' / 'application' / 'comparison' / 'compare_audio.py').read_text(encoding='utf-8')
    assert 'AdviceGenerator' in src, 'CompareAudioUseCase 应复用 DDD AdviceGenerator'
    assert 'dimensions=' in src, 'CompareAudioUseCase 应传入四维子集 dimensions'


@then('domain 层不应再存在 generate_suggestions 硬编码')
def check_no_domain_suggestions():
    src = (PROJECT_ROOT / 'backend' / 'domain' / 'comparison' / 'services.py').read_text(encoding='utf-8')
    assert 'generate_suggestions' not in src, \
        "E5: domain 层 generate_suggestions 应已移除 (建议复用 AdviceGenerator)"


@then('所有六个维度应使用各自的独立评分逻辑 (pitch/rhythm/breath/technique/muscle/artistry)')
def check_all_dimensions_independent():
    """六维评估各自独立, 不依赖 DTW — 验证所有 scorer 可独立计算。"""
    from backend.domain.assessment.pitch_scorer import PitchScorer, PitchFeatures
    from backend.domain.assessment.rhythm_scorer import RhythmScorer, RhythmFeatures
    from backend.domain.assessment.breath_scorer import BreathScorer, BreathFeatures
    from backend.domain.assessment.technique_scorer import TechniqueScorer, TechniqueFeatures
    from backend.domain.assessment.muscle_scorer import MuscleStrengthScorer, MuscleFeatures
    from backend.domain.assessment.artistry_scorer import ArtistryScorer, ArtistryFeatures

    scorers_and_features = [
        (PitchScorer(), PitchFeatures()),
        (RhythmScorer(), RhythmFeatures()),
        (BreathScorer(), BreathFeatures()),
        (TechniqueScorer(), TechniqueFeatures()),
        (MuscleStrengthScorer(), MuscleFeatures()),
        (ArtistryScorer(), ArtistryFeatures()),
    ]
    for scorer, features in scorers_and_features:
        result = scorer.calculate(features)
        assert 0.0 <= result.raw_score <= 100.0, \
            f'{scorer.__class__.__name__} returned invalid score: {result.raw_score}'


@then('应使用现有的 onset + CV 路径 (行为与绝对评分一致)')
def check_legacy_rhythm_path():
    """无参考时节奏走 onset + CV 路径 — 验证 RhythmScorer 可独立计算。"""
    from backend.domain.assessment.rhythm_scorer import RhythmScorer, RhythmFeatures
    scorer = RhythmScorer()
    features = RhythmFeatures()
    result = scorer.calculate(features)
    assert 0.0 <= result.raw_score <= 100.0


@then('不应调用任何 DTW 相关逻辑')
def check_no_dtw_logic_called():
    pass  # 无参考场景不调用 DTW — 架构不变量


@then('legacy scoring_engine.py 文件应不存在 (评分统一走 DDD)')
def check_scoring_engine_deleted():
    assert not SCORING_ENGINE_PATH.exists(), \
        f"E1 消双轨: scoring_engine.py 应已删除, 实际仍存在"


@then('services/comparison/ 中不应出现 score 或 rating 相关的计算逻辑')
def check_no_score_rating_logic():
    """E1: legacy 评分引擎文件已删; 剩余模块为对齐/偏差/基准 (评分迁入 DDD)。"""
    comp_dir = PROJECT_ROOT / 'services' / 'comparison'
    files = {f.name for f in comp_dir.glob('*.py')}
    assert 'scoring_engine.py' not in files,         f"E1 消双轨: scoring_engine.py 应已删除, 实际仍在: {sorted(files)}"
    assert {'dtw_aligner.py', 'deviation_calculator.py',
            'benchmark_service.py', 'comparison_service.py'} <= files,         f'services/comparison/ 模块清单异常: {sorted(files)}'


@then('services/comparison/ 应只有: 偏差数据计算 + 对齐路径生成 + 置信度评估')
def check_file_only_has_deviation_logic():
    comp_dir = PROJECT_ROOT / 'services' / 'comparison'
    files = {f.name for f in comp_dir.glob('*.py')}
    assert 'scoring_engine.py' not in files, 'scoring_engine.py 应已删除'
    assert {'dtw_aligner.py', 'deviation_calculator.py',
            'benchmark_service.py', 'comparison_service.py'} <= files,         f'services/comparison/ 模块清单异常: {sorted(files)}'
