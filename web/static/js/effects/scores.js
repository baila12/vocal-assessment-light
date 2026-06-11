/**
 * effects/scores.js — 评分展示动画
 *
 * GSAP Timeline 驱动的评分动画序列:
 * 1. 总分数字滚动 (ScoreCounter)
 * 2. 五维进度条依次展开 (stagger)
 * 3. 雷达图渐进绘制
 * 4. 建议列表淡入
 */

/**
 * GSAP 数字滚动计数器
 * @param {Element} element - 显示数字的 DOM 元素
 * @param {number} target - 目标数字
 * @param {Object} [options]
 * @param {number} [options.duration=1.2]
 * @param {number} [options.decimals=1]
 * @param {Function} [options.onUpdate] - 每帧回调 (currentValue)
 * @returns {gsap.core.Tween}
 */
export function animateCounter(element, target, options = {}) {
    const { duration = 1.2, decimals = 1, onUpdate } = options;

    if (typeof gsap === 'undefined') {
        element.textContent = target.toFixed(decimals);
        return null;
    }

    return gsap.fromTo(element,
        { textContent: 0 },
        {
            textContent: target,
            duration,
            snap: { textContent: Math.max(0.1, Math.pow(10, -decimals)) },
            ease: 'power3.out',
            onUpdate() {
                if (onUpdate) onUpdate(parseFloat(element.textContent));
            }
        }
    );
}

/**
 * 五维进度条 stagger 动画
 * @param {Object<string, number>} scores - { pitch: 75, rhythm: 82, ... }
 * @param {Object<string, Element>} barElements - { pitch: el, rhythm: el, ... }
 * @param {Object<string, Element>} valueElements - { pitch: el, rhythm: el, ... }
 * @returns {gsap.core.Timeline}
 */
export function animateDimensionBars(scores, barElements, valueElements) {
    if (typeof gsap === 'undefined') {
        for (const [dim, score] of Object.entries(scores)) {
            if (barElements[dim]) barElements[dim].style.width = `${score}%`;
            if (valueElements[dim]) valueElements[dim].textContent = Math.round(score);
        }
        return null;
    }

    const dimensions = ['pitch', 'rhythm', 'breath', 'technique', 'artistry'];
    const tl = gsap.timeline({ defaults: { ease: 'power2.out' } });

    dimensions.forEach((dim, i) => {
        const score = scores[dim] || 0;
        const bar = barElements[dim];
        const val = valueElements[dim];

        if (bar) {
            tl.fromTo(bar,
                { scaleX: 0, transformOrigin: 'left center' },
                { scaleX: 1, duration: 0.8 },
                i === 0 ? undefined : '-=0.65'
            );
        }

        if (val) {
            tl.fromTo(val,
                { textContent: 0 },
                {
                    textContent: Math.round(score),
                    duration: 0.8,
                    snap: { textContent: 1 }
                },
                bar ? '-=0.8' : (i === 0 ? undefined : '-=0.65')
            );
        }
    });

    return tl;
}

/**
 * 建议列表 stagger 入场
 * @param {Element} container - 建议列表容器 (ul/ol)
 * @param {number} [stagger=0.1]
 * @param {number} [duration=0.4]
 * @returns {gsap.core.Timeline}
 */
export function animateAdviceList(container, stagger = 0.1, duration = 0.4) {
    const items = container.querySelectorAll('li');
    if (items.length === 0) return null;

    if (typeof gsap === 'undefined') {
        items.forEach(item => { item.style.opacity = '1'; });
        return null;
    }

    return gsap.fromTo(items,
        { opacity: 0, y: 10 },
        { opacity: 1, y: 0, stagger, duration, ease: 'power2.out' }
    );
}

/**
 * 完整报告入场序列
 * 把上述动画串联成一条 GSAP Timeline
 *
 * @param {Object} result - 分析结果
 * @param {Object} elements - DOM 元素引用
 * @param {Element} elements.totalScore - 总分元素
 * @param {Element} elements.scoreLevel - 评级元素
 * @param {Object<string, Element>} elements.dimBars - 维度进度条
 * @param {Object<string, Element>} elements.dimValues - 维度分值
 * @param {Element} elements.adviceList - 建议列表
 * @param {Function} [elements.drawRadar] - 雷达图绘制函数
 * @returns {gsap.core.Timeline}
 */
export function animateReportEntrance(result, elements) {
    if (typeof gsap === 'undefined') {
        // 回退：直接填充
        if (elements.totalScore) {
            elements.totalScore.textContent = result.total_score?.toFixed(1) || '0';
        }
        if (elements.scoreLevel) {
            elements.scoreLevel.textContent = result.level || '';
        }
        if (elements.dimBars && elements.dimValues) {
            const scores = result.scores || {};
            for (const dim of ['pitch', 'rhythm', 'breath', 'technique', 'artistry']) {
                if (elements.dimBars[dim]) {
                    elements.dimBars[dim].style.width = `${scores[dim] || 0}%`;
                }
                if (elements.dimValues[dim]) {
                    elements.dimValues[dim].textContent = Math.round(scores[dim] || 0);
                }
            }
        }
        if (elements.drawRadar) elements.drawRadar();
        return null;
    }

    const tl = gsap.timeline({ defaults: { ease: 'power2.out' } });

    // 1. 总分数字滚动
    if (elements.totalScore) {
        tl.fromTo(elements.totalScore,
            { textContent: 0 },
            {
                textContent: result.total_score || 0,
                duration: 1.2,
                snap: { textContent: 0.1 },
                ease: 'power3.out'
            }
        );
    }

    // 2. 评级标签 (与总分并行)
    if (elements.scoreLevel) {
        tl.fromTo(elements.scoreLevel,
            { opacity: 0, y: 10 },
            { opacity: 1, y: 0, duration: 0.3 },
            '-=0.5'
        );
    }

    // 3. 五维进度条
    if (elements.dimBars && elements.dimValues) {
        const scores = result.scores || {};
        const dims = ['pitch', 'rhythm', 'breath', 'technique', 'artistry'];

        dims.forEach((dim, i) => {
            const bar = elements.dimBars[dim];
            const val = elements.dimValues[dim];
            const score = scores[dim] || 0;

            if (bar) {
                tl.fromTo(bar,
                    { scaleX: 0, transformOrigin: 'left center' },
                    { scaleX: 1, duration: 0.8 },
                    i === 0 ? '+=0.2' : '-=0.65'
                );
            }
            if (val) {
                tl.fromTo(val,
                    { textContent: 0 },
                    { textContent: Math.round(score), duration: 0.8, snap: { textContent: 1 } },
                    bar ? '-=0.8' : '-=0.65'
                );
            }
        });
    }

    // 4. 雷达图
    if (elements.drawRadar) {
        tl.call(() => elements.drawRadar(), [], '+=0.2');
    }

    // 5. 建议列表
    if (elements.adviceList) {
        const items = elements.adviceList.querySelectorAll('li');
        if (items.length > 0) {
            tl.fromTo(items,
                { opacity: 0, y: 10 },
                { opacity: 1, y: 0, stagger: 0.1, duration: 0.4 },
                '+=0.2'
            );
        }
    }

    return tl;
}
