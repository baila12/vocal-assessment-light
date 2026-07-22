/**
 * useGsap — GSAP 动画 composable
 *
 * 使用 gsap.context() 自动清理所有动画
 * 尊重 prefers-reduced-motion
 */

import { ref, onBeforeUnmount, type Ref } from 'vue'
import gsap from 'gsap'

export function useGsap(scope?: Ref<HTMLElement | null>) {
  const prefersReducedMotion = ref(false)
  let ctx: gsap.Context | null = null

  // 检测 reduced motion 偏好
  if (typeof window !== 'undefined') {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    prefersReducedMotion.value = mq.matches
    mq.addEventListener('change', (e) => {
      prefersReducedMotion.value = e.matches
    })
  }

  function createContext(): gsap.Context {
    ctx = gsap.context(() => {}, scope?.value || undefined)
    return ctx
  }

  function getContext(): gsap.Context {
    if (!ctx) {
      ctx = createContext()
    }
    return ctx
  }

  /** 安全地创建动画 — 尊重 reduced motion */
  function animate(
    target: gsap.TweenTarget,
    vars: gsap.TweenVars,
  ): gsap.core.Tween {
    const context = getContext()
    if (prefersReducedMotion.value) {
      return gsap.set(target, vars)
    }
    return context.add(() => gsap.to(target, vars))
  }

  /** 数字滚动动画 (countUp) */
  function countUp(
    target: Ref<number>,
    endValue: number,
    duration = 1.2,
  ): gsap.core.Tween {
    const obj = { val: target.value }
    return animate(obj, {
      val: endValue,
      duration: prefersReducedMotion.value ? 0 : duration,
      ease: 'power2.out',
      onUpdate: () => {
        target.value = Math.round(obj.val * 10) / 10
      },
    })
  }

  /** 交错入场动画 */
  function staggerIn(
    elements: string | Element[],
    vars?: gsap.TweenVars,
  ): gsap.core.Tween {
    return animate(elements, {
      opacity: 0,
      y: 20,
      duration: 0.4,
      stagger: 0.08,
      ...vars,
    })
  }

  onBeforeUnmount(() => {
    if (ctx) {
      ctx.revert()
      ctx = null
    }
  })

  return {
    prefersReducedMotion,
    createContext,
    getContext,
    animate,
    countUp,
    staggerIn,
  }
}
