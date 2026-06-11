/**
 * Toast — 通知组件
 *
 * 位置: 页面顶部居中固定
 * 类型: success | error | warning | info
 * 动画: GSAP fromTo (y: -20 → 0)
 * 限制: 最多 3 个同时显示
 *
 * @version 1.0
 */

import { BaseComponent } from './BaseComponent.js';
import { toastEnter, toastExit } from '../effects/micro.js';

const TOAST_TYPES = {
    success: { icon: '✓', bg: 'var(--success)', color: '#fff' },
    error:   { icon: '✕', bg: 'var(--danger)', color: '#fff' },
    warning: { icon: '⚠', bg: 'var(--warning)', color: '#fff' },
    info:    { icon: 'ℹ', bg: 'var(--info)', color: '#fff' }
};

const MAX_TOASTS = 3;

let activeToasts = 0;

export class Toast extends BaseComponent {
    /** @type {string} */
    #type;

    /** @type {string} */
    #message;

    /** @type {number} */
    #duration;

    /** @type {Function|null} */
    #onAction;

    /** @type {number|null} */
    #timer;

    /**
     * @param {Element} container
     * @param {Object} options
     * @param {string} options.type - 'success' | 'error' | 'warning' | 'info'
     * @param {string} options.message
     * @param {number} [options.duration=3000] - 自动消失时间 (ms)
     * @param {Object} [options.action] - { label: '重试', handler: () => {} }
     */
    constructor(container, options = {}) {
        super(container, options);
        this.#type = options.type || 'info';
        this.#message = options.message || '';
        this.#duration = options.duration || 3500;
        this.#onAction = options.action?.handler || null;
    }

    render() {
        if (activeToasts >= MAX_TOASTS) {
            // 移除最早的 Toast
            const first = this.container.querySelector('.toast-item');
            if (first) {
                toastExit(first);
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

        // 图标
        const icon = this.createElement('span', {
            style: {
                fontSize: '16px',
                fontWeight: '700'
            }
        }, config.icon);
        this.el.appendChild(icon);

        // 文字
        const text = this.createElement('span', {}, this.#message);
        this.el.appendChild(text);

        // 操作按钮 (仅 error 类型默认带"重试")
        if (this.#onAction) {
            const btn = this.createElement('button', {
                style: {
                    marginLeft: '12px',
                    padding: '4px 12px',
                    background: 'rgba(255,255,255,0.2)',
                    border: '1px solid rgba(255,255,255,0.3)',
                    borderRadius: 'var(--radius-sm)',
                    color: 'inherit',
                    fontSize: '12px',
                    cursor: 'pointer',
                    fontWeight: '600'
                },
                onClick: (e) => {
                    e.stopPropagation();
                    this.#onAction();
                    this.dismiss();
                }
            }, this.options.action?.label || '重试');
            this.el.appendChild(btn);
        }

        // 点击关闭
        this.el.addEventListener('click', () => this.dismiss());

        this.container.appendChild(this.el);
        activeToasts++;

        // 入场动画
        if (toastEnter) toastEnter(this.el);

        // 自动消失
        this.#timer = setTimeout(() => this.dismiss(), this.#duration);
    }

    /**
     * 主动关闭
     */
    async dismiss() {
        if (!this.el) return;
        clearTimeout(this.#timer);

        await toastExit(this.el);
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
 * @param {string} message
 * @param {string} type
 * @param {Object} [options]
 */
export function showToast(message, type = 'info', options = {}) {
    const container = document.getElementById('toastWrap');
    if (!container) return null;

    return new Toast(container, { ...options, message, type });
}

export default Toast;
