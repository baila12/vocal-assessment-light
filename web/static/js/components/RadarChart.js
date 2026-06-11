/**
 * RadarChart — Chart.js 雷达图封装 + GSAP 渐进绘制
 *
 * 支持:
 * - 单数据集 (评分展示)
 * - 多数据集 (对比模式-双雷达叠加)
 * - GSAP 入场动画
 *
 * @version 1.0
 */

import { BaseComponent } from './BaseComponent.js';

export class RadarChart extends BaseComponent {
    /** @type {HTMLCanvasElement} */
    #canvas;

    /** @type {Chart|null} */
    #chart = null;

    /** @type {Array} */
    #datasets = [];

    /** @type {string[]} */
    #labels = ['音准', '节奏', '气息', '发声技术', '艺术表现'];

    /**
     * @param {Element} container
     * @param {Object} options
     * @param {number} [options.width]
     * @param {number} [options.height]
     */
    constructor(container, options = {}) {
        super(container, options);
    }

    render() {
        const wrap = this.createElement('div', {
            style: {
                position: 'relative',
                width: '100%',
                maxWidth: '350px',
                margin: '0 auto'
            }
        });

        this.#canvas = this.createElement('canvas', {});
        wrap.appendChild(this.#canvas);
        this.el = wrap;
        this.container.appendChild(this.el);
    }

    /**
     * 设置数据并绘制
     * @param {Object<string, number>} scores - { pitch: 75, rhythm: 82, ... }
     * @param {Object} [referenceScores] - 对比模式: 参考数据集
     */
    setData(scores, referenceScores = null) {
        const dims = ['pitch', 'rhythm', 'breath', 'technique', 'artistry'];
        const data = dims.map(d => scores[d] || 0);

        this.#datasets = [{
            label: '我的评分',
            data,
            fill: true,
            backgroundColor: 'rgba(99, 102, 241, 0.2)',
            borderColor: 'rgb(99, 102, 241)',
            borderWidth: 2,
            pointBackgroundColor: 'rgb(99, 102, 241)',
            pointRadius: 4,
            pointHoverRadius: 6
        }];

        if (referenceScores) {
            const refData = dims.map(d => referenceScores[d] || 0);
            this.#datasets.push({
                label: '参考评分',
                data: refData,
                fill: false,
                backgroundColor: 'rgba(203, 213, 225, 0.1)',
                borderColor: 'rgb(148, 163, 184)',
                borderWidth: 2,
                borderDash: [4, 4],
                pointBackgroundColor: 'rgb(148, 163, 184)',
                pointRadius: 3
            });
        }

        this.#draw();
    }

    /**
     * GSAP 入场动画
     */
    animate() {
        if (typeof gsap === 'undefined') return;
        gsap.fromTo(this.el,
            { opacity: 0, scale: 0.85 },
            { opacity: 1, scale: 1, duration: 0.6, ease: 'power3.out' }
        );
    }

    #draw() {
        if (typeof Chart === 'undefined') {
            console.warn('[RadarChart] Chart.js 未加载');
            return;
        }

        if (this.#chart) {
            this.#chart.destroy();
        }

        const ctx = this.#canvas.getContext('2d');

        this.#chart = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: this.#labels,
                datasets: this.#datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            stepSize: 20,
                            display: true,
                            backdropColor: 'transparent',
                            color: 'var(--text-muted)',
                            font: { size: 9 }
                        },
                        grid: {
                            color: 'var(--border)'
                        },
                        pointLabels: {
                            color: 'var(--text-secondary)',
                            font: { size: 12, weight: '500' }
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: this.#datasets.length > 1,
                        position: 'bottom',
                        labels: {
                            color: 'var(--text-secondary)',
                            font: { size: 11 },
                            usePointStyle: true,
                            padding: 16
                        }
                    }
                }
            }
        });
    }

    destroy() {
        if (this.#chart) {
            this.#chart.destroy();
            this.#chart = null;
        }
        super.destroy();
    }
}

export default RadarChart;
