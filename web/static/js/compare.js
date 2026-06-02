/**
 * 对比分析页面 v2.1
 * 支持上传模式和实时录音模式
 */

class ComparePage {
    constructor() {
        this.apiBase = '/api';
        this.standardAudioFile = null;
        this.userAudioFile = null;
        this.compareResult = null;
        this.standardAudioEl = document.getElementById('standardAudio');
        this.userAudioEl = document.getElementById('userAudio');
        this.isPlaying = { standard: false, user: false };
        this.currentMode = 'upload'; // 'upload' or 'realtime'
        this.realtimeCompare = null;
        // v5.10: 预提取的标准音频音高曲线
        this.standardPitchData = null;
        this.init();
    }

    init() {
        const si = document.getElementById('standardFileInput');
        const ui = document.getElementById('userFileInput');
        if (si) si.addEventListener('change', e => { if (e.target.files[0]) this.handleStandardFile(e.target.files[0]); });
        if (ui) ui.addEventListener('change', e => { if (e.target.files[0]) this.handleUserFile(e.target.files[0]); });
        if (this.standardAudioEl) {
            this.standardAudioEl.addEventListener('timeupdate', () => this.updateProgress('standard'));
            this.standardAudioEl.addEventListener('loadedmetadata', () => this.updateTotalTime('standard'));
            this.standardAudioEl.addEventListener('ended', () => this.onAudioEnded('standard'));
        }
        if (this.userAudioEl) {
            this.userAudioEl.addEventListener('timeupdate', () => this.updateProgress('user'));
            this.userAudioEl.addEventListener('loadedmetadata', () => this.updateTotalTime('user'));
            this.userAudioEl.addEventListener('ended', () => this.onAudioEnded('user'));
        }
    }

    // 切换模式
    selectMode(mode) {
        this.currentMode = mode;
        const uploadBtn = document.getElementById('uploadModeBtn');
        const realtimeBtn = document.getElementById('realtimeModeBtn');
        const analyzeBtn = document.getElementById('analyzeBtn');
        const realtimeBtnAction = document.getElementById('realtimeBtn');
        const realtimePanel = document.getElementById('realtimePanel');

        if (mode === 'upload') {
            uploadBtn?.classList.add('active');
            realtimeBtn?.classList.remove('active');
            analyzeBtn?.style.setProperty('display', 'inline-flex');
            realtimeBtnAction?.style.setProperty('display', 'none');
            realtimePanel?.style.setProperty('display', 'none');
        } else {
            uploadBtn?.classList.remove('active');
            realtimeBtn?.classList.add('active');
            analyzeBtn?.style.setProperty('display', 'none');
            realtimeBtnAction?.style.setProperty('display', 'inline-flex');
            realtimePanel?.style.setProperty('display', 'none');
        }
        this.checkReadyState();
    }

    async handleStandardFile(f) {
        this.standardAudioFile = f;
        document.getElementById('standardCard').classList.add('has-file');
        document.getElementById('standardFileName').textContent = f.name;
        this.standardAudioEl.src = URL.createObjectURL(f);
        this.checkReadyState();
        document.getElementById('tipBanner').classList.remove('show');

        // v5.10: 预提取标准音频的音高曲线
        try {
            const fd = new FormData();
            fd.append('file', f);
            const res = await fetch(this.apiBase + '/extract-pitch', { method: 'POST', body: fd });
            const r = await res.json();
            if (r.success && r.data) {
                this.standardPitchData = r.data;
                const sdEl = document.getElementById('standardDuration');
                if (sdEl) sdEl.textContent = '时长: ' + this.fmt(r.data.duration);
                console.log('[Compare] 音高曲线已提取: ' + r.data.frame_count + ' 帧, ' + r.data.duration.toFixed(1) + 's');
            }
        } catch (e) {
            console.warn('[Compare] 音高曲线提取失败:', e);
            // 非致命错误，实时模式将不可用但上传模式仍可工作
        }
    }

    handleUserFile(f) {
        this.userAudioFile = f;
        document.getElementById('userCard').classList.add('has-file');
        document.getElementById('userFileName').textContent = f.name;
        this.userAudioEl.src = URL.createObjectURL(f);
        if (!this.standardAudioFile) this.showTip('建议先导入标准音频作为评估基准');
        this.checkReadyState();
    }

    checkReadyState() {
        if (this.currentMode === 'upload') {
            document.getElementById('analyzeBtn').disabled = !this.userAudioFile;
        } else {
            document.getElementById('realtimeBtn').disabled = !this.standardAudioFile;
        }
    }

    showTip(m) {
        const b = document.getElementById('tipBanner'), t = document.getElementById('tipText');
        if (b && t) { t.textContent = m; b.classList.add('show'); }
    }

    togglePlay(type) {
        const a = type === 'standard' ? this.standardAudioEl : this.userAudioEl;
        const b = document.getElementById(type + 'PlayBtn');
        if (!a) return;
        if (this.isPlaying[type]) { a.pause(); this.isPlaying[type] = false; b.textContent = '▶'; b.classList.remove('playing'); }
        else { a.play(); this.isPlaying[type] = true; b.textContent = '⏸'; b.classList.add('playing'); }
    }

    onAudioEnded(type) {
        this.isPlaying[type] = false;
        const b = document.getElementById(type + 'PlayBtn');
        if (b) { b.textContent = '▶'; b.classList.remove('playing'); }
    }

    updateProgress(type) {
        const a = type === 'standard' ? this.standardAudioEl : this.userAudioEl;
        if (!a) return;
        document.getElementById(type + 'ProgressFill').style.width = (a.currentTime / a.duration * 100) + '%';
        document.getElementById(type + 'CurrentTime').textContent = this.fmt(a.currentTime);
    }

    updateTotalTime(type) {
        const a = type === 'standard' ? this.standardAudioEl : this.userAudioEl;
        if (!a) return;
        document.getElementById(type + 'TotalTime').textContent = this.fmt(a.duration);
        document.getElementById(type + 'Duration').textContent = '时长: ' + this.fmt(a.duration);
    }

    seekAudio(type, e) {
        const a = type === 'standard' ? this.standardAudioEl : this.userAudioEl;
        if (!a || !a.duration) return;
        const r = e.currentTarget.getBoundingClientRect();
        a.currentTime = ((e.clientX - r.left) / r.width) * a.duration;
    }

    fmt(s) { return !s || isNaN(s) ? '00:00' : Math.floor(s/60).toString().padStart(2,'0') + ':' + Math.floor(s%60).toString().padStart(2,'0'); }

    // Normalize dimensions data - compatible with both old and new API formats
    normalizeDimensions(dimensions) {
        const result = {};
        if (!dimensions) return result;
        for (const [key, value] of Object.entries(dimensions)) {
            // New API format: dimensions.pitch = {score: 100, avg_deviation: 0}
            if (typeof value === 'object' && value !== null && 'score' in value) {
                result[key] = value.score;
            } else {
                // Old API format: dimensions.pitch = 100
                result[key] = typeof value === 'number' ? value : 0;
            }
        }
        return result;
    }

    async startAnalysis() {
        if (!this.userAudioFile) return;
        const btn = document.getElementById('analyzeBtn');
        btn.classList.add('loading'); btn.disabled = true;
        try {
            const fd = new FormData();
            fd.append('file', this.userAudioFile);
            if (this.standardAudioFile) {
                fd.append('standard_file', this.standardAudioFile);
                const res = await fetch(this.apiBase + '/compare', { method: 'POST', body: fd });
                const r = await res.json();
                if (!r.success) throw new Error(r.error);
                // Normalize dimensions data for compatibility
                const normalizedDims = this.normalizeDimensions(r.data.dimensions);
                this.compareResult = {
                    score: r.data.score,
                    level: r.data.level,
                    confidence: r.data.confidence,
                    pitch_match_rate: r.data.pitch_match_rate,
                    rhythm_match_rate: r.data.rhythm_match_rate,
                    avg_cents_error: r.data.avg_cents_error,
                    dimensions: normalizedDims,
                    diagnosis: r.data.diagnosis || [],
                    suggestions: r.data.suggestions || [],
                    method: r.data.method
                };
            } else {
                fd.append('mode', 'quick');
                const res = await fetch(this.apiBase + '/upload', { method: 'POST', body: fd });
                const r = await res.json();
                if (!r.success) throw new Error(r.error || '分析失败');
                // API response is flat structure, no data wrapper
                this.compareResult = {
                    score: r.total_score || r.score || 0,
                    level: r.level || '评估完成',
                    dimensions: r.scores || {},
                    suggestions: r.advice || []
                };
            }
            this.showResult();
        } catch (e) {
            console.error('分析失败:', e);
            alert('分析失败，请检查音频格式或稍后重试');
        }
        finally { btn.classList.remove('loading'); btn.disabled = false; }
    }

    // 实时录音对比
    async startRealtimeCompare() {
        if (!this.standardAudioFile) {
            alert('请先导入标准音频');
            return;
        }

        // v5.10: 检查音高曲线是否已提取
        if (!this.standardPitchData || !this.standardPitchData.frequencies || this.standardPitchData.frequencies.length === 0) {
            try {
                const fd = new FormData();
                fd.append('file', this.standardAudioFile);
                const res = await fetch(this.apiBase + '/extract-pitch', { method: 'POST', body: fd });
                const r = await res.json();
                if (r.success && r.data) {
                    this.standardPitchData = r.data;
                } else {
                    alert('音高曲线提取失败，请重试');
                    return;
                }
            } catch (e) {
                alert('音高曲线提取失败: ' + e.message);
                return;
            }
        }

        try {
            // 动态加载实时对比模块
            if (!this.realtimeCompare) {
                const module = await import('/js/modules/realtime-compare.js');
                this.realtimeCompare = new module.RealtimeCompare({
                    pitch_curve: this.standardPitchData,
                    duration: this.standardPitchData.duration
                });
            } else {
                // 更新已有实例的数据
                this.realtimeCompare.standardFrequencies = this.standardPitchData.frequencies || [];
                this.realtimeCompare.standardDuration = this.standardPitchData.duration || 0;
                this.realtimeCompare.standardPitchCurve = this.standardPitchData;
            }

            // 显示实时面板
            document.getElementById('realtimePanel').style.display = 'flex';
            document.getElementById('realtimeBtn').disabled = true;

            // 设置歌名
            const songNameEl = document.getElementById('ktvSongName');
            if (songNameEl) {
                songNameEl.textContent = this.standardAudioFile.name.replace(/\.[^.]+$/, '');
            }

            // 初始化
            await this.realtimeCompare.init(
                this.standardAudioEl,
                URL.createObjectURL(this.standardAudioFile)
            );

            // 设置回调
            this.realtimeCompare.setCallbacks(
                (deviation) => this.updateDeviationUI(deviation),
                (score, combo) => this.updateRealtimeScore(score, combo),
                (result) => this.handleRealtimeComplete(result)
            );

            // KTV 风格命中反馈
            this.realtimeCompare.onHitFeedback = (type, combo) => {
                this.showHitFeedback(type, combo);
            };

            // 初始化音高对比 Canvas
            const canvas = document.getElementById('pitchCompareCanvas');
            if (canvas) {
                this.realtimeCompare.initPitchCanvas(canvas);
            }

            // 开始
            await this.realtimeCompare.start();

        } catch (e) {
            console.error('实时录音失败:', e);
            let errorMsg = '实时录音启动失败';
            if (e.name === 'NotAllowedError' || e.name === 'PermissionDeniedError') {
                errorMsg = '麦克风权限被拒绝，请在浏览器设置中允许访问麦克风';
            } else if (e.name === 'NotFoundError') {
                errorMsg = '未检测到麦克风设备，请连接麦克风后重试';
            } else if (e.name === 'NotReadableError') {
                errorMsg = '麦克风被其他应用占用，请关闭其他应用后重试';
            } else if (e.message) {
                errorMsg = e.message;
            }
            alert(errorMsg);
            const rp = document.getElementById('realtimePanel');
            if (rp) rp.style.display = 'none';
            document.getElementById('realtimeBtn').disabled = false;
        }
    }

    updateDeviationUI(deviation) {
        const valueEl = document.getElementById('deviationValue');
        const hintEl = document.getElementById('deviationHint');
        const curNoteEl = document.getElementById('currentUserNote');
        const tgtNoteEl = document.getElementById('targetNote');
        const hitDot = document.getElementById('hitLevelDot');

        if (valueEl) {
            const cents = deviation.cents;
            valueEl.textContent = (cents > 0 ? '+' : '') + cents + ' 音分';
            valueEl.className = 'deviation-value' + (Math.abs(cents) > 20 ? (cents > 0 ? ' positive' : ' negative') : '');
        }

        if (hintEl) hintEl.textContent = deviation.hint || '保持稳定';
        if (curNoteEl && deviation.userNote) curNoteEl.textContent = deviation.userNote.fullName || '--';
        if (tgtNoteEl && deviation.targetNote) tgtNoteEl.textContent = deviation.targetNote;

        // 命中等级颜色点
        if (hitDot && deviation.hitLevel) {
            const colors = { perfect: '#ffd700', great: '#54a0ff', good: '#10b981', miss: '#666' };
            hitDot.style.backgroundColor = colors[deviation.hitLevel] || '#666';
        }
    }

    updateRealtimeScore(score, combo) {
        const scoreEl = document.getElementById('realtimeScore');
        const comboEl = document.getElementById('realtimeCombo');
        if (scoreEl) scoreEl.textContent = score;
        if (comboEl) {
            comboEl.textContent = (combo || 0) > 1 ? combo + ' COMBO' : '';
            comboEl.style.display = (combo || 0) > 1 ? 'block' : 'none';
        }
    }

    showHitFeedback(type, combo) {
        const fbEl = document.getElementById('hitFeedback');
        if (!fbEl) return;

        const labels = { perfect: 'PERFECT!', great: 'GREAT', good: 'GOOD' };
        const text = labels[type] || '';

        fbEl.textContent = text;
        fbEl.className = 'hit-feedback ' + type + ' show';

        clearTimeout(this._hitFeedbackTimer);
        this._hitFeedbackTimer = setTimeout(() => {
            fbEl.classList.remove('show');
        }, 600);
    }

    async stopRealtimeCompare() {
        if (this.realtimeCompare && this.realtimeCompare.isRecording) {
            const result = await this.realtimeCompare.stop();
            this.handleRealtimeComplete(result);
        }
    }

    handleRealtimeComplete(result) {
        document.getElementById('realtimePanel').style.display = 'none';
        document.getElementById('realtimeBtn').disabled = false;

        if (result && result.score !== undefined) {
            this.compareResult = {
                score: result.score,
                level: result.level,
                pitch_match_rate: result.pitchMatchRate,
                avg_cents_error: result.avgCentsError,
                diagnosis: result.diagnosis || [],
                suggestions: [],
                hitCounts: result.hitCounts || {},
                maxCombo: result.maxCombo || 0
            };
            this.showResult();
        }
    }

    showResult() {
        document.getElementById('resultPanel').classList.add('active');
        document.getElementById('resultScore').textContent = this.compareResult?.score || '--';
        document.getElementById('resultLevel').textContent = this.compareResult?.level || '评估完成';

        // KTV 统计
        const statsEl = document.getElementById('hitStats');
        if (statsEl && this.compareResult?.hitCounts) {
            const h = this.compareResult.hitCounts;
            statsEl.innerHTML =
                `<span class="hit-stat perfect">PERFECT ${h.perfect||0}</span>` +
                `<span class="hit-stat great">GREAT ${h.great||0}</span>` +
                `<span class="hit-stat good">GOOD ${h.good||0}</span>` +
                `<span class="hit-stat miss">MISS ${h.miss||0}</span>` +
                (this.compareResult.maxCombo > 0 ? `<span class="hit-stat combo">MAX COMBO ${this.compareResult.maxCombo}</span>` : '');
            statsEl.style.display = 'flex';
        } else if (statsEl) {
            statsEl.style.display = 'none';
        }

        this.renderDimensions();
        this.renderSuggestions();
    }

    renderDimensions() {
        const c = document.getElementById('dimensionCompare');
        if (!c || !this.compareResult) return;
        const d = this.compareResult.dimensions || {};
        const n = { pitch: '音准', rhythm: '节奏', breath: '气息', technique: '技巧', emotion: '情感' };
        c.innerHTML = Object.keys(n).map(k => {
            const v = d[k] || 0, sv = this.compareResult.standardDimensions?.[k] || 100, df = v - sv;
            return '<div class="dimension-item"><div class="dimension-header"><span class="dimension-name">' + n[k] + '</span>' +
                '<div class="dimension-scores">' + (this.standardAudioFile ? '<span class="standard-score">标准: ' + sv + '</span>' : '') +
                '<span class="user-score">得分: ' + v + '</span>' + (this.standardAudioFile ? '<span class="diff">差距: ' + (df>0?'+':'') + df + '</span>' : '') + '</div></div>' +
                '<div class="dimension-bars">' + (this.standardAudioFile ? '<div class="dimension-bar-wrap"><div class="dimension-bar standard" style="width:' + sv + '%"></div></div>' : '') +
                '<div class="dimension-bar-wrap"><div class="dimension-bar user" style="width:' + v + '%"></div></div></div></div>';
        }).join('');
    }

    renderSuggestions() {
        const c = document.getElementById('suggestionList');
        if (!c || !this.compareResult) return;
        const s = this.compareResult.suggestions || [];
        c.innerHTML = s.length ? s.map(x => '<div class="suggestion-item"><div class="suggestion-title">' + (x.title||x.dimension||'建议') + '</div><div class="suggestion-text">' + (x.content||x.text||'') + '</div></div>').join('') : '<div class="suggestion-item good"><div class="suggestion-title">整体表现良好</div><div class="suggestion-text">继续保持</div></div>';
    }

    resetAll() {
        // 释放 ObjectURL 防止内存泄漏
        if (this.standardAudioEl?.src?.startsWith('blob:')) {
            URL.revokeObjectURL(this.standardAudioEl.src);
        }
        if (this.userAudioEl?.src?.startsWith('blob:')) {
            URL.revokeObjectURL(this.userAudioEl.src);
        }
        if (this.standardAudioEl) this.standardAudioEl.pause();
        if (this.userAudioEl) this.userAudioEl.pause();
        this.standardAudioFile = null;
        this.userAudioFile = null;
        this.compareResult = null;
        this.isPlaying = { standard: false, user: false };
        ['standardCard','userCard'].forEach(i => document.getElementById(i)?.classList.remove('has-file'));
        ['standardFileName','userFileName'].forEach(i => document.getElementById(i).textContent = '-');
        ['standardProgressFill','userProgressFill'].forEach(i => document.getElementById(i).style.width = '0%');
        ['standardPlayBtn','userPlayBtn'].forEach(i => { const b=document.getElementById(i); if(b){b.textContent='▶';b.classList.remove('playing');} });
        document.getElementById('resultPanel')?.classList.remove('active');
        document.getElementById('tipBanner')?.classList.remove('show');
        document.getElementById('analyzeBtn').disabled = true;
        this.selectMode('upload');
    }
}

let comparePage;
document.addEventListener('DOMContentLoaded', () => comparePage = new ComparePage());
window.selectStandardFile = () => document.getElementById('standardFileInput')?.click();
window.selectUserFile = () => document.getElementById('userFileInput')?.click();
window.togglePlay = t => comparePage?.togglePlay(t);
window.seekAudio = (t,e) => comparePage?.seekAudio(t,e);
window.startAnalysis = () => comparePage?.startAnalysis();
window.resetAll = () => comparePage?.resetAll();
window.selectMode = m => comparePage?.selectMode(m);
window.startRealtimeCompare = () => comparePage?.startRealtimeCompare();
window.stopRealtimeCompare = () => comparePage?.stopRealtimeCompare();