/**
 * animation/Controller.js — GSAP Animation Controller
 *
 * Unified animation controller for all GSAP animations:
 *   - Preset-driven animations (enter/leave/stagger/countUp/fillBar)
 *   - Global enable/disable (setEnabled)
 *   - prefers-reduced-motion auto-detection
 *   - Animation queue conflict prevention
 *   - GSAP global defaults configuration
 *
 * Usage:
 *   const ac = new AnimationController(gsap);
 *   ac.enter(el, { preset: 'page-enter' });
 *   ac.leave(el);
 *   ac.stagger(elements, { preset: 'slideUp', stagger: 0.1 });
 *   ac.countUp(el, 88.5);
 *   ac.fillBar(el, 75);
 *
 * @version 1.0
 */

import { getPreset, hasPreset, PRESETS } from './presets.js';

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
   * @param {gsap} gsap - GSAP library reference
   * @param {Object} [options]
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

    // Set GSAP global defaults
    gsap.defaults({ ...this.defaults });
    gsap.config({ force3D: true });

    // Detect prefers-reduced-motion
    if (detectReducedMotion) {
      this.reducedMotion = this._detectReducedMotion();
      this.enabled = !this.reducedMotion;

      // Listen for runtime changes
      const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');

      mediaQuery.addEventListener('change', (e) => {
        this.reducedMotion = e.matches;
        this.setEnabled(!e.matches);
      });
    }
  }

  // ========================================================================
  // Page-level animations
  // ========================================================================

  /**
   * Page/element enter animation
   * @param {Element} el - Target element
   * @param {Object} [options]
   * @param {string} [options.preset='page-enter'] - Preset name
   * @param {number} [options.duration] - Override duration
   * @param {string} [options.ease] - Override easing
   * @param {number} [options.delay] - Delay in seconds
   * @returns {gsap.core.Tween|gsap.core.Timeline|null}
   */
  enter(el, options = {}) {
    if (!el) return null;

    const presetName = options.preset || 'page-enter';
    const preset = getPreset(presetName);

    if (!preset) {
      // Unknown preset: safe fallback — show element directly
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
   * Page/element leave animation
   * @param {Element} el - Target element
   * @param {Object} [options]
   * @param {string} [options.preset='page-leave'] - Preset name
   * @param {number} [options.duration] - Override duration
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
      let settled = false;
      const done = () => { if (!settled) { settled = true; resolve(); } };

      const tween = this._execute(el, preset, {
        ...options,
        onComplete: done
      });
      if (!tween) done();

      // Safety timeout: if the animation is killed externally
      // (e.g. killAll), onComplete never fires. Resolve anyway
      // so the router's #transition() doesn't deadlock.
      const maxDuration = ((preset.defaults && preset.defaults.duration) || 0.4) * 1000 + 500;
      setTimeout(done, maxDuration);
    });
  }

  /**
   * Stagger enter animation (multiple elements sequentially)
   * @param {Element[]|NodeList} elements - Target elements
   * @param {Object} [options]
   * @param {string} [options.preset='slideUp'] - Preset name
   * @param {number} [options.stagger=0.1] - Stagger interval in seconds
   * @param {number} [options.duration] - Override duration
   * @returns {gsap.core.Tween|null}
   */
  stagger(elements, options = {}) {
    const presetName = options.preset || 'slideUp';
    const preset = getPreset(presetName);
    const staggerAmount = options.stagger ?? 0.1;

    if (!elements || elements.length === 0) return null;
    if (!preset) return null;

    if (!this.enabled || this.reducedMotion) {
      // Show final state directly
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
  // Special-purpose animation methods
  // ========================================================================

  /**
   * Number count-up animation (GSAP textContent snap)
   * @param {Element} element - DOM element displaying the number
   * @param {number} target - Target number
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
   * Progress bar fill animation (scaleX)
   * @param {Element} element - Progress bar element
   * @param {number} percent - 0-100 percentage
   * @param {Object} [options]
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
  // Micro-interactions
  // ========================================================================

  /**
   * Button click press (shrink and bounce back)
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
   * Button hover scale up
   * @param {Element} el
   */
  hoverIn(el) {
    if (!el || !this.enabled) return null;
    return this._gsap.to(el, { scale: 1.03, duration: 0.15, ease: 'power2.out', overwrite: 'auto' });
  }

  /**
   * Button hover scale reset
   * @param {Element} el
   */
  hoverOut(el) {
    if (!el || !this.enabled) return null;
    return this._gsap.to(el, { scale: 1, duration: 0.15, ease: 'power2.out', overwrite: 'auto' });
  }

  /**
   * Score pulse animation
   * @param {Element} el
   */
  scorePulse(el) {
    if (!el || !this.enabled) return null;
    return this._gsap.timeline()
      .to(el, { scale: 1.1, duration: 0.1, ease: 'power2.out' })
      .to(el, { scale: 1, duration: 0.3, ease: 'elastic.out(1, 0.3)' });
  }

  // ========================================================================
  // Control
  // ========================================================================

  /**
   * Enable/disable animations
   * @param {boolean} val
   */
  setEnabled(val) {
    this.enabled = val;
    if (!val) {
      this.killAll();
    }
  }

  /**
   * Kill all active animations
   */
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
   * Start a new Timeline (auto-kills previous incomplete one)
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
   * Destroy — kill all animations
   */
  destroy() {
    this.killAll();
  }

  // ========================================================================
  // Internal methods
  // ========================================================================

  /**
   * Execute a preset animation
   * @private
   */
  _execute(el, preset, options = {}) {
    const defaults = { ...preset.defaults, ...options };
    delete defaults.preset;

    // Extract onComplete from merged options — must be passed to GSAP toVars
    // so the animation resolves correctly (critical for leave() Promise chain)
    let { onComplete, ...vars } = defaults;

    // Handle timeline-type presets
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

    // Standard tween types: fromTo / to / from
    // IMPORTANT: include onComplete so leave() Promises resolve
    const toVars = { ...preset.to, ...vars };
    if (onComplete) toVars.onComplete = onComplete;

    let tween;
    if (preset.type === 'fromTo') {
      tween = this._gsap.fromTo(el, preset.from, toVars);
    } else if (preset.type === 'from') {
      tween = this._gsap.from(el, toVars);
    } else {
      // 'to' — combine from + to for the case where from has data
      tween = this._gsap.to(el, toVars);
    }

    this._track(tween);
    return tween;
  }

  /**
   * Track active animation — chain cleanup after any existing onComplete
   *
   * IMPORTANT: For newly-created tweens, GSAP may not have registered the
   * vars.onComplete callback internally yet (eventCallback('onComplete')
   * can return undefined). We check both sources and prefer the internal
   * callback, falling back to vars.onComplete.
   * @private
   */
  _track(anim) {
    if (!anim) return;
    this._activeAnimations.add(anim);
    const cleanup = () => this._activeAnimations.delete(anim);

    // Get existing callback from either GSAP internal registry or raw vars
    const internalCb = (anim.eventCallback && anim.eventCallback('onComplete')) || null;
    const varsCb = (anim.vars && typeof anim.vars.onComplete === 'function' && anim.vars.onComplete) || null;
    const existingCb = internalCb || varsCb;

    const chained = () => {
      cleanup();
      if (existingCb) existingCb();
    };

    if (anim.eventCallback) {
      anim.eventCallback('onComplete', chained);
    }
    // Also update vars.onComplete in case GSAP reads it later
    if (anim.vars) {
      anim.vars.onComplete = chained;
    }
  }

  /**
   * Set final state directly (when animations disabled)
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
   * Detect prefers-reduced-motion
   * @private
   */
  _detectReducedMotion() {
    if (typeof window === 'undefined' || !window.matchMedia) return false;
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }
}

// Expose for tests
if (typeof window !== 'undefined') {
  window.__animationModule = { AnimationController, getPreset, hasPreset, PRESETS };
}
