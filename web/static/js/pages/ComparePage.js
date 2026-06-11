/**
 * ComparePage — 对比分析页
 *
 * 路由: #/compare
 *
 * @version 1.0
 */

import { BaseComponent } from '../components/BaseComponent.js';
import { RadarChart } from '../components/RadarChart.js';
import { showToast } from '../components/Toast.js';
import { ApiClient } from '../services/api.js';

export class ComparePage extends BaseComponent {
    /** @type {ApiClient} */
    #api;

    /** @type {RadarChart} */
    #radarChart;

    /** @type {File|null} */
    #standardFile = null;

    /** @type {File|null} */
    #userFile = null;

    constructor(container, options = {}) {
        super(container, options);
        this.#api = options.api || new ApiClient();
    }

    async mount(params) {
        this.render();
        this.bindEvents();
    }

    render() {
        this.el = this.createElement('div', { id: 'page-compare', className: 'page page-container-wide' });

        this.el.innerHTML = `
        <div class="compare-header" style="text-align:center;margin-bottom:32px;">
            <h2 style="font-size:22px;font-weight:700;">⚖️ 对比分析</h2>
            <p style="font-size:15px;color:var(--text-muted);margin-top:8px;">上传标准音频作为参考，录制或上传您的演唱，实时查看与标准的差距</p>
        </div>

        <div class="dual-column" style="margin-bottom:24px;">
            <!-- 标准音频 -->
            <div class="card">
                <div class="card-header"><span class="card-title">🎯 标准音频</span><span class="track-badge" style="padding:2px 8px;background:var(--primary-light);color:var(--primary);border-radius:var(--radius-full);font-size:11px;">参考</span></div>
                <div class="card-body">
                    <input type="file" id="standardFileInput" accept=".wav,.mp3,.flac,.ogg,.m4a" style="display:none;">
                    <div id="standardPlaceholder" style="text-align:center;padding:40px 20px;border:2px dashed var(--border);border-radius:var(--radius-lg);cursor:pointer;">
                        <div style="font-size:32px;margin-bottom:8px;">🎵</div>
                        <div style="font-size:14px;color:var(--text-secondary);">点击选择标准音频</div>
                        <div style="font-size:12px;color:var(--text-muted);">MP3 / WAV / FLAC</div>
                    </div>
                    <div id="standardInfo" style="display:none;">
                        <div style="font-size:14px;font-weight:600;margin-bottom:8px;" id="standardName"></div>
                        <div style="font-size:12px;color:var(--text-muted);" id="standardDuration"></div>
                    </div>
                </div>
            </div>

            <!-- 用户音频 -->
            <div class="card">
                <div class="card-header"><span class="card-title">🎤 我的演唱</span><span class="track-badge" style="padding:2px 8px;background:var(--warning-light);color:var(--warning);border-radius:var(--radius-full);font-size:11px;">待评估</span></div>
                <div class="card-body">
                    <input type="file" id="userFileInput" accept=".wav,.mp3,.flac,.ogg,.m4a" style="display:none;">
                    <div id="userPlaceholder" style="text-align:center;padding:40px 20px;border:2px dashed var(--border);border-radius:var(--radius-lg);cursor:pointer;">
                        <div style="font-size:32px;margin-bottom:8px;">🎙️</div>
                        <div style="font-size:14px;color:var(--text-secondary);">点击上传或开始录音</div>
                        <div style="font-size:12px;color:var(--text-muted);">支持录音或上传音频文件</div>
                    </div>
                    <div id="userInfo" style="display:none;">
                        <div style="font-size:14px;font-weight:600;margin-bottom:8px;" id="userName"></div>
                        <div style="font-size:12px;color:var(--text-muted);" id="userDuration"></div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 对比按钮 -->
        <div style="text-align:center;margin-bottom:24px;">
            <button id="compareBtn" class="btn btn-primary btn-lg" disabled>🔍 开始对比分析</button>
        </div>

        <!-- 对比结果 -->
        <div id="compareResult" style="display:none;">
            <div class="card" style="margin-bottom:20px;">
                <div class="card-header"><span class="card-title">📊 能力雷达对比</span></div>
                <div class="card-body" id="radarCompareContainer"></div>
            </div>

            <div class="card" style="margin-bottom:20px;">
                <div class="card-header"><span class="card-title">📋 维度对比</span></div>
                <div class="card-body">
                    <table class="compare-table" style="width:100%;border-collapse:collapse;">
                        <thead><tr style="border-bottom:1px solid var(--border);text-align:left;">
                            <th style="padding:8px;">维度</th><th style="padding:8px;">标准</th><th style="padding:8px;">我的</th><th style="padding:8px;">差距</th><th style="padding:8px;">评价</th>
                        </tr></thead>
                        <tbody id="compareTableBody"></tbody>
                    </table>
                </div>
            </div>
        </div>`;

        this.container.appendChild(this.el);
    }

    bindEvents() {
        // 标准音频选择
        this.el.querySelector('#standardPlaceholder')?.addEventListener('click', () => {
            this.el.querySelector('#standardFileInput').click();
        });
        this.el.querySelector('#standardFileInput')?.addEventListener('change', (e) => {
            this.#standardFile = e.target.files[0];
            if (this.#standardFile) {
                this.el.querySelector('#standardPlaceholder').style.display = 'none';
                this.el.querySelector('#standardInfo').style.display = 'block';
                this.el.querySelector('#standardName').textContent = this.#standardFile.name;
            }
            this.#checkCompareReady();
        });

        // 用户音频选择
        this.el.querySelector('#userPlaceholder')?.addEventListener('click', () => {
            this.el.querySelector('#userFileInput').click();
        });
        this.el.querySelector('#userFileInput')?.addEventListener('change', (e) => {
            this.#userFile = e.target.files[0];
            if (this.#userFile) {
                this.el.querySelector('#userPlaceholder').style.display = 'none';
                this.el.querySelector('#userInfo').style.display = 'block';
                this.el.querySelector('#userName').textContent = this.#userFile.name;
            }
            this.#checkCompareReady();
        });

        // 对比按钮
        this.el.querySelector('#compareBtn')?.addEventListener('click', () => this.#runComparison());
    }

    #checkCompareReady() {
        const btn = this.el.querySelector('#compareBtn');
        if (btn) btn.disabled = !(this.#standardFile && this.#userFile);
    }

    async #runComparison() {
        if (!this.#standardFile || !this.#userFile) return;

        const btn = this.el.querySelector('#compareBtn');
        btn.disabled = true;
        btn.textContent = '⏳ 分析中...';

        try {
            const result = await this.#api.compareAnalysis(this.#standardFile, this.#userFile);

            if (result?.success) {
                this.#displayResult(result);
            } else {
                throw new Error(result?.error || '对比失败');
            }
        } catch (e) {
            showToast('对比失败: ' + e.message, 'error');
        } finally {
            btn.disabled = false;
            btn.textContent = '🔍 开始对比分析';
        }
    }

    #displayResult(result) {
        this.el.querySelector('#compareResult').style.display = 'block';

        // 雷达图
        const scores = result.scores || {};
        const standardScores = result.standard_scores || {};

        const radarContainer = this.el.querySelector('#radarCompareContainer');
        this.#radarChart = new RadarChart(radarContainer);
        this.#radarChart.render();
        this.#radarChart.setData(scores, standardScores);

        // 对比表
        const dims = [
            { key: 'pitch', label: '音准' },
            { key: 'rhythm', label: '节奏' },
            { key: 'breath', label: '气息' },
            { key: 'technique', label: '发声技术' },
            { key: 'artistry', label: '艺术表现' }
        ];

        const tbody = this.el.querySelector('#compareTableBody');
        tbody.innerHTML = dims.map(d => {
            const std = Math.round(standardScores[d.key] || 0);
            const usr = Math.round(scores[d.key] || 0);
            const diff = usr - std;
            const status = diff >= 0 ? '✅ 达到' : diff >= -10 ? '⚠️ 接近' : '❌ 差距';
            return `<tr style="border-bottom:1px solid var(--border);">
                <td style="padding:10px 8px;font-weight:500;">${d.label}</td>
                <td style="padding:10px 8px;">${std}</td>
                <td style="padding:10px 8px;">${usr}</td>
                <td style="padding:10px 8px;color:${diff >= 0 ? 'var(--success)' : 'var(--danger)'};">${diff >= 0 ? '+' : ''}${diff}</td>
                <td style="padding:10px 8px;font-size:12px;">${status}</td>
            </tr>`;
        }).join('');

        // GSAP 入场
        if (typeof gsap !== 'undefined') {
            gsap.fromTo(this.el.querySelector('#compareResult'), { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.5, ease: 'power2.out' });
        }
    }

    destroy() {
        this.#radarChart?.destroy();
        super.destroy();
    }
}

export default ComparePage;
