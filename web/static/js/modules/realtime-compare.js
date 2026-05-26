/**
 * 实时录音对比模块
 * 类似全民K歌的实时反馈
 *
 * 功能：
 * 1. 播放标准音频
 * 2. 同步录音
 * 3. 实时计算音准偏差
 * 4. 更新 UI 显示
 */

import { PitchDetector, RealtimePitchAnalyzer } from './pitch-detector.js';

export class RealtimeCompare {
    constructor(standardAudioData = {}) {
        // 标准音频数据
        this.standardPitchCurve = standardAudioData.pitch_curve || [];
        this.standardDuration = standardAudioData.duration || 0;
        this.standardFrequencies = standardAudioData.pitch_curve?.frequencies || [];

        // 音频元素和上下文
        this.standardAudioElement = null;
        this.audioContext = null;

        // 录音相关
        this.mediaRecorder = null;
        this.recordChunks = [];
        this.recordStream = null;

        // 音高分析器
        this.pitchAnalyzer = null;
        this.pitchDetector = null;

        // 状态
        this.isRecording = false;
        this.startTime = 0;
        this.userPitches = []; // 用户演唱的音高记录

        // UI 回调
        this.onDeviationUpdate = null;
        this.onScoreUpdate = null;
        this.onComplete = null;

        // 评分累计
        this.totalCentsError = 0;
        this.matchCount = 0;
    }

    /**
     * 初始化
     * @param {HTMLAudioElement} audioElement - 标准音频元素
     * @param {string} standardUrl - 标准音频 URL
     */
    async init(audioElement, standardUrl) {
        this.standardAudioElement = audioElement;
        this.standardAudioElement.src = standardUrl;

        // 创建音频上下文
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();

        // 创建音高检测器
        this.pitchDetector = new PitchDetector(this.audioContext);

        // 等待音频加载
        await new Promise((resolve, reject) => {
            this.standardAudioElement.addEventListener('loadedmetadata', resolve, { once: true });
            this.standardAudioElement.addEventListener('error', reject, { once: true });
            // 如果已经加载，直接resolve
            if (this.standardAudioElement.readyState >= 1) {
                resolve();
            }
        });

        // 更新时长
        this.standardDuration = this.standardAudioElement.duration || this.standardDuration;
    }

    /**
     * 开始实时对比
     */
    async start() {
        // 检查安全上下文
        const isLocalhost = location.hostname === 'localhost' || location.hostname === '127.0.0.1' || location.hostname === '[::1]';
        const isSecure = window.isSecureContext || isLocalhost;

        if (!isSecure) {
            throw new Error('实时录音需要 HTTPS 或 localhost 环境');
        }

        // 检查浏览器支持
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            throw new Error('浏览器不支持录音功能，请使用 Chrome/Firefox/Edge');
        }

        try {
            // 获取麦克风权限
            this.recordStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    sampleRate: 44100
                }
            });

            // 创建 MediaRecorder
            this.mediaRecorder = new MediaRecorder(this.recordStream, {
                mimeType: MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4'
            });

            this.mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) {
                    this.recordChunks.push(e.data);
                }
            };

            // 创建实时音高分析器
            this.pitchAnalyzer = new RealtimePitchAnalyzer({ fftSize: 2048 });
            await this.pitchAnalyzer.init(this.audioContext, this.recordStream);

            // 开始录音
            this.mediaRecorder.start(100);
            this.isRecording = true;
            this.startTime = this.audioContext.currentTime;
            this.userPitches = [];
            this.totalCentsError = 0;
            this.matchCount = 0;

            // 播放标准音频
            if (this.audioContext.state === 'suspended') {
                await this.audioContext.resume();
            }
            this.standardAudioElement.play();

            // 开始实时分析
            this.pitchAnalyzer.start((pitchInfo) => {
                this.handlePitchDetected(pitchInfo);
            });

            // 开始进度更新
            this.startProgressUpdate();

        } catch (error) {
            console.error('启动实时对比失败:', error);
            throw error;
        }
    }

    /**
     * 处理检测到的音高
     */
    handlePitchDetected(pitchInfo) {
        if (!this.isRecording) return;

        const currentTime = this.standardAudioElement.currentTime;
        const userFreq = pitchInfo.frequency;

        // 获取当前时间点的标准音高
        const standardFreq = this.getStandardFreqAtTime(currentTime);

        if (standardFreq && standardFreq > 50 && userFreq > 50) {
            // 计算音分偏差
            const centsDiff = this.pitchDetector.calculateCentsDiff(standardFreq, userFreq);

            if (centsDiff !== null) {
                // 记录用户音高
                this.userPitches.push({
                    time: currentTime,
                    frequency: userFreq,
                    standardFreq: standardFreq,
                    centsDiff: centsDiff
                });

                // 累计评分
                this.totalCentsError += Math.abs(centsDiff);
                this.matchCount++;

                // 更新 UI
                if (this.onDeviationUpdate) {
                    this.onDeviationUpdate({
                        cents: Math.round(centsDiff),
                        userFreq: userFreq,
                        standardFreq: standardFreq,
                        hint: this.pitchDetector.getCentsHint(centsDiff),
                        userNote: pitchInfo.note
                    });
                }

                // 更新实时评分
                if (this.onScoreUpdate && this.matchCount > 0) {
                    const avgCentsError = this.totalCentsError / this.matchCount;
                    const score = this.calculateRealtimeScore(avgCentsError);
                    this.onScoreUpdate(score);
                }
            }
        }
    }

    /**
     * 获取指定时间点的标准音高
     */
    getStandardFreqAtTime(time) {
        if (!this.standardFrequencies || this.standardFrequencies.length === 0) {
            return null;
        }

        // 根据时间计算索引
        const duration = this.standardDuration;
        const index = Math.floor((time / duration) * this.standardFrequencies.length);

        if (index >= 0 && index < this.standardFrequencies.length) {
            return this.standardFrequencies[index];
        }

        return null;
    }

    /**
     * 计算实时评分
     */
    calculateRealtimeScore(avgCentsError) {
        // 音分误差越小，分数越高
        // 0 音分误差 = 100 分
        // 50 音分误差 = 70 分
        // 100 音分误差 = 40 分
        const score = Math.max(0, Math.min(100, 100 - avgCentsError * 0.6));
        return Math.round(score);
    }

    /**
     * 开始进度更新
     */
    startProgressUpdate() {
        const updateProgress = () => {
            if (!this.isRecording) return;

            const currentTime = this.standardAudioElement.currentTime;
            const duration = this.standardDuration || this.standardAudioElement.duration;
            const progress = (currentTime / duration) * 100;

            // 更新进度 UI
            const progressFill = document.getElementById('standardProgressFill');
            if (progressFill) {
                progressFill.style.width = `${progress}%`;
            }

            const progressText = document.getElementById('standardProgress');
            if (progressText) {
                progressText.textContent = `${this.formatTime(currentTime)} / ${this.formatTime(duration)}`;
            }

            const realtimeTime = document.getElementById('realtimeTime');
            if (realtimeTime) {
                realtimeTime.textContent = this.formatTime(currentTime);
            }

            requestAnimationFrame(updateProgress);
        };

        updateProgress();
    }

    /**
     * 格式化时间
     */
    formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }

    /**
     * 停止录音并获取结果
     */
    async stop() {
        if (!this.isRecording) return;

        this.isRecording = false;

        // 停止分析器
        if (this.pitchAnalyzer) {
            this.pitchAnalyzer.stop();
        }

        // 停止录音
        if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
            this.mediaRecorder.stop();
        }

        // 停止播放
        if (this.standardAudioElement) {
            this.standardAudioElement.pause();
        }

        // 停止麦克风
        if (this.recordStream) {
            this.recordStream.getTracks().forEach(track => track.stop());
        }

        // 等待录音数据完成
        await new Promise((resolve) => {
            if (this.mediaRecorder) {
                this.mediaRecorder.addEventListener('stop', resolve, { once: true });
            } else {
                resolve();
            }
        });

        // 计算最终评分
        const result = this.calculateFinalResult();

        // 回调完成
        if (this.onComplete) {
            this.onComplete(result);
        }

        return result;
    }

    /**
     * 计算最终结果
     */
    calculateFinalResult() {
        if (this.matchCount === 0) {
            return {
                score: 0,
                level: '无数据',
                pitchMatchRate: 0,
                avgCentsError: 0,
                userPitches: this.userPitches,
                audioBlob: this.getAudioBlob()
            };
        }

        const avgCentsError = this.totalCentsError / this.matchCount;
        const score = this.calculateRealtimeScore(avgCentsError);

        // 计算音准匹配率（音分误差 < 50 视为匹配）
        const matchThreshold = 50;
        const matchCount = this.userPitches.filter(p => Math.abs(p.centsDiff) < matchThreshold).length;
        const pitchMatchRate = (matchCount / this.userPitches.length) * 100;

        // 等级评定
        let level;
        if (score >= 90) level = '优秀';
        else if (score >= 80) level = '良好';
        else if (score >= 70) level = '中等';
        else if (score >= 60) level = '及格';
        else level = '需改进';

        return {
            score: score,
            level: level,
            pitchMatchRate: Math.round(pitchMatchRate),
            avgCentsError: Math.round(avgCentsError),
            userPitches: this.userPitches,
            audioBlob: this.getAudioBlob(),
            diagnosis: this.generateDiagnosis()
        };
    }

    /**
     * 生成诊断信息
     */
    generateDiagnosis() {
        const diagnosis = [];

        if (this.matchCount === 0) {
            diagnosis.push('未能检测到有效人声，请确保麦克风正常工作');
            return diagnosis;
        }

        const avgCentsError = this.totalCentsError / this.matchCount;

        if (avgCentsError < 20) {
            diagnosis.push('音准表现优秀，与标准音频高度匹配');
        } else if (avgCentsError < 40) {
            diagnosis.push('音准整体良好，部分段落略有偏差');
        } else if (avgCentsError < 60) {
            diagnosis.push('音准需要提高，建议多听标准音频找准音高');
        } else {
            diagnosis.push('音准偏差较大，建议先练习音阶建立音准感');
        }

        // 分析偏高/偏低趋势
        const positiveCount = this.userPitches.filter(p => p.centsDiff > 10).length;
        const negativeCount = this.userPitches.filter(p => p.centsDiff < -10).length;

        if (positiveCount > negativeCount * 2) {
            diagnosis.push('整体偏高，注意控制气息不要过于用力');
        } else if (negativeCount > positiveCount * 2) {
            diagnosis.push('整体偏低，注意加强气息支撑');
        }

        return diagnosis;
    }

    /**
     * 获取录音 Blob
     */
    getAudioBlob() {
        if (this.recordChunks.length === 0) return null;
        return new Blob(this.recordChunks, { type: this.mediaRecorder.mimeType });
    }

    /**
     * 绘制音高对比曲线
     */
    drawPitchCompareCanvas(canvas) {
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const width = canvas.width;
        const height = canvas.height;

        ctx.clearRect(0, 0, width, height);

        // 绘制标准音高曲线（绿色）
        if (this.standardFrequencies && this.standardFrequencies.length > 0) {
            ctx.strokeStyle = '#10b981';
            ctx.lineWidth = 2;
            ctx.beginPath();

            const validFreqs = this.standardFrequencies.filter(f => f > 50 && f < 1000);
            if (validFreqs.length > 0) {
                const minFreq = Math.min(...validFreqs) * 0.9;
                const maxFreq = Math.max(...validFreqs) * 1.1;

                for (let i = 0; i < this.standardFrequencies.length; i++) {
                    const freq = this.standardFrequencies[i];
                    if (freq < 50 || freq > 1000) continue;

                    const x = (i / this.standardFrequencies.length) * width;
                    const y = height - ((freq - minFreq) / (maxFreq - minFreq)) * height;

                    if (i === 0) ctx.moveTo(x, y);
                    else ctx.lineTo(x, y);
                }
                ctx.stroke();
            }
        }

        // 绘制用户音高曲线（蓝色）
        if (this.userPitches.length > 0) {
            ctx.strokeStyle = '#3b82f6';
            ctx.lineWidth = 2;
            ctx.beginPath();

            const validFreqs = this.userPitches.filter(p => p.frequency > 50 && p.frequency < 1000);
            if (validFreqs.length > 0) {
                const allFreqs = [...this.standardFrequencies.filter(f => f > 50 && f < 1000), ...validFreqs.map(p => p.frequency)];
                const minFreq = Math.min(...allFreqs) * 0.9;
                const maxFreq = Math.max(...allFreqs) * 1.1;

                for (let i = 0; i < this.userPitches.length; i++) {
                    const pitch = this.userPitches[i];
                    const x = (pitch.time / this.standardDuration) * width;
                    const y = height - ((pitch.frequency - minFreq) / (maxFreq - minFreq)) * height;

                    if (i === 0) ctx.moveTo(x, y);
                    else ctx.lineTo(x, y);
                }
                ctx.stroke();
            }
        }
    }

    /**
     * 设置回调函数
     */
    setCallbacks(onDeviationUpdate, onScoreUpdate, onComplete) {
        this.onDeviationUpdate = onDeviationUpdate;
        this.onScoreUpdate = onScoreUpdate;
        this.onComplete = onComplete;
    }
}

export default RealtimeCompare;