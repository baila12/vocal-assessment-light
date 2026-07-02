/**
 * animation/presets.js — GSAP 动画预设配置
 *
 * 所有预设集中在 Controller 层管理，页面无需直接写 GSAP 代码。
 * 设计原则:
 *   1. 只动画 transform/opacity (compositor-only, 遵循 gsap-performance)
 *   2. duration ≤ 600ms (页面入场) / ≤ 300ms (微交互)
 *   3. 每个预设应配置 enter/leave 或 animate 方向
 *
 * @version 1.0
 */

/**
 * @typedef {Object} PresetDefinition
 * @property {string} type - 'fromTo' | 'to' | 'from'
 * @property {Object} from - 起始状态
 * @property {Object} to - 结束状态
 * @property {Object} [defaults] - 默认配置
 */

/**
 * 预设库
 * key: 预设名称 (用于动画预设指定)
 * value: { enter/leave: PresetDefinition }
 */
export const PRESETS = {

  // —— 页面级别 ——

  /** 页面入场: 从下方淡入 (通用) */
  'page-enter': {
    type: 'fromTo',
    from: { opacity: 0, y: 12 },
    to: { opacity: 1, y: 0 },
    defaults: { duration: 0.35, ease: 'power2.out' }
  },

  /** 页面入场: 从上方淡入 (首页 welcome) */
  'page-enter-down': {
    type: 'fromTo',
    from: { opacity: 0, y: -16 },
    to: { opacity: 1, y: 0 },
    defaults: { duration: 0.4, ease: 'power2.out' }
  },

  /** 页面入场: 缩放进入 (报告页) */
  'page-enter-scale': {
    type: 'fromTo',
    from: { opacity: 0, scale: 0.97 },
    to: { opacity: 1, scale: 1 },
    defaults: { duration: 0.4, ease: 'power2.out' }
  },

  /** 页面出场: 淡出 + 左移 */
  'page-leave': {
    type: 'to',
    from: null,
    to: { opacity: 0, x: -12 },
    defaults: { duration: 0.2, ease: 'power2.in' }
  },

  /** 页面出场: 淡出 + 右移 */
  'page-leave-right': {
    type: 'to',
    from: null,
    to: { opacity: 0, x: 12 },
    defaults: { duration: 0.2, ease: 'power2.in' }
  },

  /** 新页面从右侧滑入 (配合左退) */
  'page-enter-right': {
    type: 'fromTo',
    from: { opacity: 0, x: 20 },
    to: { opacity: 1, x: 0 },
    defaults: { duration: 0.3, ease: 'power2.out' }
  },

  // —— 元素级别 ——

  /** 从下方滑入 (stagger 通用) */
  'slideUp': {
    type: 'fromTo',
    from: { opacity: 0, y: 24 },
    to: { opacity: 1, y: 0 },
    defaults: { duration: 0.5, ease: 'power2.out' }
  },

  /** 轻微上滑 (卡片、标题) */
  'slideUp-sm': {
    type: 'fromTo',
    from: { opacity: 0, y: 8 },
    to: { opacity: 1, y: 0 },
    defaults: { duration: 0.3, ease: 'power2.out' }
  },

  /** 从右侧滑入 (侧边栏) */
  'slideInRight': {
    type: 'fromTo',
    from: { opacity: 0, x: 30 },
    to: { opacity: 1, x: 0 },
    defaults: { duration: 0.4, ease: 'power2.out' }
  },

  /** 从左侧滑入 */
  'slideInLeft': {
    type: 'fromTo',
    from: { opacity: 0, x: -30 },
    to: { opacity: 1, x: 0 },
    defaults: { duration: 0.4, ease: 'power2.out' }
  },

  /** 缩放弹出 (徽标、评分标签) */
  'popIn': {
    type: 'fromTo',
    from: { opacity: 0, scale: 0.5 },
    to: { opacity: 1, scale: 1 },
    defaults: { duration: 0.4, ease: 'back.out(1.5)' }
  },

  /** 逐条淡入 (建议列表) */
  'fadeIn-stagger': {
    type: 'fromTo',
    from: { opacity: 0, y: 10 },
    to: { opacity: 1, y: 0 },
    defaults: { duration: 0.4, ease: 'power2.out' }
  },

  /** 脉冲动画 (录音按钮) */
  'pulse': {
    type: 'to',
    from: null,
    to: { scale: 1.1, opacity: 0.8 },
    defaults: { duration: 0.8, ease: 'power1.inOut', yoyo: true, repeat: -1 }
  },

  /** 按钮 hover 放大 */
  'hover-scale': {
    type: 'to',
    from: null,
    to: { scale: 1.03 },
    defaults: { duration: 0.15, ease: 'power2.out' }
  },

  /** 按钮 hover 恢复 */
  'hover-scale-reset': {
    type: 'to',
    from: null,
    to: { scale: 1 },
    defaults: { duration: 0.15, ease: 'power2.out' }
  },

  /** 点击缩放 (0.97 弹回) */
  'click-press': {
    type: 'timeline',
    steps: [
      { method: 'to', vars: { scale: 0.97, duration: 0.08, ease: 'power2.out' } },
      { method: 'to', vars: { scale: 1, duration: 0.12, ease: 'elastic.out(1, 0.3)' } }
    ]
  },

  /** Toast 入场 */
  'toast-enter': {
    type: 'fromTo',
    from: { opacity: 0, y: -20 },
    to: { opacity: 1, y: 0 },
    defaults: { duration: 0.3, ease: 'back.out(1.5)' }
  },

  /** Toast 出场 */
  'toast-exit': {
    type: 'to',
    from: null,
    to: { opacity: 0, y: -20 },
    defaults: { duration: 0.2, ease: 'power2.in' }
  },

  /** Modal 遮罩淡入 */
  'modal-overlay': {
    type: 'fromTo',
    from: { opacity: 0 },
    to: { opacity: 0.5 },
    defaults: { duration: 0.2, ease: 'power2.out' }
  },

  /** Modal 卡片入场 */
  'modal-card': {
    type: 'fromTo',
    from: { opacity: 0, scale: 0.95, y: 20 },
    to: { opacity: 1, scale: 1, y: 0 },
    defaults: { duration: 0.3, ease: 'back.out(1.5)' }
  },

  /** 评分脉冲 (更新时) */
  'score-pulse': {
    type: 'timeline',
    steps: [
      { method: 'to', vars: { scale: 1.1, duration: 0.1, ease: 'power2.out' } },
      { method: 'to', vars: { scale: 1, duration: 0.3, ease: 'elastic.out(1, 0.3)' } }
    ]
  },

  /** 进度条更新 */
  'fillBar': {
    type: 'to',
    from: null,
    to: { scaleX: 1 },
    defaults: { duration: 0.8, ease: 'power2.out', transformOrigin: 'left center' }
  }
};

/**
 * 获取预设定义
 * @param {string} name
 * @returns {object|null}
 */
export function getPreset(name) {
  return PRESETS[name] || null;
}

/**
 * 是否是一个已知的预设名称
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
