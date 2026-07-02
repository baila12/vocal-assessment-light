/**
 * Modal — 模态框组件
 *
 * 类型: confirm (确认/取消) | alert (仅确认) | custom (自定义内容)
 * 动画: AnimationController 驱动
 *
 * @version 2.0
 */

import { BaseComponent } from './BaseComponent.js';

export class Modal extends BaseComponent {
    #type;
    #title;
    #content;
    #confirmText;
    #cancelText;
    #onConfirm;
    #onCancel;
    #overlay;
    #card;
    #boundKeyHandler;
    #resolved = false;

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
        this.#overlay = this.createElement('div', {
            className: 'modal-overlay',
            style: {
                position: 'fixed', inset: '0',
                background: 'rgba(0, 0, 0, 0.5)',
                zIndex: 'var(--z-modal)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                padding: '24px'
            },
            onClick: (e) => {
                if (e.target === this.#overlay) this.dismiss(false);
            }
        });

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

        if (this.#title) {
            this.#card.appendChild(
                this.createElement('h3', {
                    style: { fontSize: '18px', fontWeight: '600', marginBottom: '12px', color: 'var(--text-primary)' }
                }, this.#title)
            );
        }

        const contentEl = this.createElement('div', {
            style: { fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.6', marginBottom: '20px' }
        });
        if (typeof this.#content === 'string') {
            contentEl.textContent = this.#content;
        } else {
            contentEl.appendChild(this.#content);
        }
        this.#card.appendChild(contentEl);

        const btnGroup = this.createElement('div', { style: { display: 'flex', justifyContent: 'flex-end', gap: '10px' } });

        if (this.#type === 'confirm') {
            btnGroup.appendChild(
                this.createElement('button', {
                    className: 'btn btn-secondary',
                    style: {
                        padding: '8px 20px', borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--border)', background: 'var(--bg-elevated)',
                        color: 'var(--text-primary)', fontSize: '14px', cursor: 'pointer'
                    },
                    onClick: () => this.dismiss(false)
                }, this.#cancelText)
            );
        }

        btnGroup.appendChild(
            this.createElement('button', {
                className: 'btn btn-primary',
                style: {
                    padding: '8px 20px', borderRadius: 'var(--radius-md)',
                    border: 'none', background: 'var(--primary)', color: '#fff',
                    fontSize: '14px', cursor: 'pointer', fontWeight: '600'
                },
                onClick: () => this.dismiss(true)
            }, this.#confirmText)
        );

        this.#card.appendChild(btnGroup);
        this.#overlay.appendChild(this.#card);

        this.#boundKeyHandler = (e) => {
            if (e.key === 'Escape') this.dismiss(false);
        };
        document.addEventListener('keydown', this.#boundKeyHandler);
        this.#card.addEventListener('click', (e) => e.stopPropagation());

        this.el = this.#overlay;
        document.body.appendChild(this.#overlay);

        // 入场动画 (AnimationController)
        if (this.ac) {
            this.ac.enter(this.#overlay, { preset: 'modal-overlay' });
            this.ac.enter(this.#card, { preset: 'modal-card' });
        } else if (typeof gsap !== 'undefined') {
            const tl = gsap.timeline();
            tl.fromTo(this.#overlay, { opacity: 0 }, { opacity: 1, duration: 0.2, ease: 'power2.out' });
            tl.fromTo(this.#card,
                { opacity: 0, scale: 0.95, y: 20 },
                { opacity: 1, scale: 1, y: 0, duration: 0.3, ease: 'back.out(1.5)' },
                '-=0.1'
            );
        }
    }

    async dismiss(confirmed) {
        if (this.#resolved) return;
        this.#resolved = true;

        document.removeEventListener('keydown', this.#boundKeyHandler);

        if (confirmed) this.#onConfirm();
        else this.#onCancel();

        // 出场动画
        if (this.#overlay && typeof gsap !== 'undefined') {
            await gsap.to(this.#overlay, { opacity: 0, duration: 0.2, ease: 'power2.in' }).then();
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

export function confirm(title, message) {
    return new Promise((resolve) => {
        new Modal(document.body, {
            type: 'confirm', title, content: message,
            onConfirm: () => resolve(true),
            onCancel: () => resolve(false)
        }).render();
    });
}

export function alert(title, message) {
    new Modal(document.body, { type: 'alert', title, content: message }).render();
}

export default Modal;
