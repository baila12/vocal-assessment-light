/**
 * animation/Controller.js 鈥?GSAP Animation Controller
 *
 * 缁熶竴绠＄悊鎵€鏈?GSAP 鍔ㄧ敾鐨勬牳蹇冩帶鍒跺櫒:
 *   - 棰勮椹卞姩 (enter/leave/stagger/countUp/fillBar)
 *   - 鍏ㄥ眬寮€鍏?绂佺敤 (setEnabled)
 *   - prefers-reduced-motion 鑷姩妫€娴? *   - 鍔ㄧ敾闃熷垪闃插啿绐? *   - GSAP 鍏ㄥ眬榛樿閰嶇疆
 *
 * 鐢ㄦ硶:
 *   const ac = new AnimationController(gsap);
 *   ac.enter(el, { preset: 'page-enter' });
 *   ac.leave(el);
 *   ac.stagger(elements, { preset: 'slideUp', stagger: 0.1 });
 *   ac.countUp(el, 88.5);
 *   ac.fillBar(el, 75);
 *
 * @version 1.0
 */

import { getPreset, hasPreset } from './presets.js';

export class AnimationController {
  /** @type {boolean} */
  enabled = true;

  /** @type {boolean} */
  reducedMotion = false;

  /** @type {Object} */
  defaults = {
    ease: 'power2.out',
    duration: 0.4,
    overwrite: 'auto'
  };

  /** @type {gsap.core.Timeline|null} */
  _currentTimeline = null;

  /** @type {Set<gsap.core.Tween|gsap.core.Timeline>} */
  _activeAnimations = new Set();

  /** @type {gsap} */
  _gsap;

  /** @type {number} */
  _nextTimelineId = 0;

  /**
   * @param {gsap} gsap - GSAP 搴撳紩鐢?   * @param {Object} [options]
   * @param {boolean} [options.detectReducedMotion=true]
   */
  constructor(gsap, options = {}) {
    const { detectReducedMotion = true } = options;

    if (!gsap) {
      console.warn('[AnimationController] GSAP not available, animations disabled');
      this.enabled = false;
      return;
    }

    this._gsap = gsap;

    // 璁剧疆 GSAP 鍏ㄥ眬榛樿
    gsap.defaults({ ...this.defaults });
    gsap.config({ force3D: true });

    // 妫€娴?prefers-reduced-motion
    if (detectReducedMotion) {
      this.reducedMotion = this._detectReducedMotion();
      this.enabled = !this.reducedMotion;

      // 鐩戝惉杩愯鏃跺彉鍖?
      const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');

      mediaQuery.addEventListener('change', (e) => {
        this.reducedMotion = e.matches;
        this.setEnabled(!e.matches);
      });
    }
  }

  // ========================================================================
  // 椤甸潰绾у姩鐢?  // ========================================================================

  /**
   * 椤甸潰/鍏冪礌鍏ュ満鍔ㄧ敾
   * @param {Element} el - 鐩爣鍏冪礌
   * @param {Object} [options]
   * @param {string} [options.preset='page-enter'] - 棰勮鍚嶇О
   * @param {number} [options.duration] - 瑕嗙洊鏃堕暱
   * @param {string} [options.ease] - 瑕嗙洊缂撳姩
   * @param {number} [options.delay] - 寤惰繜
   * @returns {gsap.core.Tween|gsap.core.Timeline|null}
   */
  enter(el, options = {}) {
    if (!el) return null;

    const presetName = options.preset || 'page-enter';
    const preset = getPreset(presetName);

    if (!preset) {
      // 鏈煡棰勮: 瀹夊叏 fallback 鈥?鐩存帴鏄剧ず
      this._setFinal(el);
      return null;
    }

    if (!this.enabled || this.reducedMotion) {
      this._setFinal(el, preset);
      return null;
    }

    return this._execute(el, preset, options);
  }

  /**
   * 椤甸潰/鍏冪礌鍑哄満鍔ㄧ敾
   * @param {Element} el - 鐩爣鍏冪礌
   * @param {Object} [options]
   * @param {string} [options.preset='page-leave'] - 棰勮鍚嶇О
   * @param {number} [options.duration] - 瑕嗙洊鏃堕暱
   * @returns {Promise<void>}
   */
  leave(el, options = {}) {
    if (!el) return Promise.resolve();

    const presetName = options.preset || 'page-leave';
    const preset = getPreset(presetName);

    if (!preset) {
      return Promise.resolve();
    }

    if (!this.enabled || this.reducedMotion) {
      return Promise.resolve();
    }

    return new Promise((resolve) => {
      const tween = this._execute(el, preset, {
        ...options,
        onComplete: resolve
      });
      if (!tween) resolve();
    });
  }

  /**
   * Stagger 鍏ュ満 (澶氫釜鍏冪礌渚濇鍔ㄧ敾)
   * @param {Element[]|NodeList} elements - 鐩爣鍏冪礌鍒楄〃
   * @param {Object} [options]
   * @param {string} [options.preset='slideUp'] - 棰勮鍚嶇О
   * @param {number} [options.stagger=0.1] - 闂撮殧绉掓暟
   * @param {number} [options.duration] - 瑕嗙洊鏃堕暱
   * @returns {gsap.core.Tween|null}
   */
  stagger(elements, options = {}) {
    const presetName = options.preset || 'slideUp';
    const preset = getPreset(presetName);
    const staggerAmount = options.stagger ?? 0.1;

    if (!elements || elements.length === 0) return null;
    if (!preset) return null;

    if (!this.enabled || this.reducedMotion) {
      // 鐩存帴鏄剧ず鏈€缁堢姸鎬?
      for (const el of elements) {
        if (el) {
          el.style.opacity = '1';
          el.style.transform = 'none';
          el.style.visibility = 'visible';
        }
      }
      return null;
    }

    const defaults = { ...preset.defaults, ...options };
    delete defaults.preset;

    const toVars = { ...preset.to, stagger: staggerAmount, ...defaults };

    if (preset.type === 'fromTo') {
      return this._gsap.fromTo(elements, preset.from, toVars);
    } else if (preset.type === 'from') {
      return this._gsap.from(elements, toVars);
    } else {
      return this._gsap.to(elements, { ...toVars, ...preset.from });
    }
  }

  // ========================================================================
  // 涓撶敤鍔ㄧ敾鏂规硶
  // ========================================================================

  /**
   * 鏁板瓧婊氬姩璁℃暟鍣?(GSAP textContent snap)
   * @param {Element} element - 鏄剧ず鏁板瓧鐨?DOM 鍏冪礌
   * @param {number} target - 鐩爣鏁板瓧
   * @param {Object} [options]
   * @param {number} [options.duration=1.2]
   * @param {number} [options.decimals=1]
   * @param {Function} [options.onUpdate]
   * @returns {gsap.core.Tween|null}
   */
  countUp(element, target, options = {}) {
    if (!element) return null;
    const { duration = 1.2, decimals = 1, onUpdate } = options;

    if (!this.enabled || this.reducedMotion) {
      element.textContent = target.toFixed(decimals);
      element.style.opacity = '1';
      return null;
    }

    const snap = Math.max(0.1, Math.pow(10, -decimals));

    return this._gsap.fromTo(element,
      { textContent: 0 },
      {
        textContent: target,
        duration,
        snap: { textContent: snap },
        ease: 'power3.out',
        overwrite: 'auto',
        onUpdate() {
          if (onUpdate) onUpdate(parseFloat(element.textContent));
        }
      }
    );
  }

  /**
   * 杩涘害鏉″～鍏?(scaleX)
   * @param {Element} element - 杩涘害鏉″厓绱?   * @param {number} percent - 0-100 鐧惧垎姣?   * @param {Object} [options]
   * @param {number} [options.duration=0.8]
   * @returns {gsap.core.Tween|null}
   */
  fillBar(element, percent, options = {}) {
    if (!element) return null;
    const { duration = 0.8 } = options;
    const pct = Math.min(100, Math.max(0, percent));

    if (!this.enabled || this.reducedMotion) {
      element.style.transform = 'scaleX(' + pct/100 + ')';
      element.style.opacity = '1';
      return null;
    }

    return this._gsap.to(element, {
      scaleX: pct / 100,
      duration,
      ease: 'power2.out',
      transformOrigin: 'left center',
      overwrite: 'auto'
    });
  }

  // ========================================================================
  // 寰氦浜?  // ========================================================================

  /**
   * 鎸夐挳鐐瑰嚮缂╁皬寮瑰洖
   * @param {Element} el
   * @returns {gsap.core.Timeline|null}
   */
  clickPress(el) {
    if (!el || !this.enabled) return null;
    return this._gsap.timeline()
      .to(el, { scale: 0.97, duration: 0.08, ease: 'power2.out' })
      .to(el, { scale: 1, duration: 0.12, ease: 'elastic.out(1, 0.3)' });
  }

  /**
   * 鎸夐挳 hover 鏀惧ぇ
   * @param {Element} el
   */
  hoverIn(el) {
    if (!el || !this.enabled) return null;
    return this._gsap.to(el, { scale: 1.03, duration: 0.15, ease: 'power2.out', overwrite: 'auto' });
  }

  /**
   * 鎸夐挳 hover 鎭㈠
   * @param {Element} el
   */
  hoverOut(el) {
    if (!el || !this.enabled) return null;
    return this._gsap.to(el, { scale: 1, duration: 0.15, ease: 'power2.out', overwrite: 'auto' });
  }

  /**
   * 璇勫垎鑴夊啿
   * @param {Element} el
   */
  scorePulse(el) {
    if (!el || !this.enabled) return null;
    return this._gsap.timeline()
      .to(el, { scale: 1.1, duration: 0.1, ease: 'power2.out' })
      .to(el, { scale: 1, duration: 0.3, ease: 'elastic.out(1, 0.3)' });
  }

  // ========================================================================
  // 鎺у埗
  // ========================================================================

  /**
   * 鍚敤/绂佺敤鍔ㄧ敾
   * @param {boolean} val
   */
  setEnabled(val) {
    this.enabled = val;
    if (!val) {
      this.killAll();
    }
  }

  /**
   * 鏉€姝绘墍鏈夋椿璺冨姩鐢?   */
  killAll() {
    if (this._currentTimeline) {
      this._currentTimeline.kill();
      this._currentTimeline = null;
    }
    for (const anim of this._activeAnimations) {
      try { anim.kill(); } catch (e) { /* ignore */ }
    }
    this._activeAnimations.clear();
    if (this._gsap) {
      this._gsap.killTweensOf('*');
    }
  }

  /**
   * 寮€濮嬩竴涓柊鐨?Timeline (鑷姩 kill 涓婁竴涓湭瀹屾垚鐨?
   * @returns {gsap.core.Timeline}
   */
  createTimeline() {
    if (this._currentTimeline) {
      this._currentTimeline.kill();
    }
    const tl = this._gsap.timeline({
      id: 'ac-tl-' + (this._nextTimelineId++)
    });
    this._currentTimeline = tl;
    this._track(tl);
    return tl;
  }

  /**
   * 閿€姣?   */
  destroy() {
    this.killAll();
  }

  // ========================================================================
  // 鍐呴儴鏂规硶
  // ========================================================================

  /**
   * 鎵ц棰勮鍔ㄧ敾
   * @private
   */
  _execute(el, preset, options = {}) {
    const defaults = { ...preset.defaults, ...options };
    delete defaults.preset;

    // 澶勭悊 completion callback 鈥?浠?defaults 涓墺绂? 涓嶄紶缁?GSAP
    let { onComplete, ...vars } = defaults;

    // 澶勭悊 timeline 绫诲瀷棰勮
    if (preset.type === 'timeline' && preset.steps) {
      const tl = this._gsap.timeline({ onComplete });
      for (const step of preset.steps) {
        const stepVars = { ...step.vars };
        if (step.method === 'fromTo' && step.from) {
          tl.fromTo(el, step.from, stepVars);
        } else {
          tl.to(el, stepVars);
        }
      }
      this._track(tl);
      return tl;
    }

    // 鏍囧噯 tween 绫诲瀷: fromTo / to / from
    const toVars = { ...preset.to, ...vars };

    let tween;
    if (preset.type === 'fromTo') {
      tween = this._gsap.fromTo(el, preset.from, toVars);
    } else if (preset.type === 'from') {
      tween = this._gsap.from(el, toVars);
    } else {
      // 'to' 鈥?combine from + to for the case where from has data

      tween = this._gsap.to(el, toVars);
    }

    this._track(tween);
    return tween;
  }

  /**
   * 璺熻釜娲昏穬鍔ㄧ敾
   * @private
   */
  _track(anim) {
    if (!anim) return;
    this._activeAnimations.add(anim);
    const cleanup = () => this._activeAnimations.delete(anim);
    if (anim.vars) anim.vars.onComplete = (() => { cleanup(); }).bind(this);
    // 瀵逛簬 Timeline, 鐩戝惉 onComplete
    if (anim.eventCallback) {
      anim.eventCallback('onComplete', cleanup);
    }
  }

  /**
   * 鐩存帴璁剧疆鏈€缁堢姸鎬?(绂佺敤鏃?
   * @private
   */
  _setFinal(el, preset = null) {
    if (!el) return;
    if (preset && preset.to) {
      const style = preset.to;
      if (style.opacity !== undefined) el.style.opacity = style.opacity;
      if (style.scale !== undefined) el.style.transform = 'scale(' + style.scale + ')';
      if (style.y !== undefined) el.style.transform +=  ' translateY(' + style.y + 'px)';
      if (style.x !== undefined) el.style.transform +=  ' translateX(' + style.x + 'px)';
      el.style.visibility = 'visible';
    } else {
      el.style.opacity = '1';
      el.style.transform = 'none';
      el.style.visibility = 'visible';
    }
  }

  /**
   * 妫€娴?prefers-reduced-motion
   * @private
   */
  _detectReducedMotion() {
    if (typeof window === 'undefined' || !window.matchMedia) return false;
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }
}
