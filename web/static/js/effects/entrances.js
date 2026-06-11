/**
 * effects/entrances.js — 通用入场动画
 *
 * 可复用的入场动画组合
 */

/**
 * 卡片 stagger 入场 (从下方滑入)
 * @param {Element|NodeList} elements - 目标元素
 * @param {Object} [options]
 * @param {number} [options.stagger=0.1]
 * @param {number} [options.duration=0.5]
 * @param {number} [options.y=24]
 * @param {number} [options.delay=0]
 * @returns {gsap.core.Timeline}
 */
export function staggerSlideUp(elements, options = {}) {
    const { stagger = 0.1, duration = 0.5, y = 24, delay = 0 } = options;

    if (typeof gsap === 'undefined') {
        const items = elements instanceof NodeList ? elements : [elements];
        items.forEach(el => { el.style.opacity = '1'; el.style.transform = 'none'; });
        return null;
    }

    return gsap.fromTo(elements,
        { opacity: 0, y },
        { opacity: 1, y: 0, stagger, duration, delay, ease: 'power2.out' }
    );
}

/**
 * 元素从左侧滑入
 * @param {Element} element
 * @param {Object} [options]
 */
export function slideInLeft(element, options = {}) {
    const { duration = 0.4, delay = 0, x = -30 } = options;

    if (typeof gsap === 'undefined') {
        element.style.opacity = '1';
        return null;
    }

    return gsap.fromTo(element,
        { opacity: 0, x },
        { opacity: 1, x: 0, duration, delay, ease: 'power2.out' }
    );
}

/**
 * 元素从右侧滑入
 * @param {Element} element
 * @param {Object} [options]
 */
export function slideInRight(element, options = {}) {
    const { duration = 0.4, delay = 0, x = 30 } = options;

    if (typeof gsap === 'undefined') {
        element.style.opacity = '1';
        return null;
    }

    return gsap.fromTo(element,
        { opacity: 0, x },
        { opacity: 1, x: 0, duration, delay, ease: 'power2.out' }
    );
}

/**
 * 缩放弹出 (评分、徽标等)
 * @param {Element} element
 * @param {Object} [options]
 */
export function scalePop(element, options = {}) {
    const { duration = 0.4, delay = 0, scale = 0.5 } = options;

    if (typeof gsap === 'undefined') {
        element.style.opacity = '1';
        element.style.transform = 'none';
        return null;
    }

    return gsap.fromTo(element,
        { opacity: 0, scale },
        { opacity: 1, scale: 1, duration, delay, ease: 'back.out(1.5)' }
    );
}

/**
 * 依次淡入 (列表项、标签等)
 * @param {Element|NodeList} elements
 * @param {Object} [options]
 */
export function staggerFadeIn(elements, options = {}) {
    const { stagger = 0.08, duration = 0.3, delay = 0 } = options;

    if (typeof gsap === 'undefined') {
        const items = elements instanceof NodeList ? elements : [elements];
        items.forEach(el => { el.style.opacity = '1'; });
        return null;
    }

    return gsap.fromTo(elements,
        { opacity: 0 },
        { opacity: 1, stagger, duration, delay, ease: 'power1.out' }
    );
}

/**
 * 页面标题入场 (淡入 + 上移)
 * @param {Element} element
 */
export function titleEntrance(element) {
    if (typeof gsap === 'undefined') {
        element.style.opacity = '1';
        return null;
    }

    return gsap.fromTo(element,
        { opacity: 0, y: -16 },
        { opacity: 1, y: 0, duration: 0.5, ease: 'power2.out' }
    );
}
