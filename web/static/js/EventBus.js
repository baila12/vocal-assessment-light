/**
 * EventBus — 轻量级事件总线
 *
 * 设计目标 (v7.0 Vue 迁移衔接):
 *   当前 Vanilla JS: EventBus 作为跨组件通信中介
 *   v7.0 Vue 3:     EventBus → mitt() 或 Pinia actions
 *
 * 使用模式:
 *   context.events.on('analysis:complete', (result) => { ... })
 *   context.events.emit('analysis:complete', result)
 *   context.events.off('analysis:complete', handler)
 *
 * 命名约定:
 *   - 领域事件:  'domain:action'     (e.g. 'analysis:complete', 'route:changed')
 *   - UI 事件:    'ui:action'        (e.g. 'toast:show', 'modal:close')
 *   - 系统事件:   'system:action'    (e.g. 'system:online', 'system:offline')
 *
 * @version 1.0 (v5.20+)
 * @migration v7.0 — 替换为 mitt()
 */

export class EventBus {
    /** @type {Map<string, Set<Function>>} */
    #listeners = new Map();

    /** @type {boolean} */
    #debug = false;

    constructor(options = {}) {
        this.#debug = options.debug || false;
    }

    /**
     * 监听事件
     * @param {string} event
     * @param {Function} handler
     */
    on(event, handler) {
        if (!this.#listeners.has(event)) {
            this.#listeners.set(event, new Set());
        }
        this.#listeners.get(event).add(handler);
    }

    /**
     * 一次性监听
     * @param {string} event
     * @param {Function} handler
     */
    once(event, handler) {
        const wrapper = (...args) => {
            this.off(event, wrapper);
            handler(...args);
        };
        this.on(event, wrapper);
    }

    /**
     * 移除监听
     * @param {string} event
     * @param {Function} [handler] — 不传则移除该事件的所有监听
     */
    off(event, handler) {
        if (!handler) {
            this.#listeners.delete(event);
            return;
        }
        const set = this.#listeners.get(event);
        if (set) {
            set.delete(handler);
            if (set.size === 0) this.#listeners.delete(event);
        }
    }

    /**
     * 触发事件
     * @param {string} event
     * @param {...*} args
     */
    emit(event, ...args) {
        if (this.#debug) {
            console.debug('[EventBus] emit:', event, ...args);
        }
        const set = this.#listeners.get(event);
        if (!set) return;
        for (const handler of set) {
            try {
                handler(...args);
            } catch (e) {
                console.error('[EventBus] Handler error for "' + event + '":', e);
            }
        }
    }

    /**
     * 移除所有监听
     */
    clear() {
        this.#listeners.clear();
    }

    /**
     * 获取已注册的事件名列表 (调试用)
     * @returns {string[]}
     */
    eventNames() {
        return Array.from(this.#listeners.keys());
    }

    /**
     * 获取某事件的监听数量
     * @param {string} event
     * @returns {number}
     */
    listenerCount(event) {
        return this.#listeners.get(event)?.size || 0;
    }

    enableDebug() { this.#debug = true; }
    disableDebug() { this.#debug = false; }
}

export default EventBus;
