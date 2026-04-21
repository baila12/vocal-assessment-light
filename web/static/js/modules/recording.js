/**
 * 录音功能模块
 */

import { AppState } from './state.js';
import { Utils, showToast } from './utils.js';
import { drawSpectrum, drawAllWaveforms, updateProgress } from './player.js';

async function startQuickRecord() {
    if (AppState.recording.isRecording) { stopRecording(); return; }

    // 检查安全上下文（HTTPS 或 localhost）
    if (!window.isSecureContext && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') {
        showToast('录音功能需要 HTTPS 或 localhost 环境', 'error');
        console.error('录音失败: 非安全上下文，请使用 https:// 或 http://localhost');
        return;
    }

    // 检查浏览器是否支持 getUserMedia
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        showToast('浏览器不支持录音功能，请使用 Chrome/Firefox/Edge', 'error');
        console.error('录音失败: navigator.mediaDevices 不可用');
        return;
    }

    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, sampleRate: 44100 }
        });
        AppState.recording.stream = stream;
        AppState.recording.isRecording = true;
        AppState.recording.chunks = [];
        AppState.recording.startTime = Date.now();
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const analyser = audioContext.createAnalyser();
        analyser.fftSize = 2048;
        const source = audioContext.createMediaStreamSource(stream);
        source.connect(analyser);
        AppState.recording.audioContext = audioContext;
        AppState.recording.analyser = analyser;
        const mediaRecorder = new MediaRecorder(stream, {
            mimeType: MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4'
        });
        mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) AppState.recording.chunks.push(e.data); };
        mediaRecorder.onstop = () => { handleRecordingComplete(); };
        AppState.recording.mediaRecorder = mediaRecorder;
        mediaRecorder.start(100);
        updateRecordingUI(true);
        showToast('开始录音...', 'success');
        drawRecordingWaveform();
    } catch (error) {
        console.error('录音启动失败:', error);
        showToast('录音启动失败: ' + error.message, 'error');
    }
}

function stopRecording() {
    if (!AppState.recording.isRecording) return;
    AppState.recording.isRecording = false;
    if (AppState.recording.mediaRecorder) AppState.recording.mediaRecorder.stop();
    if (AppState.recording.stream) AppState.recording.stream.getTracks().forEach(t => t.stop());
    if (AppState.recording.animationId) cancelAnimationFrame(AppState.recording.animationId);
    if (AppState.recording.audioContext) AppState.recording.audioContext.close();
    updateRecordingUI(false);
}

function handleRecordingComplete() {
    const chunks = AppState.recording.chunks;
    if (chunks.length === 0) { showToast('录音时间太短', 'warning'); return; }
    const blob = new Blob(chunks, { type: AppState.recording.mediaRecorder.mimeType });
    const filename = '录音_' + new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19) + '.webm';
    const file = new File([blob], filename, { type: AppState.recording.mediaRecorder.mimeType });
    AppState.audio.file = file;
    AppState.audio.name = filename;
    AppState.audio.url = URL.createObjectURL(blob);
    showToast('录音完成', 'success');
    AppState.recording.chunks = [];
}

function updateRecordingUI(isRecording) {
    const recordBtn = document.getElementById('recordBtn');
    if (recordBtn) {
        recordBtn.innerHTML = isRecording ? '<span>⏹</span> 停止录音' : '<span>🎙️</span> 快速录音';
        recordBtn.classList.toggle('recording', isRecording);
    }
}

function drawRecordingWaveform() {
    if (!AppState.recording.isRecording) return;
    const analyser = AppState.recording.analyser;
    if (analyser) {
        const dataArray = new Uint8Array(analyser.frequencyBinCount);
        analyser.getByteFrequencyData(dataArray);
        drawSpectrum(dataArray);
    }
    AppState.recording.animationId = requestAnimationFrame(drawRecordingWaveform);
}

export { startQuickRecord, stopRecording, handleRecordingComplete, updateRecordingUI, drawRecordingWaveform };
