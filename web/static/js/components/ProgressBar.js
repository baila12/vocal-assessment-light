/**
 * ProgressBar — 进度条组件
 *
 * 两种形态:
 *   1. 页面顶部细条 (top bar) — 4px 高，全宽，position: fixed
 *   2. 卡片内进度 (card) — 圆角，带百分比文字和阶段文字
 *
 * 颜色状态: 进行中 → 完成 (绿) → 错误 (红)
 *
 * @version 1.0
 */

import { BaseComponent } from './BaseComponent.js';

export class ProgressBar extends BaseComponent {
    /** @type {string} */
    #variant; // 'top' | 'card'

    /** @type {number} */
    #percent = 0;

    /** @type {string} */
    #stage = '';

    /** @type {string} */
    #status = 'active'; // 'active' | 'complete' | 'error'

    #fillEl;
    #percentEl;
    #stageEl;

    /**
     * @param {Element} container
     * @param {Object} options
     * @param {string} [options.variant='card']
     */
    constructor(container, options = {}) {
        super(container, options);
        this.#variant = options.variant || 'card';
    }

    render() {
        if (this.#variant === 'top') {
            this.#renderTop();
        } else {
            this.#renderCard();
        }
    }

    #renderTop() {
        this.el = this.createElement('div', {
            style: {
                position: 'fixed',
                top: '0',
                left: '0',
                right: '0',
                height: '4px',
                zIndex: 'var(--z-sticky)',
                background: 'transparent'
            }
        });

        this.#fillEl = this.createElement('div', {
            style: {
                height: '100%',
                width: '0%',
                background: 'var(--primary)',
                transition: 'none', // GSAP 驱动，不用 CSS transition
                borderRadius: '0 2px 2px 0'
            }
        });
        this.el.appendChild(this.#fillEl);

        // 取消按钮
        const cancelBtn = this.createElement('button', {
            style: {
                position: 'absolute',
                right: '8px',
                top: '6px',
                width: '18px',
                height: '18px',
                border: 'none',
                background: 'rgba(0,0,0,0.3)',
                color: '#fff',
                borderRadius: '50%',
                fontSize: '12px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                lineHeight: '1'
            },
            onClick: () => {
                this.emit('cancel');
            }
        }, '×');
        this.el.appendChild(cancelBtn);

        document.body.appendChild(this.el);
    }

    #renderCard() {
        this.el = this.createElement('div', {
            style: {
                padding: '12px 0'
            }
        });

        // 头部：阶段文字 + 百分比
        const header = this.createElement('div', {
            style: {
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '8px'
            }
        });

        this.#stageEl = this.createElement('span', {
            style: { fontSize: '13px', color: 'var(--text-secondary)' }
        }, '准备中...');
        header.appendChild(this.#stageEl);

        this.#percentEl = this.createElement('span', {
            style: { fontSize: '13px', fontWeight: '600', color: 'var(--primary)' }
        }, '0%');
        header.appendChild(this.#percentEl);

        this.el.appendChild(header);

        // 进度条轨道
        const track = this.createElement('div', {
            style: {
                height: '6px',
                background: 'var(--bg-elevated)',
                borderRadius: 'var(--radius-full)',
                overflow: 'hidden'
            }
        });

        this.#fillEl = this.createElement('div', {
            style: {
                height: '100%',
                width: '0%',
                background: 'var(--primary)',
                borderRadius: 'var(--radius-full)',
                transformOrigin: 'left center'
            }
        });
        track.appendChild(this.#fillEl);
        this.el.appendChild(track);

        this.container.appendChild(this.el);
    }

    /**
     * 更新进度
     * @param {Object} progress
     * @param {number} progress.percent - 0-100
     * @param {string} [progress.stage]
     * @param {string} [progress.message]
     */
    update(progress) {
        this.#percent = progress.percent || 0;
        this.#stage = progress.stage || '';
        this.#status = progress.status || 'active';

        // GSAP 平滑进度条动画
        if (this.#fillEl) {
            if (typeof gsap !== 'undefined') {
                gsap.to(this.#fillEl, {
                    scaleX: this.#percent / 100,
                    duration: 0.3,
                    ease: 'power2.out',
                    overwrite: true
                });
            } else {
                this.#fillEl.style.transform = `scaleX(${this.#percent / 100})`;
            }
        }

        // 更新百分比文字
        if (this.#percentEl) {
            this.#percentEl.textContent = `${Math.round(this.#percent)}%`;
        }

        // 更新阶段文字
        if (this.#stageEl) {
            const messages = {
                voice_check: '正在检测人声...',
                feature_pitch: '正在分析音准...',
                feature_rhythm: '正在分析节奏...',
                feature_breath: '正在分析气息...',
                feature_technique: '正在分析发声技术...',
                scoring: '正在计算评分...',
                matching: '正在匹配标准歌曲...',
                complete: '分析完成',
                error: '分析失败'
            };
            this.#stageEl.textContent = progress.message || messages[this.#stage] || this.#stage;
        }

        // 颜色状态
        if (this.#fillEl && this.#status === 'complete') {
            this.#fillEl.style.background = 'var(--success)';
        } else if (this.#fillEl && this.#status === 'error') {
            this.#fillEl.style.background = 'var(--danger)';
        }
    }

    /**
     * 标记完成
     */
    complete() {
        this.update({ percent: 100, stage: 'complete', status: 'complete' });
        // 顶部进度条延迟隐藏
        if (this.#variant === 'top') {
            setTimeout(() => this.destroy(), 1500);
        }
    }

    /**
     * 标记错误
     * @param {string} message
     */
    error(message) {
        this.update({ percent: this.#percent, stage: 'error', status: 'error', message });
    }

    /**
     * 事件发射 (供子组件向上通信)
     */
    emit(event, data) {
        if (event === 'cancel' && this.options.onCancel) {
            this.options.onCancel(data);
        }
    }

    destroy() {
        if (this.#variant === 'top' && typeof gsap !== 'undefined') {
            gsap.to(this.#fillEl, {
                opacity: 0,
                duration: 0.3,
                onComplete: () => super.destroy()
            });
        } else {
            super.destroy();
        }
    }
}

export default ProgressBar;
