/**
 * SingPage — 演唱页 (录音前选歌 + 实时音高对比)
 *
 * 路由:
 *   #/sing           — 带选歌区，选中后录音
 *   #/sing/:songId   — 直接进入该歌曲的录音准备
 *
 * 流程: 选歌 → 激活录音 → 实时对比 → 完成评分
 *
 * @version 2.0
 */

import { BaseComponent } from '../components/BaseComponent.js';
import { showToast } from '../components/Toast.js';
import { StandardAudioSelector } from '../components/StandardAudioSelector.js';
import { RealtimePitchAnalyzer } from '../modules/pitch-detector.js';

export class SingPage extends BaseComponent {
    static animationPreset = 'page-enter';

    /** @type {string|null} */
    _songId = null;

    /** @type {Object|null} */
    _selectedSong = null;

    /** @type {boolean} */
    _isRecording = false;

    /** @type {boolean} */
    _songSelectionDone = false;

    /** @type {StandardAudioSelector|null} */
    _selector = null;

    // Recording
    _mediaRecorder = null;
    _audioContext = null;
    _pitchAnalyzer = null;
    _recordingStartTime = 0;
    _chunks = [];
    _combo = 0;
    _timerInterval = null;
    #pitchCanvas;
    _pitchHistory = [];

    async mount(params) {
        this._songId = params.songId || null;
        this.render();
        this.bindEvents();

        // 加载歌曲数据
        if (this._songId) {
            await this._loadSongById(this._songId);
        } else {
            this._showSongSelection();
        }

        this._animateIn();
    }

    render() {
        this.el = this.createElement('div', { id: 'page-sing', className: 'page page-container' });

        this.el.innerHTML = `
        <!-- 歌曲选择区 (仅 #/sing 无参数时显示) -->
        <div id="songSelectionArea" style="margin-bottom:20px;"></div>

        <!-- 曲库为空提示 (#/sing 无参数且曲库空) -->
        <div id="emptyLibraryMessage" style="display:none;text-align:center;padding:40px 20px;">
            <div style="font-size:48px;margin-bottom:16px;">📭</div>
            <h3 style="color:var(--text-primary);margin-bottom:8px;">曲库为空</h3>
            <p style="color:var(--text-muted);margin-bottom:20px;">还没有导入标准歌曲</p>
            <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap;">
                <a href="#/songs" style="padding:10px 20px;background:var(--primary);color:#fff;border-radius:var(--radius-md);text-decoration:none;font-size:14px;font-weight:500;">前往曲库导入</a>
                <button id="directUploadBtn" style="padding:10px 20px;border:1px solid var(--border);color:var(--text-primary);border-radius:var(--radius-md);background:transparent;font-size:14px;cursor:pointer;">直接上传音频文件分析</button>
            </div>
        </div>

        <!-- 歌曲不存在提示 (songId 无效时) -->
        <div id="songNotFound" style="display:none;text-align:center;padding:40px 20px;">
            <div style="font-size:48px;margin-bottom:16px;">❓</div>
            <h3 style="color:var(--text-primary);margin-bottom:8px;">歌曲不存在</h3>
            <p style="color:var(--text-muted);margin-bottom:20px;">未找到该标准歌曲</p>
            <a href="#/songs" style="padding:10px 20px;background:var(--primary);color:#fff;border-radius:var(--radius-md);text-decoration:none;font-size:14px;font-weight:500;">返回曲库</a>
        </div>

        <!-- 录音区域 (初始隐藏) -->
        <div id="recordingArea" style="display:none;">

            <!-- 已选歌曲信息 -->
            <div id="songInfoBar" style="display:none;align-items:center;justify-content:space-between;padding:12px 16px;background:var(--primary-light);border-radius:var(--radius-md);margin-bottom:16px;">
                <div>
                    <div id="selectedSong" style="font-weight:600;font-size:15px;color:var(--text-primary);">--</div>
                    <div id="selectedSongMeta" style="font-size:12px;color:var(--text-muted);margin-top:2px;">--</div>
                </div>
                <div style="display:flex;gap:8px;">
                    <button id="uploadExistingBtn" class="btn btn-sm" style="padding:6px 12px;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--bg-primary);color:var(--text-secondary);font-size:12px;cursor:pointer;">📁 上传已有录音</button>
                    <button id="deselectSongBtn" style="border:none;background:none;color:var(--text-muted);cursor:pointer;font-size:14px;padding:4px;">✕</button>
                </div>
            </div>

            <!-- 选歌提示 (未选时) -->
            <div id="selectSongHint" style="display:block;text-align:center;padding:20px;color:var(--text-muted);font-size:14px;">
                🎯 请先选择一首标准歌曲
            </div>

            <!-- 音高对比 Canvas -->
            <div id="pitchCanvasWrap" style="position:relative;width:100%;height:200px;background:var(--bg-elevated);border-radius:var(--radius-lg);margin-bottom:20px;overflow:hidden;">
                <canvas id="pitchCanvas" style="width:100%;height:100%;"></canvas>
                <div id="hitFeedbackArea" style="position:absolute;inset:0;pointer-events:none;display:flex;align-items:center;justify-content:center;"></div>
                <div id="comboDisplay" style="position:absolute;top:12px;right:16px;font-size:24px;font-weight:700;color:#FFD700;opacity:0;text-shadow:0 2px 8px rgba(0,0,0,0.3);">0 COMBO</div>
            </div>

            <!-- 实时评分面板 -->
            <div id="liveScorePanel" style="display:flex;gap:16px;margin-bottom:20px;justify-content:center;">
                <div style="text-align:center;">
                    <div style="font-size:11px;color:var(--text-muted);">实时音高</div>
                    <div id="livePitch" style="font-size:24px;font-weight:700;color:var(--accent-blue);">· · ·</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:11px;color:var(--text-muted);">音量</div>
                    <div id="liveVolume" style="font-size:24px;font-weight:700;color:var(--accent-cyan);">· · ·</div>
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
            <div id="controlPanel" style="display:flex;gap:12px;justify-content:center;align-items:center;margin-bottom:20px;">
                <button id="startRecordBtn" style="width:56px;height:56px;border-radius:50%;background:var(--danger);color:#fff;border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:background 0.2s;" disabled>
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="6"/></svg>
                </button>
                <button id="stopRecordBtn" style="width:56px;height:56px;border-radius:50%;background:var(--text-muted);color:#fff;border:none;cursor:pointer;display:none;align-items:center;justify-content:center;">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
                </button>
                <div id="recordingIndicator" style="display:none;gap:6px;align-items:center;color:var(--danger);font-size:13px;font-weight:600;">
                    <span style="width:8px;height:8px;border-radius:50%;background:var(--danger);"></span> 录音中
                </div>
            </div>

            <!-- 跳过选歌按钮 (在选歌区不显示时可用) -->
            <div id="skipSongArea" style="display:none;text-align:center;margin-bottom:16px;">
                <button id="skipSongBtn" style="padding:8px 16px;border:1px solid var(--border);border-radius:var(--radius-md);background:transparent;color:var(--text-muted);font-size:12px;cursor:pointer;">跳过选歌, 直接录音</button>
            </div>
        </div>

        <!-- 完成后区域 -->
        <div id="recordingResult" style="display:none;text-align:center;padding:40px 20px;">
            <div style="font-size:48px;margin-bottom:12px;">🎉</div>
            <div style="font-size:28px;font-weight:700;color:var(--primary);" id="resultScore">--</div>
            <div style="font-size:14px;color:var(--text-muted);margin:8px 0 20px;" id="resultLevel">--</div>
            <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap;">
                <button id="viewReportBtn" class="btn btn-primary" style="padding:10px 20px;border:none;border-radius:var(--radius-md);background:var(--primary);color:#fff;font-size:14px;cursor:pointer;font-weight:600;">查看完整报告</button>
                <button id="singAgainBtn" class="btn btn-secondary" style="padding:10px 20px;border:1px solid var(--border);border-radius:var(--radius-md);background:transparent;color:var(--text-primary);font-size:14px;cursor:pointer;">🎤 再来一首</button>
            </div>
        </div>
        `;

        this.container.appendChild(this.el);
    }

    bindEvents() {
        this.el.querySelector('#startRecordBtn')?.addEventListener('click', () => this._startRecording());
        this.el.querySelector('#stopRecordBtn')?.addEventListener('click', () => this._stopRecording());
        this.el.querySelector('_deselectSongBtn')?.addEventListener('click', () => this._deselectSong());
        this.el.querySelector('#uploadExistingBtn')?.addEventListener('click', () => this._uploadExistingRecording());
        this.el.querySelector('#skipSongBtn')?.addEventListener('click', () => this._skipSongAndRecord());
        this.el.querySelector('#directUploadBtn')?.addEventListener('click', () => this._triggerDirectUpload());
        this.el.querySelector('#viewReportBtn')?.addEventListener('click', () => {
            if (this.router) this.router.navigate('#/report');
        });
        this.el.querySelector('#singAgainBtn')?.addEventListener('click', () => this._resetForNextSong());
    }

    // ========================================================================
    // Song Selection Flow
    // ========================================================================

    async _loadSongById(songId) {
        let song = null;

        // Try API first, then mock
        try {
            const res = await this._api?.getSongDetail(songId);
            song = res?.song || null;
        } catch (e) {
            // mock
            const mockSongs = window.__mockSongs || [];
            song = mockSongs.find(s => s.id === songId) || null;
        }

        if (!song) {
            this.el.querySelector('#songSelectionArea').style.display = 'none';
            this.el.querySelector('#recordingArea').style.display = 'none';
            this.el.querySelector('#songNotFound').style.display = '';
            return;
        }

        this._selectedSong = song;
        this._songSelectionDone = true;
        this._showRecordingArea();
    }

    _showSongSelection() {
        const area = this.el.querySelector('#songSelectionArea');
        const emptyMsg = this.el.querySelector('#emptyLibraryMessage');
        const recordingArea = this.el.querySelector('#recordingArea');

        area.innerHTML = '';
        emptyMsg.style.display = 'none';
        recordingArea.style.display = 'none';

        // 检查曲库
        const songs = window.__mockSongs || [];

        if (songs.length === 0) {
            emptyMsg.style.display = '';
            this.el.querySelector('#skipSongArea').style.display = 'block';
            return;
        }

        // 显示选择器
        const selectorContainer = document.createElement('div');
        selectorContainer.style.cssText = 'margin-bottom:16px;';
        area.appendChild(selectorContainer);

        // 标题
        const title = document.createElement('h3');
        title.style.cssText = 'font-size:16px;font-weight:600;margin-bottom:12px;';
        title.textContent = '选择一首标准歌曲开始练习';
        selectorContainer.appendChild(title);

        this._selector = new StandardAudioSelector(selectorContainer, {
            mode: 'inline',
            onSelect: (song) => {
                this._selectedSong = song;
                this._songSelectionDone = true;
                this._showRecordingArea();
            }
        });
        this._selector.setSongs(songs);
        this._selector.render();

        // 跳过选歌按钮
        this.el.querySelector('#skipSongArea').style.display = 'block';
    }

    _showRecordingArea() {
        const selectionArea = this.el.querySelector('#songSelectionArea');
        const emptyMsg = this.el.querySelector('#emptyLibraryMessage');
        const recordingArea = this.el.querySelector('#recordingArea');
        const songInfoBar = this.el.querySelector('#songInfoBar');
        const selectHint = this.el.querySelector('#selectSongHint');
        const startBtn = this.el.querySelector('#startRecordBtn');
        const skipArea = this.el.querySelector('#skipSongArea');

        // 隐藏选歌区
        selectionArea.style.display = 'none';
        emptyMsg.style.display = 'none';
        skipArea.style.display = 'none';

        // 显示录音区
        recordingArea.style.display = '';

        if (this._selectedSong) {
            // 显示歌曲信息
            songInfoBar.style.display = 'flex';
            selectHint.style.display = 'none';
            startBtn.disabled = false;

            const titleEl = this.el.querySelector('_selectedSong');
            const metaEl = this.el.querySelector('_selectedSongMeta');

            if (titleEl) titleEl.textContent = this._selectedSong.title + ' - ' + (this._selectedSong.artist || '');
            if (metaEl) {
                const parts = [];
                if (this._selectedSong.bpm) parts.push('BPM: ' + this._selectedSong.bpm);
                if (this._selectedSong.key) parts.push(this._selectedSong.key);
                if (this._selectedSong.difficulty) parts.push(this._selectedSong.difficulty);
                metaEl.textContent = parts.join(' · ');
            }

            // 加载标准音高参考数据
            window.__standardPitchData = { songId: this._selectedSong.id };

        } else {
            // 无歌曲 — 跳过选歌模式
            songInfoBar.style.display = 'none';
            selectHint.style.display = 'none'; // Hidden for skip mode
            startBtn.disabled = false;
            window.__standardPitchData = null;
        }

        // 入场动画
        if (this.ac) {
            this.ac.enter(recordingArea, { preset: 'slideUp' });
        }
    }

    _deselectSong() {
        this._selectedSong = null;
        this._songSelectionDone = false;
        this.el.querySelector('#recordingArea').style.display = 'none';
        this.el.querySelector('#recordingResult').style.display = 'none';
        this._showSongSelection();

        // Clean up
        if (this._isRecording) this._stopRecording();
    }

    _skipSongAndRecord() {
        this._selectedSong = null;
        this._songSelectionDone = true;
        window.__standardPitchData = null;
        this._showRecordingArea();

        // Auto start recording
        setTimeout(() => this._startRecording(), 300);
    }

    _uploadExistingRecording() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = 'audio/*,.mp3,.wav,.flac,.ogg,.m4a';
        input.onchange = async (e) => {
            const file = e.target.files?.[0];
            if (!file) return;

            showToast('文件已选择，上传分析中...', 'info');

            try {
                const formData = new FormData();
                formData.append('file', file);
                if (this._selectedSong?.id) {
                    formData.append('reference_song_id', this._selectedSong.id);
                }

                // 模拟分析
                await new Promise(r => setTimeout(r, 2000));

                const result = {
                    total_score: 82.3,
                    level: '良好',
                    analysis_id: 'upload_' + Date.now()
                };

                if (this.store) {
                    this.store.setState({
                        status: 'complete', result, analysisId: result.analysis_id
                    }, 'analysis');
                }

                // 显示结果
                this.el.querySelector('#recordingResult').style.display = '';
                this.el.querySelector('#resultScore').textContent = result.total_score.toFixed(1);
                this.el.querySelector('#resultLevel').textContent = result.level;
                this.el.querySelector('#recordingArea').style.display = 'none';

                showToast('分析完成', 'success');

            } catch (e) {
                showToast('分析失败: ' + e.message, 'error');
            }
        };
        input.click();
    }

    // ========================================================================
    // Recording
    // ========================================================================

    async _startRecording() {
        if (this._isRecording) return;

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this._audioContext = new AudioContext();
            this._mediaRecorder = new MediaRecorder(stream);
            this._chunks = [];
            this._isRecording = true;
            this._recordingStartTime = Date.now();
            this._combo = 0;

            this._mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) this._chunks.push(e.data);
            };
            this._mediaRecorder.onstop = () => { this._isRecording = false; };
            this._mediaRecorder.start(100);

            // UI
            this.el.querySelector('#startRecordBtn').style.display = 'none';
            this.el.querySelector('#stopRecordBtn').style.display = 'flex';
            this.el.querySelector('#recordingIndicator').style.display = 'flex';

            // 脉冲
            const stopBtn = this.el.querySelector('#stopRecordBtn');
            if (typeof gsap !== 'undefined') {
                gsap.to(stopBtn, { scale: 1.1, opacity: 0.8, duration: 0.8, ease: 'power1.inOut', yoyo: true, repeat: -1 });
            }

            // 计时器
            this._timerInterval = setInterval(() => this._updateTimer(), 1000);

            // 激活评分面板
            const livePanel = this.el.querySelector('#liveScorePanel');
            if (this.ac && livePanel) {
                this.ac.enter(livePanel, { preset: 'slideUp-sm' });
            }

            this._startPitchDetection();
        } catch (err) {
            showToast('无法访问麦克风: ' + err.message, 'error');
        }
    }

    _stopRecording() {
        if (!this._isRecording) return;
        if (this._mediaRecorder && this._mediaRecorder.state !== 'inactive') {
            this._mediaRecorder.stop();
            this._mediaRecorder.stream.getTracks().forEach(t => t.stop());
        }
        this._isRecording = false;

        if (this._pitchAnalyzer) { this._pitchAnalyzer.stop(); this._pitchAnalyzer = null; }
        if (this._timerInterval) { clearInterval(this._timerInterval); this._timerInterval = null; }
        if (this._audioContext) { this._audioContext.close(); this._audioContext = null; }

        // UI
        this.el.querySelector('#startRecordBtn').style.display = 'flex';
        this.el.querySelector('#stopRecordBtn').style.display = 'none';
        this.el.querySelector('#recordingIndicator').style.display = 'none';

        const stopBtn = this.el.querySelector('#stopRecordBtn');
        if (typeof gsap !== 'undefined') {
            gsap.killTweensOf(stopBtn);
            gsap.set(stopBtn, { scale: 1, opacity: 1 });
        }

        // 重置连击
        this._combo = 0;
        const comboDisplay = this.el.querySelector('_comboDisplay');
        if (typeof gsap !== 'undefined') {
            gsap.to(comboDisplay, { scale: 0, opacity: 0, duration: 0.3, ease: 'power2.in' });
        }

        // 模拟分析结果
        this._simulateAnalysisResult();
    }

    _startPitchDetection() {
        this._pitchAnalyzer = new RealtimePitchAnalyzer({ fftSize: 2048 });
        this._pitchAnalyzer.init(this._audioContext, this._mediaRecorder.stream);
        this._pitchAnalyzer.start((result) => {
            if (!this._isRecording) return;
            const freq = result.frequency;
            const note = result.note;
            const rmsDB = 20 * Math.log10(Math.max(result.rms, 1e-10));
            this._pitchHistory.push(freq);

            const noteLabel = note ? note.fullName + ' (' + (note.cents > 0 ? '+' : '') + note.cents + '¢)' : '--';
            this.el.querySelector('#livePitch').textContent = freq > 0 ? Math.round(freq) + ' Hz — ' + noteLabel : '· · ·';
            this.el.querySelector('#liveVolume').textContent = Math.round(rmsDB) + ' dB';

            if (this._selectedSong && window.__standardPitchData) {
                // Real-time reference line is active
            }

            this._simulateHit(freq);
        });
    }

    // ========================================================================
    // Hit Feedback
    // ========================================================================

    _simulateHit(freq) {
        if (Math.random() < 0.05) {
            const types = ['perfect', 'great', 'good'];
            const weights = [0.15, 0.35, 0.5];
            const r = Math.random();
            let type = 'good';
            if (r < weights[0]) type = 'perfect';
            else if (r < weights[0] + weights[1]) type = 'great';
            this._onHit(type);
        }
    }

    _onHit(type) {
        this._combo++;
        this.el.querySelector('_comboCount').textContent = this._combo;

        const area = this.el.querySelector('#hitFeedbackArea');
        const el = document.createElement('div');
        const labels = { perfect: 'PERFECT', great: 'GREAT', good: 'GOOD' };
        el.textContent = labels[type];
        el.style.cssText = 'position:absolute;font-size:20px;font-weight:700;pointer-events:none;'
            + 'color:' + (type === 'perfect' ? '#FFD700' : type === 'great' ? '#22c55e' : '#fff') + ';'
            + 'text-shadow:0 2px 8px rgba(0,0,0,0.3);';
        area.appendChild(el);

        if (typeof gsap !== 'undefined') {
            const config = type === 'perfect' ? { scale: 1.3, ease: 'back.out(2)' }
                : type === 'great' ? { scale: 1.2, ease: 'back.out(1.5)' }
                : { scale: 1.1, ease: 'power2.out' };
            gsap.timeline()
                .fromTo(el, { scale: 0, opacity: 1, y: 0 },
                    { scale: config.scale, duration: 0.3, ease: config.ease })
                .to(el, {
                    opacity: 0, y: -30, duration: 0.5, delay: 0.4, ease: 'power2.in',
                    onComplete: () => { if (el.parentNode) el.remove(); }
                });
        }

        const comboDisplay = this.el.querySelector('_comboDisplay');
        if (typeof gsap !== 'undefined') {
            if (this._combo === 1) {
                gsap.fromTo(comboDisplay, { scale: 0, opacity: 0 }, { scale: 1.5, opacity: 1, duration: 0.3, ease: 'back.out(2)' });
            } else {
                gsap.timeline()
                    .to(comboDisplay, { scale: 1.4, duration: 0.1, ease: 'power2.out' })
                    .to(comboDisplay, { scale: 1, duration: 0.3, ease: 'elastic.out(1, 0.3)' });
            }
        }
        comboDisplay.textContent = this._combo + ' COMBO';
    }

    _simulateAnalysisResult() {
        const result = {
            total_score: 65 + Math.round(Math.random() * 30),
            level: '中等',
            analysis_id: 'rec_' + Date.now()
        };

        if (this.store) {
            this.store.setState({
                status: 'complete', result, analysisId: result.analysis_id
            }, 'analysis');
        }

        setTimeout(() => {
            const recordingArea = this.el.querySelector('#recordingArea');
            const resultArea = this.el.querySelector('#recordingResult');
            const score = this.el.querySelector('#resultScore');
            const level = this.el.querySelector('#resultLevel');

            recordingArea.style.display = 'none';
            resultArea.style.display = '';
            if (score) score.textContent = result.total_score.toFixed(1);
            if (level) level.textContent = result.level;

            showToast('录音分析完成', 'success');
        }, 800);
    }

    _updateTimer() {
        if (!this._isRecording) return;
        const elapsed = Math.floor((Date.now() - this._recordingStartTime) / 1000);
        const mins = Math.floor(elapsed / 60);
        const secs = elapsed % 60;
        this.el.querySelector('#recordTime').textContent =
            (mins.toString().padStart(2, '0')) + ':' + (secs.toString().padStart(2, '0'));
    }

    // ========================================================================
    // Reset
    // ========================================================================

    _resetForNextSong() {
        this._selectedSong = null;
        this._songSelectionDone = false;
        this._combo = 0;

        this.el.querySelector('#recordingResult').style.display = 'none';
        this.el.querySelector('#recordingArea').style.display = 'none';
        this._showSongSelection();
    }

    _triggerDirectUpload() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = 'audio/*,.mp3,.wav,.flac,.ogg,.m4a';
        input.click();
    }

    // ========================================================================
    // Animation
    // ========================================================================

    _animateIn() {
        if (this.ac) {
            const header = this.el.querySelector('.sing-header');
            const canvas = this.el.querySelector('#pitchCanvasWrap');
            if (header) this.ac.enter(header, { preset: 'page-enter-down' });
            if (canvas) this.ac.enter(canvas, { preset: 'page-enter-scale' });
        }
    }

    // ========================================================================
    // API
    // ========================================================================

    get _api() {
        return window.__api || null;
    }

    destroy() {
        if (this._isRecording) this._stopRecording();
        if (this._timerInterval) clearInterval(this._timerInterval);
        this._selector?.destroy();
        super.destroy();
    }
}

export default SingPage;
