/**
 * Toast — 通知组件
 *
 * 位置: 页面顶部居中固定
 * 类型: success | error | warning | info
 * 动画: AnimationController 驱动
 * 限制: 最多 3 个同时显示
 *
 * @version 2.0
 */

import { BaseComponent } from './BaseComponent.js';

const TOAST_TYPES = {
    success: { icon: '✓', bg: 'var(--success)', color: '#fff' },
    error:   { icon: '✕', bg: 'var(--danger)', color: '#fff' },
    warning: { icon: '⚠', bg: 'var(--warning)', color: '#fff' },
    info:    { icon: 'ℹ', bg: 'var(--info)', color: '#fff' }
};

const MAX_TOASTS = 3;

let activeToasts = 0;

export class Toast extends BaseComponent {
    #type;
    #message;
    #duration;
    #onAction;
    #timer;

    constructor(container, options = {}) {
        super(container, options);
        this.#type = options.type || 'info';
        this.#message = options.message || '';
        this.#duration = options.duration || 3500;
        this.#onAction = options.action?.handler || null;
    }

    render() {
        if (activeToasts >= MAX_TOASTS) {
            const first = this.container.querySelector('.toast-item');
            if (first) {
                if (this.ac) {
                    this.ac.leave(first, { preset: 'toast-exit' });
                } else if (typeof gsap !== 'undefined') {
                    gsap.to(first, { opacity: 0, y: -20, duration: 0.2, ease: 'power2.in',
                        onComplete: () => { first.remove(); }
                    });
                } else {
                    first.remove();
                }
                activeToasts--;
            }
        }

        const config = TOAST_TYPES[this.#type] || TOAST_TYPES.info;

        this.el = this.createElement('div', {
            className: 'toast-item',
            style: {
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '12px 20px',
                background: config.bg,
                color: config.color,
                borderRadius: 'var(--radius-md)',
                boxShadow: 'var(--shadow-lg)',
                fontSize: '14px',
                fontWeight: '500',
                marginBottom: '8px',
                pointerEvents: 'auto',
                cursor: 'default',
                whiteSpace: 'nowrap'
            }
        });

        const icon = this.createElement('span', { style: { fontSize: '16px', fontWeight: '700' } }, config.icon);
        this.el.appendChild(icon);

        const text = this.createElement('span', {}, this.#message);
        this.el.appendChild(text);

        if (this.#onAction) {
            const btn = this.createElement('button', {
                style: {
                    marginLeft: '12px', padding: '4px 12px',
                    background: 'rgba(255,255,255,0.2)',
                    border: '1px solid rgba(255,255,255,0.3)',
                    borderRadius: 'var(--radius-sm)',
                    color: 'inherit', fontSize: '12px',
                    cursor: 'pointer', fontWeight: '600'
                },
                onClick: (e) => {
                    e.stopPropagation();
                    this.#onAction();
                    this.dismiss();
                }
            }, this.options.action?.label || '重试');
            this.el.appendChild(btn);
        }

        this.el.addEventListener('click', () => this.dismiss());
        this.container.appendChild(this.el);
        activeToasts++;

        // 入场动画 (使用 AnimationController)
        if (this.ac) {
            this.ac.enter(this.el, { preset: 'toast-enter' });
        } else if (typeof gsap !== 'undefined') {
            gsap.fromTo(this.el,
                { opacity: 0, y: -20 },
                { opacity: 1, y: 0, duration: 0.3, ease: 'back.out(1.5)' }
            );
        }

        this.#timer = setTimeout(() => this.dismiss(), this.#duration);
    }

    async dismiss() {
        if (!this.el) return;
        clearTimeout(this.#timer);

        if (this.ac) {
            await this.ac.leave(this.el, { preset: 'toast-exit' });
        } else if (typeof gsap !== 'undefined') {
            await gsap.to(this.el, {
                opacity: 0, y: -20, duration: 0.2, ease: 'power2.in',
                onComplete: () => { this.el.remove(); }
            }).then();
        } else {
            this.el.remove();
        }

        activeToasts = Math.max(0, activeToasts - 1);
        this.el = null;
    }

    destroy() {
        this.dismiss();
        super.destroy();
    }
}

/**
 * 快捷方法 — 显示 Toast
 */
export function showToast(message, type = 'info', options = {}) {
    const container = document.getElementById('toastWrap');
    if (!container) return null;
    return new Toast(container, { ...options, message, type });
}

export default Toast;
