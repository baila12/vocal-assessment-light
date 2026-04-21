/**
 * 音频处理模块
 * 使用 Web Audio API 进行音频播放和可视化
 */

// 音频上下文（单例）
let audioContext = null;

// 获取音频上下文
function getAudioContext() {
    if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
    return audioContext;
}

// 音频播放器类
class AudioPlayer {
    constructor() {
        this.audioContext = getAudioContext();
        this.audioElement = null;
        this.sourceNode = null;
        this.analyserNode = null;
        this.gainNode = null;
        this.isPlaying = false;
        this.currentFile = null;
    }

    // 加载音频文件
    async load(filepath) {
        // 清理之前的资源
        this.cleanup();

        // 创建音频元素
        this.audioElement = new Audio(`/api/audio?file=${encodeURIComponent(filepath)}`);
        this.currentFile = filepath;

        // 创建音频节点
        this.sourceNode = this.audioContext.createMediaElementSource(this.audioElement);
        this.analyserNode = this.audioContext.createAnalyser();
        this.gainNode = this.audioContext.createGain();

        // 配置分析器
        this.analyserNode.fftSize = 256;
        this.analyserNode.smoothingTimeConstant = 0.8;

        // 连接节点
        this.sourceNode.connect(this.analyserNode);
        this.analyserNode.connect(this.gainNode);
        this.gainNode.connect(this.audioContext.destination);

        // 等待加载
        return new Promise((resolve, reject) => {
            this.audioElement.addEventListener('canplaythrough', resolve, { once: true });
            this.audioElement.addEventListener('error', reject, { once: true });
            this.audioElement.load();
        });
    }

    // 播放
    async play() {
        if (!this.audioElement) return;

        // 恢复音频上下文（浏览器策略）
        if (this.audioContext.state === 'suspended') {
            await this.audioContext.resume();
        }

        await this.audioElement.play();
        this.isPlaying = true;

        // 触发播放事件
        window.dispatchEvent(new CustomEvent('audioPlay', {
            detail: { file: this.currentFile }
        }));
    }

    // 暂停
    pause() {
        if (this.audioElement) {
            this.audioElement.pause();
            this.isPlaying = false;

            window.dispatchEvent(new CustomEvent('audioPause'));
        }
    }

    // 停止
    stop() {
        if (this.audioElement) {
            this.audioElement.pause();
            this.audioElement.currentTime = 0;
            this.isPlaying = false;
        }
    }

    // 跳转
    seek(time) {
        if (this.audioElement) {
            this.audioElement.currentTime = time;
        }
    }

    // 设置音量
    setVolume(volume) {
        if (this.gainNode) {
            this.gainNode.gain.value = Math.max(0, Math.min(1, volume));
        }
    }

    // 获取当前时间
    getCurrentTime() {
        return this.audioElement ? this.audioElement.currentTime : 0;
    }

    // 获取总时长
    getDuration() {
        return this.audioElement ? this.audioElement.duration : 0;
    }

    // 获取频谱数据
    getFrequencyData() {
        if (!this.analyserNode) return new Uint8Array(0);

        const dataArray = new Uint8Array(this.analyserNode.frequencyBinCount);
        this.analyserNode.getByteFrequencyData(dataArray);
        return dataArray;
    }

    // 获取波形数据
    getTimeDomainData() {
        if (!this.analyserNode) return new Uint8Array(0);

        const dataArray = new Uint8Array(this.analyserNode.fftSize);
        this.analyserNode.getByteTimeDomainData(dataArray);
        return dataArray;
    }

    // 添加事件监听
    on(event, callback) {
        if (this.audioElement) {
            this.audioElement.addEventListener(event, callback);
        }
    }

    // 移除事件监听
    off(event, callback) {
        if (this.audioElement) {
            this.audioElement.removeEventListener(event, callback);
        }
    }

    // 清理资源
    cleanup() {
        if (this.audioElement) {
            this.audioElement.pause();
            this.audioElement.src = '';
            this.audioElement = null;
        }

        if (this.sourceNode) {
            this.sourceNode.disconnect();
            this.sourceNode = null;
        }

        this.isPlaying = false;
        this.currentFile = null;
    }
}

// 绘制波形可视化
function drawWaveform(canvas, player) {
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    // 清空画布
    ctx.clearRect(0, 0, width, height);

    // 获取波形数据
    const dataArray = player.getTimeDomainData();
    const bufferLength = dataArray.length;

    // 绘制样式
    ctx.lineWidth = 2;
    ctx.strokeStyle = 'var(--primary)';
    ctx.beginPath();

    const sliceWidth = width / bufferLength;
    let x = 0;

    for (let i = 0; i < bufferLength; i++) {
        const v = dataArray[i] / 128.0;
        const y = v * height / 2;

        if (i === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }

        x += sliceWidth;
    }

    ctx.lineTo(width, height / 2);
    ctx.stroke();
}

// 绘制频谱可视化
function drawFrequency(canvas, player) {
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    // 清空画布
    ctx.clearRect(0, 0, width, height);

    // 获取频谱数据
    const dataArray = player.getFrequencyData();
    const bufferLength = dataArray.length;

    const barWidth = width / bufferLength * 2.5;
    let x = 0;

    for (let i = 0; i < bufferLength; i++) {
        const barHeight = (dataArray[i] / 255) * height;

        // 渐变色
        const hue = (i / bufferLength) * 60 + 200; // 蓝紫色调
        ctx.fillStyle = `hsl(${hue}, 70%, 60%)`;

        ctx.fillRect(x, height - barHeight, barWidth, barHeight);
        x += barWidth + 1;
    }
}

// 导出
export {
    AudioPlayer,
    getAudioContext,
    drawWaveform,
    drawFrequency
};
