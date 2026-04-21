/**
 * 播放控制模块
 */

import { AppState } from './state.js';
import { Utils, frequencyToNoteName } from './utils.js';

function drawAllWaveforms(audioBuffer) {
    const data = audioBuffer.getChannelData(0);
    AppState.audio.waveformData = data;
    drawStaticWaveform('realtimeWave', data);
    drawStaticWaveform('waveformCanvas', data);
}

function drawStaticWaveform(canvasId, data) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = (rect.width || 300) * 2;
    canvas.height = (rect.height || 60) * 2;
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = canvasId === 'waveformCanvas' ? 'rgba(255,255,255,0.2)' : '#3b82f6';
    const step = Math.ceil(data.length / width);
    const amp = height / 2;
    for (let i = 0; i < width; i++) {
        let min = 1.0, max = -1.0;
        for (let j = 0; j < step; j++) {
            const idx = i * step + j;
            if (idx < data.length) {
                const datum = data[idx];
                if (datum < min) min = datum;
                if (datum > max) max = datum;
            }
        }
        ctx.fillRect(i, (1 + min) * amp, 1, Math.max(1, (max - min) * amp));
    }
}

function togglePlay() {
    if (!AppState.audio.element) return;
    if (AppState.audio.isPlaying) {
        AppState.audio.element.pause();
        AppState.audio.isPlaying = false;
        document.getElementById('playBtn').textContent = '▶';
    } else {
        if (AppState.audio.context?.state === 'suspended') {
            AppState.audio.context.resume();
        }
        AppState.audio.element.play();
        AppState.audio.isPlaying = true;
        document.getElementById('playBtn').textContent = '⏸';
        startRealtimeUpdate();
    }
}

function updateProgress() {
    if (!AppState.audio.element) return;
    const currentTime = AppState.audio.element.currentTime;
    const duration = AppState.audio.duration || 1;
    const progress = (currentTime / duration) * 100;
    document.getElementById('currentTime').textContent = Utils.formatTime(currentTime);
    updateWaveformProgress(progress);
}

function startRealtimeUpdate() {
    updateRealtimeDisplay();
}

function updateRealtimeDisplay() {
    if (!AppState.audio.isPlaying) return;
    const analyser = AppState.audio.analyser;
    if (!analyser) {
        requestAnimationFrame(updateRealtimeDisplay);
        return;
    }
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    analyser.getByteFrequencyData(dataArray);
    drawSpectrum(dataArray);
    requestAnimationFrame(updateRealtimeDisplay);
}

function drawSpectrum(dataArray) {
    const canvas = document.getElementById('realtimeSpectrum');
    if (!canvas) return;
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = (rect.width || 150) * 2;
    canvas.height = (rect.height || 80) * 2;
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);
    const barCount = 24;
    const barWidth = (width / barCount) - 3;
    const step = Math.floor(dataArray.length / barCount);
    for (let i = 0; i < barCount; i++) {
        let sum = 0;
        for (let j = 0; j < step; j++) sum += dataArray[i * step + j];
        const avg = sum / step;
        const barHeight = (avg / 255) * height * 0.85;
        const hue = 200 + (i / barCount) * 40;
        const lightness = 50 + (avg / 255) * 20;
        const x = i * (barWidth + 3) + 1;
        const y = height - barHeight;
        ctx.fillStyle = 'hsl(' + hue + ', 70%, ' + lightness + '%)';
        ctx.beginPath();
        ctx.roundRect(x, y, barWidth, barHeight, [3, 3, 0, 0]);
        ctx.fill();
    }
}

function seekAudio(event) {
    if (!AppState.audio.element || !AppState.audio.duration) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const percent = (event.clientX - rect.left) / rect.width;
    AppState.audio.element.currentTime = Math.max(0, Math.min(percent * AppState.audio.duration, AppState.audio.duration));
}

export { drawAllWaveforms, drawStaticWaveform, togglePlay, updateProgress, startRealtimeUpdate, drawSpectrum, seekAudio };
