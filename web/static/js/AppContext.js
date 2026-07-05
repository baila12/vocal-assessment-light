/**
 * AppContext — 应用级依赖注入容器
 *
 * 设计目标 (v7.0 Vue 迁移衔接):
 *   当前 Vanilla JS: AppContext 聚合 store/router/api/ac/events
 *   v7.0 Vue 3:     AppContext → createApp() + provide/inject
 *     - context.store   → Pinia createPinia()
 *     - context.router  → Vue Router createRouter()
 *     - context.api     → HTTP client 或 Electron IPC bridge
 *     - context.ac      → GSAP composable (useGsap)
 *     - context.events  → mitt() event bus
 *
 * 接入方式 (高内聚低耦合):
 *   1. 构造函数注入: new BaseComponent(container, { context })
 *   2. 全局回退:     window.__appContext (仅初始化时设置一次)
 *
 * @version 1.0 (v5.20+)
 * @migration v7.0 — 替换为 Vue provide/inject
 */

export class AppContext {
    /** @type {import('./js/state/store.js').Store|null} */
    store = null;

    /** @type {import('./router.js').HashRouter|null} */
    router = null;

    /** @type {import('./js/services/api.js').ApiClient|null} */
    api = null;

    /** @type {import('./js/animation/Controller.js').AnimationController|null} */
    ac = null;

    /** @type {import('./EventBus.js').EventBus|null} */
    events = null;

    /** @type {boolean} */
    #frozen = false;

    /**
     * @param {Object} services
     * @param {Object} [services.store]
     * @param {Object} [services.router]
     * @param {Object} [services.api]
     * @param {Object} [services.ac]
     * @param {Object} [services.events]
     */
    constructor(services = {}) {
        this.store = services.store || null;
        this.router = services.router || null;
        this.api = services.api || null;
        this.ac = services.ac || null;
        this.events = services.events || null;
    }

    /**
     * 冻结上下文 — 初始化完成后调用，防止运行时篡改。
     * 对应 Vue 的 app.mount() 之后的状态。
     */
    freeze() {
        this.#frozen = true;
    }

    /**
     * 注册或替换服务 (仅限未冻结状态)
     * @param {'store'|'router'|'api'|'ac'|'events'} name
     * @param {*} instance
     */
    register(name, instance) {
        if (this.#frozen) {
            console.warn('[AppContext] Cannot register "' + name + '" — context is frozen');
            return;
        }
        if (!(name in this)) {
            console.warn('[AppContext] Unknown service name:', name);
            return;
        }
        this[name] = instance;
    }
}

// 全局单例引用 (v7.0 中移除，改用 Vue provide/inject)
if (typeof window !== 'undefined') {
    window.__appContext = null;
}

export default AppContext;
