/**
 * BaseComponent — 组件基类 (v3.0)
 *
 * 所有页面和组件遵循统一生命周期接口。
 *
 * ## v7.0 Vue 迁移映射
 *
 *   Vanilla JS (当前)          Vue 3 (v7.0)
 *   ─────────────────────      ─────────────────
 *   constructor(container)     setup() / <script setup>
 *   render()                   <template> 或 h() render
 *   bindEvents()               @click, @input 等模板指令
 *   mount(params)              onBeforeMount + onMounted
 *   animateIn()                <Transition> 或 useGsap
 *   beforeUnmount()            onBeforeUnmount
 *   destroy()                  onUnmounted (自动 GC)
 *   this.context.store         useStore() / Pinia
 *   this.context.router        useRouter()
 *   this.context.api           HTTP client / IPC bridge
 *   this.context.ac            useGsap() composable
 *   this.context.events        mitt()
 *   createElement(tag, ...)    <template> 直接写 HTML
 *
 * ## 依赖注入
 *
 *   优先使用 context (AppContext)，回退到 window 全局。
 *   v7.0 中 window 回退将被移除，context 由 Vue provide/inject 提供。
 *
 * @version 3.0
 */

export class BaseComponent {
    // ========================================================================
    // 静态
    // ========================================================================

    /**
     * 入场动画预设名称 (子类可覆写)
     * v7.0: 替换为 <Transition name="..."> 或 useGsap preset
     */
    static animationPreset = 'page-enter';

    // ========================================================================
    // 实例属性
    // ========================================================================

    /** @type {Element} — 挂载容器 (v7.0: template ref) */
    container;

    /** @type {Object} — 构造选项 */
    options;

    /** @type {import('../AppContext.js').AppContext|null} */
    context;

    /** @type {Element|null} — 根 DOM 元素 (v7.0: template ref) */
    el;

    // ========================================================================
    // 构造函数
    // ========================================================================

    /**
     * @param {Element} container — 挂载目标容器
     * @param {Object} [options]
     * @param {import('../AppContext.js').AppContext} [options.context]
     *    AppContext 实例。v7.0 中由 Vue provide/inject 自动注入。
     */
    constructor(container, options = {}) {
        this.container = container;
        this.options = options;

        // 依赖注入: 优先显式传入，回退到全局 AppContext
        this.context = options.context || null;
        if (!this.context && typeof window !== 'undefined') {
            this.context = window.__appContext || null;
        }
    }

    // ========================================================================
    // 服务 getters (v7.0 → Vue composables)
    // ========================================================================

    /** @returns {import('../state/store.js').Store|null} */
    get store() {
        return this.context?.store
            || (typeof window !== 'undefined' && window.__store)
            || null;
    }

    /** @returns {import('../../router.js').HashRouter|null} */
    get router() {
        return this.context?.router
            || (typeof window !== 'undefined' && window.__router)
            || null;
    }

    /** @returns {import('../services/api.js').ApiClient|null} */
    get api() {
        return this.context?.api
            || (typeof window !== 'undefined' && window.__api)
            || null;
    }

    /** @returns {import('../animation/Controller.js').AnimationController|null} */
    get ac() {
        return this.context?.ac
            || (typeof window !== 'undefined' && window.__ac)
            || null;
    }

    // ========================================================================
    // 生命周期 (对齐 Vue 3)
    // ========================================================================

    /**
     * 挂载 — 对应 Vue onBeforeMount + onMounted
     *
     * 标准流程: render() → bindEvents() → animateIn()
     * 子类覆写时应遵循: super.mount(params) 或自行管理完整流程
     *
     * @param {Object} [params] — 路由参数或初始化数据
     * @returns {Promise<void>}
     */
    async mount(params) {
        // 1. onBeforeMount — 创建 DOM
        this.render(params);
        if (this.el) this.el.classList.add('active');

        // 2. onMounted — 绑定事件
        this.bindEvents();

        // 3. 入场动画 (对应 Vue <Transition>)
        await this.animateIn();
    }

    /**
     * 创建 DOM — 对应 Vue template 或 render()
     * 子类必须覆写，在其中设置 this.el 并附加到 this.container
     *
     * @param {Object} [params]
     */
    render(params) {
        // 子类覆写: this.el = this.createElement(...); this.container.appendChild(this.el);
    }

    /**
     * 绑定事件 — 对应 Vue @click/@input 等模板指令
     * v7.0 中事件绑定由模板声明，此方法废弃
     */
    bindEvents() {
        // 子类覆写
    }

    /**
     * 响应数据更新 — 对应 Vue watch 或 computed 的副作用
     * @param {Object} data
     */
    update(data) {
        // 子类覆写
    }

    /**
     * 入场动画 — 对应 Vue <Transition name="page">
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

    /**
     * 卸载前 — 对应 Vue onBeforeUnmount
     * 出场动画放在这里，保证在 DOM 移除前执行
     * @returns {Promise<void>}
     */
    async beforeUnmount() {
        const preset = 'page-leave';
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
     * 销毁 — 对应 Vue onUnmounted
     * 清理动画、事件、DOM。Vue 中 DOM 移除由框架自动处理。
     */
    destroy() {
        // 清理 GSAP 动画
        if (this.el) {
            if (typeof gsap !== 'undefined') {
                gsap.killTweensOf(this.el);
                gsap.killTweensOf(this.el.querySelectorAll('*'));
            }
        }
        // 移除 DOM
        if (this.el && this.el.parentNode) {
            this.el.remove();
        }
        this.el = null;
    }

    // ========================================================================
    // 显示/隐藏 (非路由切换场景，如 Modal/Tab)
    // ========================================================================

    /**
     * 显示 (带入场动画)
     * v7.0: v-if / v-show + <Transition>
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
     * 隐藏 (带出场动画)
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

    // ========================================================================
    // 工具方法 (v7.0 中由 <template> 替代)
    // ========================================================================

    /**
     * 创建 HTML 元素 — v7.0 废弃，替换为 <template>
     *
     * @param {string} tag
     * @param {Object} [attrs]
     * @param {...(string|Element|Element[])} children
     * @returns {Element}
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
