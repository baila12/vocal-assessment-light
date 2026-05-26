/**
 * 实时音高检测器
 * 基于 YIN 算法的前端实现
 *
 * 用于实时录音对比模式，检测用户演唱的音高
 */

export class PitchDetector {
    constructor(audioContext, options = {}) {
        this.audioContext = audioContext;
        this.threshold = options.threshold || 0.15; // YIN 阈值
        this.bufferSize = options.bufferSize || 2048;
        this.minFreq = options.minFreq || 65;   // C2
        this.maxFreq = options.maxFreq || 1047; // C6

        // 音符名称
        this.noteNames = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
    }

    /**
     * 使用 YIN 算法检测音高
     * @param {Float32Array} buffer - 时域音频数据
     * @returns {number} 检测到的频率 (Hz)，未检测到返回 0
     */
    detectPitch(buffer) {
        const bufferSize = buffer.length;
        const sampleRate = this.audioContext.sampleRate;

        // 计算 RMS 判断是否有声音
        let rms = 0;
        for (let i = 0; i < bufferSize; i++) {
            rms += buffer[i] * buffer[i];
        }
        rms = Math.sqrt(rms / bufferSize);

        // RMS 太低，认为静音
        if (rms < 0.01) {
            return 0;
        }

        // YIN 算法
        const yinBuffer = new Float32Array(bufferSize / 2);
        let runningSum = 0;

        // 第一步：计算差分函数
        for (let tau = 0; tau < yinBuffer.length; tau++) {
            yinBuffer[tau] = 0;
            for (let i = 0; i < yinBuffer.length; i++) {
                const delta = buffer[i] - buffer[i + tau];
                yinBuffer[tau] += delta * delta;
            }
            runningSum += yinBuffer[tau];
        }

        // 第二步：累积均值归一化
        yinBuffer[0] = 1;
        for (let tau = 1; tau < yinBuffer.length; tau++) {
            yinBuffer[tau] = yinBuffer[tau] * tau / runningSum;
        }

        // 第三步：找到第一个低于阈值的 tau
        let tauEstimate = -1;
        for (let tau = 2; tau < yinBuffer.length; tau++) {
            if (yinBuffer[tau] < this.threshold) {
                // 找到局部最小值
                while (tau + 1 < yinBuffer.length && yinBuffer[tau + 1] < yinBuffer[tau]) {
                    tau++;
                }
                tauEstimate = tau;
                break;
            }
        }

        if (tauEstimate === -1) {
            return 0;
        }

        // 第四步：抛物线插值提高精度
        let betterTau;
        const x0 = tauEstimate < 1 ? tauEstimate : tauEstimate - 1;
        const x2 = tauEstimate + 1 < yinBuffer.length ? tauEstimate + 1 : tauEstimate;

        if (x0 === tauEstimate) {
            betterTau = yinBuffer[tauEstimate] <= yinBuffer[x2] ? tauEstimate : x2;
        } else if (x2 === tauEstimate) {
            betterTau = yinBuffer[tauEstimate] <= yinBuffer[x0] ? tauEstimate : x0;
        } else {
            const s0 = yinBuffer[x0];
            const s1 = yinBuffer[tauEstimate];
            const s2 = yinBuffer[x2];
            betterTau = tauEstimate + (s2 - s0) / (2 * (2 * s1 - s2 - s0));
        }

        // 计算频率
        const frequency = sampleRate / betterTau;

        // 检查是否在人声范围内
        if (frequency < this.minFreq || frequency > this.maxFreq) {
            return 0;
        }

        return frequency;
    }

    /**
     * 频率转 MIDI 音符号
     * @param {number} freq - 频率 (Hz)
     * @returns {number} MIDI 音符号 (69 = A4 = 440Hz)
     */
    frequencyToMidi(freq) {
        return 69 + 12 * Math.log2(freq / 440);
    }

    /**
     * 频率转音名和八度
     * @param {number} freq - 频率 (Hz)
     * @returns {object} { note: 'A', octave: 4, cents: 0 }
     */
    frequencyToNote(freq) {
        if (freq <= 0) return null;

        const midi = this.frequencyToMidi(freq);
        const roundedMidi = Math.round(midi);
        const cents = Math.round((midi - roundedMidi) * 100);

        const noteIndex = roundedMidi % 12;
        const octave = Math.floor(roundedMidi / 12) - 1;

        return {
            note: this.noteNames[noteIndex],
            octave: octave,
            fullName: this.noteNames[noteIndex] + octave,
            cents: cents,
            midi: roundedMidi,
            frequency: freq
        };
    }

    /**
     * 计算两个频率之间的音分差
     * @param {number} freq1 - 频率1 (Hz)
     * @param {number} freq2 - 频率2 (Hz)
     * @returns {number} 音分差 (正数表示 freq2 高于 freq1)
     */
    calculateCentsDiff(freq1, freq2) {
        if (freq1 <= 0 || freq2 <= 0) return null;
        return 1200 * Math.log2(freq2 / freq1);
    }

    /**
     * 获取音分偏差的提示文本
     * @param {number} cents - 音分偏差
     * @returns {string} 提示文本
     */
    getCentsHint(cents) {
        if (Math.abs(cents) < 10) {
            return '音准准确！';
        } else if (cents > 10 && cents < 30) {
            return '略高，稍微降低一点';
        } else if (cents >= 30 && cents < 50) {
            return '偏高，需要降低';
        } else if (cents >= 50) {
            return '太高了，大幅降低';
        } else if (cents < -10 && cents > -30) {
            return '略低，稍微提高一点';
        } else if (cents <= -30 && cents > -50) {
            return '偏低，需要提高';
        } else {
            return '太低了，大幅提高';
        }
    }
}

/**
 * 实时音高分析器
 * 封装了 AnalyserNode 和 PitchDetector
 */
export class RealtimePitchAnalyzer {
    constructor(options = {}) {
        this.audioContext = null;
        this.analyser = null;
        this.pitchDetector = null;
        this.isAnalyzing = false;
        this.animationId = null;
        this.onPitchDetected = null;

        this.options = {
            fftSize: options.fftSize || 2048,
            smoothingTimeConstant: options.smoothingTimeConstant || 0.8,
            ...options
        };
    }

    /**
     * 初始化分析器
     * @param {AudioContext} audioContext - 音频上下文
     * @param {MediaStream|AudioNode} source - 音频源
     */
    async init(audioContext, source) {
        this.audioContext = audioContext;

        // 创建分析器节点
        this.analyser = audioContext.createAnalyser();
        this.analyser.fftSize = this.options.fftSize;
        this.analyser.smoothingTimeConstant = this.options.smoothingTimeConstant;

        // 连接源
        if (source instanceof MediaStream) {
            const sourceNode = audioContext.createMediaStreamSource(source);
            sourceNode.connect(this.analyser);
        } else {
            source.connect(this.analyser);
        }

        // 创建音高检测器
        this.pitchDetector = new PitchDetector(audioContext, {
            bufferSize: this.options.fftSize
        });
    }

    /**
     * 开始实时分析
     * @param {function} callback - 检测到音高时的回调函数 (pitch, time) => {}
     */
    start(callback) {
        if (!this.analyser) {
            console.error('Analyzer not initialized');
            return;
        }

        this.onPitchDetected = callback;
        this.isAnalyzing = true;
        this.analyze();
    }

    /**
     * 停止分析
     */
    stop() {
        this.isAnalyzing = false;
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
    }

    /**
     * 分析循环
     */
    analyze() {
        if (!this.isAnalyzing) return;

        const bufferLength = this.analyser.fftSize;
        const timeDomainData = new Float32Array(bufferLength);
        this.analyser.getFloatTimeDomainData(timeDomainData);

        // 检测音高
        const frequency = this.pitchDetector.detectPitch(timeDomainData);
        const time = this.audioContext.currentTime;

        if (frequency > 0 && this.onPitchDetected) {
            const noteInfo = this.pitchDetector.frequencyToNote(frequency);
            this.onPitchDetected({
                frequency: frequency,
                note: noteInfo,
                time: time,
                rms: this.calculateRMS(timeDomainData)
            });
        }

        this.animationId = requestAnimationFrame(() => this.analyze());
    }

    /**
     * 计算 RMS
     */
    calculateRMS(buffer) {
        let sum = 0;
        for (let i = 0; i < buffer.length; i++) {
            sum += buffer[i] * buffer[i];
        }
        return Math.sqrt(sum / buffer.length);
    }

    /**
     * 获取当前时域数据
     */
    getTimeDomainData() {
        if (!this.analyser) return null;
        const data = new Float32Array(this.analyser.fftSize);
        this.analyser.getFloatTimeDomainData(data);
        return data;
    }

    /**
     * 获取当前频域数据
     */
    getFrequencyData() {
        if (!this.analyser) return null;
        const data = new Uint8Array(this.analyser.frequencyBinCount);
        this.analyser.getByteFrequencyData(data);
        return data;
    }
}

export default PitchDetector;
