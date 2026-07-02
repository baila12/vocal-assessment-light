/**
 * HashRouter — 客户端 Hash 路由
 *
 * 职责:
 *   1. 监听 hashchange → 匹配路由 → 挂载/卸载
 *   2. AnimationController 页面过渡 (v2.0)
 *   3. 前置守卫
 *   4. 编程式导航
 *
 * @version 2.0
 */

export class HashRouter {
    #routes = {};
    #currentPage = null;
    #container;
    #currentRoute = null;
    #guards = [];
    #navPending = false;
    #lastNavTime = 0;

    constructor(container, routes = {}) {
        this.#container = container;

        for (const [pattern, PageClass] of Object.entries(routes)) {
            this.register(pattern, PageClass);
        }

        window.addEventListener('hashchange', () => this.#handleRoute());
        window.addEventListener('popstate', () => this.#handleRoute());
    }

    register(pattern, PageClass) {
        const paramNames = [];
        const regexStr = pattern.replace(/:([^/]+)/g, (_, name) => {
            paramNames.push(name);
            return '([^/]+)';
        });
        const regex = new RegExp('^' + regexStr + '$');

        this.#routes[pattern] = { PageClass, regex, paramNames, pattern };
    }

    onBeforeNavigate(guard) {
        this.#guards.push(guard);
    }

    start() {
        if (!location.hash || location.hash === '#') {
            location.hash = '#/';
        }
        this.#handleRoute();
    }

    navigate(hash, replace = false) {
        if (replace) {
            const url = new URL(location);
            url.hash = hash;
            history.replaceState(null, '', url.toString());
        } else {
            location.hash = hash;
        }
    }

    back() {
        history.back();
    }

    getCurrentRoute() {
        return this.#currentRoute;
    }

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
        // 防抖: 300ms 内的快速导航取消上一个
        const now = Date.now();
        if (now - this.#lastNavTime < 300) {
            // kill 上一个页面的动画
            if (window.__ac) {
                window.__ac.killAll();
            }
        }
        this.#lastNavTime = now;

        if (this.#navPending) return;
        this.#navPending = true;

        try {
            const matched = this.#matchRoute();

            if (!matched) {
                console.warn('[Router] Unknown route:', location.hash, '→ redirect to #/');
                location.replace('#/');
                return;
            }

            const next = { hash: location.hash, params: matched.params };

            // 前置守卫
            for (const guard of this.#guards) {
                const result = guard(next, this.#currentRoute);
                if (result === false) return;
                if (typeof result === 'string') {
                    this.navigate(result, true);
                    return;
                }
            }

            const prev = this.#currentRoute;
            this.#currentRoute = next;

            await this.#transition(prev, next, matched.entry);
        } finally {
            this.#navPending = false;
        }
    }

    async #transition(prevRoute, nextRoute, entry) {
        const { PageClass } = entry;

        // 1. 旧页面出场
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

        if (window.__store) page.store = window.__store;
        if (window.__router) page.router = window.__router;

        if (typeof page.mount === 'function') {
            await page.mount(nextRoute.params);
        }
    }
}

if (typeof window !== 'undefined') {
    window.__router = null;
}
