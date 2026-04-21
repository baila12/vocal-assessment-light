/**
 * 人声分离模块 v2.0
 * 支持进度条显示
 */

import { AppState } from './state.js';
import { showToast } from './utils.js';

// 分离状态
const SeparationState = {
    isSeparating: false,
    progressInterval: null,
    currentProgress: 0
};

/**
 * 开始人声分离
 */
async function startSeparation() {
    if (!AppState.audio.file) {
        showToast('请先上传音频', 'warning');
        return;
    }

    if (SeparationState.isSeparating) {
        showToast('正在分离中，请稍候...', 'warning');
        return;
    }

    SeparationState.isSeparating = true;
    SeparationState.currentProgress = 0;

    const progressEl = document.getElementById('separationProgress');
    const progressFill = document.getElementById('separationProgressFill');
    const progressText = document.getElementById('separationProgressText');
    const btnWrap = document.getElementById('separationBtnWrap');

    if (progressEl) progressEl.style.display = 'block';
    if (btnWrap) btnWrap.style.display = 'none';

    // 启动模拟进度
    startSimulatedProgress(progressFill, progressText);

    try {
        // 1. 上传音频
        updateProgressText(progressText, '正在上传音频...', 5);
        const formData = new FormData();
        formData.append('file', AppState.audio.file);
        const uploadResp = await fetch('/api/upload', { method: 'POST', body: formData });
        const uploadResult = await uploadResp.json();
        if (!uploadResult.success) throw new Error(uploadResult.error);

        // 2. 开始分离
        updateProgressText(progressText, '正在启动Demucs模型...', 15);
        const separateResp = await fetch('/api/separate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                filepath: uploadResult.filepath,
                model: 'htdemucs_ft',
                two_stems: 'vocals'
            })
        });

        const result = await separateResp.json();

        // 停止模拟进度
        stopSimulatedProgress();

        // 设置完成进度
        if (progressFill) progressFill.style.width = '100%';
        if (progressText) progressText.textContent = '分离完成！';

        if (!result.success) throw new Error(result.error);

        // 延迟隐藏进度条
        setTimeout(() => {
            if (progressEl) progressEl.style.display = 'none';
        }, 1000);

        displaySeparationResult(result);
        showToast('人声分离完成', 'success');

    } catch (error) {
        stopSimulatedProgress();
        showToast(error.message || '人声分离失败', 'error');
        if (progressEl) progressEl.style.display = 'none';
        if (btnWrap) btnWrap.style.display = 'block';
    } finally {
        SeparationState.isSeparating = false;
    }
}

/**
 * 启动模拟进度条
 * 基于典型分离时间（约30-60秒）模拟进度
 */
function startSimulatedProgress(progressFill, progressText) {
    SeparationState.currentProgress = 0;

    SeparationState.progressInterval = setInterval(() => {
        // 模拟进度增长（最大到90%，剩余10%等实际完成）
        if (SeparationState.currentProgress < 90) {
            // 非线性增长：初期快，后期慢
            const increment = Math.max(0.5, 3 - SeparationState.currentProgress * 0.03);
            SeparationState.currentProgress = Math.min(90, SeparationState.currentProgress + increment);

            if (progressFill) {
                progressFill.style.width = SeparationState.currentProgress + '%';
            }

            // 更新状态文本
            if (progressText) {
                if (SeparationState.currentProgress < 30) {
                    progressText.textContent = '正在加载Demucs模型...';
                } else if (SeparationState.currentProgress < 60) {
                    progressText.textContent = '正在分离人声和伴奏...';
                } else {
                    progressText.textContent = '正在处理音频轨道...';
                }
            }
        }
    }, 500);
}

/**
 * 停止模拟进度
 */
function stopSimulatedProgress() {
    if (SeparationState.progressInterval) {
        clearInterval(SeparationState.progressInterval);
        SeparationState.progressInterval = null;
    }
}

/**
 * 更新进度文本
 */
function updateProgressText(progressText, text, progress) {
    if (progressText) {
        progressText.textContent = text;
    }
    SeparationState.currentProgress = Math.max(SeparationState.currentProgress, progress);
}

/**
 * 显示分离结果
 */
function displaySeparationResult(result) {
    const resultEl = document.getElementById('separationResult');
    if (!resultEl) return;

    if (result.vocals_path) {
        const vocalsAudio = document.getElementById('vocalsAudio');
        if (vocalsAudio) vocalsAudio.src = result.vocals_path;
    }
    if (result.accompaniment_path) {
        const accAudio = document.getElementById('accompanimentAudio');
        if (accAudio) accAudio.src = result.accompaniment_path;
    }

    AppState.separation = {
        vocalsPath: result.vocals_path,
        accompanimentPath: result.accompaniment_path
    };

    resultEl.style.display = 'block';
}

/**
 * 关闭分离结果
 */
function closeSeparationResult() {
    const resultEl = document.getElementById('separationResult');
    const btnWrap = document.getElementById('separationBtnWrap');
    if (resultEl) resultEl.style.display = 'none';
    if (btnWrap) btnWrap.style.display = 'block';
}

export { startSeparation, displaySeparationResult, closeSeparationResult };
