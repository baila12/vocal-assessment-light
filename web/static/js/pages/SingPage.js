/**
 * SingPage — 演唱页 (录音 + 实时音高对比)
 *
 * 路由: #/sing, #/sing/:songId
 *
 * 核心: 录音时实时音高检测 + Canvas 双曲线绘制 + GSAP 命中反馈
 *
 * @version 1.0
 */

import { BaseComponent } from '../components/BaseComponent.js';
import { showToast } from '../components/Toast.js';
import { hitFeedback, comboBounce } from '../effects/micro.js';
import { RealtimePitchAnalyzer } from '../modules/pitch-detector.js';

export class SingPage extends BaseComponent {
    /** @type {MediaRecorder|null} */
    #mediaRecorder = null;

    /** @type {AudioContext|null} */
    #audioContext = null;

    /** @type {RealtimePitchAnalyzer|null} */
    #pitchAnalyzer = null;

    /** @type {boolean} */
    #isRecording = false;

    /** @type {number} */
    #recordingStartTime = 0;

    /** @type {Array} */
    #chunks = [];

    /** @type {number} */
    #combo = 0;

    /** @type {number} */
    #timerInterval = null;

    /** @type {HTMLCanvasElement} */
    #pitchCanvas;

    /** @type {number[]} */
    #pitchHistory = [];

    constructor(container, options = {}) {
        super(container, options);
    }

    async mount(params) {
        const songId = params.songId;
        this.render();
        this.bindEvents();

        // 如果有歌曲ID，加载标准歌曲数据
        if (songId) {
            this.el.querySelector('#selectedSong').textContent = `歌曲: ${songId}`;
            this.el.querySelector('#songInfo').style.display = 'block';
        }

        // GSAP 入场
        if (typeof gsap !== 'undefined') {
            const tl = gsap.timeline();
            tl.fromTo(this.el.querySelector('.sing-header'), { opacity: 0, y: -16 }, { opacity: 1, y: 0, duration: 0.4, ease: 'power2.out' });
            tl.fromTo(this.el.querySelector('#pitchCanvasWrap'), { opacity: 0, scale: 0.98 }, { opacity: 1, scale: 1, duration: 0.5, ease: 'power2.out' }, '-=0.2');
            tl.fromTo(this.el.querySelector('#controlPanel'), { opacity: 0, y: 24 }, { opacity: 1, y: 0, duration: 0.4, ease: 'power2.out' }, '-=0.3');
        }
    }

    render() {
        this.el = this.createElement('div', { id: 'page-sing', className: 'page page-container' });

        this.el.innerHTML = `
        <div class="sing-header" style="text-align:center;margin-bottom:20px;">
            <h2 style="font-size:20px;font-weight:700;">🎤 实时演唱</h2>
            <p style="font-size:14px;color:var(--text-muted);margin-top:4px;">录音时实时显示音高，与标准对比获得即时反馈</p>
        </div>

        <!-- 标准歌曲信息 -->
        <div id="songInfo" style="display:none;text-align:center;margin-bottom:16px;padding:8px 16px;background:var(--primary-light);border-radius:var(--radius-md);font-size:13px;color:var(--primary);">
            <span id="selectedSong">未选择歌曲</span>
        </div>

        <!-- 音高对比 Canvas -->
        <div id="pitchCanvasWrap" style="position:relative;width:100%;height:200px;background:var(--bg-elevated);border-radius:var(--radius-lg);margin-bottom:20px;overflow:hidden;">
            <canvas id="pitchCanvas" style="width:100%;height:100%;"></canvas>
            <!-- 命中反馈区 -->
            <div id="hitFeedbackArea" style="position:absolute;inset:0;pointer-events:none;display:flex;align-items:center;justify-content:center;"></div>
            <!-- 连击 -->
            <div id="comboDisplay" style="position:absolute;top:12px;right:16px;font-size:24px;font-weight:700;color:#FFD700;opacity:0;text-shadow:0 2px 8px rgba(0,0,0,0.3);">0 COMBO</div>
        </div>

        <!-- 实时评分面板 -->
        <div id="liveScorePanel" style="display:flex;gap:16px;margin-bottom:20px;justify-content:center;">
            <div style="text-align:center;">
                <div style="font-size:11px;color:var(--text-muted);">实时音高</div>
                <div id="livePitch" style="font-size:24px;font-weight:700;color:var(--accent-blue);">--</div>
            </div>
            <div style="text-align:center;">
                <div style="font-size:11px;color:var(--text-muted);">音量</div>
                <div id="liveVolume" style="font-size:24px;font-weight:700;color:var(--accent-cyan);">-- dB</div>
            </div>
            <div style="text-align:center;">
                <div style="font-size:11px;color:var(--text-muted);">连击</div>
                <div id="comboCount" style="font-size:24px;font-weight:700;color:#FFD700;">0</div>
            </div>
            <div style="text-align:center;">
                <div style="font-size:11px;color:var(--text-muted);">录音时长</div>
                <div id="recordTime" style="font-size:24px;font-weight:700;color:var(--text-primary);">00:00</div>
            </div>
        </div>

        <!-- 控制面板 -->
        <div id="controlPanel" style="display:flex;gap:12px;justify-content:center;">
            <button id="startRecordBtn" class="btn" style="width:64px;height:64px;border-radius:50%;background:var(--danger);color:#fff;border:none;font-size:24px;cursor:pointer;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 16px rgba(239,68,68,0.4);transition:transform 0.15s;">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="8"/></svg>
            </button>
            <button id="stopRecordBtn" class="btn" style="display:none;width:64px;height:64px;border-radius:50%;background:var(--bg-elevated);color:var(--danger);border:2px solid var(--danger);font-size:24px;cursor:pointer;align-items:center;justify-content:center;">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
            </button>
        </div>

        <!-- 导航提示 -->
        <p style="text-align:center;margin-top:16px;font-size:12px;color:var(--text-muted);">
            选择标准歌曲获得实时对比反馈 |
            <a href="#/sing" style="color:var(--primary);cursor:pointer;" id="selectSongLink">选择歌曲</a>
        </p>`;

        this.container.appendChild(this.el);
    }

    bindEvents() {
        this.el.querySelector('#startRecordBtn')?.addEventListener('click', () => this.#startRecording());
        this.el.querySelector('#stopRecordBtn')?.addEventListener('click', () => this.#stopRecording());
    }

    // ========================================================================
    // 录音逻辑
    // ========================================================================

    async #startRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

            this.#audioContext = new (window.AudioContext || window.webkitAudioContext)();

            this.#mediaRecorder = new MediaRecorder(stream);
            this.#chunks = [];
            this.#pitchHistory = [];

            this.#mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) this.#chunks.push(e.data);
            };

            this.#mediaRecorder.onstop = () => {
                const blob = new Blob(this.#chunks, { type: 'audio/webm' });
                if (this.store) {
                    this.store.emit('recording:complete', blob);
                }
            };

            this.#mediaRecorder.start();
            this.#isRecording = true;
            this.#recordingStartTime = Date.now();
            this.#combo = 0;

            // 切换 UI
            this.el.querySelector('#startRecordBtn').style.display = 'none';
            this.el.querySelector('#stopRecordBtn').style.display = 'flex';

            // 启动实时音高检测 + Canvas 绘制
            this.#startPitchDetection();
            this.#timerInterval = setInterval(() => this.#updateTimer(), 100);

            showToast('录音开始', 'info');

        } catch (err) {
            console.error('[SingPage] 录音失败:', err);
            showToast('无法访问麦克风: ' + (err.message || '未知错误'), 'error');
        }
    }

    #stopRecording() {
        if (this.#mediaRecorder && this.#isRecording) {
            this.#mediaRecorder.stop();
            this.#mediaRecorder.stream.getTracks().forEach(t => t.stop());
        }
        this.#isRecording = false;

        if (this.#pitchAnalyzer) {
            this.#pitchAnalyzer.stop();
            this.#pitchAnalyzer = null;
        }

        if (this.#timerInterval) {
            clearInterval(this.#timerInterval);
            this.#timerInterval = null;
        }

        if (this.#audioContext) {
            this.#audioContext.close();
            this.#audioContext = null;
        }

        // 切换 UI
        this.el.querySelector('#startRecordBtn').style.display = 'flex';
        this.el.querySelector('#stopRecordBtn').style.display = 'none';

        // 重置连击
        this.#combo = 0;
        const comboDisplay = this.el.querySelector('#comboDisplay');
        if (comboDisplay) comboBounce(comboDisplay, 0);

        showToast('录音完成', 'success');
    }

    // ========================================================================
    // 实时音高检测 — YIN 算法 (pitch-detector.js)
    // ========================================================================

    #startPitchDetection() {
        this.#pitchAnalyzer = new RealtimePitchAnalyzer({ fftSize: 2048 });
        this.#pitchAnalyzer.init(this.#audioContext, this.#mediaRecorder.stream);

        this.#pitchAnalyzer.start((result) => {
            if (!this.#isRecording) return;

            const freq = result.frequency;
            const note = result.note;
            const rmsDB = 20 * Math.log10(Math.max(result.rms, 1e-10));

            this.#pitchHistory.push(freq);

            // 更新实时面板
            const noteLabel = note ? `${note.fullName} (${note.cents > 0 ? '+' : ''}${note.cents}¢)` : '--';
            this.el.querySelector('#livePitch').textContent =
                freq > 0 ? `${Math.round(freq)} Hz — ${noteLabel}` : '--';
            this.el.querySelector('#liveVolume').textContent = `${Math.round(rmsDB)} dB`;

            // TODO: 替换为实际命中判定 — 需要加载标准歌曲音符数据
            // 当 songId 参数传入时，从 API 获取标准音符序列，
            // 用 note.midi 与当前时间的参考音符对比，计算偏差确定命中等级
            this.#simulateHit(freq);
        });
    }

    // ========================================================================
    // 命中反馈
    // ========================================================================

    // TODO: 替换为真实命中判定 — 加载标准歌曲的 noteSegments，
    // 用 pitchAnalyzer 每次回调的 note.midi 与当前时间点对应的参考音符对比，
    // 偏差 <15¢ → PERFECT, <35¢ → GREAT, <60¢ → GOOD
    #simulateHit(freq) {
        if (Math.random() < 0.05) {
            const types = ['perfect', 'great', 'good'];
            const weights = [0.15, 0.35, 0.5]; // 概率分布
            const r = Math.random();
            let type = 'good';
            if (r < weights[0]) type = 'perfect';
            else if (r < weights[0] + weights[1]) type = 'great';

            this.#onHit(type);
        }
    }

    #onHit(type) {
        // 连击
        this.#combo++;
        this.el.querySelector('#comboCount').textContent = this.#combo;

        // 命中反馈动画
        const area = this.el.querySelector('#hitFeedbackArea');
        const el = document.createElement('div');
        const labels = { perfect: 'PERFECT', great: 'GREAT', good: 'GOOD' };
        el.textContent = labels[type];
        el.style.cssText = `
            position: absolute;
            font-size: 20px;
            font-weight: 700;
            pointer-events: none;
            color: ${type === 'perfect' ? '#FFD700' : type === 'great' ? '#22c55e' : '#fff'};
            text-shadow: 0 2px 8px rgba(0,0,0,0.3);
        `;
        area.appendChild(el);

        hitFeedback(el, type);

        // 连击动画
        const comboDisplay = this.el.querySelector('#comboDisplay');
        comboBounce(comboDisplay, this.#combo);
    }

    // ========================================================================
    // 计时器
    // ========================================================================

    #updateTimer() {
        if (!this.#isRecording) return;
        const elapsed = Math.floor((Date.now() - this.#recordingStartTime) / 1000);
        const mins = Math.floor(elapsed / 60);
        const secs = elapsed % 60;
        this.el.querySelector('#recordTime').textContent =
            `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }

    destroy() {
        if (this.#isRecording) this.#stopRecording();
        if (this.#timerInterval) clearInterval(this.#timerInterval);
        super.destroy();
    }
}

export default SingPage;
