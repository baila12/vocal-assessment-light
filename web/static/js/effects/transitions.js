/**
 * effects/transitions.js — 页面切换动画
 *
 * 使用 GSAP Timeline 实现平滑的页面过渡
 */

/**
 * 页面切换动画
 * @param {Element} oldPage - 旧页面容器
 * @param {Element} newPage - 新页面容器
 * @param {Object} [options]
 * @param {string} [options.direction='left'] - 'left' | 'right' (旧页退出方向)
 * @param {number} [options.duration=0.3]
 * @returns {Promise<void>}
 */
export function pageTransition(oldPage, newPage, options = {}) {
    const { direction = 'left', duration = 0.3 } = options;

    return new Promise((resolve) => {
        if (typeof gsap === 'undefined') {
            // GSAP 不可用，直接切换
            if (oldPage) oldPage.style.display = 'none';
            if (newPage) newPage.style.display = 'block';
            resolve();
            return;
        }

        const xOffset = direction === 'left' ? -20 : 20;

        const tl = gsap.timeline({
            onComplete: () => {
                if (oldPage) oldPage.style.display = 'none';
                resolve();
            }
        });

        // 旧页面退出
        if (oldPage && oldPage.style.display !== 'none') {
            tl.to(oldPage, {
                opacity: 0,
                x: -xOffset,
                duration: duration * 0.6,
                ease: 'power2.in'
            });
        }

        // 新页面进入
        if (newPage) {
            tl.set(newPage, { display: 'block', opacity: 0, x: xOffset }, oldPage ? '>' : undefined);
            tl.to(newPage, {
                opacity: 1,
                x: 0,
                duration: duration,
                ease: 'power2.out'
            }, oldPage ? '-=0.1' : undefined);
        }
    });
}

/**
 * 淡入淡出切换 (无方向)
 * @param {Element} oldPage
 * @param {Element} newPage
 * @param {number} [duration=0.25]
 */
export function fadeTransition(oldPage, newPage, duration = 0.25) {
    return new Promise((resolve) => {
        if (typeof gsap === 'undefined') {
            if (oldPage) oldPage.style.display = 'none';
            if (newPage) newPage.style.display = 'block';
            resolve();
            return;
        }

        const tl = gsap.timeline({ onComplete: resolve });

        if (oldPage) {
            tl.to(oldPage, { opacity: 0, duration: duration * 0.5, ease: 'power2.in' });
        }

        if (newPage) {
            tl.set(newPage, { display: 'block', opacity: 0 }, oldPage ? '>' : undefined);
            tl.to(newPage, { opacity: 1, duration: duration, ease: 'power2.out' },
                oldPage ? '-=0.05' : undefined);
        } else {
            resolve();
        }
    });
}
