/**
 * 工具函数模块
 * 通用辅助函数
 */

// ==================== XSS 防护 ====================

/**
 * HTML 转义，防止 XSS 攻击
 * @param {string} text - 需要转义的文本
 * @returns {string} - 转义后的文本
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ==================== 时间格式化 ====================

// 格式化时间（秒 → mm:ss）
function formatTime(seconds) {
    if (!seconds || isNaN(seconds)) return '00:00';

    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);

    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

// 格式化日期
function formatDate(dateString) {
    const date = new Date(dateString);
    const year = date.getFullYear();
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const day = date.getDate().toString().padStart(2, '0');
    const hour = date.getHours().toString().padStart(2, '0');
    const minute = date.getMinutes().toString().padStart(2, '0');

    return `${year}-${month}-${day} ${hour}:${minute}`;
}

// ==================== 分数相关 ====================

// 获取分数颜色
function getScoreColor(score) {
    if (score >= 90) return 'var(--success)';
    if (score >= 75) return 'var(--primary)';
    if (score >= 60) return 'var(--warning)';
    return 'var(--danger)';
}

// 获取分数等级
function getScoreLevel(score) {
    if (score >= 90) return '优秀';
    if (score >= 75) return '良好';
    if (score >= 60) return '及格';
    return '需改进';
}

// 获取分数等级类名
function getScoreLevelClass(score) {
    if (score >= 90) return 'excellent';
    if (score >= 75) return 'good';
    if (score >= 60) return 'pass';
    return 'fail';
}

// ==================== 音乐相关 ====================

/**
 * 频率转音符名称
 * @param {number} freq - 频率 (Hz)
 * @returns {string} - 音符名称 (如 "C4", "A#5")
 */
function frequencyToNoteName(freq) {
    if (!freq || freq < 20) return '--';
    const notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
    const noteNum = 12 * Math.log2(freq / 440) + 69;
    const note = notes[Math.round(noteNum) % 12];
    const octave = Math.floor(Math.round(noteNum) / 12) - 1;
    return note + octave;
}

// ==================== UI 相关 ====================

// 显示 Toast 消息
function showToast(message, type = 'info', duration = 3000) {
    // 查找或创建容器
    let container = document.getElementById('toastWrap');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastWrap';
        container.style.cssText = 'position:fixed;top:20px;right:20px;z-index:9999;';
        document.body.appendChild(container);
    }

    // 创建 toast 元素
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    // 样式
    Object.assign(toast.style, {
        padding: '12px 20px',
        marginBottom: '8px',
        borderRadius: '6px',
        color: 'white',
        fontSize: '14px',
        fontWeight: '500',
        zIndex: '9999',
        opacity: '0',
        transform: 'translateY(-10px)',
        transition: 'all 0.3s ease'
    });

    // 背景色
    const colors = {
        info: '#3b82f6',
        success: '#10b981',
        warning: '#f59e0b',
        error: '#ef4444'
    };
    toast.style.background = colors[type] || colors.info;

    container.appendChild(toast);

    // 显示动画
    requestAnimationFrame(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateY(0)';
    });

    // 自动移除
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(-10px)';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// ==================== 函数工具 ====================

// 防抖函数
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 节流函数
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// ==================== 文件相关 ====================

// 格式化文件大小
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';

    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 验证文件类型
function validateFileType(file, allowedTypes = ['.wav', '.mp3', '.flac', '.ogg', '.m4a']) {
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    return allowedTypes.includes(ext);
}

// ==================== 其他工具 ====================

// 延迟函数
function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// ==================== Utils 对象（兼容旧代码）====================

const Utils = {
    formatTime,
    getScoreColor,
    getScoreLevel,
    frequencyToNoteName,
    escapeHtml
};

// 导出
export {
    // XSS 防护
    escapeHtml,

    // 时间格式化
    formatTime,
    formatDate,

    // 分数相关
    getScoreColor,
    getScoreLevel,
    getScoreLevelClass,

    // 音乐相关
    frequencyToNoteName,

    // UI 相关
    showToast,

    // 函数工具
    debounce,
    throttle,

    // 文件相关
    formatFileSize,
    validateFileType,

    // 其他
    delay,

    // 兼容对象
    Utils
};
