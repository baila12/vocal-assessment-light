/**
 * ApiClient — 统一 API 调用层
 *
 * 职责:
 * 1. 封装所有后端 API 调用
 * 2. 统一错误处理 + 超时 + 重试
 * 3. 请求去重 (防重复提交)
 * 4. 离线检测
 *
 * @version 1.0
 */

export class ApiError extends Error {
    /**
     * @param {string} message
     * @param {number} status - HTTP 状态码
     * @param {*} data - 响应数据
     */
    constructor(message, status = 0, data = null) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
        this.data = data;
    }
}

export class ApiClient {
    /** @type {string} */
    #baseURL;

    /** @type {boolean} */
    #isAnalyzing = false;

    /** @type {AbortController|null} */
    #activeAnalysisController = null;

    constructor(baseURL = '') {
        this.#baseURL = baseURL;
    }

    // ========================================================================
    // 核心方法
    // ========================================================================

    /**
     * 统一请求
     * @param {string} method - HTTP 方法
     * @param {string} path - API 路径
     * @param {Object} [options={}]
     * @param {Object} [options.body] - 请求体 (自动序列化为 JSON)
     * @param {number} [options.timeout=30000] - 超时 (ms)
     * @param {number} [options.retries=0] - 重试次数
     * @param {boolean} [options.isFormData=false] - 是否为 FormData
     * @param {AbortSignal} [options.signal] - 取消信号
     */
    async request(method, path, options = {}) {
        const {
            body,
            timeout = 30000,
            retries = 0,
            isFormData = false,
            signal
        } = options;

        const url = `${this.#baseURL}${path}`;
        const headers = {};

        if (!isFormData && body) {
            headers['Content-Type'] = 'application/json';
        }

        const fetchOptions = {
            method,
            headers,
            signal
        };

        if (body) {
            fetchOptions.body = isFormData ? body : JSON.stringify(body);
        }

        let lastError;
        const maxAttempts = 1 + retries;

        for (let attempt = 0; attempt < maxAttempts; attempt++) {
            try {
                // 超时控制
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), timeout);

                // 合并外部 signal
                const combinedSignal = signal
                    ? this.#combineSignals(signal, controller.signal)
                    : controller.signal;

                const response = await fetch(url, {
                    ...fetchOptions,
                    signal: combinedSignal
                });

                clearTimeout(timeoutId);

                // 处理空响应
                const text = await response.text();
                let data;
                try {
                    data = text ? JSON.parse(text) : null;
                } catch {
                    data = { message: text };
                }

                if (!response.ok) {
                    throw new ApiError(
                        data?.error || data?.message || `HTTP ${response.status}`,
                        response.status,
                        data
                    );
                }

                return data;

            } catch (error) {
                lastError = error;

                // 不重试的情况:
                // 1. 已被外部取消
                // 2. 4xx 客户端错误 (非 429)
                // 3. 最后一次尝试
                if (error.name === 'AbortError' || error instanceof ApiError) {
                    throw error;
                }
                if (attempt >= maxAttempts - 1) {
                    throw error;
                }

                // 指数退避重试
                const delay = Math.min(1000 * Math.pow(2, attempt), 5000);
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }

        throw lastError;
    }

    // ========================================================================
    // 音频相关
    // ========================================================================

    /**
     * 上传音频进行分析
     * @param {File} file - 音频文件
     * @param {string} mode - 'quick' | 'professional'
     * @returns {Promise<{ success: boolean, task_id: string, analysis_id: string }>}
     */
    async uploadAudio(file, mode = 'quick') {
        if (this.#isAnalyzing) {
            throw new ApiError('分析正在进行中，请等待完成', 429);
        }

        const formData = new FormData();
        formData.append('file', file);  // 后端接收字段名: request.files['file']
        formData.append('mode', mode);

        this.#isAnalyzing = true;
        this.#activeAnalysisController = new AbortController();

        try {
            const result = await this.request('POST', '/api/audio/analyze', {
                body: formData,
                isFormData: true,
                timeout: 300000, // 专业模式可能较慢
                signal: this.#activeAnalysisController.signal
            });
            return result;
        } finally {
            this.#isAnalyzing = false;
            this.#activeAnalysisController = null;
        }
    }

    /**
     * 取消当前分析
     */
    cancelAnalysis() {
        if (this.#activeAnalysisController) {
            this.#activeAnalysisController.abort();
            this.#activeAnalysisController = null;
            this.#isAnalyzing = false;
        }
    }

    /**
     * 获取分析状态
     * @param {string} analysisId
     */
    async getAnalysisStatus(analysisId) {
        return this.request('GET', `/api/analysis/${analysisId}/status`);
    }

    /**
     * 获取分析结果
     * @param {string} analysisId
     */
    async getAnalysisResult(analysisId) {
        return this.request('GET', `/api/analysis/${analysisId}`);
    }

    // ========================================================================
    // 历史记录
    // ========================================================================

    /**
     * 获取历史记录
     * @param {string} [filter='all'] - 'all' | 'today' | 'week' | 'month'
     */
    async getHistory(filter = 'all') {
        return this.request('GET', `/api/history?date=${filter}`);
    }

    /**
     * 删除单条记录
     * @param {number} id
     */
    async deleteHistory(id) {
        return this.request('DELETE', `/api/history/${id}`);
    }

    /**
     * 批量删除记录
     * @param {number[]} ids
     */
    async deleteHistoryBatch(ids) {
        return this.request('POST', '/api/history/batch-delete', {
            body: { ids }
        });
    }

    // ========================================================================
    // 对比分析
    // ========================================================================

    /**
     * 对比分析
     * @param {File} standardFile
     * @param {File} userFile
     */
    async compareAnalysis(standardFile, userFile) {
        const formData = new FormData();
        formData.append('standard', standardFile);
        formData.append('user', userFile);

        return this.request('POST', '/api/compare', {
            body: formData,
            isFormData: true,
            timeout: 300000
        });
    }

    // ========================================================================
    // 报告导出
    // ========================================================================

    /**
     * 导出报告
     * @param {Object} analysisResult
     * @param {string} filename
     * @param {string} format - 'pdf' | 'image'
     */
    async exportReport(analysisResult, filename, format = 'pdf') {
        return this.request('POST', '/api/report', {
            body: {
                analysis_result: analysisResult,
                filename: filename,
                format: format
            }
        });
    }

    // ========================================================================
    // 标准曲库
    // ========================================================================

    /**
     * 获取标准曲库列表
     */
    async getSongList() {
        return this.request('GET', '/api/songs');
    }

    /**
     * 获取歌曲详情 (含基频数据)
     * @param {string} songId
     */
    async getSongDetail(songId) {
        return this.request('GET', `/api/songs/${songId}`);
    }

    // ========================================================================
    // 人声分离
    // ========================================================================

    /**
     * 人声分离
     * @param {File} file
     */
    async separateVocals(file) {
        const formData = new FormData();
        formData.append('audio', file);

        return this.request('POST', '/api/separate', {
            body: formData,
            isFormData: true,
            timeout: 180000
        });
    }

    // ========================================================================
    // 工具方法
    // ========================================================================

    /**
     * 检查是否在线
     */
    isOnline() {
        return navigator.onLine;
    }

    /**
     * 检查是否正在分析
     */
    isAnalyzing() {
        return this.#isAnalyzing;
    }

    /**
     * 合并两个 AbortSignal
     */
    #combineSignals(signal1, signal2) {
        const controller = new AbortController();

        const onAbort = () => controller.abort();
        signal1.addEventListener('abort', onAbort);
        signal2.addEventListener('abort', onAbort);

        if (signal1.aborted || signal2.aborted) {
            controller.abort();
        }

        return controller.signal;
    }
}

// 默认导出单例
export default ApiClient;
