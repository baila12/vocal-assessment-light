/**
 * animation/presets.js — GSAP Animation Presets
 *
 * All presets managed at the Controller layer — pages don't write GSAP code directly.
 * Design principles:
 *   1. Only animate transform/opacity (compositor-only, per gsap-performance)
 *   2. duration <= 600ms (page enter) / <= 300ms (micro-interactions)
 *   3. Each preset should define clear enter/leave direction
 *
 * @version 1.0
 */

/**
 * @typedef {Object} PresetDefinition
 * @property {string} type - 'fromTo' | 'to' | 'from'
 * @property {Object} from - Start state
 * @property {Object} to - End state
 * @property {Object} [defaults] - Default config
 */

/**
 * Preset library
 * key: preset name (used for animation preset selection)
 */
export const PRESETS = {

  // —— Page-level ——

  /** Page enter: fade up from below (general) */
  'page-enter': {
    type: 'fromTo',
    from: { opacity: 0, y: 12 },
    to: { opacity: 1, y: 0 },
    defaults: { duration: 0.35, ease: 'power2.out' }
  },

  /** Page enter: fade down from above (home welcome) */
  'page-enter-down': {
    type: 'fromTo',
    from: { opacity: 0, y: -16 },
    to: { opacity: 1, y: 0 },
    defaults: { duration: 0.4, ease: 'power2.out' }
  },

  /** Page enter: scale up (report page) */
  'page-enter-scale': {
    type: 'fromTo',
    from: { opacity: 0, scale: 0.97 },
    to: { opacity: 1, scale: 1 },
    defaults: { duration: 0.4, ease: 'power2.out' }
  },

  /** Page leave: fade out + slide left */
  'page-leave': {
    type: 'to',
    from: null,
    to: { opacity: 0, x: -12 },
    defaults: { duration: 0.2, ease: 'power2.in' }
  },

  /** Page leave: fade out + slide right */
  'page-leave-right': {
    type: 'to',
    from: null,
    to: { opacity: 0, x: 12 },
    defaults: { duration: 0.2, ease: 'power2.in' }
  },

  /** New page slides in from right (pair with left leave) */
  'page-enter-right': {
    type: 'fromTo',
    from: { opacity: 0, x: 20 },
    to: { opacity: 1, x: 0 },
    defaults: { duration: 0.3, ease: 'power2.out' }
  },

  // —— Element-level ——

  /** Slide up from below (stagger general) */
  'slideUp': {
    type: 'fromTo',
    from: { opacity: 0, y: 24 },
    to: { opacity: 1, y: 0 },
    defaults: { duration: 0.5, ease: 'power2.out' }
  },

  /** Subtle slide up (cards, titles) */
  'slideUp-sm': {
    type: 'fromTo',
    from: { opacity: 0, y: 8 },
    to: { opacity: 1, y: 0 },
    defaults: { duration: 0.3, ease: 'power2.out' }
  },

  /** Slide in from right (sidebar) */
  'slideInRight': {
    type: 'fromTo',
    from: { opacity: 0, x: 30 },
    to: { opacity: 1, x: 0 },
    defaults: { duration: 0.4, ease: 'power2.out' }
  },

  /** Slide in from left */
  'slideInLeft': {
    type: 'fromTo',
    from: { opacity: 0, x: -30 },
    to: { opacity: 1, x: 0 },
    defaults: { duration: 0.4, ease: 'power2.out' }
  },

  /** Scale pop (badges, score labels) */
  'popIn': {
    type: 'fromTo',
    from: { opacity: 0, scale: 0.5 },
    to: { opacity: 1, scale: 1 },
    defaults: { duration: 0.4, ease: 'back.out(1.5)' }
  },

  /** Staggered fade in (advice list) */
  'fadeIn-stagger': {
    type: 'fromTo',
    from: { opacity: 0, y: 10 },
    to: { opacity: 1, y: 0 },
    defaults: { duration: 0.4, ease: 'power2.out' }
  },

  /** Pulse animation (record button) */
  'pulse': {
    type: 'to',
    from: null,
    to: { scale: 1.1, opacity: 0.8 },
    defaults: { duration: 0.8, ease: 'power1.inOut', yoyo: true, repeat: -1 }
  },

  /** Button hover scale up */
  'hover-scale': {
    type: 'to',
    from: null,
    to: { scale: 1.03 },
    defaults: { duration: 0.15, ease: 'power2.out' }
  },

  /** Button hover scale reset */
  'hover-scale-reset': {
    type: 'to',
    from: null,
    to: { scale: 1 },
    defaults: { duration: 0.15, ease: 'power2.out' }
  },

  /** Click press (0.97 scale bounce back) */
  'click-press': {
    type: 'timeline',
    steps: [
      { method: 'to', vars: { scale: 0.97, duration: 0.08, ease: 'power2.out' } },
      { method: 'to', vars: { scale: 1, duration: 0.12, ease: 'elastic.out(1, 0.3)' } }
    ]
  },

  /** Toast enter */
  'toast-enter': {
    type: 'fromTo',
    from: { opacity: 0, y: -20 },
    to: { opacity: 1, y: 0 },
    defaults: { duration: 0.3, ease: 'back.out(1.5)' }
  },

  /** Toast exit */
  'toast-exit': {
    type: 'to',
    from: null,
    to: { opacity: 0, y: -20 },
    defaults: { duration: 0.2, ease: 'power2.in' }
  },

  /** Modal overlay fade in */
  'modal-overlay': {
    type: 'fromTo',
    from: { opacity: 0 },
    to: { opacity: 0.5 },
    defaults: { duration: 0.2, ease: 'power2.out' }
  },

  /** Modal card enter */
  'modal-card': {
    type: 'fromTo',
    from: { opacity: 0, scale: 0.95, y: 20 },
    to: { opacity: 1, scale: 1, y: 0 },
    defaults: { duration: 0.3, ease: 'back.out(1.5)' }
  },

  /** Score pulse (on update) */
  'score-pulse': {
    type: 'timeline',
    steps: [
      { method: 'to', vars: { scale: 1.1, duration: 0.1, ease: 'power2.out' } },
      { method: 'to', vars: { scale: 1, duration: 0.3, ease: 'elastic.out(1, 0.3)' } }
    ]
  },

  /** Progress bar fill */
  'fillBar': {
    type: 'to',
    from: null,
    to: { scaleX: 1 },
    defaults: { duration: 0.8, ease: 'power2.out', transformOrigin: 'left center' }
  }
};

/**
 * Get a preset definition by name
 * @param {string} name
 * @returns {object|null}
 */
export function getPreset(name) {
  return PRESETS[name] || null;
}

/**
 * Check if a preset name exists
 * @param {string} name
 * @returns {boolean}
 */
export function hasPreset(name) {
  return name in PRESETS;
}

// Expose for tests
if (typeof window !== 'undefined') {
  window.__presets = PRESETS;
}
