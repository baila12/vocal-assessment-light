/**
 * AnalysisSSE — SSE 实时分析进度客户端
 *
 * 职责:
 * 1. 建立 SSE 连接监听分析进度
 * 2. 事件分发: progress / pitchData / complete / error / matching
 * 3. 自动重连 + 连接状态管理
 *
 * 后端 SSE endpoint: GET /api/analysis/progress?task_id=xxx
 * SSE 事件类型:
 *   - voice_check:    { stage, percent, is_voice }
 *   - feature_pitch:  { stage, percent, frequencies, times }
 *   - feature_rhythm: { stage, percent, onsets }
 *   - feature_breath: { stage, percent, hnr, rms }
 *   - feature_technique: { stage, percent, ... }
 *   - scoring:        { stage, percent, scores }
 *   - matching:       { stage, percent, matched_song, confidence }
 *   - complete:       { stage: 'complete', percent: 100, result }
 *   - error:          { stage: 'error', message }
 *
 * @version 1.0
 */

export class AnalysisSSE {
    /** @type {string} */
    #taskId;

    /** @type {EventSource|null} */
    #eventSource = null;

    /** @type {boolean} */
    #connected = false;

    /** @type {number} */
    #reconnectAttempts = 0;

    /** @type {number} */
    #maxReconnects = 3;

    /** @type {Object<string, Set<Function>>} */
    #handlers = {
        progress: new Set(),
        pitchData: new Set(),
        complete: new Set(),
        error: new Set(),
        matching: new Set(),
        voiceCheck: new Set(),
        scoring: new Set()
    };

    constructor(taskId) {
        if (!taskId) throw new Error('AnalysisSSE: taskId is required');
        this.#taskId = taskId;
    }

    // ========================================================================
    // 连接管理
    // ========================================================================

    /**
     * 建立 SSE 连接
     */
    connect() {
        if (this.#eventSource) {
            this.disconnect();
        }

        const url = `/api/analysis/progress?task_id=${this.#taskId}`;
        this.#eventSource = new EventSource(url);

        this.#eventSource.onopen = () => {
            this.#connected = true;
            this.#reconnectAttempts = 0;
        };

        // 注册事件监听
        this.#eventSource.addEventListener('voice_check', (e) => {
            const data = this.#parseEvent(e);
            this.#emit('voiceCheck', data);
            this.#emit('progress', data);
        });

        this.#eventSource.addEventListener('feature_pitch', (e) => {
            const data = this.#parseEvent(e);
            this.#emit('pitchData', data);
            this.#emit('progress', data);
        });

        this.#eventSource.addEventListener('feature_rhythm', (e) => {
            this.#emit('progress', this.#parseEvent(e));
        });

        this.#eventSource.addEventListener('feature_breath', (e) => {
            this.#emit('progress', this.#parseEvent(e));
        });

        this.#eventSource.addEventListener('feature_technique', (e) => {
            this.#emit('progress', this.#parseEvent(e));
        });

        this.#eventSource.addEventListener('scoring', (e) => {
            const data = this.#parseEvent(e);
            this.#emit('scoring', data);
            this.#emit('progress', data);
        });

        this.#eventSource.addEventListener('matching', (e) => {
            this.#emit('matching', this.#parseEvent(e));
        });

        this.#eventSource.addEventListener('complete', (e) => {
            const data = this.#parseEvent(e);
            this.#emit('complete', data);
            this.disconnect();
        });

        this.#eventSource.addEventListener('error', (e) => {
            const data = this.#parseEvent(e);
            this.#emit('error', data);
        });

        // 连接错误处理
        this.#eventSource.onerror = () => {
            this.#connected = false;

            if (this.#reconnectAttempts < this.#maxReconnects) {
                this.#reconnectAttempts++;
                console.warn(`[SSE] 重连中 (${this.#reconnectAttempts}/${this.#maxReconnects})...`);
                // EventSource 会自动重连，不需要手动处理
            } else {
                console.error('[SSE] 重连次数超限，关闭连接');
                this.#emit('error', {
                    stage: 'connection_error',
                    message: '与服务器的连接已断开'
                });
                this.disconnect();
            }
        };

        return this;
    }

    /**
     * 关闭连接
     */
    disconnect() {
        if (this.#eventSource) {
            this.#eventSource.close();
            this.#eventSource = null;
            this.#connected = false;
        }
    }

    /**
     * 是否已连接
     */
    isConnected() {
        return this.#connected;
    }

    // ========================================================================
    // 事件监听 (链式调用)
    // ========================================================================

    /**
     * 进度更新
     * @param {Function} callback - (data: { stage, percent, message }) => void
     */
    onProgress(callback) {
        this.#handlers.progress.add(callback);
        return this;
    }

    /**
     * 音准数据到达 (可立即渲染音高曲线)
     * @param {Function} callback - (data: { frequencies, times }) => void
     */
    onPitchData(callback) {
        this.#handlers.pitchData.add(callback);
        return this;
    }

    /**
     * 分析完成
     * @param {Function} callback - (data: { result }) => void
     */
    onComplete(callback) {
        this.#handlers.complete.add(callback);
        return this;
    }

    /**
     * 分析错误
     * @param {Function} callback - (data: { message }) => void
     */
    onError(callback) {
        this.#handlers.error.add(callback);
        return this;
    }

    /**
     * 歌曲匹配
     * @param {Function} callback - (data: { matched_song, confidence }) => void
     */
    onMatching(callback) {
        this.#handlers.matching.add(callback);
        return this;
    }

    /**
     * 人声检测
     * @param {Function} callback - (data: { is_voice }) => void
     */
    onVoiceCheck(callback) {
        this.#handlers.voiceCheck.add(callback);
        return this;
    }

    /**
     * 评分结果
     * @param {Function} callback - (data: { scores }) => void
     */
    onScoring(callback) {
        this.#handlers.scoring.add(callback);
        return this;
    }

    // ========================================================================
    // 内部方法
    // ========================================================================

    #emit(name, data) {
        const handlers = this.#handlers[name];
        if (handlers) {
            handlers.forEach(cb => {
                try { cb(data); } catch (e) { console.error(`[SSE] Handler "${name}" error:`, e); }
            });
        }
    }

    #parseEvent(event) {
        try {
            return JSON.parse(event.data);
        } catch {
            return { raw: event.data };
        }
    }
}

export default AnalysisSSE;
