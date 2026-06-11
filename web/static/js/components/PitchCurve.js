/**
 * PitchCurve — Canvas 音高曲线组件
 *
 * 功能:
 * - 用户音高曲线 (蓝色实线)
 * - 标准音高曲线 (紫色虚线，可选)
 * - 播放进度指示器
 * - 点击跳转播放位置
 *
 * @version 1.0
 */

import { BaseComponent } from './BaseComponent.js';

export class PitchCurve extends BaseComponent {
    /** @type {HTMLCanvasElement} */
    #canvas;

    /** @type {number[]} */
    #userFrequencies = [];

    /** @type {number[]} */
    #referenceFrequencies = [];

    /** @type {number[]} */
    #times = [];

    /** @type {number} */
    #duration = 0;

    /** @type {number} */
    #playProgress = 0; // 0-1

    /** @type {Function|null} */
    #onSeek = null;

    /** @type {string} */
    #referenceLabel = '';

    /**
     * @param {Element} container
     * @param {Object} options
     * @param {Function} [options.onSeek] - (time) => void 点击跳转回调
     */
    constructor(container, options = {}) {
        super(container, options);
        this.#onSeek = options.onSeek || null;
    }

    render() {
        const wrap = this.createElement('div', {
            style: {
                position: 'relative',
                width: '100%',
                paddingBottom: '5%', // 防止裁切
                cursor: this.#onSeek ? 'pointer' : 'default'
            }
        });

        // 标签
        if (this.#referenceLabel) {
            const label = this.createElement('div', {
                style: {
                    fontSize: '12px',
                    color: 'var(--text-muted)',
                    marginBottom: '8px'
                }
            }, `参考: ${this.#referenceLabel}`);
            wrap.appendChild(label);
        }

        this.#canvas = this.createElement('canvas', {
            style: {
                width: '100%',
                height: '160px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-elevated)'
            }
        });

        // 点击跳转
        if (this.#onSeek) {
            this.#canvas.addEventListener('click', (e) => {
                const rect = this.#canvas.getBoundingClientRect();
                const ratio = (e.clientX - rect.left) / rect.width;
                const time = ratio * this.#duration;
                this.#onSeek(time);
            });
        }

        // mousemove 更新播放头位置指示
        this.#canvas.addEventListener('mousemove', (e) => {
            if (!this.#duration) return;
            const rect = this.#canvas.getBoundingClientRect();
            const ratio = (e.clientX - rect.left) / rect.width;
            this.#playProgress = Math.max(0, Math.min(1, ratio));
            this.#draw();
        });

        this.#canvas.addEventListener('mouseleave', () => {
            // 恢复实际播放进度 (如果有的话)
            this.#draw();
        });

        wrap.appendChild(this.#canvas);
        this.el = wrap;
        this.container.appendChild(this.el);
    }

    /**
     * 设置用户音高数据
     * @param {Object} data - { frequencies: number[], times: number[], duration: number }
     */
    setUserData(data) {
        this.#userFrequencies = data.frequencies || [];
        this.#times = data.times || [];
        this.#duration = data.duration || 0;
        this.#resizeCanvas();
        this.#draw();
    }

    /**
     * 设置参考音高数据 (标准歌曲)
     * @param {Object} data - { frequencies: number[], label: string }
     */
    setReference(data) {
        this.#referenceFrequencies = data.frequencies || [];
        this.#referenceLabel = data.label || '';
        this.#draw();
    }

    /**
     * 更新播放进度
     * @param {number} progress - 0-1
     */
    setProgress(progress) {
        this.#playProgress = Math.max(0, Math.min(1, progress));
        this.#draw();
    }

    #resizeCanvas() {
        const rect = this.#canvas.getBoundingClientRect();
        if (rect.width === 0) return;
        this.#canvas.width = rect.width * 2;
        this.#canvas.height = 160 * 2;
    }

    #draw() {
        const ctx = this.#canvas.getContext('2d');
        const dpr = 2;
        const w = this.#canvas.width / dpr;
        const h = this.#canvas.height / dpr;

        ctx.clearRect(0, 0, w * dpr, h * dpr);
        ctx.save();
        ctx.scale(dpr, dpr);

        // 参考音高曲线 (虚线)
        if (this.#referenceFrequencies.length > 0) {
            this.#drawCurve(ctx, this.#referenceFrequencies, w, h,
                'rgba(99, 102, 241, 0.5)', 2, [6, 3]);
        }

        // 用户音高曲线 (实线)
        if (this.#userFrequencies.length > 0) {
            this.#drawCurve(ctx, this.#userFrequencies, w, h,
                'var(--accent-blue)', 2.5, []);
        }

        // 播放进度竖线
        if (this.#playProgress > 0) {
            const x = this.#playProgress * w;
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, h);
            ctx.strokeStyle = 'rgba(239, 68, 68, 0.6)';
            ctx.lineWidth = 2;
            ctx.setLineDash([]);
            ctx.stroke();

            // 进度点
            ctx.beginPath();
            ctx.arc(x, h / 2, 4, 0, Math.PI * 2);
            ctx.fillStyle = 'var(--danger)';
            ctx.fill();
        }

        ctx.restore();
    }

    #drawCurve(ctx, frequencies, w, h, color, lineWidth, dash) {
        const validFreqs = frequencies.filter(f => f > 50 && f < 1000);
        if (validFreqs.length === 0) return;

        const minFreq = Math.min(...validFreqs) * 0.9;
        const maxFreq = Math.max(...validFreqs) * 1.1;
        const range = maxFreq - minFreq || 1;

        ctx.strokeStyle = color;
        ctx.lineWidth = lineWidth;
        ctx.setLineDash(dash);
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        ctx.beginPath();

        let started = false;
        for (let i = 0; i < frequencies.length; i++) {
            const freq = frequencies[i];
            if (freq < 50 || freq > 1000) continue;

            const x = (i / frequencies.length) * w;
            const y = h - ((freq - minFreq) / range) * (h - 20) - 10;

            if (!started) { ctx.moveTo(x, y); started = true; }
            else ctx.lineTo(x, y);
        }
        ctx.stroke();
        ctx.setLineDash([]);
    }

    destroy() {
        if (this.#canvas && typeof gsap !== 'undefined') {
            gsap.killTweensOf(this.#canvas);
        }
        super.destroy();
    }
}

export default PitchCurve;
