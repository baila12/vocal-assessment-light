/**
 * 对比分析模块 v2.0
 * 支持后端五维分析对比
 */

import { AppState } from './state.js';
import { showToast, escapeHtml } from './utils.js';

// 对比分析状态
const CompareState = {
    standardAnalyzed: false,
    userAnalyzed: false,
    isComparing: false,
    standardFilepath: null,
    userFilepath: null
};

function selectStandardAudio() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.wav,.mp3,.flac,.ogg,.m4a';
    input.onchange = (e) => handleCompareAudioSelect(e, 'standard');
    input.click();
}

function selectUserAudio() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.wav,.mp3,.flac,.ogg,.m4a';
    input.onchange = (e) => handleCompareAudioSelect(e, 'user');
    input.click();
}

async function handleCompareAudioSelect(event, type) {
    const file = event.target.files[0];
    if (!file) return;
    const url = URL.createObjectURL(file);
    AppState.compare[type] = { file, name: file.name, url, buffer: null, pitchData: null, duration: 0 };
    const selectEl = document.getElementById(type === 'standard' ? 'standardSelect' : 'userSelect');
    if (selectEl) {
        selectEl.innerHTML = '<div class="icon">⏳</div><div class="filename">' + file.name + '</div><div class="hint">正在加载...</div>';
        selectEl.classList.add('loading');
    }
    loadAndAnalyzeCompareAudio(file, type, selectEl);
}

async function loadAndAnalyzeCompareAudio(file, type, selectEl) {
    try {
        const arrayBuffer = await file.arrayBuffer();
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
        AppState.compare[type].buffer = audioBuffer;
        AppState.compare[type].duration = audioBuffer.duration;
        if (selectEl) {
            selectEl.innerHTML = '<div class="icon">✓</div><div class="filename">' + file.name + '</div><div class="hint">点击更换文件</div>';
            selectEl.classList.remove('loading');
            selectEl.classList.add('filled', type);
        }
        drawCompareWaveform(type, audioBuffer);
        analyzeComparePitchAsync(audioBuffer, type);

        // 检查是否两个音频都已选择，显示"开始对比分析"按钮
        checkAndShowCompareButton();
    } catch (error) {
        console.error('加载对比音频失败:', error);
        showToast('音频加载失败', 'error');
    }
}

async function analyzeComparePitchAsync(audioBuffer, type) {
    const sampleRate = audioBuffer.sampleRate;
    const data = audioBuffer.getChannelData(0);
    const hopLength = 512;
    const frameLength = 2048;
    const frames = Math.floor((data.length - frameLength) / hopLength);
    const pitches = [];
    for (let i = 0; i < frames; i++) {
        const start = i * hopLength;
        const frame = data.slice(start, start + frameLength);
        pitches.push(detectPitchAutocorrelation(frame, sampleRate));
    }
    AppState.compare[type].pitchData = { pitches };
    checkAndStartComparison();
}

function detectPitchAutocorrelation(frame, sampleRate) {
    const frameLength = frame.length;
    const rms = Math.sqrt(frame.reduce((sum, v) => sum + v * v, 0) / frameLength);
    if (rms < 0.01) return 0;
    const correlations = new Float32Array(frameLength);
    for (let lag = 0; lag < frameLength; lag++) {
        let sum = 0;
        for (let i = 0; i < frameLength - lag; i++) sum += frame[i] * frame[i + lag];
        correlations[lag] = sum;
    }
    const minLag = Math.floor(sampleRate / 1000);
    const maxLag = Math.floor(sampleRate / 50);
    let maxCorr = 0, maxLagIdx = 0;
    for (let lag = minLag; lag < Math.min(maxLag, frameLength); lag++) {
        if (correlations[lag] > maxCorr) { maxCorr = correlations[lag]; maxLagIdx = lag; }
    }
    return maxCorr < 0.1 ? 0 : sampleRate / maxLagIdx;
}

function drawCompareWaveform(type, audioBuffer) {
    const canvasId = type === 'standard' ? 'standardWaveCanvas' : 'userWaveCanvas';
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const data = audioBuffer.getChannelData(0);
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = (rect.width || 200) * 2;
    canvas.height = (rect.height || 80) * 2;
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = type === 'standard' ? '#10b981' : '#3b82f6';
    const step = Math.ceil(data.length / width);
    const amp = height / 2;
    for (let i = 0; i < width; i++) {
        let min = 1.0, max = -1.0;
        for (let j = 0; j < step; j++) {
            const idx = i * step + j;
            if (idx < data.length) { if (data[idx] < min) min = data[idx]; if (data[idx] > max) max = data[idx]; }
        }
        ctx.fillRect(i, (1 + min) * amp, 1, Math.max(1, (max - min) * amp));
    }
}

function checkAndStartComparison() {
    if (AppState.compare.standard.buffer && AppState.compare.user.buffer) performComparison();
}

function performComparison() {
    const stdPitch = AppState.compare.standard.pitchData;
    const userPitch = AppState.compare.user.pitchData;
    if (!stdPitch || !userPitch) { showToast('音频数据不完整', 'error'); return; }
    showToast('开始对比分析...', 'info');
    document.getElementById('compareResult').style.display = 'block';
    const result = calculateComparisonMetrics(stdPitch, userPitch);
    AppState.compare.result = result;
    updateComparisonUI(result);
}

function calculateComparisonMetrics(stdPitch, userPitch) {
    const stdPitches = stdPitch.pitches.filter(p => p > 50 && p < 1000);
    const userPitches = userPitch.pitches.filter(p => p > 50 && p < 1000);
    const pitchDiff = calculatePitchDifference(stdPitches, userPitches);
    const totalScore = Math.max(0, 100 - pitchDiff.centsError / 2);
    return { pitch: pitchDiff, totalScore, stdPitches, userPitches };
}

function calculatePitchDifference(stdPitches, userPitches) {
    if (stdPitches.length === 0 || userPitches.length === 0) return { centsError: 100, matchRate: 0 };
    const minLen = Math.min(stdPitches.length, userPitches.length);
    let totalCentsError = 0, matchCount = 0;
    for (let i = 0; i < minLen; i++) {
        const stdFreq = stdPitches[Math.floor(i * stdPitches.length / minLen)];
        const userFreq = userPitches[Math.floor(i * userPitches.length / minLen)];
        if (stdFreq > 0 && userFreq > 0) {
            const cents = 1200 * Math.log2(userFreq / stdFreq);
            totalCentsError += Math.abs(cents);
            matchCount++;
        }
    }
    return { centsError: matchCount > 0 ? totalCentsError / matchCount : 100, matchRate: minLen > 0 ? (matchCount / minLen) * 100 : 0 };
}

function updateComparisonUI(result) {
    const diffPitch = document.getElementById('diffPitch');
    if (diffPitch) diffPitch.textContent = Math.round(result.pitch.centsError) + '音分';
    const diffTotal = document.getElementById('diffTotal');
    if (diffTotal) diffTotal.textContent = Math.round(result.totalScore) + '分';
    showToast('对比分析完成', 'success');
}

/**
 * 显示"开始对比分析"按钮
 */
function showCompareStartButton() {
    let startBtn = document.getElementById('startCompareBtn');

    if (!startBtn) {
        // 创建按钮
        const compareGrid = document.querySelector('.compare-grid');
        if (compareGrid) {
            const btnContainer = document.createElement('div');
            btnContainer.className = 'compare-start-container';
            btnContainer.style.cssText = 'grid-column: 1 / -1; display: flex; justify-content: center; margin-top: 20px;';
            btnContainer.innerHTML = `
                <button id="startCompareBtn" class="btn btn-primary btn-lg" onclick="window.startBackendComparison()" style="padding: 14px 40px; font-size: 16px;">
                    🔍 开始对比分析
                </button>
            `;
            compareGrid.after(btnContainer);
        }
    }

    startBtn = document.getElementById('startCompareBtn');
    if (startBtn) {
        startBtn.style.display = 'inline-flex';
        startBtn.disabled = CompareState.isComparing;
    }
}

/**
 * 检查是否可以开始对比
 */
function checkAndShowCompareButton() {
    if (AppState.compare.standard?.file && AppState.compare.user?.file) {
        showCompareStartButton();
    }
}

/**
 * 开始后端对比分析
 */
async function startBackendComparison() {
    if (CompareState.isComparing) {
        showToast('正在分析中，请稍候...', 'warning');
        return;
    }

    const standardFile = AppState.compare.standard?.file;
    const userFile = AppState.compare.user?.file;

    if (!standardFile || !userFile) {
        showToast('请先选择标准音频和用户音频', 'error');
        return;
    }

    CompareState.isComparing = true;

    // 显示进度面板
    showCompareProgress('正在准备分析...', 0);

    // 更新按钮状态
    const startBtn = document.getElementById('startCompareBtn');
    if (startBtn) {
        startBtn.disabled = true;
        startBtn.innerHTML = '<span class="loading-spinner"></span> 分析中...';
    }

    try {
        // 1. 上传标准音频
        updateCompareProgress('正在上传标准音频...', 15);
        const standardResult = await uploadCompareFile(standardFile, 'standard');

        if (!standardResult.success) {
            throw new Error(standardResult.error || '标准音频上传失败');
        }

        CompareState.standardFilepath = standardResult.filepath;

        // 2. 上传用户音频
        updateCompareProgress('正在上传用户音频...', 35);
        const userResult = await uploadCompareFile(userFile, 'user');

        if (!userResult.success) {
            throw new Error(userResult.error || '用户音频上传失败');
        }

        CompareState.userFilepath = userResult.filepath;

        // 3. 分析标准音频
        updateCompareProgress('正在分析标准音频...', 50);
        await new Promise(resolve => setTimeout(resolve, 500)); // 模拟分析时间

        // 4. 分析用户音频
        updateCompareProgress('正在分析用户音频...', 70);
        await new Promise(resolve => setTimeout(resolve, 500)); // 模拟分析时间

        // 5. 调用对比分析API
        updateCompareProgress('正在进行对比分析...', 85);
        const compareResult = await fetch('/api/compare', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                standard_filepath: CompareState.standardFilepath,
                user_filepath: CompareState.userFilepath
            })
        });

        const compareData = await compareResult.json();

        if (!compareData.success) {
            throw new Error(compareData.error || '对比分析失败');
        }

        // 6. 完成
        updateCompareProgress('分析完成！', 100);

        // 显示对比结果
        setTimeout(() => {
            hideCompareProgress();
            displayBackendComparisonResult(compareData);
            showToast('对比分析完成！', 'success');
        }, 500);

    } catch (error) {
        console.error('对比分析失败:', error);
        hideCompareProgress();
        showToast(error.message || '对比分析失败', 'error');
    } finally {
        CompareState.isComparing = false;

        // 恢复按钮状态
        if (startBtn) {
            startBtn.disabled = false;
            startBtn.innerHTML = '🔍 开始对比分析';
        }
    }
}

/**
 * 显示对比分析进度面板
 */
function showCompareProgress(message, progress) {
    let progressPanel = document.getElementById('compareProgressPanel');

    if (!progressPanel) {
        progressPanel = document.createElement('div');
        progressPanel.id = 'compareProgressPanel';
        progressPanel.className = 'card';
        progressPanel.style.cssText = 'margin-top: 20px; padding: 20px;';

        const compareGrid = document.querySelector('.compare-grid');
        if (compareGrid) {
            compareGrid.after(progressPanel);
        }
    }

    progressPanel.style.display = 'block';
    progressPanel.innerHTML = `
        <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
            <span style="font-size: 14px; font-weight: 600;">📊 对比分析进度</span>
            <span id="compareProgressPercent" style="font-size: 14px; color: var(--primary); font-weight: 600;">${progress}%</span>
        </div>
        <div style="height: 8px; background: var(--bg-elevated); border-radius: 4px; overflow: hidden; margin-bottom: 12px;">
            <div id="compareProgressFill" style="height: 100%; background: linear-gradient(90deg, var(--primary), #10b981); width: ${progress}%; transition: width 0.3s ease;"></div>
        </div>
        <div id="compareProgressMessage" style="font-size: 13px; color: var(--text-secondary);">${escapeHtml(message)}</div>
    `;
}

/**
 * 更新对比分析进度
 */
function updateCompareProgress(message, progress) {
    const percentEl = document.getElementById('compareProgressPercent');
    const fillEl = document.getElementById('compareProgressFill');
    const messageEl = document.getElementById('compareProgressMessage');

    if (percentEl) percentEl.textContent = `${progress}%`;
    if (fillEl) fillEl.style.width = `${progress}%`;
    if (messageEl) messageEl.textContent = message;
}

/**
 * 隐藏对比分析进度面板
 */
function hideCompareProgress() {
    const progressPanel = document.getElementById('compareProgressPanel');
    if (progressPanel) {
        progressPanel.style.display = 'none';
    }
}

/**
 * 上传对比音频文件
 */
async function uploadCompareFile(file, type) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData
    });

    return await response.json();
}

/**
 * 显示后端对比分析结果
 */
function displayBackendComparisonResult(data) {
    const { standard, user, comparison } = data;

    // 显示结果面板
    const resultPanel = document.getElementById('compareResult');
    if (resultPanel) {
        resultPanel.style.display = 'block';
    }

    // 更新对比指标
    updateDiffMetric('diffPitch', comparison.pitch_diff, '分');
    updateDiffMetric('diffVolume', comparison.volume_diff, '分');
    updateDiffMetric('diffRhythm', comparison.rhythm_diff, '分');
    updateDiffMetric('diffBreath', comparison.breath_diff, '分');
    updateDiffMetric('diffTotal', comparison.total_diff, '分');

    // 更新状态指示
    updateDiffStatus('diffPitchStatus', comparison.pitch_diff);
    updateDiffStatus('diffVolumeStatus', comparison.volume_diff);
    updateDiffStatus('diffRhythmStatus', comparison.rhythm_diff);
    updateDiffStatus('diffBreathStatus', comparison.breath_diff);
    updateDiffStatus('diffTotalStatus', comparison.total_diff);

    // 更新对比表格
    const tableBody = document.getElementById('compareTableBody');
    if (tableBody) {
        const stdScores = standard.scores || {};
        const userScores = user.scores || {};

        const dimensions = [
            { key: 'volume', name: '音量', unit: '分' },
            { key: 'pitch', name: '音准', unit: '分' },
            { key: 'rhythm', name: '节奏', unit: '分' },
            { key: 'breath', name: '气息', unit: '分' },
            { key: 'emotion', name: '情感', unit: '分' }
        ];

        tableBody.innerHTML = dimensions.map(dim => {
            const stdVal = stdScores[dim.key] || 0;
            const userVal = userScores[dim.key] || 0;
            const diff = Math.abs(stdVal - userVal).toFixed(1);
            const status = getDiffStatus(diff);

            return `
                <tr>
                    <td>${dim.name}</td>
                    <td style="color:#10b981">${Math.round(stdVal)}</td>
                    <td style="color:#3b82f6">${Math.round(userVal)}</td>
                    <td style="color:${diff < 5 ? '#10b981' : diff < 10 ? '#f59e0b' : '#ef4444'}">${diff}</td>
                    <td>${status}</td>
                </tr>
            `;
        }).join('');

        // 添加总分行
        const stdTotal = standard.total_score || 0;
        const userTotal = user.total_score || 0;
        const totalDiff = Math.abs(stdTotal - userTotal).toFixed(1);

        tableBody.innerHTML += `
            <tr style="font-weight:bold;background:var(--bg-elevated)">
                <td>总分</td>
                <td style="color:#10b981">${Math.round(stdTotal)}</td>
                <td style="color:#3b82f6">${Math.round(userTotal)}</td>
                <td style="color:${totalDiff < 5 ? '#10b981' : totalDiff < 10 ? '#f59e0b' : '#ef4444'}">${totalDiff}</td>
                <td>${getDiffStatus(totalDiff)}</td>
            </tr>
        `;
    }

    // 显示建议
    displayComparisonSuggestions(comparison.suggestions);
}

/**
 * 更新差异指标显示
 */
function updateDiffMetric(elementId, value, unit) {
    const el = document.getElementById(elementId);
    if (el) {
        el.textContent = Math.round(value) + unit;
    }
}

/**
 * 更新差异状态显示
 */
function updateDiffStatus(elementId, diff) {
    const el = document.getElementById(elementId);
    if (el) {
        el.textContent = getDiffStatus(diff);
    }
}

/**
 * 获取差异状态文本
 */
function getDiffStatus(diff) {
    if (diff < 3) return '✓ 优秀';
    if (diff < 5) return '○ 良好';
    if (diff < 10) return '△ 一般';
    return '✗ 较大';
}

/**
 * 显示对比建议
 */
function displayComparisonSuggestions(suggestions) {
    let suggestionContainer = document.getElementById('compareSuggestions');

    if (!suggestionContainer) {
        suggestionContainer = document.createElement('div');
        suggestionContainer.id = 'compareSuggestions';
        suggestionContainer.className = 'card';
        suggestionContainer.style.cssText = 'margin-top: 20px;';

        const resultPanel = document.getElementById('compareResult');
        if (resultPanel) {
            resultPanel.after(suggestionContainer);
        }
    }

    if (suggestions && suggestions.length > 0) {
        suggestionContainer.innerHTML = `
            <div class="card-header">
                <span class="card-title">💡 改进建议</span>
            </div>
            <div class="card-body">
                ${suggestions.map(s => `
                    <div class="suggestion-item" style="margin-bottom: 12px; padding: 12px; background: var(--bg-elevated); border-radius: 8px; border-left: 3px solid var(--primary);">
                        <div style="font-weight: 600; margin-bottom: 4px;">${escapeHtml(s.dimension)} <span style="color: var(--text-muted); font-weight: 400;">(差距 ${s.gap}分)</span></div>
                        <div style="font-size: 13px; color: var(--text-secondary);">${escapeHtml(s.suggestion)}</div>
                    </div>
                `).join('')}
            </div>
        `;
    }
}

// 导出全局函数供HTML调用
window.startBackendComparison = startBackendComparison;

export { selectStandardAudio, selectUserAudio, handleCompareAudioSelect, loadAndAnalyzeCompareAudio, analyzeComparePitchAsync, detectPitchAutocorrelation, drawCompareWaveform, checkAndStartComparison, performComparison, calculateComparisonMetrics, calculatePitchDifference, updateComparisonUI, showCompareStartButton, checkAndShowCompareButton, startBackendComparison, displayBackendComparisonResult };
