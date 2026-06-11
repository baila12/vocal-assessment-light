/**
 * AnimationController 单元测试
 *
 * 测试范围:
 * 1. Controller 初始化与配置
 * 2. enter() / leave() 预设匹配
 * 3. setEnabled() 开关
 * 4. prefers-reduced-motion 检测
 * 5. stagger() 参数正确
 * 6. countUp() / fillBar() 正确调用 gsap
 * 7. 动画队列防止冲突
 *
 * 运行方式:
 *   此文件需在浏览器环境中运行（通过 Playwright evaluate 执行）
 *   或作为 ES Module 导入后运行。
 *
 * @version 1.0
 */

const { describe, it, expect, beforeEach, afterEach } = window.__test || {};

// ============================================================================
// Mock gsap
// ============================================================================
function createMockGSAP() {
    const tweens = [];
    const timelines = [];

    const mockTween = (overrides = {}) => ({
        kill: () => {},
        pause: () => {},
        play: () => {},
        then: () => Promise.resolve(),
        ...overrides
    });

    const mockGSAP = {
        to: (target, vars) => {
            tweens.push({ type: 'to', target, vars });
            return mockTween(vars);
        },
        from: (target, vars) => {
            tweens.push({ type: 'from', target, vars });
            return mockTween(vars);
        },
        fromTo: (target, fromVars, toVars) => {
            tweens.push({ type: 'fromTo', target, fromVars, toVars });
            return mockTween(toVars);
        },
        set: (target, vars) => {
            tweens.push({ type: 'set', target, vars });
            return mockTween(vars);
        },
        timeline: (vars) => {
            const tl = {
                to: () => tl,
                from: () => tl,
                fromTo: () => tl,
                set: () => tl,
                add: () => tl,
                kill: () => {},
                clear: () => {},
                ...mockTween(vars)
            };
            timelines.push(tl);
            return tl;
        },
        killTweensOf: () => {},
        config: () => {},
        defaults: () => {},
        registerPlugin: () => {},
        utils: {
            clamp: (min, max, val) => Math.min(max, Math.max(min, val)),
            mapRange: (iMin, iMax, oMin, oMax, val) => oMin + (val - iMin) * (oMax - oMin) / (iMax - iMin),
            normalize: (min, max, val) => (val - min) / (max - min)
        },
        // 用于测试验证
        _tweens: tweens,
        _timelines: timelines,
        _reset: () => {
            tweens.length = 0;
            timelines.length = 0;
        }
    };

    return mockGSAP;
}

// ============================================================================
// Test Suite
// ============================================================================

window.__animationTests = {

    /** 1. Controller 初始化 */
    testInitialization() {
        const gsap = createMockGSAP();
        const { AnimationController } = window.__animationModule || {};
        if (!AnimationController) return { pass: false, reason: 'AnimationController not loaded' };

        const ac = new AnimationController(gsap);
        const checks = [];

        checks.push(ac.enabled === true);
        checks.push(typeof ac.enter === 'function');
        checks.push(typeof ac.leave === 'function');
        checks.push(typeof ac.stagger === 'function');
        checks.push(typeof ac.countUp === 'function');
        checks.push(typeof ac.fillBar === 'function');
        checks.push(typeof ac.setEnabled === 'function');
        checks.push(typeof ac.killAll === 'function');

        return {
            pass: checks.every(Boolean),
            detail: checks.map((c, i) => check: ),
            count: checks.length,
            passed: checks.filter(Boolean).length
        };
    },

    /** 2. enter() 使用正确预设 */
    testEnterPreset() {
        const gsap = createMockGSAP();
        const { AnimationController } = window.__animationModule || {};
        if (!AnimationController) return { pass: false, reason: 'AnimationController not loaded' };

        const ac = new AnimationController(gsap);
        const el = document.createElement('div');

        ac.enter(el, { preset: 'page-enter' });

        const lastTween = gsap._tweens[gsap._tweens.length - 1];
        return {
            pass: lastTween?.type === 'fromTo',
            tweenType: lastTween?.type,
            detail: 'enter() should call gsap.fromTo'
        };
    },

    /** 3. setEnabled(false) 跳过动画 */
    testDisabled() {
        const gsap = createMockGSAP();
        const { AnimationController } = window.__animationModule || {};
        if (!AnimationController) return { pass: false, reason: 'AnimationController not loaded' };

        const ac = new AnimationController(gsap);
        ac.setEnabled(false);

        const el = document.createElement('div');
        const beforeCount = gsap._tweens.length;
        ac.enter(el, { preset: 'page-enter' });
        const afterCount = gsap._tweens.length;

        return {
            pass: afterCount === beforeCount,
            beforeCount,
            afterCount,
            detail: 'disabled controller should not create tweens'
        };
    },

    /** 4. setEnabled(true) 恢复动画 */
    testReEnabled() {
        const gsap = createMockGSAP();
        const { AnimationController } = window.__animationModule || {};
        if (!AnimationController) return { pass: false, reason: 'AnimationController not loaded' };

        const ac = new AnimationController(gsap);
        ac.setEnabled(false);
        ac.setEnabled(true);

        const el = document.createElement('div');
        const beforeCount = gsap._tweens.length;
        ac.enter(el, { preset: 'page-enter' });
        const afterCount = gsap._tweens.length;

        return {
            pass: afterCount > beforeCount,
            detail: 're-enabled controller should create tweens'
        };
    },

    /** 5. stagger() 创建 stagger 参数 */
    testStagger() {
        const gsap = createMockGSAP();
        const { AnimationController } = window.__animationModule || {};
        if (!AnimationController) return { pass: false, reason: 'AnimationController not loaded' };

        const ac = new AnimationController(gsap);
        const elements = [document.createElement('div'), document.createElement('div'), document.createElement('div')];

        ac.stagger(elements, { preset: 'slideUp' });

        const lastTween = gsap._tweens[gsap._tweens.length - 1];
        const hasStagger = lastTween?.vars?.stagger !== undefined;

        return {
            pass: hasStagger,
            vars: lastTween?.vars,
            detail: 'stagger() should set stagger param in gsap vars'
        };
    },

    /** 6. countUp() 创建数字滚动动画 */
    testCountUp() {
        const gsap = createMockGSAP();
        const { AnimationController } = window.__animationModule || {};
        if (!AnimationController) return { pass: false, reason: 'AnimationController not loaded' };

        const ac = new AnimationController(gsap);
        const el = document.createElement('span');
        el.textContent = '0';

        ac.countUp(el, 88.5, { duration: 1.2 });

        const lastTween = gsap._tweens[gsap._tweens.length - 1];
        return {
            pass: lastTween?.vars?.snap?.textContent !== undefined,
            snap: lastTween?.vars?.snap,
            detail: 'countUp() should use snap.textContent'
        };
    },

    /** 7. fillBar() 使用 scaleX */
    testFillBar() {
        const gsap = createMockGSAP();
        const { AnimationController } = window.__animationModule || {};
        if (!AnimationController) return { pass: false, reason: 'AnimationController not loaded' };

        const ac = new AnimationController(gsap);
        const el = document.createElement('div');

        ac.fillBar(el, 75);

        const lastTween = gsap._tweens[gsap._tweens.length - 1];
        return {
            pass: lastTween?.vars?.scaleX !== undefined,
            prop: Object.keys(lastTween?.vars || {}),
            detail: 'fillBar() should use scaleX (compositor-friendly)'
        };
    },

    /** 8. 不认识的预设应优雅 fallback */
    testUnknownPreset() {
        const gsap = createMockGSAP();
        const { AnimationController } = window.__animationModule || {};
        if (!AnimationController) return { pass: false, reason: 'AnimationController not loaded' };

        const ac = new AnimationController(gsap);
        const el = document.createElement('div');

        let threw = false;
        try {
            ac.enter(el, { preset: 'non-existent-preset-xyz' });
        } catch (e) {
            threw = true;
        }

        return {
            pass: !threw,
            detail: 'unknown preset should not throw'
        };
    },

    /** 9. killAll() 杀死所有动画 */
    testKillAll() {
        const gsap = createMockGSAP();
        const { AnimationController } = window.__animationModule || {};
        if (!AnimationController) return { pass: false, reason: 'AnimationController not loaded' };

        const ac = new AnimationController(gsap);
        let killedCount = 0;
        const origKill = gsap.killTweensOf;
        gsap.killTweensOf = (target) => { killedCount++; };

        ac.killAll();

        gsap.killTweensOf = origKill;
        return {
            pass: killedCount >= 1,
            killedCount,
            detail: 'killAll() should call gsap.killTweensOf'
        };
    },

    /**
     * 运行全部测试
     * @returns {Object} 测试结果汇总
     */
    runAll() {
        const results = {};
        const methods = Object.getOwnPropertyNames(window.__animationTests.constructor.prototype)
            .filter(m => m.startsWith('test') && typeof window.__animationTests[m] === 'function');

        // 也包含直接定义在对象上的方法
        const ownMethods = Object.keys(window.__animationTests).filter(k => k.startsWith('test'));

        [...new Set([...methods, ...ownMethods])].forEach(name => {
            try {
                results[name] = window.__animationTests[name]();
            } catch (e) {
                results[name] = { pass: false, error: e.message };
            }
        });

        const passed = Object.values(results).filter(r => r.pass).length;
        const total = Object.keys(results).length;

        return { results, summary: ${passed}/ tests passed };
    }
};
