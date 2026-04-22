/**
 * 分析页面 JavaScript
 * 负责展示分析结果、音频播放、可视化等
 */

// ==================== 全局状态 ====================
const AnalysisState = {
    result: null,          // 分析结果
    audioElement: null,    // 音频元素
    audioContext: null,    // AudioContext
    analyser: null,        // 分析器节点
    isPlaying: false,      // 播放状态
    animationId: null,     // 动画ID
    analysisInProgress: false  // 分析是否在进行中
};

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', async () => {
    // 检查是否有待处理的分析请求（从首页跳转过来）
    const pendingAnalysis = sessionStorage.getItem('pendingAnalysis');
    const resultJson = sessionStorage.getItem('analysisResult');

    if (pendingAnalysis === 'true' && !resultJson) {
        // 需要进行新的分析
        await performAnalysis();
    } else if (resultJson) {
        // 已有分析结果，直接显示
        try {
            AnalysisState.result = JSON.parse(resultJson);
            displayResults(AnalysisState.result);
        } catch (e) {
            showToast('分析结果解析失败', 'error');
            console.error(e);
        }
    } else {
        // 没有任何数据，返回首页
        showToast('未找到分析数据，请重新上传音频', 'error');
        setTimeout(() => window.location.href = '/', 2000);
        return;
    }

    // 初始化事件监听
    initEventListeners();
});

// ==================== 执行分析 ====================
async function performAnalysis() {
    const fileInfoStr = sessionStorage.getItem('analysisFileInfo');

    if (!fileInfoStr) {
        showToast('缺少文件信息，请重新上传', 'error');
        setTimeout(() => window.location.href = '/', 2000);
        return;
    }

    // 显示分析进度
    showAnalysisProgress();

    try {
        // 从 IndexedDB 获取文件数据
        const fileData = await getFileFromStorage();
        if (!fileData) {
            throw new Error('无法获取文件数据，请重新上传');
        }

        const fileInfo = JSON.parse(fileInfoStr);
        const file = new File([fileData.fileData], fileData.fileName, { type: fileData.fileType });

        // 上传并分析
        const formData = new FormData();
        formData.append('file', file);

        // 获取评估模式（从 sessionStorage 或 IndexedDB 数据）
        const evalMode = fileData.evalMode || sessionStorage.getItem('evalMode') || 'quick';
        formData.append('mode', evalMode);

        // 更新进度提示
        const modeText = evalMode === 'professional' ? '专业评估' : '快速评估';
        updateAnalysisProgress(15, `正在进行${modeText}...`);

        // 使用 AbortController 设置超时 (10分钟)
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 600000);

        updateAnalysisProgress(10, '正在上传文件...');

        const uploadResponse = await fetch('/api/upload', {
            method: 'POST',
            body: formData,
            signal: controller.signal
        });

        clearTimeout(timeoutId);

        if (!uploadResponse.ok) {
            throw new Error(`服务器响应错误: ${uploadResponse.status}`);
        }

        const data = await uploadResponse.json();

        // 隐藏分析进度
        hideAnalysisProgress();

        if (data.success) {
            // 保存结果
            AnalysisState.result = data;
            sessionStorage.setItem('analysisResult', JSON.stringify(data));
            sessionStorage.removeItem('pendingAnalysis');

            // 显示结果
            displayResults(data);
            showToast('分析完成', 'success');

            // 清理 IndexedDB 中的文件数据
            clearFileFromStorage().catch(() => {});
        } else {
            throw new Error(data.error || '分析失败');
        }
    } catch (error) {
        hideAnalysisProgress();
        console.error('分析错误:', error);

        // 处理不同类型的错误
        let errorMessage = '分析失败';
        if (error.name === 'AbortError') {
            errorMessage = '请求超时，请尝试较小的文件';
        } else if (error.message.includes('Failed to fetch')) {
            errorMessage = '网络连接失败，请检查服务器状态';
        } else if (error.message) {
            errorMessage = error.message;
        }

        showToast(errorMessage, 'error');
        showAnalysisError(errorMessage);
    }
}

// ==================== IndexedDB 文件读取 ====================
function getFileFromStorage() {
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
            const transaction = db.transaction(['files'], 'readonly');
            const store = transaction.objectStore('files');
            const getRequest = store.get('pendingFile');

            getRequest.onsuccess = () => {
                resolve(getRequest.result);
            };
            getRequest.onerror = () => reject(getRequest.error);
        };
    });
}

// 清理 IndexedDB 中的文件
function clearFileFromStorage() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('VocalAnalysisDB', 1);

        request.onsuccess = (event) => {
            const db = event.target.result;
            const transaction = db.transaction(['files'], 'readwrite');
            const store = transaction.objectStore('files');
            store.delete('pendingFile');

            transaction.oncomplete = () => resolve();
            transaction.onerror = () => reject(transaction.error);
        };
    });
}

// ==================== 显示分析进度 ====================
function showAnalysisProgress() {
    AnalysisState.analysisInProgress = true;

    // 创建进度遮罩
    const overlay = document.createElement('div');
    overlay.id = 'analysisOverlay';
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(15, 15, 35, 0.95);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        z-index: 1000;
    `;

    overlay.innerHTML = `
        <div style="text-align: center;">
            <div style="font-size: 48px; margin-bottom: 20px;">🎵</div>
            <div style="font-size: 24px; color: #fff; margin-bottom: 10px;">正在分析音频...</div>
            <div style="font-size: 14px; color: #94a3b8; margin-bottom: 30px;">这可能需要几秒到几分钟</div>
            <div style="width: 300px; height: 6px; background: rgba(255,255,255,0.1); border-radius: 3px; overflow: hidden;">
                <div id="analysisProgressBar" style="width: 0%; height: 100%; background: linear-gradient(90deg, #3b82f6, #8b5cf6); border-radius: 3px; transition: width 0.3s;"></div>
            </div>
            <div id="analysisProgressText" style="font-size: 12px; color: #64748b; margin-top: 10px;">准备中...</div>
        </div>
    `;

    document.body.appendChild(overlay);

    // 模拟进度
    let progress = 0;
    AnalysisState.progressInterval = setInterval(() => {
        if (progress < 90) {
            progress += Math.random() * 5;
            progress = Math.min(90, progress);
            updateAnalysisProgress(progress, `分析中... ${Math.round(progress)}%`);
        }
    }, 500);
}

function updateAnalysisProgress(percent, text) {
    const progressBar = document.getElementById('analysisProgressBar');
    const progressText = document.getElementById('analysisProgressText');

    if (progressBar) progressBar.style.width = `${percent}%`;
    if (progressText) progressText.textContent = text;
}

function hideAnalysisProgress() {
    AnalysisState.analysisInProgress = false;

    if (AnalysisState.progressInterval) {
        clearInterval(AnalysisState.progressInterval);
        AnalysisState.progressInterval = null;
    }

    const overlay = document.getElementById('analysisOverlay');
    if (overlay) {
        overlay.remove();
    }
}

function showAnalysisError(message) {
    // 显示错误，允许用户返回首页
    const overlay = document.getElementById('analysisOverlay');
    if (overlay) {
        overlay.innerHTML = `
            <div style="text-align: center;">
                <div style="font-size: 48px; margin-bottom: 20px;">❌</div>
                <div style="font-size: 24px; color: #ef4444; margin-bottom: 10px;">分析失败</div>
                <div style="font-size: 14px; color: #94a3b8; margin-bottom: 30px;">${message}</div>
                <button onclick="window.location.href='/'" style="padding: 12px 30px; background: #3b82f6; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 16px;">
                    返回首页
                </button>
            </div>
        `;
    }
}

// ==================== 事件监听 ====================
function initEventListeners() {
    // 播放按钮
    const playBtn = document.getElementById('playBtn');
    if (playBtn) {
        playBtn.addEventListener('click', togglePlay);
    }

    // 进度条
    const progressBar = document.getElementById('progressBar');
    if (progressBar) {
        progressBar.addEventListener('click', seekAudio);
    }

    // 可视化标签页
    document.querySelectorAll('.viz-tab').forEach(tab => {
        tab.addEventListener('click', () => switchVizTab(tab.dataset.tab));
    });

    // 人声分离
    const separateBtn = document.getElementById('separateBtn');
    if (separateBtn) {
        separateBtn.addEventListener('click', separateVocals);
    }

    // 导出按钮
    const exportPdfBtn = document.getElementById('exportPdfBtn');
    const exportImageBtn = document.getElementById('exportImageBtn');
    if (exportPdfBtn) {
        exportPdfBtn.addEventListener('click', () => exportReport('pdf'));
    }
    if (exportImageBtn) {
        exportImageBtn.addEventListener('click', () => exportReport('image'));
    }
}

// ==================== 显示结果 ====================
function displayResults(result) {
    // 检查是否为有效人声
    if (result.is_voice === false) {
        displayVoiceQualityWarning(result);
    }

    // 基本信息
    if (result.basic_info) {
        document.getElementById('fileName').textContent = result.basic_info.filename || '--';
        document.getElementById('fileDuration').textContent = result.basic_info.duration || '--:--';
        document.getElementById('fileSize').textContent = result.basic_info.file_size || '--';
    }

    // 总分
    const totalScore = result.total_score || 0;
    document.getElementById('totalScore').textContent = Math.round(totalScore);
    document.getElementById('levelText').textContent = result.level || '--';
    document.getElementById('stars').textContent = result.stars || '☆☆☆☆☆';

    // 更新分数圆圈颜色
    const scoreCircle = document.getElementById('scoreCircle');
    if (scoreCircle && result.color) {
        scoreCircle.style.background = `linear-gradient(135deg, ${result.color} 0%, ${adjustColor(result.color, -20)} 100%)`;
    }

    // 五维评分
    if (result.scores) {
        displayScores(result.scores);
    }

    // 改进建议
    if (result.advice) {
        displayAdvice(result.advice);
    }

    // 可视化图片
    if (result.visualization) {
        displayVisualization(result.visualization);
    }

    // 音色分析
    if (result.timbre) {
        displayTimbre(result.timbre);
    }

    // 逐句评分
    if (result.phrases) {
        displayPhrases(result.phrases);
    }

    // 显示导出区域
    const exportSection = document.getElementById('exportSection');
    if (exportSection && result.is_voice !== false) {
        exportSection.style.display = 'block';
    }

    // 显示人声分离卡片
    const separationCard = document.getElementById('separationCard');
    if (separationCard && result.filepath) {
        separationCard.style.display = 'block';
    }

    // 初始化音频播放器
    if (result.filepath) {
        initAudioPlayer(result.filepath);
    }
}

// ==================== 显示人声质量警告 ====================
function displayVoiceQualityWarning(result) {
    const warningDiv = document.getElementById('voiceQualityWarning');
    const warningMessage = document.getElementById('warningMessage');
    const warningSuggestions = document.getElementById('warningSuggestions');

    if (!warningDiv) return;

    warningDiv.style.display = 'flex';

    if (result.voice_quality && result.voice_quality.warnings) {
        warningMessage.textContent = result.voice_quality.warnings.join('；') || '音频质量不符合评估要求';
    }

    if (result.voice_quality && result.voice_quality.suggestions) {
        warningSuggestions.innerHTML = result.voice_quality.suggestions
            .map(s => `<li>${s}</li>`)
            .join('');
    }

    // 隐藏导出按钮
    const exportSection = document.getElementById('exportSection');
    if (exportSection) {
        exportSection.style.display = 'none';
    }
}

// ==================== 显示五维评分 ====================
function displayScores(scores) {
    // 新的环形评分显示
    const dimensions = [
        { key: 'pitch', ringId: 'pitchRing', displayId: 'pitchScoreDisplay' },
        { key: 'rhythm', ringId: 'rhythmRing', displayId: 'rhythmScoreDisplay' },
        { key: 'breath', ringId: 'breathRing', displayId: 'breathScoreDisplay' },
        { key: 'technique', ringId: 'techniqueRing', displayId: 'techniqueScoreDisplay' },
        { key: 'artistry', ringId: 'artistryRing', displayId: 'artistryScoreDisplay' }
    ];

    // 映射旧字段名到新字段名
    const scoreMapping = {
        pitch: scores.pitch || 0,
        rhythm: scores.rhythm || 0,
        breath: scores.breath || 0,
        technique: scores.volume || 0,  // volume -> technique
        artistry: scores.emotion || 0   // emotion -> artistry
    };

    dimensions.forEach(dim => {
        const value = scoreMapping[dim.key];
        const ring = document.getElementById(dim.ringId);
        const display = document.getElementById(dim.displayId);

        // 更新环形进度 (周长 = 2 * π * r = 2 * 3.14159 * 34 ≈ 214)
        if (ring) {
            const circumference = 214;
            const offset = circumference * (1 - value / 100);
            ring.style.strokeDashoffset = offset;
        }

        // 更新数值显示
        if (display) {
            display.textContent = Math.round(value);
        }
    });

    // 更新总分环形
    const totalScore = AnalysisState.result?.total_score || 0;
    const scoreRingFill = document.getElementById('scoreRingFill');
    if (scoreRingFill) {
        const circumference = 327; // 2 * π * 52
        const offset = circumference * (1 - totalScore / 100);
        scoreRingFill.style.strokeDashoffset = offset;
    }

    // 兼容旧的进度条显示（如果存在）
    const oldDimensions = ['volume', 'pitch', 'rhythm', 'breath', 'emotion'];
    oldDimensions.forEach(dim => {
        const value = scores[dim] || 0;
        const bar = document.getElementById(`${dim}ScoreBar`);
        const valueEl = document.getElementById(`${dim}Score`);

        if (bar) {
            bar.style.width = `${Math.min(100, value)}%`;
            bar.style.background = getScoreGradient(value);
        }
        if (valueEl) {
            valueEl.textContent = Math.round(value);
        }
    });

    // 绘制雷达图
    drawRadarChart(scores);
}

// ==================== 显示建议 ====================
function displayAdvice(advice) {
    const list = document.getElementById('adviceList');
    if (!list) return;

    list.innerHTML = advice.map(item => `<li>${item}</li>`).join('');
}

// ==================== 显示可视化 ====================
function displayVisualization(viz) {
    // 检查是否有任何可视化数据
    const hasVisualization = viz && (viz.spectrogram || viz.pitch_trajectory || viz.energy);

    if (!hasVisualization) {
        console.warn('No visualization data available');
        // 显示占位符
        const spectrogramImg = document.getElementById('spectrogramImg');
        const pitchImg = document.getElementById('pitchImg');
        const energyImg = document.getElementById('energyImg');

        if (spectrogramImg) spectrogramImg.style.display = 'none';
        if (pitchImg) pitchImg.style.display = 'none';
        if (energyImg) energyImg.style.display = 'none';

        // 显示提示文本
        const spectrogramPanel = document.getElementById('spectrogramPanel');
        if (spectrogramPanel && !spectrogramPanel.querySelector('.no-data')) {
            const noData = document.createElement('div');
            noData.className = 'no-data';
            noData.style.cssText = 'padding:40px;text-align:center;color:var(--text-muted);';
            noData.textContent = '暂无频谱数据';
            spectrogramPanel.appendChild(noData);
        }
        return;
    }

    // 频谱图
    const spectrogramImg = document.getElementById('spectrogramImg');
    if (spectrogramImg) {
        if (viz.spectrogram) {
            spectrogramImg.src = viz.spectrogram;
            spectrogramImg.style.display = 'block';
            spectrogramImg.onerror = function() {
                this.style.display = 'none';
                console.warn('Failed to load spectrogram image');
            };
        } else {
            spectrogramImg.style.display = 'none';
        }
    }

    // 基音轨迹
    const pitchImg = document.getElementById('pitchImg');
    if (pitchImg) {
        if (viz.pitch_trajectory) {
            pitchImg.src = viz.pitch_trajectory;
            pitchImg.style.display = 'block';
            pitchImg.onerror = function() {
                this.style.display = 'none';
                console.warn('Failed to load pitch trajectory image');
            };
        } else {
            pitchImg.style.display = 'none';
        }
    }

    // 能量曲线
    const energyImg = document.getElementById('energyImg');
    if (energyImg) {
        if (viz.energy) {
            energyImg.src = viz.energy;
            energyImg.style.display = 'block';
            energyImg.onerror = function() {
                this.style.display = 'none';
                console.warn('Failed to load energy image');
            };
        } else {
            energyImg.style.display = 'none';
        }
    }
}

// ==================== 显示音色分析 ====================
function displayTimbre(timbre) {
    const section = document.getElementById('timbreSection');
    if (!section) return;

    section.style.display = 'block';

    document.getElementById('timbreBrightness').textContent = (timbre.brightness || 0).toFixed(1);
    document.getElementById('timbreWarmth').textContent = (timbre.warmth || 0).toFixed(1);
    document.getElementById('timbreNasality').textContent = (timbre.nasality || 0).toFixed(1);
    document.getElementById('timbreBreathiness').textContent = (timbre.breathiness || 0).toFixed(1);
    document.getElementById('timbreHNR').textContent = (timbre.hnr || 0).toFixed(1) + ' dB';
    document.getElementById('timbreVibratoRate').textContent = (timbre.vibrato_rate || 0).toFixed(1) + ' Hz';
    document.getElementById('timbreStyle').textContent = timbre.style || '--';
}

// ==================== 显示逐句评分 ====================
function displayPhrases(phrases) {
    const section = document.getElementById('phraseSection');
    if (!section || !phrases) return;

    section.style.display = 'block';

    const summary = document.getElementById('phraseSummary');
    if (summary) {
        summary.textContent = `共 ${phrases.total} 句，平均 ${phrases.avg_score} 分`;
    }

    const list = document.getElementById('phraseList');
    if (!list || !phrases.items) return;

    list.innerHTML = phrases.items.map((phrase, idx) => {
        const isBest = idx === phrases.best_phrase_id;
        const isWorst = idx === phrases.worst_phrase_id;
        const scoreColor = getScoreColor(phrase.total);

        return `
            <div class="phrase-item" style="padding:12px;background:var(--bg-elevated);border-radius:8px;border-left:3px solid ${scoreColor};${isBest ? 'box-shadow:0 0 0 1px var(--success);' : ''}${isWorst ? 'box-shadow:0 0 0 1px var(--danger);' : ''}">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                    <span style="font-size:14px;font-weight:600;">第 ${phrase.id + 1} 句</span>
                    <span style="font-size:16px;font-weight:700;color:${scoreColor};">${phrase.total}</span>
                </div>
                <div style="display:flex;gap:8px;font-size:12px;color:var(--text-muted);">
                    <span>音量:${phrase.scores.volume}</span>
                    <span>音准:${phrase.scores.pitch}</span>
                    <span>节奏:${phrase.scores.rhythm}</span>
                    <span>气息:${phrase.scores.breath}</span>
                </div>
            </div>
        `;
    }).join('');
}

// ==================== 音频播放器 ====================
function initAudioPlayer(filepath) {
    // 通过 API 获取音频文件（避免 file:// 协议限制）
    const audioUrl = `/api/audio?file=${encodeURIComponent(filepath)}`;

    // 创建音频元素
    AnalysisState.audioElement = new Audio(audioUrl);
    AnalysisState.audioElement.crossOrigin = 'anonymous';

    AnalysisState.audioElement.addEventListener('loadedmetadata', () => {
        updateTimeDisplay();
    });

    AnalysisState.audioElement.addEventListener('timeupdate', () => {
        updateProgress();
        updateTimeDisplay();
    });

    AnalysisState.audioElement.addEventListener('ended', () => {
        AnalysisState.isPlaying = false;
        updatePlayButton();
    });

    AnalysisState.audioElement.addEventListener('error', (e) => {
        console.error('音频加载失败:', e);
        showToast('音频加载失败，请检查文件路径', 'error');
    });
}

function togglePlay() {
    if (!AnalysisState.audioElement) return;

    if (AnalysisState.isPlaying) {
        AnalysisState.audioElement.pause();
        AnalysisState.isPlaying = false;
        if (AnalysisState.animationId) {
            cancelAnimationFrame(AnalysisState.animationId);
        }
    } else {
        // 初始化 AudioContext（首次播放时）
        if (!AnalysisState.audioContext) {
            initAudioContext();
        }
        AnalysisState.audioElement.play();
        AnalysisState.isPlaying = true;
        startVisualization();
    }

    updatePlayButton();
}

function initAudioContext() {
    AnalysisState.audioContext = new (window.AudioContext || window.webkitAudioContext)();
    AnalysisState.analyser = AnalysisState.audioContext.createAnalyser();
    AnalysisState.analyser.fftSize = 256;

    const source = AnalysisState.audioContext.createMediaElementSource(AnalysisState.audioElement);
    source.connect(AnalysisState.analyser);
    AnalysisState.analyser.connect(AnalysisState.audioContext.destination);
}

function updatePlayButton() {
    const playBtn = document.getElementById('playBtn');
    if (!playBtn) return;

    const iconPlay = playBtn.querySelector('.icon-play');
    const iconPause = playBtn.querySelector('.icon-pause');

    if (AnalysisState.isPlaying) {
        iconPlay.style.display = 'none';
        iconPause.style.display = 'block';
    } else {
        iconPlay.style.display = 'block';
        iconPause.style.display = 'none';
    }
}

function updateProgress() {
    const progressFill = document.getElementById('progressFill');
    if (!progressFill || !AnalysisState.audioElement) return;

    const progress = (AnalysisState.audioElement.currentTime / AnalysisState.audioElement.duration) * 100;
    progressFill.style.width = `${progress}%`;
}

function updateTimeDisplay() {
    const timeDisplay = document.getElementById('timeDisplay');
    if (!timeDisplay || !AnalysisState.audioElement) return;

    const current = formatTime(AnalysisState.audioElement.currentTime);
    const total = formatTime(AnalysisState.audioElement.duration || 0);
    timeDisplay.textContent = `${current} / ${total}`;
}

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function seekAudio(e) {
    if (!AnalysisState.audioElement) return;

    const rect = e.target.getBoundingClientRect();
    const percent = (e.clientX - rect.left) / rect.width;
    AnalysisState.audioElement.currentTime = percent * AnalysisState.audioElement.duration;
}

// ==================== 实时可视化 ====================
function startVisualization() {
    if (!AnalysisState.analyser) return;

    const canvas = document.getElementById('waveformCanvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const bufferLength = AnalysisState.analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    function draw() {
        if (!AnalysisState.isPlaying) return;

        AnalysisState.animationId = requestAnimationFrame(draw);

        AnalysisState.analyser.getByteFrequencyData(dataArray);

        // 清空画布
        ctx.fillStyle = 'rgba(15, 15, 35, 1)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // 绘制频谱
        const barWidth = (canvas.width / bufferLength) * 2.5;
        let x = 0;

        for (let i = 0; i < bufferLength; i++) {
            const barHeight = (dataArray[i] / 255) * canvas.height * 0.8;

            const gradient = ctx.createLinearGradient(0, canvas.height - barHeight, 0, canvas.height);
            gradient.addColorStop(0, '#667eea');
            gradient.addColorStop(1, '#764ba2');

            ctx.fillStyle = gradient;
            ctx.fillRect(x, canvas.height - barHeight, barWidth - 1, barHeight);

            x += barWidth;
        }

        // 更新实时信息
        updateLiveInfo(dataArray);
    }

    draw();
}

function updateLiveInfo(dataArray) {
    // 计算音量
    const sum = dataArray.reduce((a, b) => a + b, 0);
    const avg = sum / dataArray.length;
    const volumePercent = Math.round((avg / 255) * 100);

    const volumeBar = document.getElementById('volumeBar');
    const volumeValue = document.getElementById('volumeValue');
    if (volumeBar) volumeBar.style.width = `${volumePercent}%`;
    if (volumeValue) volumeValue.textContent = `${volumePercent}%`;
}

// ==================== 可视化标签页切换 ====================
function switchVizTab(tabName) {
    // 更新标签页状态
    document.querySelectorAll('.viz-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });

    // 更新面板显示
    document.querySelectorAll('.viz-panel').forEach(panel => {
        panel.classList.toggle('active', panel.id === `${tabName}Panel`);
    });
}

// ==================== 人声分离 ====================
async function separateVocals() {
    const separateBtn = document.getElementById('separateBtn');
    const separationResult = document.getElementById('separationResult');

    if (!AnalysisState.result || !AnalysisState.result.filepath) {
        showToast('请先上传音频', 'error');
        return;
    }

    separateBtn.disabled = true;
    separateBtn.textContent = '分离中...';

    try {
        const response = await fetch('/api/separate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                filepath: AnalysisState.result.filepath,
                model: document.getElementById('separationModel').value
            })
        });

        const data = await response.json();

        if (data.success) {
            // 显示分离结果
            separationResult.style.display = 'block';

            const vocalsAudio = document.getElementById('vocalsAudio');
            const accompAudio = document.getElementById('accompAudio');

            if (data.vocals_path) vocalsAudio.src = data.vocals_path;
            if (data.accompaniment_path) accompAudio.src = data.accompaniment_path;

            showToast('人声分离完成', 'success');
        } else {
            showToast(data.error || '分离失败', 'error');
        }
    } catch (e) {
        showToast('分离请求失败', 'error');
        console.error(e);
    } finally {
        separateBtn.disabled = false;
        separateBtn.textContent = '分离人声';
    }
}

// ==================== 导出报告 ====================
async function exportReport(format) {
    if (!AnalysisState.result) {
        showToast('没有分析结果', 'error');
        return;
    }

    try {
        const response = await fetch('/api/report', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                analysis_result: AnalysisState.result,
                filename: AnalysisState.result.basic_info?.filename || 'report',
                format: format
            })
        });

        const data = await response.json();

        if (data.success) {
            const path = format === 'pdf' ? data.pdf_path : data.image_path;
            if (path) {
                window.open(path, '_blank');
                showToast('报告生成成功', 'success');
            }
        } else {
            showToast(data.error || '生成失败', 'error');
        }
    } catch (e) {
        showToast('导出请求失败', 'error');
        console.error(e);
    }
}

// ==================== 雷达图 ====================
function drawRadarChart(scores) {
    const canvas = document.getElementById('radarChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');

    // 销毁已有图表
    if (window.radarChartInstance) {
        window.radarChartInstance.destroy();
    }

    // 使用新的五维评分标签
    window.radarChartInstance = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: ['音准', '节奏', '气息', '发声技术', '艺术表现'],
            datasets: [{
                label: '评分',
                data: [
                    scores.pitch || 0,
                    scores.rhythm || 0,
                    scores.breath || 0,
                    scores.volume || 0,  // volume -> 发声技术
                    scores.emotion || 0  // emotion -> 艺术表现
                ],
                backgroundColor: 'rgba(99, 102, 241, 0.2)',
                borderColor: 'rgba(99, 102, 241, 1)',
                borderWidth: 2,
                pointBackgroundColor: 'rgba(99, 102, 241, 1)',
                pointBorderColor: '#fff',
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: 'rgba(99, 102, 241, 1)'
            }]
        },
        options: {
            responsive: true,
            scales: {
                r: {
                    beginAtZero: true,
                    max: 100,
                    ticks: { stepSize: 20 },
                    grid: { color: 'rgba(0, 0, 0, 0.05)' },
                    angleLines: { color: 'rgba(0, 0, 0, 0.05)' },
                    pointLabels: {
                        font: { size: 12 },
                        color: '#475569'
                    }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

// ==================== 工具函数 ====================
function showToast(message, type = 'info') {
    const wrap = document.getElementById('toastWrap');
    if (!wrap) return;

    // 图标映射
    const icons = {
        success: '✓',
        error: '✕',
        warning: '⚠',
        info: 'ℹ'
    };

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || icons.info}</span>
        <span class="toast-content">${message}</span>
    `;

    wrap.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function adjustColor(color, amount) {
    const clamp = (num) => Math.min(255, Math.max(0, num));

    let hex = color.replace('#', '');
    if (hex.length === 3) {
        hex = hex.split('').map(c => c + c).join('');
    }

    const r = clamp(parseInt(hex.slice(0, 2), 16) + amount);
    const g = clamp(parseInt(hex.slice(2, 4), 16) + amount);
    const b = clamp(parseInt(hex.slice(4, 6), 16) + amount);

    return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
}

function getScoreColor(score) {
    if (score >= 90) return '#10b981';
    if (score >= 80) return '#22c55e';
    if (score >= 70) return '#eab308';
    if (score >= 60) return '#f97316';
    return '#ef4444';
}

function getScoreGradient(score) {
    if (score >= 80) return 'linear-gradient(90deg, #10b981 0%, #22c55e 100%)';
    if (score >= 60) return 'linear-gradient(90deg, #eab308 0%, #f97316 100%)';
    return 'linear-gradient(90deg, #f97316 0%, #ef4444 100%)';
}
