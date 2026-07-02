/**
 * BaseComponent — 组件基类
 *
 * 所有页面和组件遵循统一生命周期接口
 * 集成 AnimationController: mount → enter(), beforeUnmount → leave()
 *
 * @version 2.0
 */
export class BaseComponent {
    /** @type {Element} */
    container;

    /** @type {Object} */
    options;

    /** @type {import('../state/store.js').Store|null} */
    store;

    /** @type {import('../../router.js').HashRouter|null} */
    router;

    /** @type {import('../api/backend.js').ApiClient|null} */
    api;

    /** @type {Element|null} */
    el;

    /**
     * 页面动画预设 (子类可覆写)
     * 页面入场预设名称，例如 'page-enter', 'page-enter-down', 'page-enter-scale'
     */
    static animationPreset = 'page-enter';

    constructor(container, options = {}) {
        this.container = container;
        this.options = options;
        this.store = options.store || null;
        this.router = options.router || null;
        this.api = options.api || null;

        if (!this.store && typeof window !== 'undefined' && window.__store) {
            this.store = window.__store;
        }
        if (!this.router && typeof window !== 'undefined' && window.__router) {
            this.router = window.__router;
        }
        if (!this.api && typeof window !== 'undefined' && window.__api) {
            this.api = window.__api;
        }
    }

    /**
     * 获取 AnimationController 实例
     * @returns {import('../animation/Controller.js').AnimationController|null}
     */
    get ac() {
        return (typeof window !== 'undefined' && window.__ac) || null;
    }

    /**
     * 挂载 — 创建 DOM，绑定事件，触发入场动画
     * @param {Object} [params]
     * @returns {Promise<void>}
     */
    async mount(params) {
        this.render(params);
        this.bindEvents();
        await this.animateIn();
    }

    /**
     * 入场动画 — 自动使用 AnimationController
     * 子类可覆写以实现自定义动画序列
     * @returns {Promise<void>}
     */
    async animateIn() {
        const preset = this.constructor.animationPreset || 'page-enter';
        if (this.ac && this.el) {
            this.ac.enter(this.el, { preset });
        } else if (this.el && typeof gsap !== 'undefined') {
            await gsap.fromTo(this.el,
                { opacity: 0, y: 12 },
                { opacity: 1, y: 0, duration: 0.35, ease: 'power2.out' }
            ).then();
        } else if (this.el) {
            this.el.style.opacity = '1';
        }
    }

    render(params) {
        // 子类覆写
    }

    bindEvents() {
        // 子类覆写
    }

    update(data) {
        // 子类覆写
    }

    /**
     * 卸载前的出场动画
     * @returns {Promise<void>}
     */
    async beforeUnmount() {
        const preset = this.constructor.animationPreset || 'page-leave';
        if (this.ac && this.el) {
            await this.ac.leave(this.el, { preset });
        } else if (this.el && typeof gsap !== 'undefined') {
            await gsap.to(this.el, {
                opacity: 0,
                duration: 0.15,
                ease: 'power2.in'
            }).then();
        }
    }

    /**
     * 销毁 — 清理动画、事件、DOM
     */
    destroy() {
        if (this.el) {
            if (this.ac) {
                // 由 Controller 统一清理
            } else if (typeof gsap !== 'undefined') {
                gsap.killTweensOf(this.el);
                gsap.killTweensOf(this.el.querySelectorAll('*'));
            }
        }
        if (this.el && this.el.parentNode) {
            this.el.remove();
        }
        this.el = null;
    }

    /**
     * 显示 (带 GSAP 入场动画)
     * @returns {Promise<void>}
     */
    async show() {
        if (!this.el) return;
        if (this.ac) {
            this.ac.enter(this.el, { preset: 'slideUp-sm' });
            return;
        }
        if (typeof gsap === 'undefined') {
            this.el.style.display = '';
            this.el.style.opacity = '1';
            return;
        }
        this.el.style.display = '';
        return gsap.fromTo(this.el,
            { opacity: 0, y: 12 },
            { opacity: 1, y: 0, duration: 0.3, ease: 'power2.out' }
        ).then();
    }

    /**
     * 隐藏 (带 GSAP 出场动画)
     * @returns {Promise<void>}
     */
    async hide() {
        if (!this.el) return;
        if (this.ac) {
            await this.ac.leave(this.el, { preset: 'page-leave' });
            return;
        }
        if (typeof gsap === 'undefined') {
            this.el.style.display = 'none';
            return;
        }
        return gsap.to(this.el, {
            opacity: 0,
            y: -8,
            duration: 0.2,
            ease: 'power2.in',
            onComplete: () => { this.el.style.display = 'none'; }
        }).then();
    }

    /**
     * 创建元素 (快捷方法)
     */
    createElement(tag, attrs = {}, ...children) {
        const el = document.createElement(tag);
        for (const [key, value] of Object.entries(attrs)) {
            if (key === 'className') { el.className = value; }
            else if (key === 'style' && typeof value === 'object') { Object.assign(el.style, value); }
            else if (key.startsWith('on') && typeof value === 'function') { el.addEventListener(key.substring(2).toLowerCase(), value); }
            else if (key === 'dataset' && typeof value === 'object') { Object.assign(el.dataset, value); }
            else if (key === 'html') { el.innerHTML = value; }
            else { el.setAttribute(key, value); }
        }
        for (const child of children) {
            if (typeof child === 'string') { el.appendChild(document.createTextNode(child)); }
            else if (child instanceof Element) { el.appendChild(child); }
            else if (Array.isArray(child)) { child.forEach(c => el.appendChild(typeof c === 'string' ? document.createTextNode(c) : c)); }
        }
        return el;
    }
}

export default BaseComponent;
