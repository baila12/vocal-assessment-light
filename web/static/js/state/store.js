/**
 * Store — 统一响应式状态管理 (Proxy-based)
 *
 * 职责:
 * 1. 单一数据源 — 整个应用一份状态树
 * 2. 响应式更新 — Proxy 拦截 setState，自动通知订阅者
 * 3. 不可变更新 — setState 使用浅合并，返回新对象
 * 4. localStorage 持久化 — persist() 标记路径，自动同步
 * 5. 事件总线 — on/emit 支持自定义事件
 *
 * @version 1.0
 */

/** @type {Object} 初始状态 */
const initialState = {
    // ── 路由 ──
    route: {
        current: '#/',
        params: {},
        previous: null
    },

    // ── 音频 (当前选中的文件) ──
    audio: {
        file: null,
        name: '',
        duration: 0,
        url: '',
        format: ''
    },

    // ── 分析 ──
    analysis: {
        taskId: null,
        analysisId: null,
        mode: 'quick',
        status: 'idle',       // 'idle' | 'uploading' | 'analyzing' | 'complete' | 'error'
        progress: {
            stage: '',
            percent: 0,
            message: ''
        },
        result: null,
        error: null
    },

    // ── 录音 ──
    recording: {
        isRecording: false,
        duration: 0
        // 注意: mediaRecorder, stream, chunks 等不可序列化对象不存 store
    },

    // ── 播放器 ──
    player: {
        isPlaying: false,
        currentTime: 0,
        duration: 0,
        volume: 0.8
    },

    // ── 对比分析 ──
    compare: {
        standard: { file: null, name: '', url: '', duration: 0 },
        user: { file: null, name: '', url: '', duration: 0 },
        result: null
    },

    // ── UI 状态 ──
    ui: {
        theme: 'light',
        sidebarCollapsed: false,
        loadingStack: [],
        activeModal: null
    },

    // ── 用户偏好 (持久化) ──
    preferences: {
        evalMode: 'quick',
        theme: 'light',
        autoPlay: false
    }
};

export class Store {
    /** @type {Object} */
    #state;

    /** @type {Map<string, Set<Function>>} */
    #subscribers = new Map();

    /** @type {Map<string, Function>} */
    #events = new Map();

    /** @type {Set<string>} */
    #persistedKeys = new Set();

    /** @type {ProxyHandler} */
    #proxy;

    constructor(initial = {}) {
        this.#state = this.#deepClone({ ...initialState, ...initial });
        this.#restorePreferences();
        this.#setupProxy();
    }

    // ========================================================================
    // 核心 API
    // ========================================================================

    /**
     * 获取当前状态快照 (深拷贝，只读)
     * @param {string} [path] - 可选，获取嵌套路径的值
     * @returns {*}
     */
    getState(path) {
        if (path) {
            return this.#getNestedValue(this.#state, path);
        }
        return this.#deepClone(this.#state);
    }

    /**
     * 合并更新状态 (不可变)
     * @param {Object} updates - 要合并的更新对象
     * @param {string} [basePath] - 可选，更新的基础路径
     *
     * @example
     * store.setState({ status: 'analyzing' }, 'analysis')
     * store.setState({ audio: { name: 'test.mp3' } })
     */
    setState(updates, basePath) {
        if (basePath) {
            const target = this.#getNestedValue(this.#state, basePath);
            if (target && typeof target === 'object') {
                Object.assign(target, updates);
                this.#notify(basePath, target);
            }
        } else {
            for (const [key, value] of Object.entries(updates)) {
                if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
                    // 浅合并对象
                    Object.assign(this.#state[key], value);
                } else {
                    this.#state[key] = value;
                }
                this.#notify(key, this.#state[key]);
            }
        }

        // 同步持久化
        this.#syncPersisted();
    }

    /**
     * 订阅状态变化
     * @param {string} path - 状态路径
     * @param {Function} callback - 回调 (newValue, oldValue)
     * @returns {Function} 取消订阅函数
     */
    subscribe(path, callback) {
        if (!this.#subscribers.has(path)) {
            this.#subscribers.set(path, new Set());
        }
        this.#subscribers.get(path).add(callback);

        // 返回取消订阅函数
        return () => this.unsubscribe(path, callback);
    }

    /**
     * 取消订阅
     * @param {string} path
     * @param {Function} callback
     */
    unsubscribe(path, callback) {
        const subs = this.#subscribers.get(path);
        if (subs) {
            subs.delete(callback);
        }
    }

    // ========================================================================
    // 事件总线
    // ========================================================================

    /**
     * 监听事件
     * @param {string} event - 事件名
     * @param {Function} callback
     * @returns {Function} 取消监听函数
     *
     * @example
     * store.on('analysis:complete', (result) => { ... })
     */
    on(event, callback) {
        if (!this.#events.has(event)) {
            this.#events.set(event, new Set());
        }
        this.#events.get(event).add(callback);
        return () => this.off(event, callback);
    }

    /**
     * 取消事件监听
     * @param {string} event
     * @param {Function} callback
     */
    off(event, callback) {
        const handlers = this.#events.get(event);
        if (handlers) {
            handlers.delete(callback);
        }
    }

    /**
     * 发送事件
     * @param {string} event
     * @param {*} data
     */
    emit(event, data) {
        const handlers = this.#events.get(event);
        if (handlers) {
            handlers.forEach(cb => {
                try { cb(data); } catch (e) { console.error(`[Store] Event "${event}" handler error:`, e); }
            });
        }
    }

    // ========================================================================
    // 持久化
    // ========================================================================

    /**
     * 标记路径需要 localStorage 持久化
     * @param {string} key - 状态路径，如 'preferences'
     */
    persist(key) {
        this.#persistedKeys.add(key);
        // 立即从 localStorage 恢复 (解决构造函数中 #restorePreferences 时 persistedKeys 为空的问题)
        try {
            const stored = localStorage.getItem(`vocal_app_${key}`);
            if (stored && this.#state[key] && typeof this.#state[key] === 'object') {
                Object.assign(this.#state[key], JSON.parse(stored));
            }
        } catch { /* ignore parse errors */ }
        this.#syncPersisted();
    }

    /**
     * 重置指定路径到初始值
     * @param {string} path
     */
    reset(path) {
        const initialValue = this.#getNestedValue(initialState, path);
        if (initialValue !== undefined) {
            const keys = path.split('.');
            let current = this.#state;
            for (let i = 0; i < keys.length - 1; i++) {
                current = current[keys[i]];
            }
            const lastKey = keys[keys.length - 1];
            if (typeof initialValue === 'object' && initialValue !== null) {
                current[lastKey] = this.#deepClone(initialValue);
            } else {
                current[lastKey] = initialValue;
            }
            this.#notify(path, current[lastKey]);
        }
    }

    // ========================================================================
    // 内部方法
    // ========================================================================

    #setupProxy() {
        // 使用 Proxy 监听顶层 key 的赋值 (备用，主要依赖 setState)
        const self = this;
        this.#proxy = new Proxy(this.#state, {
            set(target, prop, value) {
                const oldValue = target[prop];
                target[prop] = value;
                self.#notify(prop, value);
                self.#syncPersisted();
                return true;
            }
        });
    }

    /**
     * 通知订阅者
     */
    #notify(path, newValue) {
        const subs = this.#subscribers.get(path);
        if (subs) {
            subs.forEach(cb => {
                try { cb(newValue); } catch (e) { console.error(`[Store] Subscriber "${path}" error:`, e); }
            });
        }

        // 也通知父级路径的订阅者
        const dotIndex = path.lastIndexOf('.');
        if (dotIndex > 0) {
            const parentPath = path.substring(0, dotIndex);
            const parentSubs = this.#subscribers.get(parentPath);
            if (parentSubs) {
                const parentValue = this.#getNestedValue(this.#state, parentPath);
                parentSubs.forEach(cb => {
                    try { cb(parentValue); } catch (e) { console.error(`[Store] Subscriber "${parentPath}" error:`, e); }
                });
            }
        }
    }

    /**
     * 同步持久化数据到 localStorage
     */
    #syncPersisted() {
        for (const key of this.#persistedKeys) {
            const value = this.#state[key];
            if (value !== undefined) {
                try {
                    // 过滤不可序列化的值
                    const serializable = JSON.parse(JSON.stringify(value));
                    localStorage.setItem(`vocal_app_${key}`, JSON.stringify(serializable));
                } catch (e) {
                    console.warn(`[Store] 无法持久化 ${key}:`, e);
                }
            }
        }
    }

    /**
     * 从 localStorage 恢复持久化数据
     */
    #restorePreferences() {
        for (const key of this.#persistedKeys) {
            try {
                const stored = localStorage.getItem(`vocal_app_${key}`);
                if (stored) {
                    const parsed = JSON.parse(stored);
                    if (this.#state[key] && typeof this.#state[key] === 'object') {
                        Object.assign(this.#state[key], parsed);
                    } else {
                        this.#state[key] = parsed;
                    }
                }
            } catch (e) {
                console.warn(`[Store] 恢复 ${key} 失败:`, e);
            }
        }
    }

    /**
     * 获取嵌套路径的值
     */
    #getNestedValue(obj, path) {
        const keys = path.split('.');
        let current = obj;
        for (const key of keys) {
            if (current === undefined || current === null) return undefined;
            current = current[key];
        }
        return current;
    }

    /**
     * 深拷贝
     */
    #deepClone(obj) {
        if (obj === null || typeof obj !== 'object') return obj;
        if (Array.isArray(obj)) return obj.map(item => this.#deepClone(item));
        const clone = {};
        for (const [key, value] of Object.entries(obj)) {
            clone[key] = this.#deepClone(value);
        }
        return clone;
    }
}

// 默认导出单例 (由 app.js 初始化和配置)
export default Store;
