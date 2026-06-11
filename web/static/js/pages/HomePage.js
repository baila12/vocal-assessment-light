/**
 * HomePage — 首页 (上传 + 录音 + 模式选择)
 *
 * 路由: #/
 *
 * @version 1.0
 */

import { BaseComponent } from '../components/BaseComponent.js';
import { showToast } from '../components/Toast.js';
import { ProgressBar } from '../components/ProgressBar.js';
import { AnalysisSSE } from '../services/sse.js';
import { ApiClient, ApiError } from '../services/api.js';
import { staggerSlideUp, slideInRight } from '../effects/entrances.js';

// 复用现有模块的核心逻辑
import { handleFileSelect as loadFileInfo } from '../modules/upload.js';

export class HomePage extends BaseComponent {
    #api;
    #progressBar;

    constructor(container, options = {}) {
        super(container, options);
        this.#api = options.api || new ApiClient();
    }

    async mount(params) {
        this.render();
        this.bindEvents();
        this.#checkMicrophone();

        // GSAP 入场动画
        if (typeof gsap !== 'undefined') {
            const welcome = this.el.querySelector('.welcome-section');
            const cards = this.el.querySelectorAll('.action-card');
            const sidebar = this.el.querySelector('.sidebar');

            const tl = gsap.timeline();
            if (welcome) tl.fromTo(welcome, { opacity: 0, y: -16 }, { opacity: 1, y: 0, duration: 0.4, ease: 'power2.out' });
            if (cards.length) tl.fromTo(cards, { opacity: 0, y: 24 }, { opacity: 1, y: 0, stagger: 0.15, duration: 0.5, ease: 'power2.out' }, '-=0.2');
            if (sidebar) tl.fromTo(sidebar, { opacity: 0, x: 30 }, { opacity: 1, x: 0, duration: 0.4, ease: 'power2.out' }, '-=0.3');
        }
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

                <input type="file" id="fileInput" accept=".wav,.mp3,.flac,.ogg,.m4a,.m4a" style="display:none">

                <div class="mode-selector" id="modeSelector">
                    <div class="mode-header">
                        <span class="mode-title">评估模式</span>
                        <span class="mode-hint" id="modeHint">快速评估，适合日常练习</span>
                    </div>
                    <div class="mode-options">
                        <label class="mode-option active" id="modeQuick">
                            <input type="radio" name="evalMode" value="quick" checked>
                            <div class="mode-option-content">
                                <div class="mode-icon">⚡</div>
                                <div class="mode-info">
                                    <div class="mode-name">快速评估</div>
                                    <div class="mode-desc">~30秒完成，基础五维评分</div>
                                </div>
                            </div>
                        </label>
                        <label class="mode-option" id="modeProfessional">
                            <input type="radio" name="evalMode" value="professional">
                            <div class="mode-option-content">
                                <div class="mode-icon">🎯</div>
                                <div class="mode-info">
                                    <div class="mode-name">专业评估</div>
                                    <div class="mode-desc">~2-5分钟，逐句评分+音色分析</div>
                                </div>
                            </div>
                        </label>
                    </div>
                </div>

                <div class="audio-card" id="selectedAudioCard" style="display:none">
                    <div class="audio-card-header">
                        <div class="audio-file-info">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>
                            <span id="selectedFileName">未选择文件</span>
                        </div>
                        <button class="btn btn-ghost btn-sm" id="clearFileBtn">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                        </button>
                    </div>
                    <div class="audio-card-body">
                        <div class="audio-stats">
                            <div class="stat-item"><span class="stat-label">时长</span><span class="stat-value" id="audioDuration">--:--</span></div>
                            <div class="stat-item"><span class="stat-label">大小</span><span class="stat-value" id="audioSize">--</span></div>
                            <div class="stat-item"><span class="stat-label">格式</span><span class="stat-value" id="audioFormat">--</span></div>
                        </div>
                        <div class="audio-actions">
                            <button id="analyzeBtn" class="btn btn-primary btn-lg">
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                                <span id="analyzeBtnText">开始分析</span>
                            </button>
                            <button id="stopAnalyzeBtn" class="btn btn-danger btn-lg" style="display:none">停止分析</button>
                        </div>
                    </div>
                </div>
            </div>

            <div class="sidebar">
                <div class="sidebar-card">
                    <div class="sidebar-card-header">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
                        <span>使用说明</span>
                    </div>
                    <div class="sidebar-card-body">
                        <ol class="steps-list">
                            <li><span class="step-num">1</span><span>导入音频文件或录制演唱</span></li>
                            <li><span class="step-num">2</span><span>点击「开始分析」按钮</span></li>
                            <li><span class="step-num">3</span><span>查看五维评分和详细分析</span></li>
                            <li><span class="step-num">4</span><span>根据建议改进演唱技巧</span></li>
                        </ol>
                    </div>
                </div>
                <div class="sidebar-card">
                    <div class="sidebar-card-header">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.21 15.89A10 10 0 1 1 8 2.83"/><path d="M22 12A10 10 0 0 0 12 2v10z"/></svg>
                        <span>五维评分</span>
                    </div>
                    <div class="sidebar-card-body">
                        <div class="dimension-list">
                            <div class="dimension-item"><span class="dim-dot" style="background:var(--dim-pitch)"></span><span class="dim-name">音准</span><span class="dim-weight">35%</span></div>
                            <div class="dimension-item"><span class="dim-dot" style="background:var(--dim-rhythm)"></span><span class="dim-name">节奏</span><span class="dim-weight">25%</span></div>
                            <div class="dimension-item"><span class="dim-dot" style="background:var(--dim-breath)"></span><span class="dim-name">气息</span><span class="dim-weight">10%</span></div>
                            <div class="dimension-item"><span class="dim-dot" style="background:var(--dim-technique)"></span><span class="dim-name">发声技术</span><span class="dim-weight">25%</span></div>
                            <div class="dimension-item"><span class="dim-dot" style="background:var(--dim-artistry)"></span><span class="dim-name">艺术表现</span><span class="dim-weight">15%</span></div>
                        </div>
                    </div>
                </div>
                <div class="sidebar-card">
                    <div class="sidebar-card-header">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                        <span>演唱技巧提示</span>
                    </div>
                    <div class="sidebar-card-body">
                        <div class="tips-list">
                            <div class="tip-item"><span class="tip-icon">💡</span><span>保持稳定的呼吸节奏</span></div>
                            <div class="tip-item"><span class="tip-icon">💡</span><span>注意音准，避免跑调</span></div>
                            <div class="tip-item"><span class="tip-icon">💡</span><span>控制音量动态范围</span></div>
                            <div class="tip-item"><span class="tip-icon">💡</span><span>跟随节奏，不要抢拍</span></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>`;

        this.container.appendChild(this.el);
    }

    bindEvents() {
        // 上传点击
        this.el.querySelector('#uploadCard')?.addEventListener('click', () => {
            document.getElementById('fileInput')?.click();
        });

        // 录音点击
        this.el.querySelector('#recordCard')?.addEventListener('click', () => {
            if (this.router) this.router.navigate('#/sing');
            else location.hash = '#/sing';
        });

        // 文件选择
        document.getElementById('fileInput')?.addEventListener('change', (e) => this.#onFileSelect(e));

        // 清除文件
        this.el.querySelector('#clearFileBtn')?.addEventListener('click', () => this.#clearFile());

        // 分析按钮
        this.el.querySelector('#analyzeBtn')?.addEventListener('click', () => this.#startAnalysis());

        // 停止分析
        this.el.querySelector('#stopAnalyzeBtn')?.addEventListener('click', () => this.#stopAnalysis());

        // 模式选择
        this.el.querySelectorAll('.mode-option').forEach(opt => {
            opt.addEventListener('click', () => this.#onModeChange(opt));
        });
    }

    // ========================================================================
    // 文件处理
    // ========================================================================

    async #onFileSelect(event) {
        const file = event.target.files?.[0];
        if (!file) return;

        // 更新 store
        if (this.store) {
            this.store.setState({
                name: file.name,
                duration: 0,
                format: file.name.split('.').pop()?.toUpperCase() || '--',
                file: file
            }, 'audio');
        }

        // 更新 UI
        this.el.querySelector('#selectedFileName').textContent = file.name;
        this.el.querySelector('#audioFormat').textContent = file.name.split('.').pop()?.toUpperCase() || '--';

        // 文件大小
        const sizeMB = file.size / (1024 * 1024);
        this.el.querySelector('#audioSize').textContent = sizeMB >= 1 ? `${sizeMB.toFixed(1)} MB` : `${Math.round(file.size / 1024)} KB`;

        // 时长 (异步读取)
        try {
            const audio = new Audio();
            audio.src = URL.createObjectURL(file);
            await new Promise((resolve, reject) => {
                audio.addEventListener('loadedmetadata', resolve);
                audio.addEventListener('error', reject);
            });
            const mins = Math.floor(audio.duration / 60);
            const secs = Math.floor(audio.duration % 60);
            this.el.querySelector('#audioDuration').textContent = `${mins}:${secs.toString().padStart(2, '0')}`;

            if (this.store) {
                this.store.setState({ duration: audio.duration, url: audio.src }, 'audio');
            }
        } catch {
            this.el.querySelector('#audioDuration').textContent = '--:--';
        }

        // 显示音频卡片
        const card = this.el.querySelector('#selectedAudioCard');
        if (card) {
            card.style.display = 'block';
            if (typeof gsap !== 'undefined') {
                gsap.fromTo(card, { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.3, ease: 'power2.out' });
            }
        }

        // 隐藏 action cards
        const actionCards = this.el.querySelector('#actionCards');
        if (actionCards) actionCards.style.display = 'none';
    }

    #clearFile() {
        const card = this.el.querySelector('#selectedAudioCard');
        if (card) card.style.display = 'none';

        const actionCards = this.el.querySelector('#actionCards');
        if (actionCards) actionCards.style.display = '';

        document.getElementById('fileInput').value = '';

        if (this.store) {
            this.store.setState({ file: null, name: '', duration: 0, url: '', format: '' }, 'audio');
        }
    }

    // ========================================================================
    // 分析
    // ========================================================================

    async #startAnalysis() {
        const file = this.store?.getState('audio').file;
        if (!file) {
            showToast('请先选择音频文件', 'warning');
            return;
        }

        const mode = this.#getSelectedMode();
        if (this.store) {
            this.store.setState({ status: 'analyzing', mode, progress: { percent: 0, stage: '', message: '准备中...' } }, 'analysis');
        }

        // 显示进度条
        if (!this.#progressBar) {
            this.#progressBar = new ProgressBar(this.el.querySelector('.main-content'), { variant: 'card' });
            this.#progressBar.render();
        } else {
            this.#progressBar.el.style.display = '';
        }

        // 切换按钮状态
        this.el.querySelector('#analyzeBtn').style.display = 'none';
        this.el.querySelector('#stopAnalyzeBtn').style.display = '';

        try {
            const result = await this.#api.uploadAudio(file, mode);

            if (result?.success) {
                // 后端返回的 result 不含 analysis_id，用时间戳 + 文件名生成
                const analysisId = result.analysis_id || result.id
                    || `${Date.now()}_${file.name.replace(/[^a-zA-Z0-9]/g, '_')}`;

                if (this.store) {
                    this.store.setState({
                        status: 'complete',
                        result: result,
                        analysisId: analysisId
                    }, 'analysis');
                    this.store.emit('analysis:complete', result);
                }

                this.#progressBar?.complete();

                // 导航到报告页 (ReportPage 从 store 取结果，不依赖 URL 参数)
                if (this.router) {
                    setTimeout(() => this.router.navigate('#/report'), 500);
                }
            } else {
                throw new ApiError(result?.error || '分析失败', 500);
            }
        } catch (error) {
            console.error('[HomePage] 分析失败:', error);
            this.#progressBar?.error(error.message);
            showToast(error.message || '分析失败', 'error');

            if (this.store) {
                this.store.setState({ status: 'error', error: error.message }, 'analysis');
            }
        } finally {
            this.el.querySelector('#analyzeBtn').style.display = '';
            this.el.querySelector('#stopAnalyzeBtn').style.display = 'none';
        }
    }

    #stopAnalysis() {
        this.#api.cancelAnalysis();
        this.#progressBar?.destroy();
        this.#progressBar = null;

        if (this.store) {
            this.store.setState({ status: 'idle', progress: { percent: 0, stage: '', message: '' } }, 'analysis');
        }

        this.el.querySelector('#analyzeBtn').style.display = '';
        this.el.querySelector('#stopAnalyzeBtn').style.display = 'none';
    }

    // ========================================================================
    // 模式选择
    // ========================================================================

    #onModeChange(option) {
        this.el.querySelectorAll('.mode-option').forEach(o => o.classList.remove('active'));
        option.classList.add('active');

        const mode = option.querySelector('input')?.value || 'quick';
        const hint = this.el.querySelector('#modeHint');
        const btnText = this.el.querySelector('#analyzeBtnText');

        if (mode === 'quick') {
            if (hint) hint.textContent = '快速评估，适合日常练习';
            if (btnText) btnText.textContent = '快速分析';
        } else {
            if (hint) hint.textContent = '专业评估，适合详细诊断';
            if (btnText) btnText.textContent = '专业分析';
        }

        if (this.store) this.store.setState({ evalMode: mode }, 'preferences');
    }

    #getSelectedMode() {
        const active = this.el.querySelector('.mode-option.active input');
        return active?.value || 'quick';
    }

    // ========================================================================
    // 麦克风检测
    // ========================================================================

    async #checkMicrophone() {
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

    destroy() {
        this.#progressBar?.destroy();
        super.destroy();
    }
}

export default HomePage;
