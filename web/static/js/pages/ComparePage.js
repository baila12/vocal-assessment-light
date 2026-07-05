/**
 * ComparePage — 对比分析页 (双模式: 标准对比 / 历史对比)
 *
 * 路由: #/compare
 *
 * 标准对比模式: 左栏从曲库选标准音频, 右栏上传/历史选用户音频
 * 历史对比模式: 左右栏都从历史记录选
 * 评分参数面板: 风格选择 + 权重展示
 *
 * @version 2.0
 */

import { BaseComponent } from '../components/BaseComponent.js';
import { showToast } from '../components/Toast.js';
import { StandardAudioSelector } from '../components/StandardAudioSelector.js';
import { ApiClient } from '../services/api.js';

export class ComparePage extends BaseComponent {
    static animationPreset = 'page-enter';

    #mode = 'standard'; // 'standard' | 'history'
    #api;
    #standardSong = null;
    #userAudio = null;
    #userHistoryRecord = null;
    #leftHistoryRecord = null;
    #rightHistoryRecord = null;
    #result = null;
    #isAnalyzing = false;
    #selector = null;

    constructor(container, options = {}) {
        super(container, options);
        this.#api = options.api || new ApiClient();
    }

    async mount(params) {
        this.render();
        this.bindEvents();
    }

    render() {
        this.el = this.createElement('div', { id: 'page-compare', className: 'page page-container' });

        this.el.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;flex-wrap:wrap;gap:8px;">
            <h2 style="font-size:18px;font-weight:600;">🔁 对比分析</h2>
            <div class="compare-mode-tabs" style="display:flex;gap:4px;background:var(--bg-elevated);border-radius:var(--radius-md);padding:3px;">
                <button class="compare-mode-tab active" data-mode="standard" style="padding:6px 14px;border:none;border-radius:var(--radius-sm);background:var(--primary);color:#fff;font-size:12px;font-weight:600;cursor:pointer;transition:all 0.2s;">标准对比</button>
                <button class="compare-mode-tab" data-mode="history" style="padding:6px 14px;border:none;border-radius:var(--radius-sm);background:transparent;color:var(--text-secondary);font-size:12px;cursor:pointer;transition:all 0.2s;">历史对比</button>
            </div>
        </div>

        <!-- 双栏选择区域 -->
        <div class="compare-grid" style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px;">
            <!-- 左栏 -->
            <div class="card" id="leftCard">
                <div class="card-header">
                    <span class="card-title" id="leftCardTitle">🎵 标准音频</span>
                </div>
                <div class="card-body">
                    <div id="leftSelect" style="cursor:pointer;padding:40px 20px;text-align:center;border:2px dashed var(--border);border-radius:var(--radius-lg);color:var(--text-muted);transition:all 0.2s;">
                        <div style="font-size:32px;margin-bottom:8px;" id="leftIcon">📂</div>
                        <p id="leftGuideText">选择标准音频 (从曲库)</p>
                        <p style="font-size:12px;" id="leftGuideSub">点击浏览曲库</p>
                    </div>
                    <div id="leftResult" style="display:none;">
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                            <div id="leftSongInfo" style="font-weight:600;font-size:14px;color:var(--text-primary);">--</div>
                            <button id="leftChangeBtn" style="border:none;background:var(--bg-elevated);color:var(--text-muted);padding:4px 10px;border-radius:var(--radius-sm);font-size:11px;cursor:pointer;">更换</button>
                        </div>
                        <div id="leftMeta" style="font-size:12px;color:var(--text-muted);"></div>
                    </div>
                </div>
            </div>

            <!-- 右栏 -->
            <div class="card" id="rightCard">
                <div class="card-header">
                    <span class="card-title" id="rightCardTitle">🎤 用户音频</span>
                </div>
                <div class="card-body">
                    <div id="rightSelect" style="cursor:pointer;padding:40px 20px;text-align:center;border:2px dashed var(--border);border-radius:var(--radius-lg);color:var(--text-muted);transition:all 0.2s;">
                        <div style="font-size:32px;margin-bottom:8px;" id="rightIcon">📂</div>
                        <p id="rightGuideText">选择用户音频</p>
                        <p style="font-size:12px;" id="rightGuideSub">上传文件或从历史选择</p>
                    </div>
                    <div id="rightResult" style="display:none;">
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                            <div id="rightAudioInfo" style="font-weight:600;font-size:14px;color:var(--text-primary);">--</div>
                            <button id="rightChangeBtn" style="border:none;background:var(--bg-elevated);color:var(--text-muted);padding:4px 10px;border-radius:var(--radius-sm);font-size:11px;cursor:pointer;">更换</button>
                        </div>
                        <div id="rightMeta" style="font-size:12px;color:var(--text-muted);"></div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 评分参数面板 -->
        <div class="card" id="paramsCard" style="margin-bottom:20px;">
            <div class="card-header" style="cursor:pointer;" id="paramsHeader">
                <span class="card-title">⚙️ 评分参数</span>
                <span id="paramsToggle" style="font-size:12px;color:var(--text-muted);">展开 ▾</span>
            </div>
            <div class="card-body" id="paramsContent" style="display:none;">
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
                    <div>
                        <label style="display:block;font-size:13px;font-weight:500;color:var(--text-secondary);margin-bottom:4px;">风格</label>
                        <select id="styleSelect" style="width:100%;padding:8px 12px;border:1px solid var(--border);border-radius:var(--radius-md);background:var(--bg-primary);font-size:13px;">
                            <option value="pop">流行 (Pop)</option>
                            <option value="jazz">爵士 (Jazz)</option>
                            <option value="classical">古典 (Classical)</option>
                            <option value="folk">民谣 (Folk)</option>
                        </select>
                    </div>
                    <div>
                        <label style="display:block;font-size:13px;font-weight:500;color:var(--text-secondary);margin-bottom:4px;">五维权重 (风格预设)</label>
                        <div id="weightsDisplay" style="display:grid;grid-template-columns:1fr 1fr;gap:4px;font-size:12px;color:var(--text-muted);padding:4px 0;">
                            <span>音准 35%</span>
                            <span>节奏 25%</span>
                            <span>气息 10%</span>
                            <span>技术 20%</span>
                            <span>艺术 10%</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 开始对比按钮 -->
        <button id="startCompareBtn" class="btn btn-primary" disabled
                style="width:100%;padding:14px 24px;border:none;border-radius:var(--radius-md);background:var(--primary);color:#fff;font-size:15px;font-weight:600;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:8px;opacity:0.5;">
            🚀 开始对比
        </button>

        <!-- 对比结果 -->
        <div id="compareResults" style="display:none;margin-top:24px;">
            <!-- 总分 -->
            <div class="card" style="margin-bottom:20px;text-align:center;">
                <div class="card-body" style="padding:32px;">
                    <div style="font-size:13px;color:var(--text-muted);margin-bottom:8px;">DTW 对比总分</div>
                    <div class="dtw-total-score" style="font-size:56px;font-weight:700;color:var(--primary);line-height:1;" id="resultScore">--</div>
                    <div style="font-size:14px;color:var(--text-secondary);margin-top:8px;" id="resultLevel">--</div>
                </div>
            </div>

            <!-- 双曲线叠加视图 -->
            <div class="card" style="margin-bottom:20px;">
                <div class="card-header">
                    <span class="card-title">📈 音准叠加</span>
                    <button id="pitchOverlayTab" style="border:none;background:var(--primary-ghost);color:var(--primary);padding:4px 12px;border-radius:var(--radius-sm);font-size:11px;cursor:pointer;">展开</button>
                </div>
                <div class="card-body" style="height:200px;background:var(--bg-elevated);border-radius:var(--radius-md);display:flex;align-items:center;justify-content:center;color:var(--text-muted);font-size:13px;">
                    <canvas id="pitchOverlayCanvas" style="width:100%;height:100%;display:none;"></canvas>
                    <span id="pitchOverlayPlaceholder">🎵 选择音频并分析后显示叠加曲线</span>
                </div>
            </div>

            <!-- 差距分析表格 -->
            <div class="card" style="margin-bottom:20px;">
                <div class="card-header"><span class="card-title">📊 差距分析</span></div>
                <div class="card-body" id="gapContent"></div>
            </div>

            <!-- 改进建议 -->
            <div class="card" style="margin-bottom:20px;">
                <div class="card-header"><span class="card-title">💡 改进建议</span></div>
                <div class="card-body">
                    <ul id="adviceList" style="list-style:none;padding:0;margin:0;"></ul>
                </div>
            </div>
        </div>
        `;

        this.container.appendChild(this.el);
    }

    bindEvents() {
        // 模式切换
        this.el.querySelectorAll('.compare-mode-tab').forEach(tab => {
            tab.addEventListener('click', () => this.#switchMode(tab.dataset.mode));
        });

        // 左侧选择
        this.el.querySelector('#leftSelect')?.addEventListener('click', () => this.#selectLeft());
        this.el.querySelector('#leftChangeBtn')?.addEventListener('click', () => this.#selectLeft());

        // 右侧选择
        this.el.querySelector('#rightSelect')?.addEventListener('click', () => this.#selectRight());
        this.el.querySelector('#rightChangeBtn')?.addEventListener('click', () => this.#selectRight());

        // 参数面板展开
        this.el.querySelector('#paramsHeader')?.addEventListener('click', () => {
            const content = this.el.querySelector('#paramsContent');
            const toggle = this.el.querySelector('#paramsToggle');
            const isOpen = content.style.display !== 'none';
            content.style.display = isOpen ? 'none' : '';
            toggle.textContent = isOpen ? '展开 ▾' : '收起 ▴';
        });

        // 风格切换 — 更新权重
        this.el.querySelector('#styleSelect')?.addEventListener('change', (e) => {
            this.#updateWeights(e.target.value);
        });

        // 开始对比
        this.el.querySelector('#startCompareBtn')?.addEventListener('click', () => this.#startCompare());
    }

    // ========================================================================
    // 模式切换
    // ========================================================================

    #switchMode(mode) {
        if (this.#isAnalyzing) {
            showToast('分析进行中，请等待完成', 'warning');
            return;
        }

        this.#mode = mode;
        this.#clearSelections();

        // 切换 tab 高亮
        this.el.querySelectorAll('.compare-mode-tab').forEach(t => {
            const isActive = t.dataset.mode === mode;
            t.className = 'compare-mode-tab' + (isActive ? ' active' : '');
            t.style.background = isActive ? 'var(--primary)' : 'transparent';
            t.style.color = isActive ? '#fff' : 'var(--text-secondary)';
        });

        // 更新左侧标题和引导
        const leftTitle = this.el.querySelector('#leftCardTitle');
        const leftGuide = this.el.querySelector('#leftGuideText');
        const leftGuideSub = this.el.querySelector('#leftGuideSub');
        const leftIcon = this.el.querySelector('#leftIcon');

        if (mode === 'standard') {
            leftTitle.textContent = '🎵 标准音频';
            leftGuide.textContent = '从曲库选择标准歌曲';
            leftGuideSub.textContent = '点击浏览曲库';
            leftIcon.textContent = '🎵';
        } else {
            leftTitle.textContent = '📋 历史记录 (左侧)';
            leftGuide.textContent = '选择历史分析记录';
            leftGuideSub.textContent = '点击从历史记录选择';
            leftIcon.textContent = '📋';
        }
    }

    // ========================================================================
    // 左侧选择
    // ========================================================================

    #selectLeft() {
        if (this.#isAnalyzing) {
            showToast('分析进行中', 'warning');
            return;
        }

        if (this.#mode === 'standard') {
            this.#openSongSelector('left');
        } else {
            this.#openHistorySelector('left');
        }
    }

    #openSongSelector(target) {
        // StandardAudioSelector modal 模式自带 overlay, 直接挂载到 body
        this.#selector = new StandardAudioSelector(document.body, {
            mode: 'modal',
            onSelect: (song) => {
                this.#onSongSelected(target, song);
            }
        });

        // 加载歌曲数据
        const songs = window.__mockSongs || [];
        this.#selector.setSongs(songs);
        this.#selector.render();
    }

    #onSongSelected(target, song) {
        this.#standardSong = song;

        // 更新左侧 UI
        const select = this.el.querySelector('#leftSelect');
        const result = this.el.querySelector('#leftResult');
        const info = this.el.querySelector('#leftSongInfo');
        const meta = this.el.querySelector('#leftMeta');

        if (select) select.style.display = 'none';
        if (result) result.style.display = '';
        if (info) info.textContent = song.title + ' - ' + (song.artist || '');
        if (meta) {
            const parts = [];
            if (song.difficulty) parts.push(song.difficulty);
            if (song.bpm) parts.push('BPM: ' + song.bpm);
            if (song.key) parts.push(song.key);
            if (song.style) parts.push(song.style);
            meta.textContent = parts.join(' · ');
        }

        this.#updateCompareBtn();
    }

    #openHistorySelector(target) {
        const label = target === 'left' ? '左侧' : '右侧';
        // 从 store 或 API 获取历史记录
        const history = this.store?.getState('history') || [];

        if (!history || history.length === 0) {
            showToast('暂无历史记录', 'warning');
            return;
        }

        // 简单列表弹窗
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.4);z-index:var(--z-modal);display:flex;align-items:center;justify-content:center;padding:24px;';

        const card = document.createElement('div');
        card.style.cssText = 'background:var(--bg-card);border-radius:var(--radius-lg);padding:24px;max-width:420px;width:100%;max-height:70vh;overflow-y:auto;box-shadow:var(--shadow-xl);';

        card.innerHTML = '<h3 style="font-size:16px;font-weight:600;margin-bottom:16px;">选择历史记录 (' + label + ')</h3>'
            + history.map(r => '<div class="history-card" data-id="' + r.id + '" style="display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid var(--border);cursor:pointer;">'
                + '<div><div style="font-weight:500;font-size:14px;">' + (r.filename || '未知') + '</div>'
                + '<div style="font-size:12px;color:var(--text-muted);">' + (r.timestamp ? new Date(r.timestamp).toLocaleDateString() : '') + '</div></div>'
                + '<span style="font-size:18px;font-weight:700;color:var(--primary);">' + (r.total_score?.toFixed(1) || '--') + '</span></div>'
            ).join('')
            + '<button id="closeHistorySelector" style="width:100%;margin-top:16px;padding:8px;border:1px solid var(--border);border-radius:var(--radius-md);background:transparent;color:var(--text-secondary);cursor:pointer;font-size:13px;">取消</button>';

        overlay.appendChild(card);
        document.body.appendChild(overlay);

        // 选中记录
        card.querySelectorAll('.history-card').forEach(item => {
            item.addEventListener('click', () => {
                const id = parseInt(item.dataset.id);
                const record = history.find(r => r.id === id);
                if (record) {
                    this.#onHistorySelected(target, record);
                }
                overlay.remove();
            });
        });

        overlay.querySelector('#closeHistorySelector')?.addEventListener('click', () => overlay.remove());
        overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
    }

    #onHistorySelected(target, record) {
        if (target === 'left') {
            this.#leftHistoryRecord = record;
        } else {
            this.#rightHistoryRecord = record;
        }

        // 更新对应侧 UI
        const side = target === 'left' ? 'left' : 'right';
        const select = this.el.querySelector('#' + side + 'Select');
        const result = this.el.querySelector('#' + side + 'Result');
        const info = this.el.querySelector('#' + side + (target === 'left' ? 'SongInfo' : 'AudioInfo'));
        const meta = this.el.querySelector('#' + side + 'Meta');

        if (select) select.style.display = 'none';
        if (result) result.style.display = '';
        if (info) info.textContent = record.filename || '未知文件';
        if (meta) meta.textContent = (record.total_score ? '总分: ' + record.total_score.toFixed(1) : '') + (record.timestamp ? ' · ' + new Date(record.timestamp).toLocaleDateString() : '');

        this.#updateCompareBtn();
    }

    // ========================================================================
    // 右侧选择
    // ========================================================================

    #selectRight() {
        if (this.#isAnalyzing) {
            showToast('分析进行中', 'warning');
            return;
        }

        // 右侧可以选择上传或从历史记录
        const actions = ['上传新音频', '从历史记录选择'];
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.4);z-index:var(--z-modal);display:flex;align-items:center;justify-content:center;padding:24px;';

        const card = document.createElement('div');
        card.style.cssText = 'background:var(--bg-card);border-radius:var(--radius-lg);padding:24px;max-width:360px;width:100%;box-shadow:var(--shadow-xl);text-align:center;';

        card.innerHTML = '<h3 style="font-size:16px;font-weight:600;margin-bottom:16px;">选择用户音频</h3>'
            + '<div style="display:flex;flex-direction:column;gap:12px;">'
            + '<button id="rightUploadBtn" class="btn btn-primary" style="padding:14px;border:none;border-radius:var(--radius-md);background:var(--primary);color:#fff;font-size:14px;cursor:pointer;font-weight:600;">📁 上传新音频</button>'
            + '<button id="rightHistoryBtn" class="btn btn-secondary" style="padding:14px;border:1px solid var(--border);border-radius:var(--radius-md);background:transparent;color:var(--text-primary);font-size:14px;cursor:pointer;">📋 从历史记录选择</button>'
            + '<button id="closeRightSelector" style="padding:8px;border:none;background:none;color:var(--text-muted);font-size:13px;cursor:pointer;">取消</button>'
            + '</div>';

        overlay.appendChild(card);
        document.body.appendChild(overlay);

        overlay.querySelector('#rightUploadBtn')?.addEventListener('click', () => {
            overlay.remove();
            this.#uploadRightAudio();
        });
        overlay.querySelector('#rightHistoryBtn')?.addEventListener('click', () => {
            overlay.remove();
            this.#openHistorySelector('right');
        });
        overlay.querySelector('#closeRightSelector')?.addEventListener('click', () => overlay.remove());
        overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
    }

    #uploadRightAudio() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = 'audio/*,.mp3,.wav,.flac,.ogg,.m4a';
        input.onchange = (e) => {
            const file = e.target.files?.[0];
            if (!file) return;

            this.#userAudio = file;

            const select = this.el.querySelector('#rightSelect');
            const result = this.el.querySelector('#rightResult');
            const info = this.el.querySelector('#rightAudioInfo');
            const meta = this.el.querySelector('#rightMeta');

            if (select) select.style.display = 'none';
            if (result) result.style.display = '';
            if (info) info.textContent = file.name;
            if (meta) meta.textContent = (file.size / 1024 / 1024).toFixed(1) + ' MB · 用户上传';

            this.#updateCompareBtn();
            showToast('文件已加载: ' + file.name, 'success');
        };
        input.click();
    }

    // ========================================================================
    // 对比按钮状态
    // ========================================================================

    #updateCompareBtn() {
        const btn = this.el.querySelector('#startCompareBtn');
        if (!btn) return;

        let ready = false;
        let reason = '';

        if (this.#mode === 'standard') {
            const hasLeft = this.#standardSong !== null;
            const hasRight = this.#userAudio !== null || this.#rightHistoryRecord !== null;

            if (!hasLeft) reason = '请选择标准音频';
            else if (!hasRight) reason = '请选择用户音频';
            else ready = true;
        } else {
            const hasLeft = this.#leftHistoryRecord !== null;
            const hasRight = this.#rightHistoryRecord !== null;

            if (!hasLeft) reason = '请选择左侧历史记录';
            else if (!hasRight) reason = '请选择右侧历史记录';
            else if (this.#leftHistoryRecord?.id === this.#rightHistoryRecord?.id) {
                reason = '请选择两条不同的记录';
                ready = false;
            } else ready = true;
        }

        btn.disabled = !ready;
        btn.style.opacity = ready ? '1' : '0.5';
        btn.innerHTML = ready ? '🚀 开始对比' : '⏳ ' + reason;
    }

    // ========================================================================
    // 开始对比
    // ========================================================================

    async #startCompare() {
        if (this.#isAnalyzing) return;
        this.#isAnalyzing = true;

        const btn = this.el.querySelector('#startCompareBtn');
        btn.disabled = true;
        btn.innerHTML = '⏳ 分析中...';

        try {
            // 模拟对比分析
            await new Promise(resolve => setTimeout(resolve, 1500));

            // 模拟结果
            const result = {
                total_score: 78.5,
                level: '中等',
                scores: { pitch: 75, rhythm: 82, breath: 70, technique: 76, artistry: 80 },
                advice: ['注意高音区的音准稳定性', '副歌部分节奏略快，建议跟节拍器练习', '气息支撑需要加强，特别是长音部分']
            };

            this.#result = result;
            this.#showResults(result);

        } catch (e) {
            showToast('对比分析失败: ' + e.message, 'error');
        } finally {
            this.#isAnalyzing = false;
            this.#updateCompareBtn();
        }
    }

    #showResults(result) {
        const results = this.el.querySelector('#compareResults');
        const score = this.el.querySelector('#resultScore');
        const level = this.el.querySelector('#resultLevel');
        const gapContent = this.el.querySelector('#gapContent');
        const adviceList = this.el.querySelector('#adviceList');

        if (results) results.style.display = '';
        if (score) score.textContent = result.total_score?.toFixed(1) || '--';
        if (level) level.textContent = result.level || '';

        // 差距分析表格
        if (gapContent) {
            const dims = [
                { key: 'pitch', label: '音准' },
                { key: 'rhythm', label: '节奏' },
                { key: 'breath', label: '气息' },
                { key: 'technique', label: '发声技术' },
                { key: 'artistry', label: '艺术表现' }
            ];

            gapContent.innerHTML = '<table style="width:100%;border-collapse:collapse;">'
                + '<tr style="border-bottom:1px solid var(--border);">'
                + '<th style="text-align:left;padding:8px;font-size:13px;">维度</th>'
                + '<th style="text-align:right;padding:8px;font-size:13px;">得分</th>'
                + '<th style="text-align:right;padding:8px;font-size:13px;">评级</th></tr>'
                + dims.map(d => {
                    const s = result.scores?.[d.key] || 0;
                    const rating = s >= 90 ? '优秀' : s >= 80 ? '良好' : s >= 70 ? '中等' : s >= 60 ? '及格' : '需改进';
                    const color = s >= 90 ? 'var(--success)' : s >= 80 ? 'var(--accent-blue)' : s >= 70 ? 'var(--warning)' : 'var(--danger)';
                    return '<tr style="border-bottom:1px solid var(--border);">'
                        + '<td style="padding:8px;color:var(--text-secondary);font-size:13px;">' + d.label + '</td>'
                        + '<td style="text-align:right;padding:8px;font-weight:600;color:' + color + ';">' + Math.round(s) + '</td>'
                        + '<td style="text-align:right;padding:8px;font-size:12px;color:var(--text-muted);">' + rating + '</td></tr>';
                }).join('')
                + '</table>';
        }

        // 改进建议
        if (adviceList && result.advice?.length) {
            adviceList.innerHTML = result.advice.map(a =>
                '<li style="padding:10px 0;border-bottom:1px solid var(--border);color:var(--text-secondary);font-size:14px;">💡 ' + a + '</li>'
            ).join('');
        }

        // 动画
        if (this.ac) {
            this.ac.enter(results, { preset: 'slideUp' });
        }
    }

    // ========================================================================
    // 权重预设
    // ========================================================================

    #updateWeights(style) {
        const presets = {
            pop: { pitch: 35, rhythm: 25, breath: 10, technique: 20, artistry: 10 },
            jazz: { pitch: 30, rhythm: 20, breath: 15, technique: 20, artistry: 15 },
            classical: { pitch: 30, rhythm: 15, breath: 20, technique: 25, artistry: 10 },
            folk: { pitch: 30, rhythm: 20, breath: 15, technique: 20, artistry: 15 }
        };

        const w = presets[style] || presets.pop;
        const display = this.el.querySelector('#weightsDisplay');
        if (display) {
            display.innerHTML = '<span>音准 ' + w.pitch + '%</span>'
                + '<span>节奏 ' + w.rhythm + '%</span>'
                + '<span>气息 ' + w.breath + '%</span>'
                + '<span>技术 ' + w.technique + '%</span>'
                + '<span>艺术 ' + w.artistry + '%</span>';
        }
    }

    // ========================================================================
    // Utils
    // ========================================================================

    #clearSelections() {
        this.#standardSong = null;
        this.#userAudio = null;
        this.#leftHistoryRecord = null;
        this.#rightHistoryRecord = null;
        this.#result = null;

        this.el.querySelector('#leftSelect').style.display = '';
        this.el.querySelector('#leftResult').style.display = 'none';
        this.el.querySelector('#rightSelect').style.display = '';
        this.el.querySelector('#rightResult').style.display = 'none';
        this.el.querySelector('#compareResults').style.display = 'none';
    }

    destroy() {
        this.#selector?.destroy();
        super.destroy();
    }
}

export default ComparePage;
