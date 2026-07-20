/**
 * ApiClient 鈥?缁熶竴 API 璋冪敤灞?
 *
 * 鑱岃矗:
 * 1. 灏佽鎵€鏈夊悗绔?API 璋冪敤
 * 2. 缁熶竴閿欒澶勭悊 + 瓒呮椂 + 閲嶈瘯
 * 3. 璇锋眰鍘婚噸 (闃查噸澶嶆彁浜?
 * 4. 绂荤嚎妫€娴?
 *
 * @version 1.0
 */

export class ApiError extends Error {
    /**
     * @param {string} message
     * @param {number} status - HTTP 鐘舵€佺爜
     * @param {*} data - 鍝嶅簲鏁版嵁
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
    _baseURL;

    /** @type {boolean} */
    _isAnalyzing = false;

    /** @type {AbortController|null} */
    _activeAnalysisController = null;

    constructor(baseURL = '') {
        this._baseURL = baseURL;
    }

    // ========================================================================
    // 鏍稿績鏂规硶
    // ========================================================================

    /**
     * 缁熶竴璇锋眰
     * @param {string} method - HTTP 鏂规硶
     * @param {string} path - API 璺緞
     * @param {Object} [options={}]
     * @param {Object} [options.body] - 璇锋眰浣?(鑷姩搴忓垪鍖栦负 JSON)
     * @param {number} [options.timeout=30000] - 瓒呮椂 (ms)
     * @param {number} [options.retries=0] - 閲嶈瘯娆℃暟
     * @param {boolean} [options.isFormData=false] - 鏄惁涓?FormData
     * @param {AbortSignal} [options.signal] - 鍙栨秷淇″彿
     */
    async request(method, path, options = {}) {
        const {
            body,
            timeout = 30000,
            retries = 0,
            isFormData = false,
            signal
        } = options;

        const url = `${this._baseURL}${path}`;
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
                // 瓒呮椂鎺у埗
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), timeout);

                // 鍚堝苟澶栭儴 signal
                const combinedSignal = signal
                    ? this._combineSignals(signal, controller.signal)
                    : controller.signal;

                const response = await fetch(url, {
                    ...fetchOptions,
                    signal: combinedSignal
                });

                clearTimeout(timeoutId);

                // 澶勭悊绌哄搷搴?
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

                // 涓嶉噸璇曠殑鎯呭喌:
                // 1. 宸茶澶栭儴鍙栨秷
                // 2. 4xx 瀹㈡埛绔敊璇?(闈?429)
                // 3. 鏈€鍚庝竴娆″皾璇?
                if (error.name === 'AbortError' || error instanceof ApiError) {
                    throw error;
                }
                if (attempt >= maxAttempts - 1) {
                    throw error;
                }

                // 鎸囨暟閫€閬块噸璇?
                const delay = Math.min(1000 * Math.pow(2, attempt), 5000);
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }

        throw lastError;
    }

    // ========================================================================
    // 闊抽鐩稿叧
    // ========================================================================

    /**
     * 涓婁紶闊抽杩涜鍒嗘瀽
     * @param {File} file - 闊抽鏂囦欢
     * @param {string} mode - 'quick' | 'professional'
     * @returns {Promise<{ success: boolean, task_id: string, analysis_id: string }>}
     */
    async uploadAudio(file, mode = 'quick') {
        if (this._isAnalyzing) {
            throw new ApiError('Processing in progress', 429);
        }

        const formData = new FormData();
        formData.append('file', file);  // 鍚庣鎺ユ敹瀛楁鍚? request.files['file']
        formData.append('mode', mode);

        this._isAnalyzing = true;
        this._activeAnalysisController = new AbortController();

        try {
            const result = await this.request('POST', '/api/upload', {
                body: formData,
                isFormData: true,
                timeout: 300000, // 涓撲笟妯″紡鍙兘杈冩參
                signal: this._activeAnalysisController.signal
            });
            return result;
        } finally {
            this._isAnalyzing = false;
            this._activeAnalysisController = null;
        }
    }

    /**
     * 鍙栨秷褰撳墠鍒嗘瀽
     */
    cancelAnalysis() {
        if (this._activeAnalysisController) {
            this._activeAnalysisController.abort();
            this._activeAnalysisController = null;
            this._isAnalyzing = false;
        }
    }

    /**
     * 鑾峰彇鍒嗘瀽鐘舵€?
     * @param {string} analysisId
     */
    async getAnalysisStatus(analysisId) {
        return this.request('GET', `/api/analysis/${analysisId}/status`);
    }

    /**
     * 鑾峰彇鍒嗘瀽缁撴灉
     * @param {string} analysisId
     */
    async getAnalysisResult(analysisId) {
        return this.request('GET', `/api/analysis/${analysisId}`);
    }

    // ========================================================================
    // 鍘嗗彶璁板綍
    // ========================================================================

    /**
     * 鑾峰彇鍘嗗彶璁板綍
     * @param {string} [filter='all'] - 'all' | 'today' | 'week' | 'month'
     */
    async getHistory(filter = 'all') {
        return this.request('GET', `/api/history?date=${filter}`);
    }

    /**
     * 鍒犻櫎鍗曟潯璁板綍
     * @param {number} id
     */
    async deleteHistory(id) {
        return this.request('DELETE', `/api/history/${id}`);
    }

    /**
     * 鎵归噺鍒犻櫎璁板綍
     * @param {number[]} ids
     */
    async deleteHistoryBatch(ids) {
        return this.request('DELETE', '/api/history/batch', {
            body: { ids }
        });
    }

    async deleteHistoryAll() {
        return this.request('DELETE', '/api/history/all');
    }

    // ========================================================================
    // 瀵规瘮鍒嗘瀽
    // ========================================================================

    /**
     * 瀵规瘮鍒嗘瀽
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
    // 鎶ュ憡瀵煎嚭
    // ========================================================================

    /**
     * 瀵煎嚭鎶ュ憡
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
    // 鏍囧噯鏇插簱
    // ========================================================================

    /**
     * 鑾峰彇鏍囧噯鏇插簱鍒楄〃
     */
    async getSongList() {
        return this.request('GET', '/api/songs');
    }

    /**
     * 鑾峰彇姝屾洸璇︽儏 (鍚熀棰戞暟鎹?
     * @param {string} songId
     */
    async getSongDetail(songId) {
        return this.request('GET', `/api/songs/${songId}`);
    }

    // ========================================================================
    // 浜哄０鍒嗙
    // ========================================================================

    /**
     * 浜哄０鍒嗙
     * @param {File} file
     */
    async separateVocals(file) {
        // 先上传获取 filepath，再调用分离 API
        const uploadResult = await this.uploadAudio(file);
        const filepath = uploadResult.filepath;
        if (!filepath) throw new Error('上传失败，未获取到文件路径');

        return this.request('POST', '/api/separate', {
            body: { filepath: filepath },
            isFormData: false,
            timeout: 180000
        });
    }

    // ========================================================================
    // 宸ュ叿鏂规硶
    // ========================================================================

    /**
     * 妫€鏌ユ槸鍚﹀湪绾?
     */
    isOnline() {
        return navigator.onLine;
    }

    /**
     * 妫€鏌ユ槸鍚︽鍦ㄥ垎鏋?
     */
    isAnalyzing() {
        return this._isAnalyzing;
    }

    /**
     * 鍚堝苟涓や釜 AbortSignal
     */
    _combineSignals(signal1, signal2) {
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

// 榛樿瀵煎嚭鍗曚緥
export default ApiClient;
