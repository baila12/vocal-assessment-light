/**
 * 状态管理模块
 * 统一的应用状态管理
 *
 * 注意：此文件为 ES 模块版本，供未来重构使用
 * 当前 app.js 使用全局 AppState 对象（在 app.js 中定义）
 */

// ==================== 主应用状态 ====================
export const AppState = {
    currentPage: 'home',
    isLoading: false,

    // 音频状态
    audio: {
        file: null,
        name: '',
        duration: 0,
        url: '',
        isPlaying: false,
        currentTime: 0,
        element: null,
        buffer: null,
        context: null,
        analyser: null,
        sourceNode: null,
        waveformData: null,
        smoothedVolume: 0,
        smoothedFreq: { low: 0, mid: 0, high: 0 }
    },

    // 录音状态
    recording: {
        isRecording: false,
        mediaRecorder: null,
        audioContext: null,
        analyser: null,
        stream: null,
        chunks: [],
        startTime: 0,
        animationId: null
    },

    // 对比分析状态
    compare: {
        standard: {
            file: null,
            name: '',
            url: '',
            buffer: null,
            pitchData: null,
            duration: 0,
            element: null,
            isPlaying: false
        },
        user: {
            file: null,
            name: '',
            url: '',
            buffer: null,
            pitchData: null,
            duration: 0,
            element: null,
            isPlaying: false
        },
        isComparing: false,
        result: null
    },

    // 人声分离结果
    separation: null,

    // 分析结果
    result: null,

    // 历史记录
    history: []
};

// ==================== 分析页面状态 ====================
export const AnalysisState = {
    result: null,
    audioElement: null,
    audioContext: null,
    analyser: null,
    isPlaying: false,
    animationId: null,
    analysisInProgress: false,
    progressInterval: null
};

// ==================== 原有状态（兼容性保留）====================
const state = {
    currentPage: 'home',
    upload: {
        file: null,
        status: 'idle',
        progress: 0
    },
    analysis: {
        basic: null,
        volume: null,
        pitch: null,
        scores: null,
        advice: null
    },
    history: {
        records: [],
        filter: 'all',
        loading: false
    },
    audio: {
        currentFile: null,
        isPlaying: false,
        currentTime: 0,
        duration: 0
    }
};

// ==================== 状态更新函数 ====================

// 状态更新函数（不可变更新）
export function updateState(path, value) {
    const keys = path.split('.');
    let current = state;

    for (let i = 0; i < keys.length - 1; i++) {
        current = current[keys[i]];
    }

    current[keys[keys.length - 1]] = value;

    // 触发状态更新事件
    if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('stateChange', {
            detail: { path, value, state: getState() }
        }));
    }
}

// 深度更新（用于对象）
export function updateStateDeep(path, updates) {
    const keys = path.split('.');
    let current = state;

    for (let i = 0; i < keys.length - 1; i++) {
        current = current[keys[i]];
    }

    const target = current[keys[keys.length - 1]];
    Object.assign(target, updates);

    if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('stateChange', {
            detail: { path, value: target, state: getState() }
        }));
    }
}

// 获取状态快照
export function getState() {
    return JSON.parse(JSON.stringify(state));
}

// 获取特定路径的值
export function getStateValue(path) {
    const keys = path.split('.');
    let current = state;

    for (const key of keys) {
        if (current === undefined || current === null) {
            return undefined;
        }
        current = current[key];
    }

    return current;
}

// 重置状态
export function resetState(path) {
    if (path === 'upload') {
        updateStateDeep('upload', {
            file: null,
            status: 'idle',
            progress: 0
        });
    } else if (path === 'analysis') {
        updateStateDeep('analysis', {
            basic: null,
            volume: null,
            pitch: null,
            scores: null,
            advice: null
        });
    }
}

// 默认导出
export default {
    AppState,
    AnalysisState,
    state,
    updateState,
    updateStateDeep,
    getState,
    getStateValue,
    resetState
};
