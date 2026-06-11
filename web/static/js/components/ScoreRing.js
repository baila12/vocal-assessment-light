/**
 * ScoreRing — GSAP 环形评分动画 (Canvas)
 *
 * 绘制带进度动画的评分圆环，中心显示数字
 *
 * @version 1.0
 */

import { BaseComponent } from './BaseComponent.js';

export class ScoreRing extends BaseComponent {
    /** @type {number} */
    #score = 0;

    /** @type {number} */
    #size = 140;

    /** @type {number} */
    #strokeWidth = 8;

    /** @type {string} */
    #color = '#6366f1';

    /** @type {HTMLCanvasElement} */
    #canvas;

    /** @type {number} */
    #animProgress = 0;

    #animObj = { progress: 0 };

    /**
     * @param {Element} container
     * @param {Object} options
     * @param {number} [options.size=140]
     * @param {number} [options.strokeWidth=8]
     * @param {string} [options.color] - 默认根据分值自动选择
     */
    constructor(container, options = {}) {
        super(container, options);
        this.#size = options.size || 140;
        this.#strokeWidth = options.strokeWidth || 8;
    }

    render() {
        this.el = this.createElement('div', {
            style: {
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '4px'
            }
        });

        const canvasWrap = this.createElement('div', {
            style: { position: 'relative', width: `${this.#size}px`, height: `${this.#size}px` }
        });

        const ringId = `scoreRing-${Date.now()}-${Math.random().toString(36).slice(2,7)}`;

        this.#canvas = this.createElement('canvas', {
            id: ringId,
            width: this.#size * 2,
            height: this.#size * 2,
            style: {
                width: `${this.#size}px`,
                height: `${this.#size}px`
            }
        });
        canvasWrap.appendChild(this.#canvas);

        // 中心文字
        const centerText = this.createElement('div', {
            id: `${ringId}-center`,
            style: {
                position: 'absolute',
                inset: '0',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center'
            }
        });
        const scoreText = this.createElement('div', {
            style: {
                fontSize: `${Math.round(this.#size * 0.22)}px`,
                fontWeight: '700',
                color: 'var(--text-primary)',
                lineHeight: '1'
            }
        }, '--');
        centerText.appendChild(scoreText);
        const labelText = this.createElement('div', {
            style: {
                fontSize: '11px',
                color: 'var(--text-muted)',
                marginTop: '2px'
            }
        }, '总分');
        centerText.appendChild(labelText);

        canvasWrap.appendChild(centerText);
        this.el.appendChild(canvasWrap);

        this.container.appendChild(this.el);

        // 初始绘制 (空环)
        this.#draw(0, this.#getColor(0));
    }

    /**
     * 启动评分动画
     * @param {number} score - 最终分数 (0-100)
     */
    animate(score) {
        this.#score = Math.min(100, Math.max(0, score));
        this.#color = this.#getColor(this.#score);

        if (typeof gsap === 'undefined') {
            this.#draw(this.#score / 100, this.#color);
            return null;
        }

        this.#animObj.progress = 0;
        return gsap.to(this.#animObj, {
            progress: this.#score / 100,
            duration: 1.5,
            ease: 'power3.out',
            onUpdate: () => {
                this.#draw(this.#animObj.progress, this.#color);
                // 更新中心文字
                const centerEl = this.el.querySelector(`[id$="-center"]`);
                if (centerEl) {
                    const scoreEl = centerEl.querySelector('div');
                    if (scoreEl) {
                        scoreEl.textContent = Math.round(this.#animObj.progress * 100);
                    }
                }
            }
        });
    }

    /**
     * 绘制圆环
     * @param {number} progress - 0-1
     * @param {string} color
     */
    #draw(progress, color) {
        const ctx = this.#canvas.getContext('2d');
        const dpr = 2; // Retina
        const w = this.#size;
        const cx = w / 2;
        const cy = w / 2;
        const radius = (w - this.#strokeWidth) / 2;
        const startAngle = -Math.PI / 2;
        const endAngle = startAngle + progress * Math.PI * 2;

        ctx.clearRect(0, 0, w * dpr, w * dpr);
        ctx.save();
        ctx.scale(dpr, dpr);

        // 背景圆环
        ctx.beginPath();
        ctx.arc(cx, cy, radius, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(99, 102, 241, 0.12)';
        ctx.lineWidth = this.#strokeWidth;
        ctx.lineCap = 'round';
        ctx.stroke();

        // 进度圆环
        if (progress > 0) {
            ctx.beginPath();
            ctx.arc(cx, cy, radius, startAngle, endAngle);
            ctx.strokeStyle = color;
            ctx.lineWidth = this.#strokeWidth;
            ctx.lineCap = 'round';
            ctx.stroke();
        }

        ctx.restore();
    }

    /**
     * 根据分数返回颜色
     */
    #getColor(score) {
        if (score >= 90) return '#22c55e';
        if (score >= 80) return '#3b82f6';
        if (score >= 70) return '#f59e0b';
        if (score >= 60) return '#f97316';
        return '#ef4444';
    }
}

export default ScoreRing;
