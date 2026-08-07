/**
 * 键盘快捷键映射 — v7.13 Phase 5 对比分析快捷键
 *
 * 纯函数, 零 Vue 依赖, 可直接 Vitest 测试。
 * 对齐 pitch-realtime.feature "键盘快捷键":
 *   | Space | 播放/暂停             |
 *   | ←     | 后退 5 秒             |
 *   | →     | 前进 5 秒             |
 *   | R     | 切换参考曲线显示/隐藏  |
 *   | S     | 截图                  |
 *   | 1     | 仅显示用户曲线         |
 *   | 2     | 显示双曲线对比         |
 * 修饰键 (Ctrl/Meta/Alt) 按下或目标为可编辑元素时返回 null (不劫持浏览器)。
 */

/** 快捷键动作 */
export type KeyboardAction =
  | 'playPause'
  | 'seekBack'
  | 'seekForward'
  | 'toggleReference'
  | 'takeScreenshot'
  | 'modeUserOnly'
  | 'modeDualCurve'

/** 按键 → 动作映射 (只读) */
export const KEYBOARD_SHORTCUTS: Readonly<Record<string, KeyboardAction>> = {
  ' ': 'playPause',
  ArrowLeft: 'seekBack',
  ArrowRight: 'seekForward',
  r: 'toggleReference',
  R: 'toggleReference',
  s: 'takeScreenshot',
  S: 'takeScreenshot',
  '1': 'modeUserOnly',
  '2': 'modeDualCurve',
}

/** 目标是否为可编辑/自交互元素 (input/textarea/select/contenteditable/滑块) */
export function isEditableTarget(e: KeyboardEvent): boolean {
  const target = e.target as HTMLElement | null
  if (!target) return false
  const tag = target.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true
  // Element Plus 滑块 (el-slider) 渲染为 div[role=slider] — 方向键由组件自身消费, 不劫持
  if (target.closest?.('[role="slider"]')) return true
  // isContentEditable 在 jsdom 中恒为 false; contentEditable 属性为 'true' 时视为可编辑
  return target.isContentEditable || target.contentEditable === 'true'
}

/** 按键事件 → 快捷键动作; 不适用 (未知键/修饰键/可编辑目标) → null */
export function mapKeyboardAction(e: KeyboardEvent): KeyboardAction | null {
  if (e.ctrlKey || e.metaKey || e.altKey) return null
  if (isEditableTarget(e)) return null
  return KEYBOARD_SHORTCUTS[e.key] ?? null
}
