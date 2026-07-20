/**
 * ReportPage — 报告页 (评分展示 + 雷达图 + 特征图)
 *
 * 路由: #/report/:analysisId
 * 动画序列 (v2.0, AnimationController 驱动):
 *   1. 总分环形 + 数字滚动 (ScoreRing)
 *   2. 五维进度条 fillBar
 *   3. 雷达图渐进
 *   4. 建议列表 stagger fadeIn
 *
 * @version 2.0
 */

import { BaseComponent } from '../components/BaseComponent.js';
import { ScoreRing } from '../components/ScoreRing.js';
import { AudioPlayer } from '../modules/audio.js';
import { ScoreCounter } from '../components/ScoreCounter.js';
import { RadarChart } from '../components/RadarChart.js';
import { PitchCurve } from '../components/PitchCurve.js';
import { showToast } from '../components/Toast.js';

export class ReportPage extends BaseComponent {
    static animationPreset = 'page-enter-scale';

    _scoreRing;
    _radarChart;
    _pitchCurve;
    _audioPlayer;
    _result = null;

    async mount(params) {
        if (this.store) {
            this._result = this.store.getState('analysis').result;
        }

        this.render();
        this.bindEvents();

        if (!this._result) {
            this.el.querySelector('#reportContent').style.display = 'none';
            this.el.querySelector('#reportEmpty').style.display = 'block';
            return;
        }

        this._populateData(this._result);
        this._animateEntrance(this._result);
    }

    render() {
        this.el = this.createElement('div', { id: 'page-report', className: 'page page-container' });

        this.el.innerHTML = `
        <div id="reportContent">
            <!-- 总分区域 -->
            <div class="score-header" id="scoreHeader" style="text-align:center; margin-bottom:32px;">
                <div id="scoreRingContainer"></div>
                <div class="score-level" id="scoreLevel" style="margin-top:8px;font-size:18px;font-weight:600;color:var(--text-secondary);">--</div>
                <div id="modeBadge" style="margin-top:6px;font-size:11px;color:var(--text-muted);"></div>
            </div>

            <!-- 音频播放器 -->
            <div class="card" id="audioPlayerCard" style="margin-bottom:24px; display:none;">
                <div class="card-header"><span class="card-title">🎧 音频回放</span></div>
                <div class="card-body" style="display:flex;align-items:center;gap:12px;">
                    <button id="audioPlayBtn" class="btn btn-primary" style="padding:8px 16px;">▶ 播放</button>
                    <div id="audioProgress" style="flex:1;height:6px;background:var(--bg-elevated);border-radius:3px;overflow:hidden;">
                        <div id="audioProgressFill" style="height:100%;width:0%;background:var(--primary);transition:width 0.1s linear;"></div>
                    </div>
                    <span id="audioTime" style="font-size:12px;color:var(--text-muted);min-width:80px;text-align:right;">00:00 / 00:00</span>
                </div>
            </div>

            <!-- 五维评分 -->
            <div class="card" id="dimensionCard" style="margin-bottom:24px;">
                <div class="card-header"><span class="card-title">📊 五维评分</span></div>
                <div class="card-body">
                    <div class="dimension-bars" id="dimensionBars"></div>
                </div>
            </div>

            <!-- 雷达图 -->
            <div class="card" id="radarCard" style="margin-bottom:24px;">
                <div class="card-header"><span class="card-title">🎯 能力雷达图</span></div>
                <div class="card-body" id="radarChartContainer"></div>
            </div>

            <!-- 音高曲线 -->
            <div class="card" id="pitchCard" style="margin-bottom:24px;">
                <div class="card-header"><span class="card-title">📈 音高曲线</span></div>
                <div class="card-body" id="pitchCurveContainer"></div>
            </div>

            <div class="card" id="vizCard" style="margin-bottom:24px; display:none;">
                <div class="card-header"><span class="card-title">🔬 特征可视化</span></div>
                <div class="card-body" id="featureVisualization"></div>
            </div>

            <div class="card" id="phraseCard" style="margin-bottom:24px; display:none;">
                <div class="card-header"><span class="card-title">📝 逐句评分</span></div>
                <div class="card-body" id="phraseSection"></div>
            </div>

            <!-- 改进建议 -->
            <div class="card" id="adviceCard" style="margin-bottom:24px;">
                <div class="card-header"><span class="card-title">💡 改进建议</span></div>
                <div class="card-body">
                    <ul id="adviceList" style="list-style:none;padding:0;margin:0;"></ul>
                </div>
            </div>

            <!-- 操作栏 -->
            <div class="action-bar" style="display:flex;gap:12px;justify-content:center;margin-bottom:32px;">
                <button class="btn btn-primary" id="exportPdfBtn">📄 导出 PDF</button>
                <button class="btn btn-secondary" id="exportImgBtn">🖼️ 导出图片</button>
                <button class="btn btn-secondary" id="reAnalyzeBtn">🔄 重新分析</button>
            </div>
        </div>

        <div id="reportEmpty" style="display:none; text-align:center; padding:60px 20px;">
            <div style="font-size:48px; margin-bottom:16px;">📭</div>
            <h2 style="color:var(--text-primary); margin-bottom:8px;">未找到分析结果</h2>
            <p style="color:var(--text-muted); margin-bottom:24px;">该分析记录不存在或已过期</p>
            <button class="btn btn-primary" onclick="window.__router?.navigate('#/')">返回首页</button>
        </div>
        `;
        this.container.appendChild(this.el);
    }

    bindEvents() {
        this.el.querySelector('#exportPdfBtn')?.addEventListener('click', () => this._exportReport('pdf'));
        this.el.querySelector('#exportImgBtn')?.addEventListener('click', () => this._exportReport('image'));
        this.el.querySelector('#reAnalyzeBtn')?.addEventListener('click', () => {
            if (this.router) this.router.navigate('#/');
        });
    }

    // ========================================================================
    // 数据填充
    // ========================================================================

    _populateData(result) {
        const scores = result.scores || {};

        // 模式标识
        const modeEl = this.el.querySelector('#modeBadge');
        if (modeEl && result.mode) {
            const label = result.mode === 'professional' ? '🔬 专业评估' : '⚡ 快速评估';
            modeEl.textContent = label;
        }

        // 五维进度条
        const barsContainer = this.el.querySelector('#dimensionBars');
        if (barsContainer && scores) {
            const dims = [
                { key: 'pitch', label: '音准', color: 'var(--dim-pitch)', weight: '25%' },
                { key: 'rhythm', label: '节奏', color: 'var(--dim-rhythm)', weight: '25%' },
                { key: 'breath', label: '气息', color: 'var(--dim-breath)', weight: '10%' },
                { key: 'technique', label: '发声技术', color: 'var(--dim-technique)', weight: '25%' },
                { key: 'artistry', label: '艺术表现', color: 'var(--dim-artistry)', weight: '15%' }
            ];

            barsContainer.innerHTML = dims.map(d => {
                const score = scores[d.key] || 0;
                return '<div class="dimension-row" style="display:flex;align-items:center;gap:12px;margin-bottom:14px;">'
                    + '<span style="width:80px;font-size:13px;color:var(--text-secondary);text-align:right;">' + d.label + '</span>'
                    + '<div style="flex:1;height:8px;background:var(--bg-elevated);border-radius:var(--radius-full);overflow:hidden;">'
                    + '<div id="dim' + d.key.charAt(0).toUpperCase() + d.key.slice(1) + 'Bar"'
                    + ' style="height:100%;width:0%;background:' + d.color + ';border-radius:var(--radius-full);transform-origin:left center;"></div></div>'
                    + '<span id="dim' + d.key.charAt(0).toUpperCase() + d.key.slice(1) + 'Value"'
                    + ' style="width:36px;font-size:13px;font-weight:600;color:' + d.color + ';text-align:right;">0</span>'
                    + '<span style="width:30px;font-size:11px;color:var(--text-muted);">' + d.weight + '</span></div>';
            }).join('');
        }

        // 改进建议
        const adviceList = this.el.querySelector('#adviceList');
        if (adviceList && result.advice?.length) {
            adviceList.innerHTML = result.advice.map(a =>
                '<li style="padding:10px 0;border-bottom:1px solid var(--border);color:var(--text-secondary);font-size:14px;">💡 ' + a + '</li>'
            ).join('');
        }

        // 评分等级
        const scoreLevel = this.el.querySelector('#scoreLevel');
        if (scoreLevel && result.total_score !== undefined) {
            const ts = result.total_score;
            if (ts >= 90) scoreLevel.textContent = '优秀';
            else if (ts >= 80) scoreLevel.textContent = '良好';
            else if (ts >= 70) scoreLevel.textContent = '中等';
            else if (ts >= 60) scoreLevel.textContent = '及格';
            else scoreLevel.textContent = '需改进';
        }
    }

    // ========================================================================
    // GSAP 动画 (AnimationController 驱动)
    // ========================================================================

    _animateEntrance(result) {
        const scores = result.scores || {};

        // 0. 音频播放器
        if (result.filepath) {
            const playerCard = this.el.querySelector('#audioPlayerCard');
            if (playerCard) playerCard.style.display = '';
            this._audioPlayer = new AudioPlayer();
            this._audioPlayer.load(result.filepath).then(() => {
                this._setupAudioControls();
            }).catch(() => {
                // 文件不可用时隐藏播放器
                if (playerCard) playerCard.style.display = 'none';
            });
        }

        // 1. 环形评分 (独立于 Controller, Canvas 动画)
        const ringContainer = this.el.querySelector('#scoreRingContainer');
        this._scoreRing = new ScoreRing(ringContainer, { size: 140 });
        this._scoreRing.render();
        this._scoreRing.animate(result.total_score || 0);

        // 2. 雷达图
        const radarContainer = this.el.querySelector('#radarChartContainer');
        this._radarChart = new RadarChart(radarContainer);
        this._radarChart.render();
        this._radarChart.setData(scores);
        this._radarChart.animate();

        // 3. 音高曲线
        const pitchContainer = this.el.querySelector('#pitchCurveContainer');
        if (pitchContainer && result.pitch_curve) {
            this._pitchCurve = new PitchCurve(pitchContainer);
            this._pitchCurve.render();
            this._pitchCurve.setUserData({
                frequencies: result.pitch_curve.frequencies || [],
                times: result.pitch_curve.times || [],
                duration: (result.basic_info?.duration_seconds) || 0
            });
        }

        // 4. AnimationController 驱动的序列
        const dimBars = {};
        const dimValues = {};
        ['Pitch', 'Rhythm', 'Breath', 'Technique', 'Artistry'].forEach(name => {
            dimBars[name.toLowerCase()] = this.el.querySelector('#dim' + name + 'Bar');
            dimValues[name.toLowerCase()] = this.el.querySelector('#dim' + name + 'Value');
        });

        const adviceList = this.el.querySelector('#adviceList');

        if (this.ac) {
            const tl = this.ac.createTimeline();

            // 进度条依次展开 (stagger +0.15s 间隔)
            const dims = ['pitch', 'rhythm', 'breath', 'technique', 'artistry'];
            dims.forEach((dim, i) => {
                const bar = dimBars[dim];
                const val = dimValues[dim];
                const score = scores[dim] || 0;

                if (bar) {
                    tl.to(bar, {
                        scaleX: score / 100,
                        duration: 0.8,
                        ease: 'power2.out',
                        transformOrigin: 'left center'
                    }, i === 0 ? '+=0.2' : '-=0.65');
                }
                if (val) {
                    // 数字滚动
                    tl.fromTo(val,
                        { textContent: 0 },
                        {
                            textContent: Math.round(score),
                            duration: 0.8,
                            snap: { textContent: 1 },
                            overwrite: 'auto'
                        },
                        bar ? '-=0.8' : '-=0.65'
                    );
                }
            });

            // 建议列表 stagger
            if (adviceList) {
                const items = adviceList.querySelectorAll('li');
                if (items.length > 0) {
                    tl.fromTo(items,
                        { opacity: 0, y: 10 },
                        { opacity: 1, y: 0, stagger: 0.1, duration: 0.4, ease: 'power2.out' },
                        '+=0.2'
                    );
                }
            }
        } else {
            // 无动画回退: 直接设置最终状态
            if (dimBars) dimBars.forEach(bar => { bar.style.width = (bar.dataset.value || 0) + '%'; });
        }
    }

    async _exportReport(format) {
        if (!this._result) return;
        try {
            const api = new (await import('../services/api.js')).ApiClient();
            const filename = this._result.filename || 'report';
            const res = await api.exportReport(this._result, filename, format);
            if (res?.pdf_path || res?.image_path) {
                const link = document.createElement('a');
                link.href = res.pdf_path || res.image_path;
                link.download = (res.pdf_path || res.image_path).split('/').pop();
                link.click();
                showToast('报告已导出', 'success');
            }
        } catch (e) {
            showToast('导出失败: ' + e.message, 'error');
        }
    }

    _setupAudioControls() {
        const playBtn = this.el.querySelector('#audioPlayBtn');
        const progressFill = this.el.querySelector('#audioProgressFill');
        const timeDisplay = this.el.querySelector('#audioTime');
        if (!playBtn || !this._audioPlayer) return;

        let updateInterval;
        const formatTime = (s) => {
            const m = Math.floor(s / 60), sec = Math.floor(s % 60);
            return String(m).padStart(2, '0') + ':' + String(sec).padStart(2, '0');
        };

        playBtn.addEventListener('click', () => {
            if (this._audioPlayer.isPlaying) {
                this._audioPlayer.pause();
                playBtn.textContent = '▶ 播放';
            } else {
                this._audioPlayer.play();
                playBtn.textContent = '⏸ 暂停';
            }
        });

        this._audioPlayer.audioElement?.addEventListener('play', () => {
            playBtn.textContent = '⏸ 暂停';
        });
        this._audioPlayer.audioElement?.addEventListener('pause', () => {
            playBtn.textContent = '▶ 播放';
        });
        this._audioPlayer.audioElement?.addEventListener('ended', () => {
            playBtn.textContent = '▶ 播放';
        });
        this._audioPlayer.audioElement?.addEventListener('timeupdate', () => {
            const el = this._audioPlayer.audioElement;
            const pct = el.duration ? (el.currentTime / el.duration * 100) : 0;
            if (progressFill) progressFill.style.width = pct + '%';
            if (timeDisplay) timeDisplay.textContent = formatTime(el.currentTime) + ' / ' + formatTime(el.duration);
        });
    }

    destroy() {
        this._audioPlayer?.stop();
        this._audioPlayer?.cleanup();
        this._scoreRing?.destroy();
        this._radarChart?.destroy();
        this._pitchCurve?.destroy();
        super.destroy();
    }
}

export default ReportPage;
