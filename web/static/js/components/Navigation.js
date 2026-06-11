/**
 * TopNav + BottomNav — 导航组件
 *
 * PC 端: 顶部横排导航
 * 移动端: 底部固定导航
 * 使用 gsap.matchMedia() 自适配
 *
 * @version 1.0
 */

import { BaseComponent } from './BaseComponent.js';

const NAV_ITEMS = [
    { hash: '#/',         icon: 'home',    label: '首页' },
    { hash: '#/sing',     icon: 'sing',    label: '演唱' },
    { hash: '#/compare',  icon: 'compare', label: '对比' },
    { hash: '#/history',  icon: 'history', label: '历史' },
    { hash: '#/settings', icon: 'settings',label: '设置' }
];

// SVG 图标
const ICONS = {
    home: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>',
    sing: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>',
    compare: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>',
    history: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
    settings: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H12a1.65 1.65 0 0 0 1-1.51V9a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V12a1.65 1.65 0 0 0 1.51 1H3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09z"/></svg>'
};

export class TopNav extends BaseComponent {
    /** @type {string} */
    #activeHash = '#/';

    #buttons = {};

    render() {
        this.el = this.createElement('nav', {
            className: 'navbar top-nav',
            style: {
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0 24px',
                height: '56px',
                background: 'var(--bg-card)',
                borderBottom: '1px solid var(--border)',
                position: 'sticky',
                top: '0',
                zIndex: 'var(--z-sticky)'
            }
        });

        // 品牌区
        const brand = this.createElement('div', {
            className: 'navbar-brand',
            style: { display: 'flex', alignItems: 'center', gap: '10px' }
        });
        brand.innerHTML = `
            <div class="logo">
                ${ICONS.sing}
            </div>
            <div class="brand-text">
                <span class="brand-name">声乐评估系统</span>
                <span class="brand-tag">专业版</span>
            </div>
        `;
        this.el.appendChild(brand);

        // 导航标签
        const tabs = this.createElement('div', {
            className: 'nav-tabs',
            style: { display: 'flex', gap: '2px' }
        });

        NAV_ITEMS.forEach(item => {
            const btn = this.createElement('button', {
                className: 'nav-tab',
                dataset: { hash: item.hash },
                style: {
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '8px 14px',
                    border: 'none',
                    background: 'transparent',
                    color: 'var(--text-secondary)',
                    fontSize: '13px',
                    fontWeight: '500',
                    cursor: 'pointer',
                    borderRadius: 'var(--radius-md)',
                    transition: 'color 0.2s'
                },
                onClick: () => this.#navigate(item.hash)
            });
            btn.innerHTML = `${ICONS[item.icon]} <span>${item.label}</span>`;
            this.#buttons[item.hash] = btn;
            tabs.appendChild(btn);
        });

        this.el.appendChild(tabs);
        this.container.appendChild(this.el);

        this.#updateActive();
    }

    /**
     * 更新当前高亮
     * @param {string} hash
     */
    setActive(hash) {
        this.#activeHash = hash;
        this.#updateActive();
    }

    #navigate(hash) {
        if (this.router) {
            this.router.navigate(hash);
        } else {
            location.hash = hash;
        }
    }

    #updateActive() {
        Object.entries(this.#buttons).forEach(([hash, btn]) => {
            const isActive = this.#activeHash === hash ||
                (hash !== '#/' && this.#activeHash.startsWith(hash));
            btn.classList.toggle('active', isActive);
            btn.style.color = isActive ? 'var(--primary)' : 'var(--text-secondary)';
            btn.style.background = isActive ? 'var(--primary-ghost)' : 'transparent';
        });
    }
}

export class BottomNav extends BaseComponent {
    /** @type {string} */
    #activeHash = '#/';

    #buttons = {};

    render() {
        this.el = this.createElement('nav', {
            className: 'bottom-nav',
            style: {
                display: 'none', // 默认隐藏，matchMedia 控制
                position: 'fixed',
                bottom: '0',
                left: '0',
                right: '0',
                height: '64px',
                background: 'var(--bg-card)',
                borderTop: '1px solid var(--border)',
                zIndex: 'var(--z-sticky)',
                justifyContent: 'space-around',
                alignItems: 'center',
                paddingBottom: 'env(safe-area-inset-bottom, 0)'
            }
        });

        const items = NAV_ITEMS.slice(0, 4); // 移动端只显示4个 (不含设置)

        items.forEach(item => {
            const btn = this.createElement('button', {
                className: 'nav-tab-mobile',
                dataset: { hash: item.hash },
                style: {
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: '3px',
                    padding: '8px 12px',
                    border: 'none',
                    background: 'transparent',
                    color: 'var(--text-muted)',
                    fontSize: '10px',
                    fontWeight: '500',
                    cursor: 'pointer',
                    minWidth: '60px'
                },
                onClick: () => this.#navigate(item.hash)
            });
            btn.innerHTML = `${ICONS[item.icon]}<span>${item.label}</span>`;
            this.#buttons[item.hash] = btn;
            this.el.appendChild(btn);
        });

        document.body.appendChild(this.el); // 挂到 body，不是 container
    }

    setActive(hash) {
        this.#activeHash = hash;
        this.#updateActive();
    }

    #navigate(hash) {
        if (this.router) {
            this.router.navigate(hash);
        } else {
            location.hash = hash;
        }
    }

    #updateActive() {
        Object.entries(this.#buttons).forEach(([hash, btn]) => {
            const isActive = this.#activeHash === hash ||
                (hash !== '#/' && this.#activeHash.startsWith(hash));
            btn.style.color = isActive ? 'var(--primary)' : 'var(--text-muted)';
        });
    }
}

/**
 * 初始化响应式导航 (gsap.matchMedia)
 */
export function initResponsiveNav() {
    const topNav = document.querySelector('.top-nav');
    const bottomNav = document.querySelector('.bottom-nav');

    if (!topNav || !bottomNav) return;

    const updateNav = () => {
        const isMobile = window.matchMedia('(max-width: 767px)').matches;
        topNav.style.display = isMobile ? 'none' : 'flex';
        bottomNav.style.display = isMobile ? 'flex' : 'none';
    };

    // 初始检查
    updateNav();

    // 监听变化
    const mq = window.matchMedia('(max-width: 767px)');
    mq.addEventListener('change', updateNav);

    // GSAP matchMedia 增强 (如果可用)
    if (typeof gsap !== 'undefined') {
        gsap.matchMedia().add({
            mobile: '(max-width: 767px)',
            desktop: '(min-width: 768px)',
            reduceMotion: '(prefers-reduced-motion: reduce)'
        }, (ctx) => {
            const { mobile } = ctx.conditions;
            if (topNav) topNav.style.display = mobile ? 'none' : 'flex';
            if (bottomNav) bottomNav.style.display = mobile ? 'flex' : 'none';
        });
    }
}

export default { TopNav, BottomNav, initResponsiveNav };
