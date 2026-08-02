/**
 * useGsap — GSAP 动画 composable (Vue 3)
 *
 * 遵循 GSAP 官方 Vue 3 最佳实践:
 * - gsap.context(scope) 隔离选择器 + 自动清理
 * - gsap.matchMedia() 响应 reduced-motion + 响应式断点
 * - compositor-only 属性 (autoAlpha, x, y, scale, rotation)
 *
 * 用法:
 *   const { tl, enterFrom } = useGsap(container)
 *   onMounted(() => {
 *     enterFrom('.card', { y: 24, stagger: 0.08 })
 *   })
 */
import { ref, onBeforeUnmount, type Ref } from 'vue'
import { gsap } from 'gsap'

export interface UseGsapOptions {
  /** 自定义动画时长 (默认 0.4s) */
  duration?: number
  /** 自定义 ease (默认 power2.out) */
  ease?: string
}

export function useGsap(
  scope?: Ref<HTMLElement | null>,
  opts: UseGsapOptions = {},
) {
  const { duration = 0.4, ease = 'power2.out' } = opts

  // ---- reduced-motion 检测 ----
  const prefersReducedMotion = ref(false)
  let mm: gsap.MatchMedia | null = null

  if (typeof window !== 'undefined') {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    prefersReducedMotion.value = mq.matches

    mm = gsap.matchMedia()
    mm.add('(prefers-reduced-motion: reduce)', () => {
      prefersReducedMotion.value = true
    })
    mm.add('(prefers-reduced-motion: no-preference)', () => {
      prefersReducedMotion.value = false
    })
  }

  // ---- gsap.context 隔离 ----
  let ctx: gsap.Context | null = null

  function getCtx(): gsap.Context {
    if (!ctx) {
      ctx = gsap.context(() => {}, scope?.value || undefined)
    }
    return ctx
  }

  // ---- 安全动画 (尊重 reduced-motion) ----
  function safeVars(vars: gsap.TweenVars): gsap.TweenVars {
    if (prefersReducedMotion.value) {
      return { ...vars, duration: 0, stagger: 0, delay: 0 }
    }
    return vars
  }

  // ---- 核心方法 ----

  /** 创建 Timeline (自动注册到 context) */
  function tl(defaults?: gsap.TimelineVars): gsap.core.Timeline {
    const timeline = gsap.timeline({
      defaults: { ease, duration, ...defaults },
    })
    getCtx().add(() => timeline)
    return timeline
  }

  /** 从隐藏状态入场 (gsap.from) */
  function enterFrom(
    target: gsap.TweenTarget,
    vars: gsap.TweenVars = {},
  ): gsap.core.Tween {
    const tween = gsap.from(target, safeVars({
      autoAlpha: 0,
      y: 20,
      duration,
      ease,
      ...vars,
    }))
    getCtx().add(() => tween)
    return tween
  }

  /** 交错入场 */
  function staggerIn(
    target: gsap.TweenTarget,
    vars: gsap.TweenVars = {},
  ): gsap.core.Tween {
    const tween = gsap.from(target, safeVars({
      autoAlpha: 0,
      y: 20,
      duration: 0.4,
      stagger: 0.08,
      ease,
      ...vars,
    }))
    getCtx().add(() => tween)
    return tween
  }

  /** 从左侧滑入 */
  function slideInLeft(
    target: gsap.TweenTarget,
    vars: gsap.TweenVars = {},
  ): gsap.core.Tween {
    const tween = gsap.from(target, safeVars({
      autoAlpha: 0,
      x: -30,
      duration,
      ease,
      ...vars,
    }))
    getCtx().add(() => tween)
    return tween
  }

  /** 从右侧滑入 */
  function slideInRight(
    target: gsap.TweenTarget,
    vars: gsap.TweenVars = {},
  ): gsap.core.Tween {
    const tween = gsap.from(target, safeVars({
      autoAlpha: 0,
      x: 30,
      duration,
      ease,
      ...vars,
    }))
    getCtx().add(() => tween)
    return tween
  }

  /** 缩放弹入 */
  function scaleIn(
    target: gsap.TweenTarget,
    vars: gsap.TweenVars = {},
  ): gsap.core.Tween {
    const tween = gsap.from(target, safeVars({
      autoAlpha: 0,
      scale: 0.9,
      duration,
      ease: 'back.out(1.7)',
      ...vars,
    }))
    getCtx().add(() => tween)
    return tween
  }

  /** 数字滚动动画 (countUp) */
  function countUp(
    target: Ref<number>,
    endValue: number,
    animDuration = 1.2,
  ): gsap.core.Tween {
    const obj = { val: target.value }
    const tween = gsap.to(obj, safeVars({
      val: endValue,
      duration: animDuration,
      ease: 'power3.out',
      onUpdate: () => {
        target.value = Math.round(obj.val * 10) / 10
      },
    }))
    getCtx().add(() => tween)
    return tween
  }

  /** 脉冲动画 (repeat) */
  function pulse(
    target: gsap.TweenTarget,
    vars: gsap.TweenVars = {},
  ): gsap.core.Tween {
    const tween = gsap.to(target, safeVars({
      scale: 1.05,
      duration: 0.6,
      repeat: -1,
      yoyo: true,
      ease: 'sine.inOut',
      ...vars,
    }))
    getCtx().add(() => tween)
    return tween
  }

  // ---- 生命周期清理 ----
  onBeforeUnmount(() => {
    ctx?.revert()
    ctx = null
    mm?.revert()
    mm = null
  })

  return {
    prefersReducedMotion,
    getCtx,
    tl,
    enterFrom,
    staggerIn,
    slideInLeft,
    slideInRight,
    scaleIn,
    countUp,
    pulse,
  }
}
