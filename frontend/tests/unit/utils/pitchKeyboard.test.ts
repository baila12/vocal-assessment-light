/**
 * pitchKeyboard 单元测试 — v7.13 Phase 5 键盘快捷键
 *
 * 对齐 pitch-realtime.feature "键盘快捷键":
 *   | Space | 播放/暂停            |
 *   | ←     | 后退 5 秒            |
 *   | →     | 前进 5 秒            |
 *   | R     | 切换参考曲线显示/隐藏 |
 *   | S     | 截图                 |
 *   | 1     | 仅显示用户曲线       |
 *   | 2     | 显示双曲线对比       |
 *   And 不应与浏览器默认快捷键冲突 (可编辑目标/修饰键守卫)
 */
import { describe, it, expect } from 'vitest'
import {
  mapKeyboardAction,
  isEditableTarget,
  KEYBOARD_SHORTCUTS,
  type KeyboardAction,
} from '@/utils/pitchKeyboard'

/** 构造带指定 target 的 keydown 事件 (KeyboardEvent 构造器无法直接设置 target) */
function keyEvent(key: string, target: HTMLElement | null = document.body, opts: KeyboardEventInit = {}): KeyboardEvent {
  const evt = new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true, ...opts })
  Object.defineProperty(evt, 'target', { value: target })
  return evt
}

describe('mapKeyboardAction', () => {
  it('Space → playPause', () => {
    expect(mapKeyboardAction(keyEvent(' '))).toBe('playPause')
  })

  it('←/→ → seekBack/seekForward (5s 步进)', () => {
    expect(mapKeyboardAction(keyEvent('ArrowLeft'))).toBe('seekBack')
    expect(mapKeyboardAction(keyEvent('ArrowRight'))).toBe('seekForward')
  })

  it('R/r → toggleReference (切换参考曲线)', () => {
    expect(mapKeyboardAction(keyEvent('R'))).toBe('toggleReference')
    expect(mapKeyboardAction(keyEvent('r'))).toBe('toggleReference')
  })

  it('S/s → takeScreenshot', () => {
    expect(mapKeyboardAction(keyEvent('S'))).toBe('takeScreenshot')
    expect(mapKeyboardAction(keyEvent('s'))).toBe('takeScreenshot')
  })

  it('1/2 → modeUserOnly/modeDualCurve', () => {
    expect(mapKeyboardAction(keyEvent('1'))).toBe('modeUserOnly')
    expect(mapKeyboardAction(keyEvent('2'))).toBe('modeDualCurve')
  })

  it('未知按键 → null', () => {
    expect(mapKeyboardAction(keyEvent('Enter'))).toBeNull()
    expect(mapKeyboardAction(keyEvent('a'))).toBeNull()
  })

  it('修饰键按下 (Ctrl/Meta/Alt) → null (不劫持浏览器快捷键)', () => {
    expect(mapKeyboardAction(keyEvent(' ', document.body, { ctrlKey: true }))).toBeNull()
    expect(mapKeyboardAction(keyEvent('S', document.body, { metaKey: true }))).toBeNull()
    expect(mapKeyboardAction(keyEvent('1', document.body, { altKey: true }))).toBeNull()
  })

  it('可编辑目标 (input/textarea/contenteditable) → null', () => {
    const input = document.createElement('input')
    const textarea = document.createElement('textarea')
    const editable = document.createElement('div')
    editable.contentEditable = 'true'
    expect(mapKeyboardAction(keyEvent(' ', input))).toBeNull()
    expect(mapKeyboardAction(keyEvent(' ', textarea))).toBeNull()
    expect(mapKeyboardAction(keyEvent(' ', editable))).toBeNull()
  })

  it('滑块 (el-slider div[role=slider]) → null (方向键由组件消费, 不劫持)', () => {
    const slider = document.createElement('div')
    slider.setAttribute('role', 'slider')
    expect(mapKeyboardAction(keyEvent('ArrowLeft', slider))).toBeNull()
    expect(mapKeyboardAction(keyEvent('ArrowRight', slider))).toBeNull()
    expect(mapKeyboardAction(keyEvent(' ', slider))).toBeNull()
  })
})

describe('isEditableTarget', () => {
  it('body → false', () => {
    expect(isEditableTarget(keyEvent(' ', document.body))).toBe(false)
  })

  it('input/textarea/contenteditable → true', () => {
    expect(isEditableTarget(keyEvent(' ', document.createElement('input')))).toBe(true)
    expect(isEditableTarget(keyEvent(' ', document.createElement('textarea')))).toBe(true)
    const div = document.createElement('div')
    div.contentEditable = 'true'
    expect(isEditableTarget(keyEvent(' ', div))).toBe(true)
  })

  it('div[role=slider] → true', () => {
    const slider = document.createElement('div')
    slider.setAttribute('role', 'slider')
    expect(isEditableTarget(keyEvent('ArrowLeft', slider))).toBe(true)
  })
})

describe('KEYBOARD_SHORTCUTS', () => {
  it('覆盖 feature 表全部 7 个按键', () => {
    const keys = Object.keys(KEYBOARD_SHORTCUTS)
    for (const expected of [' ', 'ArrowLeft', 'ArrowRight', 'R', 'S', '1', '2']) {
      expect(keys).toContain(expected)
    }
    // 每个映射都是合法动作
    const actions = new Set<KeyboardAction>(Object.values(KEYBOARD_SHORTCUTS))
    for (const a of actions) {
      expect(['playPause', 'seekBack', 'seekForward', 'toggleReference', 'takeScreenshot', 'modeUserOnly', 'modeDualCurve']).toContain(a)
    }
  })
})
