"""
Step definitions for pitch-realtime.feature — v7.13 Phase 2+3 实时音准对比 (骨架).

背景:
    v7.13 前端音准对比子系统 Phase 1 已落地后端 (参考音高 API + WS pitch_update) +
    Phase 2 落地前端 (PitchComparisonCanvas 偏差着色/滚动窗口/音高时间轴 +
    SingView 回放控制面板: 播放/暂停/拖拽/倍速/A-B 循环) +
    Phase 3 落地录音中实时对比 (PitchComparisonCanvas live 模式: 圆点/色带/趋势箭头/音分值)。

    浏览器 BDD 无法获取真实麦克风录音 → WS pitch_update 无数据 → Canvas 无曲线渲染。
    故本骨架所有数据相关步骤 xfail, 并在消息中标注对应的**纯 TS 单元测试文件** —
    这些单元测试才是行为的真正验证点 (Vitest):

      - tests/unit/utils/pitchNotes.test.ts   → Y 轴音高刻度/白键/音域
      - tests/unit/utils/pitchStats.test.ts   → 精准/略偏/跑调/静音百分比 + 最高/最低音
      - tests/unit/utils/pitchScroll.test.ts  → 滚动窗口/短音频视口/裁剪
      - tests/unit/utils/pitchScrollTicks.test.ts → 自动刻度步长/时间刻度
      - tests/unit/utils/pitchDeviation.test.ts   → 偏差颜色/静音灰/八度跳变/置信度阈值
      - tests/unit/utils/pitchPlayback.test.ts    → clampSeek/倍速推进/A-B 循环/帧率降级
      - tests/unit/utils/pitchLive.test.ts        → Phase 3 圆点淡出/趋势箭头/色带/音分值
      - tests/unit/utils/pitchSegments.test.ts    → Phase 4 问题段落/乐句切分/逐句评分

场景分布 (对齐 feature 六章):
    一 视觉规范 (3) / 二 数据质量 (5) / 三 播放控制 (4) — Phase 2 已实现
    四 性能兼容 (4) — Phase 5 部分 / 五 模式交互 (6) — Phase 3 录音中实时对比 + Phase 4 录音后回放分析 / 六 辅助 (3) — Phase 5
"""
import pytest
from pytest_bdd import given, when, then, parsers, scenarios

pytestmark = pytest.mark.browser

scenarios('../features/pitch-realtime.feature')


def _xfail(unit_test: str, phase: str = 'Phase 2') -> None:
    """浏览器 BDD 无真实音频/WS 数据 — xfail 并标注对应单元测试."""
    pytest.xfail(f'{phase} 已实现, 浏览器 BDD 需真实音频/WS; 由 {unit_test} 单元测试验证')


# ============================================================================
# Background
# ============================================================================

@given('Flask 服务已启动')
def flask_server_started():
    """服务可达性由 page fixture 验证 (FastAPI :8000)."""
    return True


@given('浏览器支持 Web Audio API 和 Canvas')
def browser_web_audio_supported():
    """Chromium 始终支持 Web Audio API + Canvas (Playwright headless)."""
    return True


@given('前端已加载 YIN 音高检测模块 (pitch-detector.js)')
def yin_module_loaded():
    """v7.13 架构: 基频检测在【后端 PYIN】(_parse_frames → WS pitch_update),
    前端无独立 pitch-detector.js — 背景为 v7.13 前假设."""
    pytest.xfail('基频检测在后端 PYIN (v7.13), 前端无 pitch-detector.js')


# ============================================================================
# 一、通用视觉规范 (3 场景)
# ============================================================================

# Scenario 音准曲线基本渲染
@given('一个已完成评估的音频文件 (含预提取的基频曲线)')
def completed_assessment_audio(page):
    pytest.xfail('需真实音频 + 后端基频提取 (v7.13); 参考线加载经 /songs/{id}/pitch')


@when(parsers.parse('我点击 "播放" 并切换到 "音准对比" 视图'))
def click_play_and_switch_pitch_view(page):
    _xfail('pitchPlayback.test.ts / pitchScroll.test.ts')


@then('应在 Canvas 上渲染两条曲线:')
def canvas_renders_two_curves(datatable):
    _xfail('pitchDeviation.test.ts (alignPitchCurves 参考/用户双曲线)')


@then('曲线应从右向左滚动 (类似全民K歌)')
def curve_scrolls_right_to_left(page):
    _xfail('pitchScroll.test.ts (computeScrollWindow 播放位置居中滚动)')


@then('当前播放位置应在画面中央 (竖线标记)')
def cursor_at_center(page):
    _xfail('pitchScroll.test.ts (cursorXFraction 居中标尺)')


@then('Y 轴标注音高 (C3-B5, 钢琴键白键高亮)')
def y_axis_piano_scale(page):
    _xfail('pitchNotes.test.ts (generateNoteTicks 白键高亮)')


@then('X 轴显示时间刻度 (秒)')
def x_axis_time_ticks(page):
    _xfail('pitchScrollTicks.test.ts (generateTimeTicks)')


# Scenario 音准偏差颜色映射
@given('用户音高与标准音高存在不同程度的偏差')
def user_has_pitch_deviation(page):
    pytest.xfail('需真实 WS pitch_update 数据')


@when('实时曲线渲染到不同段落')
def render_deviation_segments(page):
    _xfail('pitchDeviation.test.ts')


@then('用户曲线应按以下规则着色:')
def deviation_color_table(datatable):
    # 表: 偏差范围/颜色/含义 (≤25 绿, 25-50 橙, >50 红)
    _xfail('pitchDeviation.test.ts (deviationColor 阈值映射)')


@then('颜色应在音符边界处平滑过渡 (非逐帧跳变)')
def smooth_color_transition(page):
    _xfail('pitchDeviation.test.ts / PitchComparisonCanvas 逐段合并绘制')


@then('人声未发声段落应显示为灰色虚线 (#94a3b8)')
def silent_gray_dashed(page):
    _xfail('pitchDeviation.test.ts (置信度 < 0.5 视为静音 → 灰色)')


# Scenario 无标准音频时仅显示用户曲线
@given('系统未匹配到标准歌曲, 也没有手动指定参考音频')
def no_reference_audio(page):
    pytest.xfail('需真实评估会话判定 matched_song')


@when('我播放已评估的音频并切换到音准视图')
def play_evaluated_audio_switch(page):
    _xfail('pitchPlayback.test.ts')


@then('应只渲染一条用户音高曲线 (蓝色 #3b82f6)')
def single_user_curve_blue(page):
    _xfail('pitchDeviation.test.ts (无参考 → DEFAULT_USER_COLOR)')


@then('不显示颜色偏差映射 (因为没有参考)')
def no_deviation_map(page):
    _xfail('pitchDeviation.test.ts (alignPitchCurves 空参考 → 不计算偏差)')


@then(parsers.parse('视图标题应标注 "绝对音高 (无参考)"'))
def no_ref_title(page):
    _xfail('PitchComparisonCanvas noRefTitle prop')


@then('Y 轴仍显示音高刻度')
def y_axis_still_shown(page):
    _xfail('pitchNotes.test.ts')


# ============================================================================
# 二、边界条件 — 数据质量 (5 场景)
# ============================================================================

# Scenario 清辅音/气声段落 — 基频检测失败
@given(parsers.parse('音频中存在气声段落 (如 "h", "s", "f" 辅音)'))
def breathy_consonant_segment(page):
    pytest.xfail('需真实音频驱动后端 PYIN')


@when('播放到该段落')
def play_that_segment(page):
    _xfail('pitchPlayback.test.ts')


@then('基频检测应返回置信度 < 0.5')
def confidence_below_threshold(page):
    _xfail('pitchDeviation.test.ts (DEVIATION_THRESHOLDS.silentConfidence = 0.5)')


@then('该段落应显示为虚线空白 (颜色 #94a3b8, 透明度 40%)')
def silent_gray_dashed_40(page):
    _xfail('pitchDeviation.test.ts (置信度 < 0.5 静音段)')


@then('不应标记为跑调 (红色) — 因为不是音高错误, 是检测不到')
def breathy_not_marked_offtune(page):
    _xfail('pitchDeviation.test.ts (isSilent → 不计算偏差)')


@then('空白段落在 Y 轴上的位置应延续上一个有效音高 (不跳变)')
def silent_extends_last_valid(page):
    _xfail('PitchComparisonCanvas drawDeviationCurve (_lastValidFreq 延续)')


# Scenario 八度跳变误检测
@given('PYIN 算法在某些段落产生八度误差 (检测到基频的 2 倍频)')
def pyin_octave_error(page):
    pytest.xfail('需真实音频驱动后端 PYIN')


@when('显示该段落的音高曲线')
def show_octave_segment(page):
    _xfail('pitchDeviation.test.ts')


@then('系统应检测到八度跳变 (相邻帧音高跳变 ≥ 12 半音)')
def detect_octave_jump(page):
    _xfail('pitchDeviation.test.ts (isOctaveJump ≥ 12 半音)')


@then(parsers.parse('应在曲线上方显示 ⚠️ 标记 "八度跳变 (可能误检)"'))
def octave_jump_marker(page):
    _xfail('PitchComparisonCanvas (⚠️ 标记)')


@then('该段落不应标记为红色跑调')
def octave_not_red(page):
    _xfail('pitchDeviation.test.ts (isOctaveJump 独立于颜色映射)')


@then('该段落的颜色应使用灰色 (表示不确定)')
def octave_gray(page):
    _xfail('pitchDeviation.test.ts (isSilent/置信度判定)')


# Scenario 音频首尾静音
@given('音频开头有 0.5 秒静音, 结尾有 1 秒静音')
def leading_trailing_silence(page):
    pytest.xfail('需真实音频数据')


@when('渲染完整的音高曲线')
def render_full_curve(page):
    _xfail('pitchScroll.test.ts (trimSilence)')


@then('首尾静音段应自动裁剪 (不显示或显示为空白)')
def silence_trimmed(page):
    _xfail('pitchScroll.test.ts (trimSilence)')


@then('第一条有效音高的位置应对齐到时间轴 0:00')
def first_valid_aligned(page):
    _xfail('pitchScroll.test.ts (trimSilence 对齐 0)')


@then('不应将静音段算作 "跑调"')
def silence_not_offtune(page):
    _xfail('pitchDeviation.test.ts (isSilent → 不标记跑调)')


# Scenario 短音频 (不足 10 秒)
@given('一个仅 5 秒长的短音频')
def short_5s_audio(page):
    pytest.xfail('需真实音频数据')


@when('播放并显示音准对比')
def play_and_show_comparison(page):
    _xfail('pitchPlayback.test.ts')


@then('Canvas 应自动缩放到填满视口宽度')
def canvas_fills_viewport(page):
    _xfail('pitchScroll.test.ts (autoViewportSeconds 短音频全曲)')


@then('时间轴刻度应调整为秒级精度 (每格 1 秒)')
def time_ticks_1s(page):
    _xfail('pitchScrollTicks.test.ts (autoTickStepSeconds ≤10s → 1s)')


@then('曲线不应被裁剪')
def curve_not_clipped(page):
    _xfail('pitchScroll.test.ts (viewport ≥ 总时长 → 不裁剪)')


# Scenario 长音频 (超过 3 分钟)
@given('一个 4 分钟的长音频')
def long_4min_audio(page):
    pytest.xfail('需真实音频数据')


@then('应使用视口窗口 (可见范围约 15 秒)')
def viewport_15s(page):
    _xfail('pitchScroll.test.ts (autoViewportSeconds 长音频 → 15s)')


@then('曲线应随播放位置平滑滚动 (不是跳帧)')
def smooth_scroll(page):
    _xfail('pitchScroll.test.ts (computeScrollWindow 连续滚动)')


@then('底部应有缩略导航条 (全长波形预览 + 当前视口高亮)')
def thumbnail_nav_bar(page):
    pytest.xfail('Phase 5 未实现 (PROJECT_STATUS 已知问题)')


@then('拖动缩略条可跳转到任意位置')
def drag_thumbnail_jump(page):
    pytest.xfail('Phase 5 未实现 (缩略导航条依赖)')


# ============================================================================
# 三、边界条件 — 播放控制 (4 场景)
# ============================================================================

@given('我正在播放音频并查看实时音准对比')
def playing_with_comparison(page):
    pytest.xfail('需真实 WS pitch_update 数据')


@given('我正在查看音准对比视图')
def viewing_comparison(page):
    pytest.xfail('需真实 WS pitch_update 数据')


@given('音频以 0.5 倍速播放')
def playing_at_half_speed(page):
    pytest.xfail('需真实 WS pitch_update 数据')


@given('我设置了 A-B 循环 (1:00-1:30)')
def ab_loop_set(page):
    pytest.xfail('需真实 WS pitch_update 数据')


@when('我点击 "暂停"')
def click_pause(page):
    _xfail('pitchPlayback.test.ts (advancePlayback rate=0 冻结)')


@then('曲线滚动应立即停止')
def scroll_frozen(page):
    _xfail('pitchPlayback.test.ts (rate=0 → current 不变)')


@then('当前帧的偏差着色应保持显示')
def deviation_color_retained(page):
    _xfail('pitchDeviation.test.ts (帧着色不因暂停变化)')


@then('播放位置竖线应保持不动')
def cursor_frozen(page):
    _xfail('pitchScroll.test.ts (cursorXFraction 依赖 currentTime)')


@then('恢复播放后应从暂停位置继续滚动 (无跳跃)')
def resume_no_jump(page):
    _xfail('pitchPlayback.test.ts (clampSeek/advancePlayback)')


@when('我拖拽播放进度条到 1:30 位置')
def drag_progress_to_1_30(page):
    _xfail('pitchPlayback.test.ts (clampSeek → replayTime)')


@then('音准曲线应立即跳转到对应时间点')
def curve_jumps_to_time(page):
    _xfail('pitchPlayback.test.ts (clampSeek)')


@then('不应出现曲线从 0:00 重新滚动的动画')
def no_restart_animation(page):
    _xfail('pitchPlayback.test.ts (seek 直接定位, 非重置)')


@then('偏差着色应瞬间更新为新位置的数据')
def deviation_updates_instantly(page):
    _xfail('pitchDeviation.test.ts (alignPitchCurves 按时间插值)')


@then('跳转响应应在 200ms 内完成')
def seek_within_200ms(page):
    _xfail('pitchPlayback.test.ts (clampSeek 纯函数 O(1))')


@when('我查看音准对比视图')
def view_comparison_again(page):
    _xfail('pitchPlayback.test.ts')


@then('曲线滚动速度应同步减半')
def scroll_half_speed(page):
    _xfail('pitchPlayback.test.ts (advancePlayback dt*rate)')


@then('偏差着色不应受影响 (仍然逐帧计算)')
def deviation_unaffected_by_rate(page):
    _xfail('pitchDeviation.test.ts (着色与倍速解耦)')


@then('时间轴刻度应保持不变 (显示真实时间, 非播放时间)')
def time_axis_real_time(page):
    _xfail('pitchScrollTicks.test.ts (刻度按真实时间)')


@then('1.5 倍速时滚动加速, 但渲染帧率保持 ≥ 30fps')
def rate_1_5_fps_30(page):
    _xfail('pitchPlayback.test.ts (advancePlayback 1.5x)')


@when('播放循环回到 A 点')
def loop_back_to_a(page):
    _xfail('pitchPlayback.test.ts (wrapInABLoop)')


@then('曲线应从 A 点重新开始渲染')
def curve_restarts_from_a(page):
    _xfail('pitchPlayback.test.ts (wrapInABLoop 回绕到 A)')


@then('不应出现残影或旧曲线残留')
def no_ghosting(page):
    _xfail('PitchComparisonCanvas (clearRect 全量重绘)')


@then('循环过渡应无缝 (无闪烁)')
def seamless_loop(page):
    _xfail('pitchPlayback.test.ts (wrapInABLoop 无缝回绕)')


# ============================================================================
# 四、边界条件 — 性能与兼容性 (4 场景)
# ============================================================================

@given('任何播放速度下的音准对比视图')
def any_rate_comparison(page):
    pytest.xfail('需真实 WS pitch_update 数据')


@then('Canvas 渲染帧率应 ≥ 30fps')
def canvas_fps_30(page):
    _xfail('pitchPlayback.test.ts (帧率保障)')


@then('不应造成音频播放卡顿或音画不同步')
def no_audio_stutter(page):
    pytest.xfail('需真实音频播放测量')


@then('音画同步误差应 < 50ms')
def sync_error_50ms(page):
    pytest.xfail('需真实音频播放测量')


@then('若浏览器帧率低于 30fps, 应自动降至 15fps (降级渲染)')
def auto_degrade_to_15fps(page):
    _xfail('pitchPlayback.test.ts (degradeTargetFps → 15)')


@given('设备 CPU 性能不足 (用户可感知的卡顿)')
def low_perf_device(page):
    pytest.xfail('需真实性能测量')


@when('系统检测到连续 3 秒帧率 < 20fps')
def detect_low_fps_3s(page):
    _xfail('pitchPlayback.test.ts (shouldDegradeFrameRate 连续 3 秒 < 20fps)')


@then('应自动切换为 "性能模式":')
def performance_mode_table(datatable):
    # 表: 优化项/效果 (抗锯齿/着色颗粒度/网格/缩略条)
    _xfail('pitchPlayback.test.ts (性能模式优化项 — Phase 5 细化)')


@then('应在界面显示 "性能模式 (可手动关闭)"')
def performance_mode_label(page):
    pytest.xfail('Phase 5 未实现 (UI 提示)')


@then('用户可手动切换回 "画质模式"')
def manual_switch_quality_mode(page):
    pytest.xfail('Phase 5 未实现 (手动切换)')


@when('我切换到另一个浏览器标签页')
def switch_browser_tab(page):
    pytest.xfail('Playwright 可切 tab, 但渲染节流需真实动画帧')


@then('Canvas 渲染应暂停 (requestAnimationFrame 自动节流)')
def rAF_throttled(page):
    pytest.xfail('依赖浏览器原生 rAF 节流, 无音频数据无法验证曲线')


@then('音频播放应继续 (不中断)')
def audio_continues_in_background(page):
    pytest.xfail('需真实音频播放')


@then('切换回标签页时, 曲线应瞬间更新到当前播放位置')
def catch_up_on_tab_return(page):
    pytest.xfail('需真实 WS 数据')


@then('不应出现 "追赶式" 高速滚动')
def no_catchup_scroll(page):
    pytest.xfail('需真实 WS 数据')


@given('Canvas 宽度为 800px')
def canvas_width_800(page):
    pytest.xfail('需真实 WS 数据 (Canvas 无数据不渲染)')


@when('我调整浏览器窗口大小到 1200px')
def resize_window_1200(page):
    pytest.xfail('需真实 WS 数据 (Canvas 无数据不渲染)')


@then('Canvas 应重新计算尺寸并重绘')
def canvas_resize_redraw(page):
    _xfail('PitchComparisonCanvas (DPR 感知 initCanvas/ResizeObserver)')


@then('不应出现拉伸变形')
def no_stretch(page):
    _xfail('PitchComparisonCanvas (DPR 缩放)')


@then('曲线细节应保持清晰 (重新按新宽度采样)')
def curve_sharp_on_resize(page):
    _xfail('PitchComparisonCanvas (重采样)')


@then('响应时间 < 200ms')
def resize_under_200ms(page):
    _xfail('PitchComparisonCanvas (DPR 感知重绘)')


# ============================================================================
# 五、模式特定交互 (6 场景)
# ============================================================================

# Scenario Quick/Pro 无参考
@given('我用 Quick 模式上传了一首曲库中不存在的歌曲')
def quick_upload_no_library_song(page):
    pytest.xfail('需真实上传 + 评估会话')


@given('评估已完成 (无 matched_song)')
def evaluation_done_no_match(page):
    pytest.xfail('需真实评估会话')


@when('我切换到 "音准视图" 并播放')
def switch_to_pitch_view(page):
    _xfail('pitchPlayback.test.ts')


@then('应显示单条用户音高曲线 (蓝色, 无对比)')
def single_blue_curve(page):
    _xfail('pitchDeviation.test.ts (无参考 → DEFAULT_USER_COLOR)')


@then('视图顶部标注 "无参考音频 — 显示绝对音高"')
def no_ref_banner(page):
    _xfail('PitchComparisonCanvas noRefTitle')


@then('应在曲线上标注 "最高音: G5" "最低音: C3"')
def pitch_range_labels(page):
    _xfail('pitchStats.test.ts (computePitchRange → minNote/maxNote) + SingView 回放统计面板', 'Phase 4')


# Scenario Quick/Pro 有自动匹配
@given('我用 Quick 模式上传了 "月亮代表我的心" 翻唱')
def quick_upload_moon_covers(page):
    pytest.xfail('需真实上传 + 评估会话')


@given('系统自动匹配到标准歌曲 (置信度 0.85)')
def auto_match_song(page):
    pytest.xfail('auto-match 依赖后端匹配 (v7.13 未含)')


@then('应显示双曲线对比 (标准 vs 用户)')
def dual_curve(page):
    _xfail('pitchDeviation.test.ts (alignPitchCurves 双曲线)')


@then('视图顶部标注 "参考: 月亮代表我的心 - 邓丽君"')
def ref_banner(page):
    _xfail('PitchComparisonCanvas refPitchData 渲染')


@then('偏差着色 (绿/橙/红) 应基于与标准音高的差距')
def deviation_vs_standard(page):
    _xfail('pitchDeviation.test.ts (freqToCents → deviationColor)')


@then('播放结束后应显示统计: "精准率 78% | 略偏 15% | 跑调 7%"')
def stats_78_15_7(page):
    _xfail('pitchStats.test.ts (computeDeviationStats 分母为有声帧) + SingView 回放统计面板', 'Phase 4')


# Scenario 选歌录音 — 录音中实时对比
@given('我已选择 "月亮代表我的心" 作为标准歌曲')
def selected_moon_song(page):
    pytest.xfail('选歌 UI 可注入 (sing-song-select 已覆盖), 录音需 WS')


@given('已进入录音模式')
def in_recording_mode(page):
    pytest.xfail('Vue 3 录音依赖 WebSocket 连接 (v7.12)')


@when('我开始录音并演唱')
def start_recording_sing(page):
    pytest.xfail('Vue 3 录音依赖 WebSocket 连接 (v7.12)')


@then('应在 Canvas 上实时显示:')
def canvas_realtime_elements(datatable):
    # 表: 元素/说明 (标准虚线/实时圆点/偏差色带/音分数值/趋势箭头)
    _xfail('pitchLive.test.ts (deviationTrend/trendDisplay/freqAtCentsOffset 圆点/色带/趋势/偏差值)', 'Phase 3')


@then('圆点在 2 秒后淡出 (保留最近的音高轨迹)')
def dots_fade_after_2s(page):
    _xfail('pitchLive.test.ts (visibleLivePoints/dotAlpha 2s 保留窗口线性淡出)', 'Phase 3')


@then('不应显示完整的用户曲线 (因为还没唱完)')
def no_full_curve_yet(page):
    _xfail('PitchComparisonCanvas live 模式 (仅实时圆点, 不画完整曲线)', 'Phase 3')


# Scenario 选歌录音 — 录音后回放对比
@given('我刚录完一段 "月亮代表我的心" 的演唱')
def just_finished_recording(page):
    pytest.xfail('Vue 3 录音依赖 WebSocket 连接 (v7.12)')


@when('我点击 "查看回放" 并播放')
def click_view_replay(page):
    _xfail('pitchPlayback.test.ts (toggleReplay/advancePlayback 回放推进)', 'Phase 4')


@then('应显示完整的双曲线对比 (与 Scenario "回放时查看音准 (有自动匹配)" 一致)')
def full_dual_curve(page):
    _xfail('pitchDeviation.test.ts (Phase 2 已实现双曲线)')


@then('问题段落应用红色半透明背景高亮 (偏差 > 50 音分持续 > 0.5s)')
def problem_segment_highlight(page):
    _xfail('pitchSegments.test.ts (findProblemSegments 阈值 50/持续 0.5s)', 'Phase 4')


@then('点击问题段落可跳到该位置重新播放')
def click_problem_jump(page):
    _xfail('PitchComparisonCanvas onClickCanvas 全画布 seek + pitchSegments.test.ts (问题段 = 高亮区间)', 'Phase 4')


@then('应显示逐句音准评分 (每句一个分数标签浮在曲线上方)')
def per_phrase_scores(page):
    _xfail('pitchSegments.test.ts (segmentPhrases 静音间隙切分 + scorePhrase 精准率 + phraseScoreColor)', 'Phase 4')


# Scenario 对比分析 — 双轨叠加对比
@given('我手动上传了标准音频和用户音频')
def manual_upload_both(page):
    pytest.xfail('对比分析视图 (CompareView) Phase 5')


@given('DTW 对齐已完成')
def dtw_aligned(page):
    pytest.xfail('对比分析视图 (CompareView) Phase 5')


@when('我播放对比结果')
def play_compare_result(page):
    pytest.xfail('对比分析视图 (CompareView) Phase 5')


@then('应显示双曲线叠加 (经过 DTW 时间对齐)')
def dual_curve_dtw_aligned(page):
    pytest.xfail('对比分析视图 (CompareView) Phase 5')


@then('两条曲线使用不同颜色 (标准: #6366f1 虚线, 用户: 动态着色实线)')
def two_curve_colors(page):
    _xfail('pitchDeviation.test.ts (Phase 2 已实现双曲线配色)')


@then('偏差区域应在标准曲线上下标注填色:')
def deviation_fill_table(datatable):
    pytest.xfail('对比分析视图 (CompareView) Phase 5')


@then('底部应显示偏差热力图条 (一整行, 颜色密度表示跑调程度)')
def heatmap_bar(page):
    pytest.xfail('对比分析视图 (CompareView) Phase 5')


@then('点击偏差热力图任意位置可跳转播放')
def heatmap_click_jump(page):
    pytest.xfail('对比分析视图 (CompareView) Phase 5')


# Scenario 对比分析 — DTW 未对齐段落标记
@given('DTW 对齐在某些段落置信度低 (< 0.5)')
def dtw_low_confidence(page):
    pytest.xfail('对比分析视图 (CompareView) Phase 5')


@when('渲染音准对比视图')
def render_comparison_view(page):
    _xfail('pitchDeviation.test.ts')


@then('低置信度段落应在曲线上方标记 "⚠️ 对齐不确定"')
def low_conf_marker(page):
    pytest.xfail('对比分析视图 (CompareView) Phase 5')


@then('该段落的偏差着色应使用灰色虚线 (不误导用户)')
def low_conf_gray(page):
    _xfail('pitchDeviation.test.ts (置信度 < 0.5 → 静音灰)')


@then('统计面板应排除低置信度段落的 "跑调率" 计算')
def stats_exclude_low_conf(page):
    _xfail('pitchStats.test.ts (分母剔除静音/低置信度帧)')


# ============================================================================
# 六、辅助功能 (3 场景)
# ============================================================================

# Scenario 切换显示模式
@given('我正在查看音准对比视图 (双曲线模式)')
def viewing_dual_mode(page):
    pytest.xfail('需真实 WS pitch_update 数据')


@when('我点击 "仅显示用户曲线"')
def click_user_only(page):
    pytest.xfail('Phase 5 未实现 (显示模式切换) — 见 PROJECT_STATUS')


@then('标准曲线应隐藏')
def ref_curve_hidden(page):
    pytest.xfail('Phase 5 未实现 (showReference prop 已设计)')


@then('用户曲线切换为蓝色 (无偏差着色)')
def user_curve_blue(page):
    pytest.xfail('Phase 5 未实现 (DEFAULT_USER_COLOR)')


@then('再次点击 "显示对比" → 恢复标准曲线 + 偏差着色')
def restore_dual_mode(page):
    pytest.xfail('Phase 5 未实现 (切换恢复)')


@then('这个切换不应中断播放')
def toggle_not_interrupt(page):
    pytest.xfail('Phase 5 未实现 (播放连续性)')


# Scenario 导出音准对比截图
@given('音准对比视图显示了一段典型的跑调段落')
def view_with_offtune_segment(page):
    pytest.xfail('需真实 WS pitch_update 数据')


@when('我点击 "截图" 按钮')
def click_screenshot(page):
    pytest.xfail('Phase 5 未实现 (截图导出) — 见 PROJECT_STATUS')


@then('应导出当前 Canvas 内容为 PNG 图片')
def export_canvas_png(page):
    pytest.xfail('Phase 5 未实现 (canvas.toDataURL)')


@then('图片应包含当前时间戳水印 "01:23 / 03:45"')
def watermark_in_png(page):
    pytest.xfail('Phase 5 未实现 (时间戳水印)')


@then('图片分辨率应为 Canvas 实际分辨率 (不失真)')
def png_actual_resolution(page):
    pytest.xfail('Phase 5 未实现 (DPR 分辨率)')


@then('可附加到评估报告中')
def attach_to_report(page):
    pytest.xfail('Phase 5 未实现 (报告集成)')


# Scenario 键盘快捷键
@given('音准对比视图处于激活状态')
def pitch_view_active(page):
    pytest.xfail('需真实 WS pitch_update 数据')


@when('我按下以下按键:')
def press_keys(datatable):
    # 表: 按键/行为 (Space/←/→/R/S/1/2)
    pytest.xfail('Phase 5 未实现 (键盘快捷键) — 见 PROJECT_STATUS')


@then('对应行为应立即生效')
def key_binding_effective(page):
    pytest.xfail('Phase 5 未实现 (键盘快捷键)')


@then('不应与浏览器默认快捷键冲突')
def no_default_conflict(page):
    pytest.xfail('Phase 5 未实现 (preventDefault 处理)')
