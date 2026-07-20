/**
 * HomePage — 首页 (上传 + 录音 + 模式选择)
 *
 * 路由: #/
 * 入场动画: AnimationController page-enter-down (BaseComponent 自动)
 * 模式: 快速/专业模式传到后端
 *
 * @version 2.1
 */

import { BaseComponent } from '../components/BaseComponent.js';
import { showToast } from '../components/Toast.js';
import { ProgressBar } from '../components/ProgressBar.js';
import { ApiClient, ApiError } from '../services/api.js';
import { handleFileSelect as loadFileInfo } from '../modules/upload.js';

export class HomePage extends BaseComponent {
    static animationPreset = 'page-enter-down';

    _api;
    _progressBar;
    _selectedFile = null;
    _isAnalyzing = false;

    constructor(container, options = {}) {
        super(container, options);
        this._api = options.api || new ApiClient();
    }

    async mount(params) {
        this.render();
        this.bindEvents();
        this._checkMicrophone();
        this._restoreMode();
        this._animateEntrance();
    }

    render() {
        this.el = this.createElement('div', { id: 'page-home', className: 'page' });

        this.el.innerHTML = `
        <div class="home-layout page-container">
            <div class="main-content">
                <div class="welcome-section">
                    <div class="welcome-icon">🎵</div>
                    <div class="welcome-text">
                        <h1>专业声乐能力评估</h1>
                        <p>上传音频或录制演唱，获取五维专业评分分析</p>
                    </div>
                    <div class="welcome-features">
                        <span class="feature-tag">🔒 离线分析</span>
                        <span class="feature-tag">📊 五维评分</span>
                        <span class="feature-tag">💡 改进建议</span>
                    </div>
                </div>

                <div class="action-cards" id="actionCards">
                    <div class="action-card primary" id="uploadCard">
                        <div class="card-icon">
                            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                                <polyline points="17 8 12 3 7 8"/>
                                <line x1="12" y1="3" x2="12" y2="15"/>
                            </svg>
                        </div>
                        <div class="card-content">
                            <h3>导入音频</h3>
                            <p>上传已有录音文件进行分析</p>
                            <div class="card-formats">MP3 · WAV · FLAC · M4A · OGG</div>
                        </div>
                        <div class="card-arrow">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="9 18 15 12 9 6"/>
                            </svg>
                        </div>
                    </div>

                    <div class="action-card secondary" id="recordCard">
                        <div class="card-icon">
                            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
                                <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                                <line x1="12" y1="19" x2="12" y2="23"/>
                                <line x1="8" y1="23" x2="16" y2="23"/>
                            </svg>
                        </div>
                        <div class="card-content">
                            <h3>快速录音</h3>
                            <p>实时录制您的演唱</p>
                            <div class="card-status" id="micStatus">
                                <span class="status-dot"></span> 检测麦克风中...
                            </div>
                        </div>
                        <div class="card-arrow">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="9 18 15 12 9 6"/>
                            </svg>
                        </div>
                    </div>
                </div>

                <!-- 文件信息 -->
                <div id="fileInfo" style="display:none;padding:12px 16px;background:var(--bg-elevated);border-radius:var(--radius-md);margin-bottom:16px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                            <div id="fileName" style="font-weight:600;font-size:14px;color:var(--text-primary);"></div>
                            <div id="fileSize" style="font-size:12px;color:var(--text-muted);"></div>
                        </div>
                        <button id="clearFileBtn" style="border:none;background:none;color:var(--text-muted);cursor:pointer;font-size:16px;">✕</button>
                    </div>
                </div>

                <!-- 分析进度 -->
                <div id="progressArea" style="display:none;margin-bottom:16px;"></div>

                <!-- 模式选择 -->
                <div class="mode-selector">
                    <div class="mode-option active" data-mode="quick">
                        <input type="radio" name="evalMode" value="quick" checked hidden>
                        <div class="mode-icon">⚡</div>
                        <div class="mode-text">
                            <div class="mode-title">快速模式</div>
                            <div class="mode-desc" id="modeHint">快速评估，适合日常练习</div>
                        </div>
                    </div>
                    <div class="mode-option" data-mode="professional">
                        <input type="radio" name="evalMode" value="professional" hidden>
                        <div class="mode-icon">🎯</div>
                        <div class="mode-text">
                            <div class="mode-title">专业模式</div>
                            <div class="mode-desc" id="modeHintProf">全面诊断，适合专项提升</div>
                        </div>
                    </div>
                </div>

                <!-- 分析按钮 -->
                <div id="analysisActions" style="display:none;margin-top:16px;">
                    <button id="analyzeBtn" class="btn btn-primary" style="width:100%;padding:14px 24px;border:none;border-radius:var(--radius-md);background:var(--primary);color:#fff;font-size:15px;font-weight:600;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:8px;">
                        <span id="analyzeBtnIcon">🚀</span>
                        <span id="analyzeBtnText">快速分析</span>
                    </button>
                    <button id="stopAnalyzeBtn" style="display:none;width:100%;padding:14px 24px;border:1px solid var(--danger);border-radius:var(--radius-md);background:transparent;color:var(--danger);font-size:15px;font-weight:600;cursor:pointer;margin-top:8px;">
                        ⏹ 停止分析
                    </button>
                </div>

                <!-- 分析完成后结果预览 -->
                <div id="resultPreview" style="display:none;margin-top:16px;padding:16px;background:var(--bg-elevated);border-radius:var(--radius-md);text-align:center;">
                    <div style="font-size:32px;font-weight:700;color:var(--primary);" id="previewScore">--</div>
                    <div style="font-size:13px;color:var(--text-muted);margin-top:4px;" id="previewLevel">--</div>
                    <button id="viewReportBtn" class="btn btn-primary" style="margin-top:12px;padding:8px 20px;border:none;border-radius:var(--radius-md);background:var(--primary);color:#fff;font-size:13px;cursor:pointer;font-weight:600;">
                        查看完整报告
                    </button>
                </div>
            </div>

            <div class=sidebar>\n            <div class=sidebar-card>\n                <div class=sidebar-card-header><span>📋</span><span>使用步骤</span></div>\n                <div class=sidebar-card-body><ol class=steps-list>\n                    <li><span class=step-num>1</span>导入音频或直接录音</li>\n                    <li><span class=step-num>2</span>选择评估模式</li>\n                    <li><span class=step-num>3</span>点击分析按钮</li>\n                    <li><span class=step-num>4</span>查看五维评分报告</li>\n                </ol></div>\n            </div>\n            <div class=sidebar-card>\n                <div class=sidebar-card-header><span>📊</span><span>五维评分体系</span></div>\n                <div class=sidebar-card-body><div class=dimension-list>\n                    <div class=dimension-item><span class=dim-dot style=background:var(--dim-pitch)></span><span class=dim-name>音准</span><span class=dim-weight>音高准确度</span></div>\n                    <div class=dimension-item><span class=dim-dot style=background:var(--dim-rhythm)></span><span class=dim-name>节奏</span><span class=dim-weight>节奏稳定度</span></div>\n                    <div class=dimension-item><span class=dim-dot style=background:var(--dim-breath)></span><span class=dim-name>气息</span><span class=dim-weight>气息控制力</span></div>\n                    <div class=dimension-item><span class=dim-dot style=background:var(--dim-technique)></span><span class=dim-name>技巧</span><span class=dim-weight>发声技巧</span></div>\n                    <div class=dimension-item><span class=dim-dot style=background:var(--dim-artistry)></span><span class=dim-name>表现力</span><span class=dim-weight>情感表达</span></div>\n                </div></div>\n            </div>\n            <div class=sidebar-card>\n                <div class=sidebar-card-header><span>💡</span><span>快速技巧</span></div>\n                <div class=sidebar-card-body><div class=tips-list>\n                    <div class=tip-item><span class=tip-icon>🎧</span><span>使用高质量的录音设备</span></div>\n                    <div class=tip-item><span class=tip-icon>🔇</span><span>在安静环境中录音</span></div>\n                    <div class=tip-item><span class=tip-icon>🎤</span><span>保持30-50cm最佳录音距离</span></div>\n                </div></div>\n            </div>\n        </div>
        </div>\n        <input type="file" id="fileInput" accept="audio/*,.mp3,.wav,.flac,.m4a,.ogg" style="display:none">
        `;
        this.container.appendChild(this.el);
    }

    bindEvents() {
        this.el.querySelector('#uploadCard')?.addEventListener('click', () => this.#triggerUpload());
        this.el.querySelector('#recordCard')?.addEventListener('click', () => this._startRecording());
        this.el.querySelector('#fileInput')?.addEventListener('change', (e) => this.#onFileSelected(e));
        this.el.querySelector('#clearFileBtn')?.addEventListener('click', () => this.#clearFile());
        this.el.querySelector('#analyzeBtn')?.addEventListener('click', () => this._startAnalysis());
        this.el.querySelector('#stopAnalyzeBtn')?.addEventListener('click', () => this._stopAnalysis());
        this.el.querySelector('#viewReportBtn')?.addEventListener('click', () => {
            if (this.router) this.router.navigate('#/report');
        });
        this.el.querySelectorAll('.mode-option').forEach(opt => {
            opt.addEventListener('click', () => this.#onModeChange(opt));
        });
    }

    // ========================================================================
    // 文件选择
    // ========================================================================

    #triggerUpload() {
        this.el.querySelector('#fileInput')?.click();
    }

    #onFileSelected(e) {
        const file = e.target.files?.[0];
        if (!file) return;

        this._selectedFile = file;

        // 显示文件信息
        const fileInfo = this.el.querySelector('#fileInfo');
        const fileName = this.el.querySelector('#fileName');
        const fileSize = this.el.querySelector('#fileSize');

        if (fileInfo) fileInfo.style.display = '';
        if (fileName) fileName.textContent = file.name;
        if (fileSize) fileSize.textContent = (file.size / 1024 / 1024).toFixed(1) + ' MB';

        // 显示分析按钮
        const actions = this.el.querySelector('#analysisActions');
        if (actions) actions.style.display = '';

        // 更新按钮文字
        this.#updateAnalyzeBtnText();
    }

    #clearFile() {
        this._selectedFile = null;
        this.el.querySelector('#fileInfo').style.display = 'none';
        this.el.querySelector('#analysisActions').style.display = 'none';
        this.el.querySelector('#fileInput').value = '';
        this.el.querySelector('#resultPreview').style.display = 'none';
    }

    // ========================================================================
    // 模式选择 — 快速/专业
    // ========================================================================

    _restoreMode() {
        const saved = this.store?.getState('preferences')?.evalMode || localStorage.getItem('vocal_app_evalMode') || 'quick';
        this.el.querySelectorAll('.mode-option').forEach(o => {
            const isActive = o.dataset.mode === saved;
            o.classList.toggle('active', isActive);
            const radio = o.querySelector('input');
            if (radio) radio.checked = isActive;
        });
        this.#updateModeHint(saved);
        this.#updateAnalyzeBtnText();
    }

    #onModeChange(option) {
        this.el.querySelectorAll('.mode-option').forEach(o => o.classList.remove('active'));
        option.classList.add('active');

        const mode = option.dataset.mode || 'quick';
        this.#updateModeHint(mode);
        this.#updateAnalyzeBtnText();

        // 持久化
        localStorage.setItem('vocal_app_evalMode', mode);
        if (this.store) this.store.setState({ evalMode: mode }, 'preferences');
    }

    #updateModeHint(mode) {
        const hint = this.el.querySelector('#modeHint');
        const hintProf = this.el.querySelector('#modeHintProf');
        if (mode === 'quick' && hint) hint.textContent = '快速评估，适合日常练习';
        if (mode === 'professional' && hintProf) hintProf.textContent = '专业评估，适合详细诊断';
    }

    #getSelectedMode() {
        const active = this.el.querySelector('.mode-option.active');
        return active?.dataset?.mode || 'quick';
    }

    #updateAnalyzeBtnText() {
        const mode = this.#getSelectedMode();
        const text = this.el.querySelector('#analyzeBtnText');
        const icon = this.el.querySelector('#analyzeBtnIcon');
        if (text) text.textContent = mode === 'quick' ? '快速分析' : '专业分析';
        if (icon) icon.textContent = mode === 'quick' ? '⚡' : '🎯';
    }

    // ========================================================================
    // 分析
    // ========================================================================

    async _startAnalysis() {
        if (this._isAnalyzing || !this._selectedFile) return;

        // 同步模式到 store
        const mode = this.#getSelectedMode();
        if (this.store) this.store.setState({ mode }, 'analysis');

        // 切换按钮状态
        this.el.querySelector('#analyzeBtn').style.display = 'none';
        this.el.querySelector('#stopAnalyzeBtn').style.display = '';

        // 显示进度
        if (!this._progressBar) {
            this._progressBar = new ProgressBar(this.el.querySelector('#progressArea'), { variant: 'card' });
            this._progressBar.render();
        } else {
            this._progressBar.el.style.display = '';
        }
        this.el.querySelector('#progressArea').style.display = '';

        this._isAnalyzing = true;

        try {
            // 传入 mode 到后端
            const result = await this._api.uploadAudio(this._selectedFile, mode);
            this._isAnalyzing = false;

            if (result?.success) {
                const analysisId = result.analysis_id || result.id
                    || Date.now() + '_' + this._selectedFile.name.replace(/[^a-zA-Z0-9]/g, '_');

                if (this.store) {
                    this.store.setState({
                        status: 'complete',
                        result: result,
                        analysisId: analysisId,
                        mode: mode
                    }, 'analysis');
                    this.store.emit('analysis:complete', result);
                }

                this._progressBar?.complete();

                // 预览
                const preview = this.el.querySelector('#resultPreview');
                const score = this.el.querySelector('#previewScore');
                const level = this.el.querySelector('#previewLevel');
                if (preview) preview.style.display = '';
                if (score) score.textContent = (result.total_score || 0).toFixed(1);
                if (level) level.textContent = result.level || '';

                // 导航到报告页
                if (this.router) {
                    setTimeout(() => this.router.navigate('#/report'), 500);
                }
            } else {
                throw new ApiError(result?.error || '分析失败', 500);
            }
        } catch (error) {
            this._isAnalyzing = false;
            console.error('[HomePage] 分析失败:', error);
            if (this._progressBar) this._progressBar.error(error.message);
            showToast(error.message || '分析失败', 'error');
            if (this.store) this.store.setState({ status: 'error', error: error.message }, 'analysis');
        } finally {
            this.el.querySelector('#analyzeBtn').style.display = '';
            this.el.querySelector('#stopAnalyzeBtn').style.display = 'none';
        }
    }

    _stopAnalysis() {
        if (!this._isAnalyzing) return;
        this._api.cancelAnalysis();
        this._isAnalyzing = false;
        this._progressBar?.destroy();
        this._progressBar = null;
        this.el.querySelector('#progressArea').style.display = 'none';
        if (this.store) {
            this.store.setState({ status: 'idle', progress: { percent: 0, stage: '', message: '' } }, 'analysis');
        }
        this.el.querySelector('#analyzeBtn').style.display = '';
        this.el.querySelector('#stopAnalyzeBtn').style.display = 'none';
    }

    // ========================================================================
    // 录音
    // ========================================================================

    _startRecording() {
        if (!navigator.mediaDevices?.getUserMedia) {
            showToast('浏览器不支持录音', 'error');
            return;
        }
        // 跳到演唱页 — 可选: 传递模式参数
        if (this.router) {
            // 从曲库选歌还是直接录音？让 SingPage 处理
            this.router.navigate('#/sing');
        }
    }

    // ========================================================================
    // 麦克风检测
    // ========================================================================

    async _checkMicrophone() {
        const micStatus = this.el.querySelector('#micStatus');
        if (!micStatus) return;

        if (!navigator.mediaDevices?.getUserMedia) {
            micStatus.innerHTML = '<span class="status-dot" style="background:#ef4444"></span> 浏览器不支持录音';
            return;
        }

        try {
            const devices = await navigator.mediaDevices.enumerateDevices();
            const hasMic = devices.some(d => d.kind === 'audioinput');
            if (hasMic) {
                micStatus.innerHTML = '<span class="status-dot" style="background:#22c55e"></span> 麦克风就绪';
            } else {
                micStatus.innerHTML = '<span class="status-dot" style="background:#f59e0b"></span> 未检测到麦克风';
            }
        } catch {
            micStatus.innerHTML = '<span class="status-dot" style="background:#f59e0b"></span> 无法检测（需HTTPS）';
        }
    }

    // ========================================================================
    // 入场动画
    // ========================================================================

    _animateEntrance() {
        if (this.ac) {
            const welcome = this.el.querySelector('.welcome-section');
            const cards = this.el.querySelectorAll('.action-card');
            if (welcome) this.ac.enter(welcome, { preset: 'page-enter-down' });
            if (cards.length) this.ac.stagger(cards, { preset: 'slideUp', stagger: 0.15 });
        } else if (typeof gsap !== 'undefined') {
            const welcome = this.el.querySelector('.welcome-section');
            const cards = this.el.querySelectorAll('.action-card');
            const tl = gsap.timeline();
            if (welcome) tl.fromTo(welcome, { opacity: 0, y: -16 }, { opacity: 1, y: 0, duration: 0.4, ease: 'power2.out' });
            if (cards.length) tl.fromTo(cards, { opacity: 0, y: 24 }, { opacity: 1, y: 0, stagger: 0.15, duration: 0.5, ease: 'power2.out' }, '-=0.2');
        }
    }

    destroy() {
        this._progressBar?.destroy();
        super.destroy();
    }
}

export default HomePage;

