/**
 * effects/micro.js — 微交互动画
 *
 * 按钮点击、hover、波纹等小型交互动画
 */

/**
 * 按钮点击波纹效果
 * @param {MouseEvent} event
 */
export function rippleEffect(event) {
    if (typeof gsap === 'undefined') return;

    const button = event.currentTarget;
    const rect = button.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const x = event.clientX - rect.left - size / 2;
    const y = event.clientY - rect.top - size / 2;

    const ripple = document.createElement('span');
    ripple.style.cssText = `
        position: absolute;
        width: ${size}px;
        height: ${size}px;
        left: ${x}px;
        top: ${y}px;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.3);
        pointer-events: none;
    `;
    button.style.position = button.style.position || 'relative';
    button.style.overflow = 'hidden';
    button.appendChild(ripple);

    gsap.fromTo(ripple,
        { scale: 0, opacity: 1 },
        {
            scale: 2,
            opacity: 0,
            duration: 0.6,
            ease: 'power2.out',
            onComplete: () => ripple.remove()
        }
    );
}

/**
 * 按钮 hover 放大 (微小)
 * @param {Element} element
 * @returns {gsap.core.Tween}
 */
export function buttonHoverScale(element) {
    if (typeof gsap === 'undefined') return null;
    return gsap.to(element, { scale: 1.03, duration: 0.15, ease: 'power2.out' });
}

/**
 * 按钮 hover 恢复
 * @param {Element} element
 * @returns {gsap.core.Tween}
 */
export function buttonHoverReset(element) {
    if (typeof gsap === 'undefined') return null;
    return gsap.to(element, { scale: 1, duration: 0.15, ease: 'power2.out' });
}

/**
 * 评分更新时的脉冲动画
 * @param {Element} element
 */
export function scorePulse(element) {
    if (typeof gsap === 'undefined') return null;

    return gsap.timeline()
        .to(element, { scale: 1.1, duration: 0.1, ease: 'power2.out' })
        .to(element, { scale: 1, duration: 0.3, ease: 'elastic.out(1, 0.3)' });
}

/**
 * 击打反馈动画 (PERFECT/GREAT/GOOD)
 * @param {Element} element - 反馈文字元素
 * @param {string} type - 'perfect' | 'great' | 'good'
 * @param {Object} [options]
 * @returns {gsap.core.Timeline}
 */
export function hitFeedback(element, type, options = {}) {
    if (typeof gsap === 'undefined') return null;

    const configs = {
        perfect: { scale: 1.3, color: '#FFD700', ease: 'back.out(2)' },
        great:   { scale: 1.2, color: '#22c55e', ease: 'back.out(1.5)' },
        good:    { scale: 1.1, color: '#ffffff', ease: 'power2.out' }
    };

    const config = configs[type] || configs.good;

    return gsap.timeline()
        .fromTo(element,
            { scale: 0, opacity: 1, y: 0 },
            { scale: config.scale, duration: 0.3, ease: config.ease }
        )
        .to(element, {
            opacity: 0,
            y: -30,
            duration: 0.5,
            delay: 0.4,
            ease: 'power2.in',
            onComplete: () => {
                if (element.parentNode) element.remove();
            }
        });
}

/**
 * 连击数字弹跳动画
 * @param {Element} element
 * @param {number} combo - 当前连击数
 */
export function comboBounce(element, combo) {
    if (typeof gsap === 'undefined') return null;

    if (combo === 0) {
        return gsap.to(element, {
            scale: 0,
            opacity: 0,
            duration: 0.3,
            ease: 'power2.in'
        });
    }

    if (combo === 1) {
        return gsap.fromTo(element,
            { scale: 0, opacity: 0 },
            { scale: 1.5, opacity: 1, duration: 0.3, ease: 'back.out(2)' }
        );
    }

    return gsap.timeline()
        .to(element, { scale: 1.4, duration: 0.1, ease: 'power2.out' })
        .to(element, { scale: 1, duration: 0.3, ease: 'elastic.out(1, 0.3)' });
}

/**
 * Toast 入场
 * @param {Element} element
 */
export function toastEnter(element) {
    if (typeof gsap === 'undefined') return null;
    return gsap.fromTo(element,
        { opacity: 0, y: -20 },
        { opacity: 1, y: 0, duration: 0.3, ease: 'back.out(1.5)' }
    );
}

/**
 * Toast 出场
 * @param {Element} element
 */
export function toastExit(element) {
    return new Promise((resolve) => {
        if (typeof gsap === 'undefined') {
            element.remove();
            resolve();
            return;
        }
        gsap.to(element, {
            opacity: 0,
            y: -20,
            duration: 0.2,
            ease: 'power2.in',
            onComplete: () => {
                element.remove();
                resolve();
            }
        });
    });
}

/**
 * Modal 入场
 * @param {Element} overlay - 遮罩层
 * @param {Element} card - 内容卡片
 */
export function modalEnter(overlay, card) {
    if (typeof gsap === 'undefined') return null;

    const tl = gsap.timeline();

    tl.fromTo(overlay,
        { opacity: 0 },
        { opacity: 1, duration: 0.2, ease: 'power2.out' }
    );

    tl.fromTo(card,
        { opacity: 0, scale: 0.95, y: 20 },
        { opacity: 1, scale: 1, y: 0, duration: 0.3, ease: 'back.out(1.5)' },
        '-=0.1'
    );

    return tl;
}
