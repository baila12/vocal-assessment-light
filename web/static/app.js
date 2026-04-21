/**
 * 声乐评估系统 - 前端应用主入口
 *
 * 模块化重构版本
 * 各功能模块位于 ./js/modules/ 目录下
 *
 * @version 4.0
 * @author Vocal Assessment Team
 */

// ============================================================================
// 模块导入
// ============================================================================

import { AppState } from './js/modules/state.js';
import { showToast, escapeHtml, formatTime, frequencyToNoteName } from './js/modules/utils.js';
import { handleFileSelect, loadAudioFileInfo, analyzeAudio, stopAnalysis } from './js/modules/upload.js';
import {
    togglePlay,
    updateProgress,
    startRealtimeUpdate,
    drawSpectrum,
    seekAudio,
    drawAllWaveforms,
    drawStaticWaveform
} from './js/modules/player.js';
import {
    startQuickRecord,
    stopRecording,
    handleRecordingComplete,
    updateRecordingUI,
    drawRecordingWaveform
} from './js/modules/recording.js';
import {
    startSeparation,
    displaySeparationResult,
    closeSeparationResult
} from './js/modules/separation.js';
import {
    loadHistory,
    viewHistoryDetail,
    deleteHistoryRecord,
    drawGrowthChart,
    calculateTrendLine,
    updateGrowthStats
} from './js/modules/history.js';
import {
    selectStandardAudio,
    selectUserAudio,
    handleCompareAudioSelect,
    loadAndAnalyzeCompareAudio,
    performComparison,
    updateComparisonUI,
    showCompareStartButton,
    checkAndShowCompareButton,
    startBackendComparison,
    displayBackendComparisonResult
} from './js/modules/compare.js';

// ============================================================================
// 全局工具函数（向后兼容）
// ============================================================================

const Utils = {
    formatTime,
    getScoreColor(score) {
        if (score >= 90) return '#10b981';
        if (score >= 80) return '#3b82f6';
        if (score >= 70) return '#f59e0b';
        if (score >= 60) return '#f97316';
        return '#ef4444';
    },
    getScoreLevel(score) {
        if (score >= 90) return '优秀';
        if (score >= 80) return '良好';
        if (score >= 70) return '中等';
        if (score >= 60) return '及格';
        return '需改进';
    }
};

// ============================================================================
// 页面导航
// ============================================================================

function showPage(pageName) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    const targetPage = document.getElementById(`page-${pageName}`);
    if (targetPage) targetPage.classList.add('active');

    document.querySelectorAll('.nav-tab').forEach(tab => tab.classList.remove('active'));

    const navTabMap = {
        'home': 'navHome',
        'compare': 'navCompare',
        'history': 'navHistory'
    };
    const activeTabId = navTabMap[pageName];
    if (activeTabId) {
        const activeTab = document.getElementById(activeTabId);
        if (activeTab) activeTab.classList.add('active');
    }

    AppState.currentPage = pageName;

    if (pageName === 'history') loadHistory();
}

// ============================================================================
// 结果显示
// ============================================================================

function displayResults(result) {
    if (!result.success) return;

    AppState.result = result;
    const totalScore = result.total_score || 0;

    document.getElementById('totalScore').textContent = Math.round(totalScore);
    document.getElementById('totalScore').style.color = Utils.getScoreColor(totalScore);
    document.getElementById('scoreLevel').textContent = result.level || Utils.getScoreLevel(totalScore);

    const scores = result.scores || {
        volume: result.volume_info?.score || 0,
        pitch: result.pitch_info?.score || 0,
        rhythm: result.rhythm_info?.score || 0,
        breath: result.breath_info?.score || 0,
        emotion: result.emotion_info?.scores ? Math.max(...Object.values(result.emotion_info.scores)) : 0
    };

    ['volume', 'pitch', 'rhythm', 'breath', 'emotion'].forEach(dim => {
        const score = scores[dim] || 0;
        const bar = document.getElementById(`dim${dim.charAt(0).toUpperCase() + dim.slice(1)}Bar`);
        const val = document.getElementById(`dim${dim.charAt(0).toUpperCase() + dim.slice(1)}`);
        if (bar) bar.style.width = `${score}%`;
        if (val) val.textContent = Math.round(score);
    });

    if (result.advice?.length > 0) {
        document.getElementById('adviceList').innerHTML = result.advice.map(a => `<li>${a}</li>`).join('');
    }

    document.getElementById('scorePanel').style.display = 'block';
    document.getElementById('realtimePanel').style.display = 'block';
    document.getElementById('adviceSection').style.display = 'block';
    document.getElementById('chartSection').style.display = 'grid';

    drawRadarChart(scores);
    drawPitchCurve(result.pitch_curve);

    if (result.visualization) displayFeatureVisualization(result.visualization);
    if (result.timbre) displayTimbreAnalysis(result.timbre);
    if (result.phrases) displayPhraseAnalysis(result.phrases);

    const exportSection = document.getElementById('exportSection');
    if (exportSection) exportSection.style.display = 'block';

    if (result.emotion_info) {
        document.getElementById('currentEmotion').textContent = result.emotion_info.dominant || '--';
    }
    if (result.rhythm_info) {
        document.getElementById('currentRhythm').textContent = Math.round(result.rhythm_info.bpm || 0);
        document.getElementById('currentBPM').textContent = Math.round(result.rhythm_info.bpm || 0);
    }
    document.getElementById('liveScore').textContent = Math.round(totalScore);
    document.getElementById('statScore').textContent = Math.round(totalScore);
}

// ============================================================================
// 图表绘制
// ============================================================================

function drawRadarChart(scores) {
    const canvas = document.getElementById('radarChart');
    if (!canvas || typeof Chart === 'undefined') return;

    const ctx = canvas.getContext('2d');

    if (window.radarChart && typeof window.radarChart.destroy === 'function') {
        window.radarChart.destroy();
    }

    window.radarChart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: ['音量', '音准', '节奏', '气息', '情绪'],
            datasets: [{
                data: [scores.volume || 0, scores.pitch || 0, scores.rhythm || 0, scores.breath || 0, scores.emotion || 0],
                fill: true,
                backgroundColor: 'rgba(59, 130, 246, 0.2)',
                borderColor: 'rgb(59, 130, 246)',
                pointBackgroundColor: 'rgb(59, 130, 246)'
            }]
        },
        options: {
            responsive: true,
            scales: { r: { beginAtZero: true, max: 100 } },
            plugins: { legend: { display: false } }
        }
    });
}

function drawPitchCurve(pitchCurve) {
    if (!pitchCurve?.frequencies) return;

    const canvas = document.getElementById('pitchCanvas');
    if (!canvas) return;

    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = (rect.width || 300) * 2;
    canvas.height = (rect.height || 100) * 2;

    const ctx = canvas.getContext('2d');
    const frequencies = pitchCurve.frequencies;
    const width = canvas.width;
    const height = canvas.height;

    ctx.clearRect(0, 0, width, height);

    const validFreqs = frequencies.filter(f => f > 50 && f < 1000);
    if (validFreqs.length === 0) return;

    const minFreq = Math.min(...validFreqs) * 0.9;
    const maxFreq = Math.max(...validFreqs) * 1.1;

    document.getElementById('pitchRange').textContent = `${Math.round(minFreq)} Hz ~ ${Math.round(maxFreq)} Hz`;

    ctx.strokeStyle = '#3b82f6';
    ctx.lineWidth = 2;
    ctx.beginPath();

    let started = false;
    for (let i = 0; i < frequencies.length; i++) {
        const freq = frequencies[i];
        if (freq < 50 || freq > 1000) continue;

        const x = (i / frequencies.length) * width;
        const y = height - ((freq - minFreq) / (maxFreq - minFreq)) * height;

        if (!started) { ctx.moveTo(x, y); started = true; }
        else ctx.lineTo(x, y);
    }
    ctx.stroke();
}

// ============================================================================
// 可视化展示
// ============================================================================

function displayFeatureVisualization(data) {
    const container = document.getElementById('featureVisualization');
    if (!container || !data) return;

    container.style.display = 'block';

    const combinedImg = container.querySelector('.viz-combined img');
    if (combinedImg && data.combined) combinedImg.src = data.combined;

    const spectrogramImg = container.querySelector('.viz-spectrogram img');
    if (spectrogramImg && data.spectrogram) spectrogramImg.src = data.spectrogram;

    const pitchImg = container.querySelector('.viz-pitch img');
    if (pitchImg && data.pitch_trajectory) pitchImg.src = data.pitch_trajectory;

    const energyImg = container.querySelector('.viz-energy img');
    if (energyImg && data.energy) energyImg.src = data.energy;
}

function displayTimbreAnalysis(timbreData) {
    const section = document.getElementById('timbreSection');
    if (!section || !timbreData) return;

    section.style.display = 'block';

    const styleEl = document.getElementById('timbreStyle');
    if (styleEl) styleEl.textContent = timbreData.style || '中性音色';

    const brightness = (timbreData.brightness || 0) * 100;
    document.getElementById('timbreBrightness').textContent = Math.round(brightness) + '%';
    document.getElementById('timbreBrightnessBar').style.width = brightness + '%';

    const warmth = (timbreData.warmth || 0) * 100;
    document.getElementById('timbreWarmth').textContent = Math.round(warmth) + '%';
    document.getElementById('timbreWarmthBar').style.width = warmth + '%';

    const nasality = (timbreData.nasality || 0) * 100;
    document.getElementById('timbreNasality').textContent = Math.round(nasality) + '%';
    document.getElementById('timbreNasalityBar').style.width = nasality + '%';

    const breathiness = (timbreData.breathiness || 0) * 100;
    document.getElementById('timbreBreathiness').textContent = Math.round(breathiness) + '%';
    document.getElementById('timbreBreathinessBar').style.width = breathiness + '%';

    document.getElementById('timbreHNR').textContent = (timbreData.hnr || 0).toFixed(1) + ' dB';
    document.getElementById('timbreVibratoRate').textContent = (timbreData.vibrato_rate || 0).toFixed(1) + ' Hz';
    document.getElementById('timbreVibratoCount').textContent = timbreData.vibrato_count || 0;
}

function displayPhraseAnalysis(phraseData) {
    const section = document.getElementById('phraseSection');
    if (!section || !phraseData) return;

    section.style.display = 'block';

    const summaryEl = document.getElementById('phraseSummary');
    if (summaryEl) {
        summaryEl.textContent = `共 ${phraseData.total} 句，平均 ${phraseData.avg_score} 分`;
    }

    const listEl = document.getElementById('phraseList');
    if (!listEl) return;

    listEl.innerHTML = '';

    const items = phraseData.items || [];
    items.forEach((phrase, idx) => {
        const isBest = idx === phraseData.best_phrase_id;
        const isWorst = idx === phraseData.worst_phrase_id;
        const scoreColor = Utils.getScoreColor(phrase.total);

        const itemEl = document.createElement('div');
        itemEl.className = 'phrase-item';
        itemEl.style.cssText = `
            padding: 12px;
            background: var(--bg-elevated);
            border-radius: 8px;
            border-left: 3px solid ${scoreColor};
            ${isBest ? 'box-shadow: 0 0 0 1px var(--success);' : ''}
            ${isWorst ? 'box-shadow: 0 0 0 1px var(--danger);' : ''}
        `;

        itemEl.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-size:14px; font-weight:600;">第 ${phrase.id + 1} 句</span>
                    <span style="font-size:12px; color:var(--text-muted);">${formatTime(phrase.start)} - ${formatTime(phrase.end)}</span>
                    ${isBest ? '<span style="padding:2px 6px; background:var(--success-light); color:var(--success); border-radius:4px; font-size:11px;">最佳</span>' : ''}
                    ${isWorst ? '<span style="padding:2px 6px; background:var(--danger-light); color:var(--danger); border-radius:4px; font-size:11px;">待改进</span>' : ''}
                </div>
                <div style="font-size:18px; font-weight:700; color:${scoreColor};">${phrase.total}</div>
            </div>
            <div style="display:grid; grid-template-columns:repeat(5, 1fr); gap:4px; margin-bottom:8px;">
                <div style="text-align:center;"><div style="font-size:10px; color:var(--text-muted);">音量</div><div style="font-size:12px; font-weight:600;">${phrase.scores.volume}</div></div>
                <div style="text-align:center;"><div style="font-size:10px; color:var(--text-muted);">音准</div><div style="font-size:12px; font-weight:600;">${phrase.scores.pitch}</div></div>
                <div style="text-align:center;"><div style="font-size:10px; color:var(--text-muted);">节奏</div><div style="font-size:12px; font-weight:600;">${phrase.scores.rhythm}</div></div>
                <div style="text-align:center;"><div style="font-size:10px; color:var(--text-muted);">气息</div><div style="font-size:12px; font-weight:600;">${phrase.scores.breath}</div></div>
                <div style="text-align:center;"><div style="font-size:10px; color:var(--text-muted);">情绪</div><div style="font-size:12px; font-weight:600;">${phrase.scores.emotion}</div></div>
            </div>
            ${phrase.advice && phrase.advice.length > 0 ? `
                <div style="font-size:12px; color:var(--text-secondary); padding-top:8px; border-top:1px solid var(--border);">
                    ${phrase.advice.map(a => `<span style="margin-right:8px;">💡 ${a}</span>`).join('')}
                </div>
            ` : ''}
        `;

        listEl.appendChild(itemEl);
    });
}

// ============================================================================
// 导出报告
// ============================================================================

async function exportReport(format) {
    if (!AppState.result) {
        showToast('请先分析音频', 'warning');
        return;
    }

    try {
        showToast('正在生成报告...', 'info');

        const response = await fetch('/api/report', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                analysis_result: AppState.result,
                filename: AppState.audio.name.replace(/\.[^.]+$/, ''),
                format: format
            })
        });

        const result = await response.json();

        if (!result.success) {
            throw new Error(result.error || '报告生成失败');
        }

        const reportPath = result.pdf_path || result.image_path;
        if (reportPath) {
            const link = document.createElement('a');
            link.href = reportPath;
            link.download = reportPath.split('/').pop();
            link.click();
            showToast('报告已生成并开始下载', 'success');
        }

    } catch (error) {
        console.error('导出报告失败:', error);
        showToast(error.message || '导出失败', 'error');
    }
}

// ============================================================================
// 加载/保存状态（页面跳转支持）
// ============================================================================

function showLoading(title, message) {
    const overlay = document.getElementById('loadingOverlay');
    const titleEl = document.getElementById('loadingTitle');
    const msgEl = document.getElementById('loadingMessage');

    if (overlay) overlay.style.display = 'flex';
    if (titleEl) titleEl.textContent = title || '加载中...';
    if (msgEl) msgEl.textContent = message || '';
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) overlay.style.display = 'none';
}

// ============================================================================
// 全局函数导出（向后兼容）
// ============================================================================

window.AppState = AppState;
window.Utils = Utils;
window.showToast = showToast;
window.escapeHtml = escapeHtml;
window.showPage = showPage;

window.handleFileSelect = handleFileSelect;
window.analyzeAudio = analyzeAudio;
window.togglePlay = togglePlay;
window.seekAudio = seekAudio;
window.stopAnalysis = stopAnalysis;

window.startQuickRecord = startQuickRecord;
window.stopRecording = stopRecording;

window.startSeparation = startSeparation;
window.displaySeparationResult = displaySeparationResult;
window.closeSeparationResult = closeSeparationResult;

window.loadHistory = loadHistory;
window.viewHistoryDetail = viewHistoryDetail;
window.deleteHistoryRecord = deleteHistoryRecord;
window.filterHistory = (filter) => {
    fetch(`/api/history?date=${filter}`)
        .then(r => r.json())
        .then(data => {
            const container = document.getElementById('historyGrid');
            if (!container || !data.history) return;

            drawGrowthChart(data.history);
            updateGrowthStats(data.history);

            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.filter === filter);
            });

            if (data.history.length === 0) {
                container.innerHTML = '<p style="color:var(--text-muted);text-align:center;grid-column:1/-1;">暂无记录</p>';
                return;
            }

            container.innerHTML = data.history.map(h => `
                <div class="history-card" data-id="${h.id}" onclick="viewHistoryDetail(${h.id})">
                    <div class="filename">${escapeHtml(h.filename) || '未知'}</div>
                    <div class="score" style="color:${Utils.getScoreColor(h.total_score || 0)}">${Math.round(h.total_score || 0)}分</div>
                    <div class="time">${h.timestamp || ''}</div>
                    <button class="delete-btn" onclick="event.stopPropagation(); deleteHistoryRecord(${h.id})" title="删除">×</button>
                </div>
            `).join('');
        })
        .catch(e => console.error('筛选历史失败:', e));
};

window.selectStandardAudio = selectStandardAudio;
window.selectUserAudio = selectUserAudio;
window.exportReport = exportReport;
window.switchVisualizationTab = (tabName) => {
    const tabs = document.querySelectorAll('.viz-tabs .viz-tab');
    const panels = document.querySelectorAll('.viz-panel');
    tabs.forEach(tab => tab.classList.toggle('active', tab.dataset.tab === tabName));
    panels.forEach(panel => panel.classList.toggle('active', panel.dataset.panel === tabName));
};

// ============================================================================
// 初始化
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('Vocal Assessment System Initialized (Modular)');

    // 文件输入
    document.getElementById('fileInput')?.addEventListener('change', handleFileSelect);

    // 播放按钮
    document.getElementById('playBtn')?.addEventListener('click', togglePlay);

    // 波形进度条点击
    document.getElementById('waveformProgress')?.addEventListener('click', seekAudio);

    // 分析按钮
    document.getElementById('analyzeBtn')?.addEventListener('click', analyzeAudio);

    // 停止分析按钮
    document.getElementById('stopAnalyzeBtn')?.addEventListener('click', stopAnalysis);
});
