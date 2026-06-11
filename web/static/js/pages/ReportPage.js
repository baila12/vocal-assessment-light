/**
 * ReportPage — 报告页 (评分展示 + 雷达图 + 特征图)
 *
 * 路由: #/report/:analysisId
 *
 * GSAP 动画序列:
 *   1. 总分环形 + 数字滚动
 *   2. 五维进度条 stagger
 *   3. 雷达图渐进
 *   4. 建议列表淡入
 *
 * @version 1.0
 */

import { BaseComponent } from '../components/BaseComponent.js';
import { ScoreRing } from '../components/ScoreRing.js';
import { ScoreCounter } from '../components/ScoreCounter.js';
import { RadarChart } from '../components/RadarChart.js';
import { PitchCurve } from '../components/PitchCurve.js';
import { showToast } from '../components/Toast.js';
import { animateReportEntrance } from '../effects/scores.js';

export class ReportPage extends BaseComponent {
    /** @type {ScoreRing} */
    #scoreRing;

    /** @type {RadarChart} */
    #radarChart;

    /** @type {PitchCurve} */
    #pitchCurve;

    /** @type {Object|null} */
    #result = null;

    async mount(params) {
        // 从 store 获取最新分析结果 (HomePage 完成分析后存入)
        if (this.store) {
            this.#result = this.store.getState('analysis').result;
        }

        this.render();
        this.bindEvents();

        if (!this.#result) {
            this.el.querySelector('#reportContent').style.display = 'none';
            this.el.querySelector('#reportEmpty').style.display = 'block';
            return;
        }

        this.#populateData(this.#result);
        this.#animateEntrance(this.#result);
    }

    render() {
        this.el = this.createElement('div', { id: 'page-report', className: 'page page-container' });

        this.el.innerHTML = `
        <div id="reportContent">
            <!-- 总分区域 -->
            <div class="score-header" id="scoreHeader" style="text-align:center; margin-bottom:32px;">
                <div id="scoreRingContainer"></div>
                <div class="score-level" id="scoreLevel" style="margin-top:8px;font-size:18px;font-weight:600;color:var(--text-secondary);">--</div>
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

            <!-- 特征可视化 -->
            <div class="card" id="vizCard" style="margin-bottom:24px; display:none;">
                <div class="card-header"><span class="card-title">🔬 特征可视化</span></div>
                <div class="card-body" id="featureVisualization"></div>
            </div>

            <!-- 逐句评分 -->
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

        <!-- 空状态 -->
        <div id="reportEmpty" style="display:none; text-align:center; padding:60px 20px;">
            <div style="font-size:48px; margin-bottom:16px;">📭</div>
            <h2 style="color:var(--text-primary); margin-bottom:8px;">未找到分析结果</h2>
            <p style="color:var(--text-muted); margin-bottom:24px;">该分析记录不存在或已过期</p>
            <button class="btn btn-primary" id="goHomeBtn">返回首页</button>
        </div>`;

        this.container.appendChild(this.el);
    }

    bindEvents() {
        this.el.querySelector('#goHomeBtn')?.addEventListener('click', () => {
            if (this.router) this.router.navigate('#/');
        });

        this.el.querySelector('#exportPdfBtn')?.addEventListener('click', () => this.#exportReport('pdf'));
        this.el.querySelector('#exportImgBtn')?.addEventListener('click', () => this.#exportReport('image'));
        this.el.querySelector('#reAnalyzeBtn')?.addEventListener('click', () => {
            if (this.router) this.router.navigate('#/');
        });
    }

    // ========================================================================
    // 数据填充
    // ========================================================================

    #populateData(result) {
        const scores = result.scores || {};

        // 五维进度条
        const barsContainer = this.el.querySelector('#dimensionBars');
        if (barsContainer) {
            const dims = [
                { key: 'pitch', label: '音准', color: 'var(--dim-pitch)', weight: '35%' },
                { key: 'rhythm', label: '节奏', color: 'var(--dim-rhythm)', weight: '25%' },
                { key: 'breath', label: '气息', color: 'var(--dim-breath)', weight: '10%' },
                { key: 'technique', label: '发声技术', color: 'var(--dim-technique)', weight: '25%' },
                { key: 'artistry', label: '艺术表现', color: 'var(--dim-artistry)', weight: '15%' }
            ];

            barsContainer.innerHTML = dims.map(d => {
                const score = scores[d.key] || 0;
                return `
                <div class="dimension-row" style="display:flex;align-items:center;gap:12px;margin-bottom:14px;">
                    <span style="width:80px;font-size:13px;color:var(--text-secondary);text-align:right;">${d.label}</span>
                    <div style="flex:1;height:8px;background:var(--bg-elevated);border-radius:var(--radius-full);overflow:hidden;">
                        <div id="dim${d.key.charAt(0).toUpperCase() + d.key.slice(1)}Bar"
                             style="height:100%;width:0%;background:${d.color};border-radius:var(--radius-full);transform-origin:left center;"></div>
                    </div>
                    <span id="dim${d.key.charAt(0).toUpperCase() + d.key.slice(1)}Value"
                          style="width:36px;font-size:13px;font-weight:600;color:${d.color};text-align:right;">0</span>
                    <span style="width:30px;font-size:11px;color:var(--text-muted);">${d.weight}</span>
                </div>`;
            }).join('');
        }

        // 改进建议
        const adviceList = this.el.querySelector('#adviceList');
        if (adviceList && result.advice?.length) {
            adviceList.innerHTML = result.advice.map(a => `<li style="padding:10px 0;border-bottom:1px solid var(--border);color:var(--text-secondary);font-size:14px;">💡 ${a}</li>`).join('');
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
    // GSAP 动画
    // ========================================================================

    #animateEntrance(result) {
        const scores = result.scores || {};

        // 1. 环形评分
        const ringContainer = this.el.querySelector('#scoreRingContainer');
        this.#scoreRing = new ScoreRing(ringContainer, { size: 140 });
        this.#scoreRing.render();
        this.#scoreRing.animate(result.total_score || 0);

        // 2. 雷达图
        const radarContainer = this.el.querySelector('#radarChartContainer');
        this.#radarChart = new RadarChart(radarContainer);
        this.#radarChart.render();
        this.#radarChart.setData(scores);
        this.#radarChart.animate();

        // 3. GSAP 序列 (进度条 + 建议列表)
        const dimBars = {};
        const dimValues = {};
        ['Pitch', 'Rhythm', 'Breath', 'Technique', 'Artistry'].forEach(name => {
            dimBars[name.toLowerCase()] = this.el.querySelector(`#dim${name}Bar`);
            dimValues[name.toLowerCase()] = this.el.querySelector(`#dim${name}Value`);
        });

        animateReportEntrance(result, {
            totalScore: null, // 已由 ScoreRing 处理
            scoreLevel: this.el.querySelector('#scoreLevel'),
            dimBars,
            dimValues,
            adviceList: this.el.querySelector('#adviceList'),
            drawRadar: () => this.#radarChart?.animate()
        });
    }

    async #exportReport(format) {
        if (!this.#result) return;
        try {
            const api = new (await import('../services/api.js')).ApiClient();
            const filename = this.#result.filename || 'report';
            const res = await api.exportReport(this.#result, filename, format);
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

    destroy() {
        this.#scoreRing?.destroy();
        this.#radarChart?.destroy();
        this.#pitchCurve?.destroy();
        super.destroy();
    }
}

export default ReportPage;
