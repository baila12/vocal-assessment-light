/**
 * 实时录音对比模块 v5.11 — 全民K歌风格
 *
 * 功能：
 * 1. 滚动式音高条可视化 (piano roll 风格)
 * 2. 标准音高音符块 + 用户音高轨迹叠加
 * 3. 音符命中判定 (Perfect/Great/Good/Miss)
 * 4. 连击计数器 + 分数动画
 * 5. 音分偏差实时仪表
 */

import { PitchDetector, RealtimePitchAnalyzer } from './pitch-detector.js';

// 命中等级阈值 (音分) — 经验值
const HIT = { PERFECT: 15, GREAT: 35, GOOD: 60 };

// Canvas roundRect polyfill
if (!CanvasRenderingContext2D.prototype.roundRect) {
    CanvasRenderingContext2D.prototype.roundRect = function(x, y, w, h, r) {
        if (typeof r === 'number') r = { tl: r, tr: r, br: r, bl: r };
        this.beginPath();
        this.moveTo(x + r.tl, y);
        this.lineTo(x + w - r.tr, y);
        this.quadraticCurveTo(x + w, y, x + w, y + r.tr);
        this.lineTo(x + w, y + h - r.br);
        this.quadraticCurveTo(x + w, y + h, x + w - r.br, y + h);
        this.lineTo(x + r.bl, y + h);
        this.quadraticCurveTo(x, y + h, x, y + h - r.bl);
        this.lineTo(x, y + r.tl);
        this.quadraticCurveTo(x, y, x + r.tl, y);
        this.closePath();
    };
}

export class RealtimeCompare {
    constructor(standardAudioData = {}) {
        const pitchCurve = standardAudioData.pitch_curve || standardAudioData;
        this.standardPitchCurve = pitchCurve;
        this.standardFrequencies = pitchCurve.frequencies || [];
        this.standardTimes = pitchCurve.times || [];
        this.standardFrameCount = pitchCurve.frame_count || 0;
        this.standardDuration = standardAudioData.duration || pitchCurve.duration || 0;

        // 预计算的音符段 [{startIdx, endIdx, midi, noteName, startTime, endTime}]
        this.noteSegments = [];
        this._buildNoteSegments();

        // 音频
        this.standardAudioElement = null;
        this.audioContext = null;

        // 录音
        this.mediaRecorder = null;
        this.recordChunks = [];
        this.recordStream = null;

        // 音高
        this.pitchAnalyzer = null;
        this.pitchDetector = null;

        // Canvas
        this.pitchCanvas = null;
        this.pitchCanvasCtx = null;
        this.canvasDrawInterval = null;

        // 状态
        this.isRecording = false;
        this.startTime = 0;
        this.userPitches = [];
        this.latencyCompensationMs = 80;

        // 全民K歌风格: 命中/连击系统
        this.combo = 0;
        this.maxCombo = 0;
        this.hitCounts = { perfect: 0, great: 0, good: 0, miss: 0 };
        this.currentNoteIdx = -1;        // 当前活跃音符索引
        this.notePitchBuffer = [];       // 当前音符的音高采样缓冲
        this.lastHitFeedback = null;     // {type, time} 最近的命中反馈
        this.currentScore = 0;

        // 回调
        this.onDeviationUpdate = null;
        this.onScoreUpdate = null;
        this.onHitFeedback = null;       // (type, combo) => {}
        this.onComplete = null;
    }

    // ==================== 音符段构建 ====================

    _buildNoteSegments() {
        if (!this.standardFrequencies || this.standardFrequencies.length < 10) return;

        const freqs = this.standardFrequencies;
        const times = this.standardTimes;
        let segStart = -1;
        let lastMidi = -1;
        const MIN_NOTE_FRAMES = 3; // 最小音符帧数,过滤噪声

        for (let i = 0; i < freqs.length; i++) {
            const f = freqs[i];
            const isVoiced = f > 50 && f < 1000;
            const midi = isVoiced ? Math.round(69 + 12 * Math.log2(f / 440)) : -1;

            if (isVoiced && segStart === -1) {
                segStart = i;
                lastMidi = midi;
            } else if (isVoiced && midi !== lastMidi) {
                // 音符变化
                if (i - segStart >= MIN_NOTE_FRAMES) {
                    this.noteSegments.push({
                        startIdx: segStart,
                        endIdx: i,
                        midi: lastMidi,
                        noteName: this._midiToName(lastMidi),
                        startTime: times.length > 0 ? times[segStart] : (segStart / freqs.length * this.standardDuration),
                        endTime: times.length > 0 ? times[i] : (i / freqs.length * this.standardDuration)
                    });
                }
                segStart = i;
                lastMidi = midi;
            } else if (!isVoiced && segStart !== -1) {
                if (i - segStart >= MIN_NOTE_FRAMES) {
                    this.noteSegments.push({
                        startIdx: segStart,
                        endIdx: i,
                        midi: lastMidi,
                        noteName: this._midiToName(lastMidi),
                        startTime: times.length > 0 ? times[segStart] : (segStart / freqs.length * this.standardDuration),
                        endTime: times.length > 0 ? times[i] : (i / freqs.length * this.standardDuration)
                    });
                }
                segStart = -1;
            }
        }
        // 末尾段
        if (segStart !== -1 && freqs.length - segStart >= MIN_NOTE_FRAMES) {
            this.noteSegments.push({
                startIdx: segStart,
                endIdx: freqs.length - 1,
                midi: lastMidi,
                noteName: this._midiToName(lastMidi),
                startTime: times.length > 0 ? times[segStart] : (segStart / freqs.length * this.standardDuration),
                endTime: times.length > 0 ? times[times.length - 1] : this.standardDuration
            });
        }
    }

    _midiToName(midi) {
        const names = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
        return names[midi % 12] + Math.floor(midi / 12 - 1);
    }

    // ==================== 初始化 ====================

    async init(audioElement, standardUrl) {
        this.standardAudioElement = audioElement;
        this.standardAudioElement.src = standardUrl;
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        this.pitchDetector = new PitchDetector(this.audioContext);

        await new Promise((resolve, reject) => {
            this.standardAudioElement.addEventListener('loadedmetadata', resolve, { once: true });
            this.standardAudioElement.addEventListener('error', reject, { once: true });
            if (this.standardAudioElement.readyState >= 1) resolve();
        });

        if (this.standardAudioElement.duration && isFinite(this.standardAudioElement.duration)) {
            this.standardDuration = this.standardAudioElement.duration;
        }
    }

    initPitchCanvas(canvas) {
        this.pitchCanvas = canvas;
        this.pitchCanvasCtx = canvas.getContext('2d');
        // 设置高DPI
        const dpr = window.devicePixelRatio || 1;
        const rect = canvas.getBoundingClientRect();
        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
        this.pitchCanvasCtx.scale(dpr, dpr);
        this._canvasW = rect.width;
        this._canvasH = rect.height;
    }

    // ==================== 开始/停止 ====================

    async start() {
        const isLocalhost = location.hostname === 'localhost' || location.hostname === '127.0.0.1' || location.hostname === '[::1]';
        if (!(window.isSecureContext || isLocalhost)) {
            throw new Error('实时录音需要 HTTPS 或 localhost 环境');
        }
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            throw new Error('浏览器不支持录音功能');
        }

        this.recordStream = await navigator.mediaDevices.getUserMedia({
            audio: { echoCancellation: false, noiseSuppression: true, autoGainControl: true }
        });

        let mimeType = '';
        for (const mt of ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4']) {
            if (MediaRecorder.isTypeSupported(mt)) { mimeType = mt; break; }
        }
        this.mediaRecorder = new MediaRecorder(this.recordStream, mimeType ? { mimeType } : {});
        this.mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) this.recordChunks.push(e.data); };

        this.pitchAnalyzer = new RealtimePitchAnalyzer({ fftSize: 2048 });
        await this.pitchAnalyzer.init(this.audioContext, this.recordStream);

        this.mediaRecorder.start(100);
        this.isRecording = true;
        this.startTime = this.audioContext.currentTime;
        this.userPitches = [];
        this.combo = 0;
        this.maxCombo = 0;
        this.hitCounts = { perfect: 0, great: 0, good: 0, miss: 0 };
        this.currentNoteIdx = -1;
        this.notePitchBuffer = [];
        this.currentScore = 0;
        this.lastHitFeedback = null;

        if (this.audioContext.state === 'suspended') await this.audioContext.resume();
        this.standardAudioElement.play();

        this.pitchAnalyzer.start((info) => this.handlePitchDetected(info));
        this.startProgressUpdate();
        if (this.pitchCanvas) this.startCanvasDraw();
    }

    async stop() {
        if (!this.isRecording) return;
        this.isRecording = false;

        if (this.pitchAnalyzer) this.pitchAnalyzer.stop();
        if (this.canvasDrawInterval) { cancelAnimationFrame(this.canvasDrawInterval); this.canvasDrawInterval = null; }
        if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') this.mediaRecorder.stop();
        if (this.standardAudioElement) this.standardAudioElement.pause();
        if (this.recordStream) this.recordStream.getTracks().forEach(t => t.stop());

        // 处理最后音符
        this._finalizeCurrentNote();

        await new Promise((resolve) => {
            if (this.mediaRecorder) this.mediaRecorder.addEventListener('stop', resolve, { once: true });
            else resolve();
        });

        this.drawFinalPitchCurve();
        const result = this.calculateFinalResult();
        if (this.onComplete) this.onComplete(result);
        return result;
    }

    // ==================== 音高检测处理 ====================

    handlePitchDetected(pitchInfo) {
        if (!this.isRecording) return;

        const currentTime = Math.max(0, this.standardAudioElement.currentTime - this.latencyCompensationMs / 1000);
        const userFreq = pitchInfo.frequency;
        const standardResult = this.getStandardFreqAtTime(currentTime);
        const standardFreq = standardResult ? standardResult.frequency : null;

        if (standardFreq && standardFreq > 50 && userFreq > 50) {
            const centsDiff = this.pitchDetector.calculateCentsDiff(standardFreq, userFreq);
            if (centsDiff === null) return;

            const absCents = Math.abs(centsDiff);

            this.userPitches.push({
                time: currentTime, frequency: userFreq,
                standardFreq, centsDiff, absCents
            });

            // 音符命中判定
            this._processNoteHit(currentTime, absCents, centsDiff);

            // 实时得分
            this.currentScore = this._calcRunningScore();
            if (this.onScoreUpdate) this.onScoreUpdate(this.currentScore, this.combo);

            // 偏差 UI
            if (this.onDeviationUpdate) {
                this.onDeviationUpdate({
                    cents: Math.round(centsDiff),
                    userFreq,
                    standardFreq,
                    hint: this.pitchDetector.getCentsHint(centsDiff),
                    userNote: pitchInfo.note,
                    targetNote: standardResult.noteName || null,
                    hitLevel: absCents <= HIT.PERFECT ? 'perfect' : absCents <= HIT.GREAT ? 'great' : absCents <= HIT.GOOD ? 'good' : 'miss'
                });
            }
        }
    }

    _processNoteHit(time, absCents, centsDiff) {
        // 找到当前时间对应的音符
        let activeSeg = null;
        for (let i = 0; i < this.noteSegments.length; i++) {
            const s = this.noteSegments[i];
            if (time >= s.startTime && time <= s.endTime) {
                activeSeg = s;
                if (this.currentNoteIdx !== i) {
                    // 切换到新音符,完成前一个
                    this._finalizeCurrentNote();
                    this.currentNoteIdx = i;
                    this.notePitchBuffer = [];
                }
                break;
            }
        }

        if (!activeSeg) {
            if (this.currentNoteIdx >= 0) {
                this._finalizeCurrentNote();
                this.currentNoteIdx = -1;
            }
            return;
        }

        this.notePitchBuffer.push({ time, absCents, centsDiff });
    }

    _finalizeCurrentNote() {
        if (this.currentNoteIdx < 0 || this.notePitchBuffer.length === 0) return;

        const avgCents = this.notePitchBuffer.reduce((s, p) => s + p.absCents, 0) / this.notePitchBuffer.length;
        let type;
        if (avgCents <= HIT.PERFECT) type = 'perfect';
        else if (avgCents <= HIT.GREAT) type = 'great';
        else if (avgCents <= HIT.GOOD) type = 'good';
        else type = 'miss';

        if (type === 'miss') {
            this.combo = 0;
        } else {
            this.combo++;
            if (this.combo > this.maxCombo) this.maxCombo = this.combo;
        }
        this.hitCounts[type]++;

        this.lastHitFeedback = { type, time: performance.now(), combo: this.combo };
        if (this.onHitFeedback) this.onHitFeedback(type, this.combo);
    }

    _calcRunningScore() {
        const total = this.hitCounts.perfect + this.hitCounts.great + this.hitCounts.good + this.hitCounts.miss;
        if (total === 0) return 0;
        const weighted = this.hitCounts.perfect * 100 + this.hitCounts.great * 80 + this.hitCounts.good * 60;
        return Math.round(weighted / total);
    }

    // ==================== 标准音高查找 ====================

    getStandardFreqAtTime(time) {
        if (!this.standardFrequencies || this.standardFrequencies.length === 0) return null;

        if (this.standardTimes && this.standardTimes.length > 0) {
            let lo = 0, hi = this.standardTimes.length - 1;
            while (lo < hi) { const mid = (lo + hi) >> 1; if (this.standardTimes[mid] < time) lo = mid + 1; else hi = mid; }
            const idx = Math.max(0, lo - 1);
            if (idx < this.standardFrequencies.length) {
                const freq = this.standardFrequencies[idx];
                const noteName = freq > 50 && this.pitchDetector ? this.pitchDetector.frequencyToNote(freq) : null;
                return { frequency: freq, noteName: noteName ? noteName.fullName : null };
            }
            return null;
        }

        const index = Math.floor((time / this.standardDuration) * this.standardFrequencies.length);
        if (index >= 0 && index < this.standardFrequencies.length) {
            const freq = this.standardFrequencies[index];
            const noteName = freq > 50 && this.pitchDetector ? this.pitchDetector.frequencyToNote(freq) : null;
            return { frequency: freq, noteName: noteName ? noteName.fullName : null };
        }
        return null;
    }

    // ==================== KTV 风格 Canvas 绘制 ====================

    startCanvasDraw() {
        if (!this.pitchCanvasCtx || !this._canvasW) return;

        // 音符颜色映射
        const MIDI_COLORS = [
            '#ff6b6b','#ff9f43','#feca57','#54a0ff','#5f27cd',
            '#ff6b6b','#ff9f43','#feca57','#54a0ff','#5f27cd',
            '#ff6b6b','#ff9f43'
        ];

        const draw = () => {
            if (!this.isRecording) return;
            this.canvasDrawInterval = requestAnimationFrame(draw);

            const ctx = this.pitchCanvasCtx;
            const w = this._canvasW;
            const h = this._canvasH;
            const dpr = window.devicePixelRatio || 1;

            // 清除时恢复 dpr scale
            ctx.save();
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
            ctx.clearRect(0, 0, w, h);

            const currentTime = this.standardAudioElement ? this.standardAudioElement.currentTime : 0;
            const progress = this.standardDuration > 0 ? currentTime / this.standardDuration : 0;

            // 可见时间窗口: 前后各2.5秒, 当前位置居中偏左
            const VISIBLE_SEC = 5.0;
            const viewStart = Math.max(0, currentTime - 1.5);
            const viewEnd = Math.min(this.standardDuration, currentTime + VISIBLE_SEC - 1.5);
            const viewRange = viewEnd - viewStart || 1;

            // 时间→X坐标
            const timeToX = (t) => ((t - viewStart) / viewRange) * w * 0.9 + w * 0.05;

            // 音符MIDI范围
            let minMidi = 60, maxMidi = 72;
            for (const s of this.noteSegments) {
                if (s.endTime >= viewStart && s.startTime <= viewEnd) {
                    if (s.midi < minMidi) minMidi = s.midi;
                    if (s.midi > maxMidi) maxMidi = s.midi;
                }
            }
            if (maxMidi - minMidi < 4) { minMidi -= 2; maxMidi += 2; }
            const midiToY = (m) => h * 0.9 - ((m - minMidi) / (maxMidi - minMidi)) * h * 0.75;

            // --- 背景网格 ---
            ctx.fillStyle = '#0d1117';
            ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = 'rgba(255,255,255,0.04)';
            ctx.lineWidth = 1;
            for (let m = minMidi; m <= maxMidi; m++) {
                const y = midiToY(m);
                ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
            }

            // --- 标准音符块 ---
            for (const seg of this.noteSegments) {
                if (seg.endTime < viewStart || seg.startTime > viewEnd) continue;
                const sx = timeToX(Math.max(viewStart, seg.startTime));
                const ex = timeToX(Math.min(viewEnd, seg.endTime));
                const y = midiToY(seg.midi);
                const noteH = h * 0.75 / (maxMidi - minMidi) * 0.7;

                const color = MIDI_COLORS[seg.midi % MIDI_COLORS.length];

                // 音符块
                ctx.fillStyle = color;
                ctx.globalAlpha = 0.25;
                ctx.beginPath();
                ctx.roundRect(sx, y - noteH / 2, Math.max(1, ex - sx), noteH, 3);
                ctx.fill();

                // 边框
                ctx.strokeStyle = color;
                ctx.globalAlpha = 0.5;
                ctx.lineWidth = 1.5;
                ctx.stroke();
                ctx.globalAlpha = 1;

                // 音名标签
                ctx.fillStyle = color;
                ctx.globalAlpha = 0.7;
                ctx.font = '10px monospace';
                ctx.fillText(seg.noteName, sx + 2, y - noteH / 2 - 2);
                ctx.globalAlpha = 1;
            }

            // --- 用户音高轨迹 ---
            const recentPitches = this.userPitches.filter(p => p.time >= viewStart - 0.5 && p.time <= viewEnd);
            if (recentPitches.length > 1) {
                ctx.strokeStyle = '#ffffff';
                ctx.lineWidth = 2.5;
                ctx.shadowColor = 'rgba(59, 130, 246, 0.6)';
                ctx.shadowBlur = 6;
                ctx.beginPath();
                let startedTrail = false;
                for (let i = 0; i < recentPitches.length; i++) {
                    const p = recentPitches[i];
                    if (p.frequency < 50) { startedTrail = false; continue; }
                    const x = timeToX(p.time);
                    const midi = 69 + 12 * Math.log2(p.frequency / 440);
                    const y = midiToY(Math.max(minMidi, Math.min(maxMidi, midi)));
                    if (!startedTrail) { ctx.moveTo(x, y); startedTrail = true; }
                    else ctx.lineTo(x, y);
                }
                ctx.stroke();
                ctx.shadowBlur = 0;

                // 用户音高点(当前)
                const lastP = recentPitches[recentPitches.length - 1];
                if (lastP.frequency > 50) {
                    const lx = timeToX(lastP.time);
                    const lmidi = 69 + 12 * Math.log2(lastP.frequency / 440);
                    const ly = midiToY(Math.max(minMidi, Math.min(maxMidi, lmidi)));

                    // 光晕
                    const grad = ctx.createRadialGradient(lx, ly, 0, lx, ly, 8);
                    grad.addColorStop(0, 'rgba(255,255,255,0.9)');
                    grad.addColorStop(0.5, 'rgba(59,130,246,0.4)');
                    grad.addColorStop(1, 'rgba(59,130,246,0)');
                    ctx.fillStyle = grad;
                    ctx.beginPath(); ctx.arc(lx, ly, 8, 0, Math.PI * 2); ctx.fill();
                }
            }

            // --- 当前位置线 ---
            const cx = timeToX(currentTime);
            ctx.strokeStyle = 'rgba(255,255,255,0.5)';
            ctx.lineWidth = 1;
            ctx.setLineDash([4, 6]);
            ctx.beginPath(); ctx.moveTo(cx, 0); ctx.lineTo(cx, h); ctx.stroke();
            ctx.setLineDash([]);

            // --- 命中反馈动画 ---
            if (this.lastHitFeedback) {
                const elapsed = performance.now() - this.lastHitFeedback.time;
                if (elapsed < 800) {
                    const alpha = 1 - elapsed / 800;
                    const scale = 1 + (1 - alpha) * 0.3;
                    const text = this.lastHitFeedback.type === 'perfect' ? 'PERFECT!' :
                                 this.lastHitFeedback.type === 'great' ? 'GREAT' :
                                 this.lastHitFeedback.type === 'good' ? 'GOOD' : '';
                    if (text) {
                        ctx.save();
                        ctx.translate(cx, h * 0.3);
                        ctx.scale(scale, scale);
                        ctx.font = 'bold 24px sans-serif';
                        ctx.textAlign = 'center';
                        ctx.fillStyle = this.lastHitFeedback.type === 'perfect' ? '#ffd700' :
                                       this.lastHitFeedback.type === 'great' ? '#54a0ff' : '#10b981';
                        ctx.globalAlpha = alpha;
                        ctx.fillText(text, 0, 0);
                        ctx.globalAlpha = 1;
                        ctx.restore();

                        // COMBO
                        if (this.lastHitFeedback.combo > 1) {
                            ctx.font = 'bold 14px sans-serif';
                            ctx.textAlign = 'center';
                            ctx.fillStyle = '#ffffff';
                            ctx.globalAlpha = alpha * 0.8;
                            ctx.fillText(this.lastHitFeedback.combo + ' COMBO', cx, h * 0.3 + 24);
                            ctx.globalAlpha = 1;
                        }
                    }
                }
            }

            ctx.restore();
        };

        this.canvasDrawInterval = requestAnimationFrame(draw);
    }

    // ==================== 最终曲线 ====================

    drawFinalPitchCurve() {
        if (!this.pitchCanvasCtx || !this._canvasW) return;
        const ctx = this.pitchCanvasCtx;
        const w = this._canvasW;
        const h = this._canvasH;
        const dpr = window.devicePixelRatio || 1;

        ctx.save();
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        ctx.clearRect(0, 0, w, h);
        ctx.fillStyle = '#0d1117';
        ctx.fillRect(0, 0, w, h);

        const allFreqs = [];
        for (const f of this.standardFrequencies) { if (f > 50 && f < 1000) allFreqs.push(f); }
        for (const p of this.userPitches) { if (p.frequency > 50 && p.frequency < 1000) allFreqs.push(p.frequency); }
        if (allFreqs.length < 5) { ctx.restore(); return; }

        const minFreq = Math.min(...allFreqs) * 0.9;
        const maxFreq = Math.max(...allFreqs) * 1.1;
        const range = maxFreq - minFreq || 1;
        const freqToY = (f) => h * 0.9 - ((f - minFreq) / range) * h * 0.8;

        // 标准
        ctx.strokeStyle = '#10b981';
        ctx.lineWidth = 2;
        ctx.beginPath();
        let s = false;
        for (let i = 0; i < this.standardFrequencies.length; i++) {
            const f = this.standardFrequencies[i];
            if (f < 50 || f > 1000) continue;
            const x = (i / this.standardFrequencies.length) * w;
            if (!s) { ctx.moveTo(x, freqToY(f)); s = true; } else ctx.lineTo(x, freqToY(f));
        }
        ctx.stroke();

        // 用户
        if (this.userPitches.length > 1) {
            ctx.strokeStyle = '#3b82f6';
            ctx.lineWidth = 2;
            ctx.beginPath();
            s = false;
            for (const p of this.userPitches) {
                if (p.frequency < 50 || p.frequency > 1000) continue;
                const x = (p.time / this.standardDuration) * w;
                if (!s) { ctx.moveTo(x, freqToY(p.frequency)); s = true; } else ctx.lineTo(x, freqToY(p.frequency));
            }
            ctx.stroke();
        }

        // 图例 + 统计
        ctx.font = '12px sans-serif';
        ctx.fillStyle = '#10b981';
        ctx.fillRect(10, 8, 12, 12); ctx.fillText('标准音高', 26, 18);
        ctx.fillStyle = '#3b82f6';
        ctx.fillRect(100, 8, 12, 12); ctx.fillText('您的演唱', 116, 18);

        const stats = `PERFECT ${this.hitCounts.perfect} | GREAT ${this.hitCounts.great} | GOOD ${this.hitCounts.good} | MISS ${this.hitCounts.miss} | MAX COMBO ${this.maxCombo}`;
        ctx.fillStyle = '#888';
        ctx.textAlign = 'right';
        ctx.fillText(stats, w - 10, 18);
        ctx.textAlign = 'left';

        ctx.restore();
    }

    // ==================== 进度更新 ====================

    startProgressUpdate() {
        const update = () => {
            if (!this.isRecording) return;
            const t = this.standardAudioElement.currentTime;
            const d = this.standardDuration || this.standardAudioElement.duration;
            const pct = d > 0 ? (t / d) * 100 : 0;

            const pf = document.getElementById('realtimeProgressFill');
            if (pf) pf.style.width = pct + '%';
            const pt = document.getElementById('realtimeTime');
            if (pt) pt.textContent = this.formatTime(t) + ' / ' + this.formatTime(d);

            requestAnimationFrame(update);
        };
        update();
    }

    formatTime(s) {
        if (!s || isNaN(s)) return '00:00';
        return Math.floor(s/60).toString().padStart(2,'0') + ':' + Math.floor(s%60).toString().padStart(2,'0');
    }

    // ==================== 最终结果 ====================

    calculateFinalResult() {
        const total = this.hitCounts.perfect + this.hitCounts.great + this.hitCounts.good + this.hitCounts.miss;
        if (total === 0) return { score: 0, level: '无数据', pitchMatchRate: 0, avgCentsError: 0, userPitches: this.userPitches, audioBlob: this.getAudioBlob(), hitCounts: this.hitCounts, maxCombo: this.maxCombo, diagnosis: ['未能检测到有效人声'] };

        const weighted = this.hitCounts.perfect * 100 + this.hitCounts.great * 80 + this.hitCounts.good * 60;
        const score = Math.round(weighted / total);
        const matchRate = Math.round((this.hitCounts.perfect + this.hitCounts.great + this.hitCounts.good) / total * 100);

        let level;
        if (score >= 90) level = 'SSS';
        else if (score >= 85) level = 'SS';
        else if (score >= 80) level = 'S';
        else if (score >= 70) level = 'A';
        else if (score >= 60) level = 'B';
        else level = 'C';

        return {
            score, level, pitchMatchRate: matchRate,
            avgCentsError: 0, userPitches: this.userPitches,
            audioBlob: this.getAudioBlob(),
            hitCounts: this.hitCounts, maxCombo: this.maxCombo,
            diagnosis: this.generateDiagnosis(score, matchRate)
        };
    }

    generateDiagnosis(score, matchRate) {
        const d = [];
        if (score >= 85) d.push('音准表现极佳，SS级评价！');
        else if (score >= 75) d.push('音准整体优秀，继续保持！');
        else if (score >= 65) d.push('音准良好，部分音符可更精准');
        else d.push('多加练习音准，你会越来越好的！');

        if (this.maxCombo >= 20) d.push(`超强连击 ${this.maxCombo} 次！`);
        else if (this.maxCombo >= 10) d.push(`连击 ${this.maxCombo} 次，不错！`);

        const pos = this.userPitches.filter(p => p.centsDiff > 10).length;
        const neg = this.userPitches.filter(p => p.centsDiff < -10).length;
        if (pos > neg * 2) d.push('整体偏高，注意控制气息');
        else if (neg > pos * 2) d.push('整体偏低，加强气息支撑');

        return d;
    }

    getAudioBlob() {
        if (this.recordChunks.length === 0) return null;
        return new Blob(this.recordChunks, { type: this.mediaRecorder.mimeType || 'audio/webm' });
    }

    setCallbacks(onDeviationUpdate, onScoreUpdate, onComplete) {
        this.onDeviationUpdate = onDeviationUpdate;
        this.onScoreUpdate = onScoreUpdate;
        this.onComplete = onComplete;
    }
}

export default RealtimeCompare;
