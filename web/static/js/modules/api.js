/**
 * API 调用模块
 * 封装所有后端接口调用
 */

// API 基础路径
const API_BASE = '/api';

// 通用请求函数
async function request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;

    const defaultOptions = {
        headers: {}
    };

    // 如果不是 FormData，设置 JSON Content-Type
    if (!(options.body instanceof FormData)) {
        defaultOptions.headers['Content-Type'] = 'application/json';
    }

    const finalOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers
        }
    };

    try {
        const response = await fetch(url, finalOptions);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || `HTTP ${response.status}`);
        }

        return data;
    } catch (error) {
        console.error(`API Error [${endpoint}]:`, error);
        throw error;
    }
}

// 上传并分析音频
async function uploadAudio(file, onProgress) {
    const formData = new FormData();
    formData.append('audio', file);

    // 模拟进度（fetch 不支持真实进度）
    if (onProgress) {
        onProgress(10);
    }

    const result = await request('/upload', {
        method: 'POST',
        body: formData
    });

    if (onProgress) {
        onProgress(100);
    }

    return result;
}

// 获取历史记录
async function getHistory(filter = 'all') {
    const params = new URLSearchParams();
    if (filter && filter !== 'all') {
        params.append('date', filter);
    }

    const queryString = params.toString();
    const endpoint = queryString ? `/history?${queryString}` : '/history';

    return request(endpoint);
}

// 获取单个历史记录详情
async function getHistoryDetail(id) {
    return request(`/history/${id}`);
}

// 删除历史记录
async function deleteHistory(id) {
    return request(`/history/${id}`, {
        method: 'DELETE'
    });
}

// 获取音频文件 URL
function getAudioUrl(filepath) {
    return `${API_BASE}/audio?file=${encodeURIComponent(filepath)}`;
}

// 导出
export {
    uploadAudio,
    getHistory,
    getHistoryDetail,
    deleteHistory,
    getAudioUrl
};
