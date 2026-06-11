/**
 * Modal — 模态框组件
 *
 * 类型: confirm (确认/取消) | alert (仅确认) | custom (自定义内容)
 * 关闭: ESC 键、点击遮罩层、点击取消
 *
 * @version 1.0
 */

import { BaseComponent } from './BaseComponent.js';
import { modalEnter } from '../effects/micro.js';

export class Modal extends BaseComponent {
    /** @type {string} */
    #type;

    /** @type {string} */
    #title;

    /** @type {string|Element} */
    #content;

    /** @type {string} */
    #confirmText;

    /** @type {string} */
    #cancelText;

    /** @type {Function} */
    #onConfirm;

    /** @type {Function} */
    #onCancel;

    #overlay;
    #card;
    #boundKeyHandler;

    /**
     * @param {Element} container
     * @param {Object} options
     * @param {string} options.type - 'confirm' | 'alert' | 'custom'
     * @param {string} options.title
     * @param {string|Element} options.content
     * @param {string} [options.confirmText='确认']
     * @param {string} [options.cancelText='取消']
     * @param {Function} [options.onConfirm]
     * @param {Function} [options.onCancel]
     */
    constructor(container, options = {}) {
        super(container, options);
        this.#type = options.type || 'alert';
        this.#title = options.title || '';
        this.#content = options.content || '';
        this.#confirmText = options.confirmText || '确认';
        this.#cancelText = options.cancelText || '取消';
        this.#onConfirm = options.onConfirm || (() => {});
        this.#onCancel = options.onCancel || (() => {});
    }

    render() {
        // 遮罩层
        this.#overlay = this.createElement('div', {
            className: 'modal-overlay',
            style: {
                position: 'fixed',
                inset: '0',
                background: 'rgba(0, 0, 0, 0.5)',
                zIndex: 'var(--z-modal)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '24px'
            },
            onClick: (e) => {
                if (e.target === this.#overlay) this.dismiss(false);
            }
        });

        // 内容卡片
        const cardStyle = {
            background: 'var(--bg-card)',
            borderRadius: 'var(--radius-lg)',
            padding: '24px',
            maxWidth: '420px',
            width: '100%',
            boxShadow: 'var(--shadow-xl)',
            color: 'var(--text-primary)'
        };

        this.#card = this.createElement('div', { style: cardStyle });

        // 标题
        if (this.#title) {
            this.#card.appendChild(
                this.createElement('h3', {
                    style: {
                        fontSize: '18px',
                        fontWeight: '600',
                        marginBottom: '12px',
                        color: 'var(--text-primary)'
                    }
                }, this.#title)
            );
        }

        // 内容
        const contentEl = this.createElement('div', {
            style: {
                fontSize: '14px',
                color: 'var(--text-secondary)',
                lineHeight: '1.6',
                marginBottom: '20px'
            }
        });
        if (typeof this.#content === 'string') {
            contentEl.textContent = this.#content;
        } else {
            contentEl.appendChild(this.#content);
        }
        this.#card.appendChild(contentEl);

        // 按钮组
        const btnGroup = this.createElement('div', {
            style: { display: 'flex', justifyContent: 'flex-end', gap: '10px' }
        });

        if (this.#type === 'confirm') {
            btnGroup.appendChild(
                this.createElement('button', {
                    className: 'btn btn-secondary',
                    style: {
                        padding: '8px 20px',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--border)',
                        background: 'var(--bg-elevated)',
                        color: 'var(--text-primary)',
                        fontSize: '14px',
                        cursor: 'pointer'
                    },
                    onClick: () => this.dismiss(false)
                }, this.#cancelText)
            );
        }

        btnGroup.appendChild(
            this.createElement('button', {
                className: 'btn btn-primary',
                style: {
                    padding: '8px 20px',
                    borderRadius: 'var(--radius-md)',
                    border: 'none',
                    background: 'var(--primary)',
                    color: '#fff',
                    fontSize: '14px',
                    cursor: 'pointer',
                    fontWeight: '600'
                },
                onClick: () => this.dismiss(true)
            }, this.#confirmText)
        );

        this.#card.appendChild(btnGroup);
        this.#overlay.appendChild(this.#card);

        // ESC 关闭
        this.#boundKeyHandler = (e) => {
            if (e.key === 'Escape') this.dismiss(false);
        };
        document.addEventListener('keydown', this.#boundKeyHandler);

        // 阻止冒泡
        this.#card.addEventListener('click', (e) => e.stopPropagation());

        // 挂载
        this.el = this.#overlay;
        document.body.appendChild(this.#overlay);

        // 入场动画
        if (modalEnter) modalEnter(this.#overlay, this.#card);
    }

    /**
     * 关闭模态框
     * @param {boolean} confirmed - 是否确认
     */
    async dismiss(confirmed) {
        document.removeEventListener('keydown', this.#boundKeyHandler);

        if (confirmed) {
            this.#onConfirm();
        } else {
            this.#onCancel();
        }

        if (this.#overlay && typeof gsap !== 'undefined') {
            await gsap.to(this.#overlay, {
                opacity: 0,
                duration: 0.2,
                ease: 'power2.in'
            }).then();
        }

        this.destroy();
    }

    destroy() {
        document.removeEventListener('keydown', this.#boundKeyHandler);
        if (this.#overlay && this.#overlay.parentNode) {
            this.#overlay.remove();
        }
        super.destroy();
    }
}

/**
 * 快捷方法 — 确认对话框
 * @param {string} title
 * @param {string} message
 * @returns {Promise<boolean>}
 */
export function confirm(title, message) {
    return new Promise((resolve) => {
        new Modal(document.body, {
            type: 'confirm',
            title,
            content: message,
            onConfirm: () => resolve(true),
            onCancel: () => resolve(false)
        }).render();
    });
}

/**
 * 快捷方法 — 提示框
 * @param {string} title
 * @param {string} message
 */
export function alert(title, message) {
    new Modal(document.body, {
        type: 'alert',
        title,
        content: message
    }).render();
}

export default Modal;
