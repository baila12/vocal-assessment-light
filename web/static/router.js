/**
 * HashRouter — 客户端 Hash 路由
 *
 * 职责:
 * 1. 监听 hashchange 事件 → 匹配路由表 → 挂载/卸载页面
 * 2. GSAP 页面过渡动画
 * 3. 前置守卫 (onBeforeNavigate)
 * 4. 编程式导航 (navigate, back)
 *
 * @version 1.0
 */

/**
 * @typedef {{ hash: string, params: Object<string, string> }} RouteMatch
 */

export class HashRouter {
    /** @type {Object<string, typeof import('./js/components/BaseComponent.js').BaseComponent>} */
    #routes = {};

    /** @type {import('./js/components/BaseComponent.js').BaseComponent|null} */
    #currentPage = null;

    /** @type {Element} */
    #container;

    /** @type {RouteMatch|null} */
    #currentRoute = null;

    /** @type {Array<(next: RouteMatch, prev: RouteMatch|null) => boolean|string>} */
    #guards = [];

    /**
     * @param {Element} container - 页面挂载容器
     * @param {Object<string, class>} routes - { hashPattern: PageClass }
     */
    constructor(container, routes = {}) {
        this.#container = container;

        for (const [pattern, PageClass] of Object.entries(routes)) {
            this.register(pattern, PageClass);
        }

        // 监听 hashchange
        window.addEventListener('hashchange', () => this.#handleRoute());

        // 监听 popstate (浏览器后退/前进)
        window.addEventListener('popstate', () => this.#handleRoute());
    }

    /**
     * 注册路由
     * @param {string} pattern - 路由模式，如 '#/', '#/sing/:songId', '#/report/:analysisId'
     * @param {class} PageClass - 页面类
     */
    register(pattern, PageClass) {
        // 将 :param 转换为命名捕获组
        const paramNames = [];
        const regexStr = pattern.replace(/:([^/]+)/g, (_, name) => {
            paramNames.push(name);
            return '([^/]+)';
        });
        const regex = new RegExp(`^${regexStr}$`);

        this.#routes[pattern] = {
            PageClass,
            regex,
            paramNames,
            pattern
        };
    }

    /**
     * 添加前置守卫
     * @param {(next: RouteMatch, prev: RouteMatch|null) => boolean|string} guard
     *       返回 true 放行，返回 false 阻止，返回字符串则重定向到该路径
     */
    onBeforeNavigate(guard) {
        this.#guards.push(guard);
    }

    /**
     * 启动路由 — 处理当前 hash
     */
    start() {
        if (!location.hash || location.hash === '#') {
            location.hash = '#/';
        }
        this.#handleRoute();
    }

    /**
     * 编程式导航
     * @param {string} hash - 目标 hash，如 '#/history', '#/report/42'
     * @param {boolean} [replace=false] - 是否替换历史记录 (不产生新的 history entry)
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
     * 返回上一页
     */
    back() {
        history.back();
    }

    /**
     * 获取当前路由信息
     * @returns {RouteMatch|null}
     */
    getCurrentRoute() {
        return this.#currentRoute;
    }

    /**
     * 解析 URL 查询参数
     * @returns {Object<string, string>}
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
    // 内部方法
    // ========================================================================

    /**
     * 解析当前 hash 匹配路由
     * @returns {{ entry: object, params: Object<string, string> }|null}
     */
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

    /**
     * 处理路由变化
     */
    async #handleRoute() {
        const matched = this.#matchRoute();

        // 无效路由 → 重定向到首页
        if (!matched) {
            console.warn(`[Router] 未知路由: ${location.hash}，重定向到首页`);
            location.replace('#/');
            return;
        }

        const next = {
            hash: location.hash,
            params: matched.params
        };

        // 前置守卫检查
        for (const guard of this.#guards) {
            const result = guard(next, this.#currentRoute);
            if (result === false) {
                // 阻止导航
                return;
            }
            if (typeof result === 'string') {
                // 重定向
                this.navigate(result, true);
                return;
            }
        }

        const prev = this.#currentRoute;
        this.#currentRoute = next;

        // GSAP 页面过渡
        await this.#transition(prev, next, matched.entry);
    }

    /**
     * GSAP 页面过渡动画
     */
    async #transition(prevRoute, nextRoute, entry) {
        const { PageClass } = entry;

        // 1. 旧页面出场动画
        if (this.#currentPage && typeof this.#currentPage.beforeUnmount === 'function') {
            await this.#currentPage.beforeUnmount();
        }

        // 2. 销毁旧页面
        if (this.#currentPage && typeof this.#currentPage.destroy === 'function') {
            this.#currentPage.destroy();
        }
        this.#container.innerHTML = '';

        // 3. 创建并挂载新页面
        const page = new PageClass(this.#container);
        this.#currentPage = page;

        // 注入 router 和 store (如果存在)
        if (window.__store) {
            page.store = window.__store;
        }
        if (window.__router) {
            page.router = window.__router;
        }

        if (typeof page.mount === 'function') {
            await page.mount(nextRoute.params);
        }
    }
}

// 单例引用 — 挂载到 window 供非模块代码使用
if (typeof window !== 'undefined') {
    window.__router = null; // 由 app.js 初始化时设置
}
