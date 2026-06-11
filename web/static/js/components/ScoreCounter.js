/**
 * ScoreCounter — GSAP 数字滚动计数器
 *
 * 驱动 textContent 从 0 滚动到目标数字
 *
 * @version 1.0
 */

import { BaseComponent } from './BaseComponent.js';

export class ScoreCounter extends BaseComponent {
    /** @type {number} */
    #target = 0;

    /** @type {number} */
    #duration = 1.2;

    /** @type {number} */
    #decimals = 1;

    /**
     * @param {Element} container
     * @param {Object} options
     * @param {number} [options.duration=1.2]
     * @param {number} [options.decimals=1]
     * @param {Object} [options.style] - 额外的 CSS
     */
    constructor(container, options = {}) {
        super(container, options);
        this.#duration = options.duration || 1.2;
        this.#decimals = options.decimals ?? 1;
    }

    render() {
        const defaultStyle = {
            fontSize: '48px',
            fontWeight: '700',
            color: 'var(--text-primary)',
            lineHeight: '1',
            fontVariantNumeric: 'tabular-nums'
        };

        this.el = this.createElement('span', {
            style: { ...defaultStyle, ...(this.options.style || {}) }
        }, '0');

        this.container.appendChild(this.el);
    }

    /**
     * 启动计数动画
     * @param {number} target
     * @returns {gsap.core.Tween|null}
     */
    animate(target) {
        this.#target = target;

        if (typeof gsap === 'undefined') {
            this.el.textContent = target.toFixed(this.#decimals);
            this.#updateColor(target);
            return null;
        }

        const obj = { value: 0 };
        return gsap.to(obj, {
            value: target,
            duration: this.#duration,
            ease: 'power3.out',
            onUpdate: () => {
                this.el.textContent = obj.value.toFixed(this.#decimals);
                this.#updateColor(obj.value);
            }
        });
    }

    #updateColor(value) {
        if (value >= 90) this.el.style.color = 'var(--success)';
        else if (value >= 80) this.el.style.color = 'var(--accent-blue)';
        else if (value >= 70) this.el.style.color = 'var(--warning)';
        else if (value >= 60) this.el.style.color = '#f97316';
        else this.el.style.color = 'var(--danger)';
    }
}

export default ScoreCounter;
