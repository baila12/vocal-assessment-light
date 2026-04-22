/**
 * 文件上传模块
 * 处理音频文件选择、加载和预处理
 */

import { AppState } from './state.js';
import { showToast, formatTime } from './utils.js';

// ==================== 文件上传处理 ====================

/**
 * 处理文件选择
 * @param {Event|File} event - 文件选择事件或文件对象
 */
function handleFileSelect(event) {
    const file = event.target?.files?.[0] || event;
    if (!file) return;

    // 验证文件类型
    const validTypes = ['audio/wav', 'audio/mp3', 'audio/mpeg', 'audio/ogg', 'audio/flac', 'audio/m4a'];
    if (!validTypes.includes(file.type) && !file.name.match(/\.(wav|mp3|flac|ogg|m4a)$/i)) {
        showToast('请上传有效的音频文件', 'error');
        return;
    }

    // 验证文件大小 (最大 50MB)
    if (file.size > 50 * 1024 * 1024) {
        showToast('文件大小不能超过 50MB', 'error');
        return;
    }

    // 清理旧的音频资源
    cleanupAudioResources();

    // 更新状态
    AppState.audio = {
        file: file,
        name: file.name,
        url: URL.createObjectURL(file),
        isPlaying: false,
        duration: 0,
        currentTime: 0,
        element: null,
        buffer: null,
        context: null,
        analyser: null,
        sourceNode: null,
        waveformData: null
    };

    // 更新 UI
    updateFileSelectionUI(file);

    // 加载音频信息
    loadAudioFileInfo(file);

    showToast('音频文件已加载', 'success');
}

/**
 * 清理音频资源
 */
function cleanupAudioResources() {
    if (AppState.audio.element) {
        AppState.audio.element.pause();
        AppState.audio.isPlaying = false;
    }
    if (AppState.audio.url) {
        URL.revokeObjectURL(AppState.audio.url);
    }
}

/**
 * 更新文件选择 UI
 * @param {File} file - 选中的文件
 */
function updateFileSelectionUI(file) {
    const selectedFileName = document.getElementById('selectedFileName');
    if (selectedFileName) {
        selectedFileName.textContent = file.name;
    }

    const selectedAudioCard = document.getElementById('selectedAudioCard');
    if (selectedAudioCard) {
        selectedAudioCard.style.display = 'block';
    }
}

// ==================== 音频加载 ====================

/**
 * 加载音频文件信息
 * @param {File} file - 音频文件
 */
async function loadAudioFileInfo(file) {
    try {
        const arrayBuffer = await file.arrayBuffer();
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

        // 更新状态
        AppState.audio.buffer = audioBuffer;
        AppState.audio.duration = audioBuffer.duration;
        AppState.audio.context = audioContext;

        // 更新 UI 显示
        updateAudioInfoUI(audioBuffer.duration, file.size);

    } catch (error) {
        console.error('加载音频信息失败:', error);
        showToast('音频加载失败', 'error');
    }
}

/**
 * 更新音频信息 UI
 * @param {number} duration - 音频时长（秒）
 * @param {number} size - 文件大小（字节）
 */
function updateAudioInfoUI(duration, size) {
    const durationEl = document.getElementById('audioDuration');
    if (durationEl) {
        durationEl.textContent = formatTime(duration);
    }

    const sizeEl = document.getElementById('audioSize');
    if (sizeEl) {
        sizeEl.textContent = (size / 1024 / 1024).toFixed(2) + ' MB';
    }
}

// ==================== 音频分析请求 ====================

let analysisController = null;

/**
 * 开始音频分析
 */
async function analyzeAudio() {
    if (!AppState.audio.file) {
        showToast('请先选择音频文件', 'warning');
        return;
    }

    // 获取评估模式
    const evalMode = getEvalMode();

    try {
        // 读取文件数据
        const fileData = await AppState.audio.file.arrayBuffer();

        // 存储到 IndexedDB
        await storeFileForAnalysis(
            fileData,
            AppState.audio.file.name,
            AppState.audio.file.type,
            evalMode  // 传递评估模式
        );

        // 清除旧的分析结果，确保执行新分析
        sessionStorage.removeItem('analysisResult');

        // 设置会话标记
        sessionStorage.setItem('pendingAnalysis', 'true');
        sessionStorage.setItem('analysisFileName', AppState.audio.name);
        sessionStorage.setItem('evalMode', evalMode);  // 保存评估模式

        const fileInfo = {
            name: AppState.audio.file.name,
            size: AppState.audio.file.size,
            type: AppState.audio.file.type,
            lastModified: AppState.audio.file.lastModified
        };
        sessionStorage.setItem('analysisFileInfo', JSON.stringify(fileInfo));

        showToast('正在跳转到分析页面...', 'info');

        // 跳转到分析页面
        window.location.href = '/analysis.html';

    } catch (error) {
        console.error('存储文件失败:', error);
        showToast('文件处理失败，请重试', 'error');
    }
}

/**
 * 获取当前选择的评估模式
 * @returns {string} 'quick' 或 'professional'
 */
function getEvalMode() {
    // 从全局状态获取
    if (AppState.evalMode) {
        return AppState.evalMode;
    }
    // 从 DOM 获取
    const activeOption = document.querySelector('.mode-option.active');
    if (activeOption) {
        return activeOption.querySelector('input').value;
    }
    // 默认快速模式
    return 'quick';
}

/**
 * 存储文件到 IndexedDB
 * @param {ArrayBuffer} fileData - 文件数据
 * @param {string} fileName - 文件名
 * @param {string} fileType - 文件类型
 * @param {string} evalMode - 评估模式 ('quick' 或 'professional')
 * @returns {Promise<void>}
 */
function storeFileForAnalysis(fileData, fileName, fileType, evalMode = 'quick') {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('VocalAnalysisDB', 1);

        request.onerror = () => reject(request.error);

        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains('files')) {
                db.createObjectStore('files');
            }
        };

        request.onsuccess = (event) => {
            const db = event.target.result;
            const transaction = db.transaction(['files'], 'readwrite');
            const store = transaction.objectStore('files');

            const data = {
                fileData: fileData,
                fileName: fileName,
                fileType: fileType,
                evalMode: evalMode,  // 保存评估模式
                timestamp: Date.now()
            };

            store.put(data, 'pendingFile');

            transaction.oncomplete = () => resolve();
            transaction.onerror = () => reject(transaction.error);
        };
    });
}

/**
 * 停止分析
 */
function stopAnalysis() {
    if (analysisController) {
        analysisController.abort();
        analysisController = null;
    }
}

// ==================== 导出 ====================

export {
    handleFileSelect,
    loadAudioFileInfo,
    analyzeAudio,
    stopAnalysis,
    storeFileForAnalysis,
    cleanupAudioResources
};
