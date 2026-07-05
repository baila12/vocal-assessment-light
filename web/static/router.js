/**
 * HashRouter — 客户端 Hash 路由 (v3.0)
 *
 * 职责:
 *   1. 监听 hashchange → 匹配路由 → 挂载/卸载
 *   2. AnimationController 页面过渡
 *   3. 前置守卫
 *   4. 编程式导航
 *
 * v7.0 迁移: HashRouter → Vue Router createRouter/createWebHashHistory
 *   - register()      → router.addRoute()
 *   - onBeforeNavigate() → router.beforeEach()
 *   - navigate()      → router.push()
 *   - 页面生命周期      → <RouterView> + keep-alive
 *
 * @version 3.0
 */

export class HashRouter {
    /** @type {Object<string, {PageClass, regex, paramNames, pattern}>} */
    #routes = {};

    /** @type {import('./js/components/BaseComponent.js').BaseComponent|null} */
    #currentPage = null;

    /** @type {Element} */
    #container;

    /** @type {Object|null} */
    #currentRoute = null;

    /** @type {Function[]} */
    #guards = [];

    /** @type {boolean} */
    #navPending = false;

    /** @type {number} */
    #lastNavTime = 0;

    /**
     * AppContext reference (v7.0: provided by Vue inject)
     * @type {import('./js/AppContext.js').AppContext|null}
     */
    #context = null;

    /**
     * @param {Element} container — 页面挂载容器
     * @param {Object} [routes] — 初始路由表
     */
    constructor(container, routes = {}) {
        this.#container = container;

        for (const [pattern, PageClass] of Object.entries(routes)) {
            this.register(pattern, PageClass);
        }

        window.addEventListener('hashchange', () => this.#handleRoute());
        window.addEventListener('popstate', () => this.#handleRoute());
    }

    // ========================================================================
    // 公共 API
    // ========================================================================

    /**
     * 注册路由
     * @param {string} pattern — e.g. '#/report/:analysisId'
     * @param {typeof import('./js/components/BaseComponent.js').BaseComponent} PageClass
     */
    register(pattern, PageClass) {
        const paramNames = [];
        const regexStr = pattern.replace(/:([^/]+)/g, (_, name) => {
            paramNames.push(name);
            return '([^/]+)';
        });
        const regex = new RegExp('^' + regexStr + '$');

        this.#routes[pattern] = { PageClass, regex, paramNames, pattern };
    }

    /**
     * 前置守卫 (v7.0 → router.beforeEach)
     * @param {Function} guard — (next, prev) => true | false | 'redirectHash'
     */
    onBeforeNavigate(guard) {
        this.#guards.push(guard);
    }

    /**
     * 启动路由 — 匹配当前 URL 并渲染首页
     */
    start() {
        if (!location.hash || location.hash === '#') {
            location.hash = '#/';
        }
        this.#handleRoute();
    }

    /**
     * 编程式导航 (v7.0 → router.push)
     * @param {string} hash — e.g. '#/history'
     * @param {boolean} [replace=false] — replaceState 不产生历史
     */
    navigate(hash, replace = false) {
        if (replace) {
            const url = new URL(location);
            url.hash = hash;
            history.replaceState(null, '', url.toString());
        } else {
            location.hash = hash;
        }
    }

    /**
     * 后退 (v7.0 → router.back)
     */
    back() {
        history.back();
    }

    /**
     * @returns {Object|null} 当前路由 { hash, params }
     */
    getCurrentRoute() {
        return this.#currentRoute;
    }

    /**
     * @returns {Object} URL query params
     */
    getQueryParams() {
        const params = {};
        const search = location.search.substring(1);
        if (!search) return params;
        for (const pair of search.split('&')) {
            const [key, value] = pair.split('=');
            if (key) params[decodeURIComponent(key)] = decodeURIComponent(value || '');
        }
        return params;
    }

    // ========================================================================
    // 依赖注入 (v7.0 → Vue inject)
    // ========================================================================

    /**
     * 注入 AppContext (替代 window.__* 全局变量)
     * @param {import('./js/AppContext.js').AppContext} context
     */
    useContext(context) {
        this.#context = context;
    }

    /**
     * 获取 AnimationController
     * v7.0 → useGsap() composable
     * @private
     */
    get #ac() {
        if (this.#context?.ac) return this.#context.ac;
        if (typeof window !== 'undefined' && window.__ac) return window.__ac;
        return null;
    }

    // ========================================================================
    // 内部
    // ========================================================================

    #matchRoute() {
        const hash = location.hash || '#/';

        for (const entry of Object.values(this.#routes)) {
            const match = hash.match(entry.regex);
            if (match) {
                const params = {};
                entry.paramNames.forEach((name, i) => {
                    params[name] = match[i + 1];
                });
                return { entry, params };
            }
        }
        return null;
    }

    async #handleRoute() {
        console.log('[Router] handleRoute called, hash=' + location.hash + ', pending=' + this.#navPending);

        // CRITICAL: check pending FIRST, before any killAll().
        // A single click fires both hashchange + popstate; the second
        // call must not kill the first call's leave animation.
        if (this.#navPending) {
            console.warn('[Router] BLOCKED: navigation already pending');
            return;
        }
        this.#navPending = true;

        // 防抖: 300ms 内的快速导航取消上一个 (已废弃的动画)
        const now = Date.now();
        if (now - this.#lastNavTime < 300) {
            const ac = this.#ac;
            if (ac) ac.killAll();
        }
        this.#lastNavTime = now;

        try {
            const matched = this.#matchRoute();
            console.log('[Router] matchRoute result:', matched ? matched.entry.pattern : 'NO MATCH');

            if (!matched) {
                console.warn('[Router] Unknown route:', location.hash, '→ redirect to #/');
                location.replace('#/');
                return;
            }

            const next = { hash: location.hash, params: matched.params };

            // 前置守卫
            for (const guard of this.#guards) {
                const result = guard(next, this.#currentRoute);
                if (result === false) {
                    console.warn('[Router] Guard blocked navigation');
                    return;
                }
                if (typeof result === 'string') {
                    console.log('[Router] Guard redirect to:', result);
                    this.navigate(result, true);
                    return;
                }
            }

            const prev = this.#currentRoute;
            this.#currentRoute = next;

            console.log('[Router] Starting transition to:', next.hash);
            await this.#transition(prev, next, matched.entry);
            console.log('[Router] Transition complete');
        } catch(e) {
            console.error('[Router] Unhandled error in handleRoute:', e);
        } finally {
            this.#navPending = false;
        }
    }

    async #transition(prevRoute, nextRoute, entry) {
        const { PageClass } = entry;
        console.log('[Router] transition start, PageClass:', PageClass?.name || 'unknown');

        // 1. 旧页面出场 (v7.0: <RouterView> + <Transition>)
        if (this.#currentPage && typeof this.#currentPage.beforeUnmount === 'function') {
            try { await this.#currentPage.beforeUnmount(); } catch (e) { console.warn('[Router] beforeUnmount error:', e); }
        }

        // 2. 销毁旧页面 (v7.0: keep-alive → onUnmounted)
        if (this.#currentPage && typeof this.#currentPage.destroy === 'function') {
            try { this.#currentPage.destroy(); } catch (e) { console.warn('[Router] destroy error:', e); }
        }
        this.#container.innerHTML = '';
        console.log('[Router] old page destroyed, container cleared');

        // 3. 创建并挂载新页面 (v7.0: <RouterView> 自动)
        try {
            console.log('[Router] creating new page...');

            // 注入 context 到页面 (v7.0: Vue provide/inject 自动)
            const page = new PageClass(this.#container, {
                context: this.#context || undefined
            });
            console.log('[Router] page created:', page.constructor.name);
            this.#currentPage = page;

            // 确保页面有 store/router 引用 (向后兼容)
            // v7.0: 由 Pinia/useRouter inject 自动提供
            if (!page.store && typeof window !== 'undefined' && window.__store) {
                page.store = window.__store;
            }
            if (!page.router && typeof window !== 'undefined' && window.__router) {
                page.router = window.__router;
            }

            if (typeof page.mount === 'function') {
                console.log('[Router] calling page.mount()...');
                await page.mount(nextRoute.params);
                console.log('[Router] page.mount() completed');
            }
            console.log('[Router] container children:', this.#container.children.length);
        } catch (e) {
            console.error('[Router] Page mount failed:', e);
            this.#container.innerHTML = `<div style="padding:40px;text-align:center;color:var(--danger)">
                <h2>页面加载失败</h2>
                <p>${e.message || '未知错误'}</p>
                <button onclick="location.hash='#/'" style="margin-top:16px;padding:8px 20px;border:none;border-radius:8px;background:var(--primary);color:#fff;cursor:pointer;font-size:14px;">返回首页</button>
            </div>`;
        }
    }
}

if (typeof window !== 'undefined') {
    window.__router = null;
}
