/**
 * BaseComponent — 组件基类
 *
 * 所有页面和组件遵循统一生命周期接口
 *
 * @version 1.0
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

    /** @type {Element|null} */
    el; // 根 DOM 元素

    /**
     * @param {Element} container - 父容器
     * @param {Object} [options={}]
     */
    constructor(container, options = {}) {
        this.container = container;
        this.options = options;
        this.store = options.store || null;
        this.router = options.router || null;
        this.api = options.api || null;

        // 从全局获取 (如果未通过 options 传入)
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
     * 挂载 — 创建 DOM，绑定事件，触发入场动画
     * @param {Object} [params] - 路由参数或其他上下文
     * @returns {Promise<void>}
     */
    async mount(params) {
        this.render(params);
        this.bindEvents();
    }

    /**
     * 渲染 DOM
     * @param {Object} [params]
     */
    render(params) {
        // 子类覆写
    }

    /**
     * 绑定事件
     */
    bindEvents() {
        // 子类覆写
    }

    /**
     * 更新 — 接收新数据，驱动 DOM 变化
     * @param {*} data
     */
    update(data) {
        // 子类覆写
    }

    /**
     * 卸载前的 GSAP 出场动画
     * @returns {Promise<void>}
     */
    async beforeUnmount() {
        if (this.el && typeof gsap !== 'undefined') {
            await gsap.to(this.el, {
                opacity: 0,
                duration: 0.15,
                ease: 'power2.in'
            }).then();
        }
    }

    /**
     * 销毁 — 移除事件监听、清理定时器/动画、移除 DOM
     */
    destroy() {
        // 清理 GSAP 动画
        if (this.el && typeof gsap !== 'undefined') {
            gsap.killTweensOf(this.el);
            gsap.killTweensOf(this.el.querySelectorAll('*'));
        }
        // 移除 DOM
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
     * @param {string} tag
     * @param {Object} [attrs]
     * @param {string|Element|Element[]} [children]
     * @returns {Element}
     */
    createElement(tag, attrs = {}, ...children) {
        const el = document.createElement(tag);
        for (const [key, value] of Object.entries(attrs)) {
            if (key === 'className') {
                el.className = value;
            } else if (key === 'style' && typeof value === 'object') {
                Object.assign(el.style, value);
            } else if (key.startsWith('on') && typeof value === 'function') {
                el.addEventListener(key.substring(2).toLowerCase(), value);
            } else if (key === 'dataset' && typeof value === 'object') {
                Object.assign(el.dataset, value);
            } else if (key === 'html') {
                el.innerHTML = value;
            } else {
                el.setAttribute(key, value);
            }
        }
        for (const child of children) {
            if (typeof child === 'string') {
                el.appendChild(document.createTextNode(child));
            } else if (child instanceof Element) {
                el.appendChild(child);
            } else if (Array.isArray(child)) {
                child.forEach(c => el.appendChild(typeof c === 'string' ? document.createTextNode(c) : c));
            }
        }
        return el;
    }
}

export default BaseComponent;
