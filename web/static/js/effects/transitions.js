/**
 * effects/transitions.js — DEPRECATED (v2.0)
 *
 * 请使用 AnimationController (js/animation/Controller.js) 替代:
 *   - ac.enter(el, { preset: 'page-enter-right' }) → 入场
 *   - ac.leave(el, { preset: 'page-leave' }) → 出场
 *
 * 保留此文件仅用于向后兼容。
 */
export function pageTransition() { return Promise.resolve(); }
export function fadeTransition() { return Promise.resolve(); }
