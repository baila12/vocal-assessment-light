# 前端 GSAP 动效系统 + 布局重构设计 v3.0

> ⚠️ **已废弃**: 本文档描述 v5.x Vanilla JS 前端 (`web/static/js/`) 的动效设计。当前 v7.13 前端已迁移至 Vue 3 + Element Plus (`frontend/src/`)，动效通过 GSAP 3.15 npm 包 + `useGsap()` composable + `<Transition>` 组件实现。本文档保留作为历史参考，部分 GSAP 动画原则仍适用于 Vue 3 实现。v7.8 已完成全站 GSAP 动效重建 (6 页面覆盖，prefers-reduced-motion 双重保护)；v7.12 已迁移 BDD animations.feature 到 Vue 3 data-test 选择器 (7 PASS + 9 XFAIL，无 UI 场景带理由标注)；v7.13 已新增实时音准对比画布 (PitchComparisonCanvas 偏差着色/滚动 + CompareView 双轨叠加)。
>
> 更新: 2026-06-11 | 基于 BDD/TDD/SDD 三驱动 + GSAP 系列技能官方规范

---

## 目录

1. [设计目标](#1-设计目标)
2. [当前问题分析](#2-当前问题分析)
3. [GSAP 技能参考总览](#3-gsap-技能参考总览)
4. [Animation Controller 层](#4-animation-controller-层)
5. [预设动画方案](#5-预设动画方案)
6. [页面布局重构](#6-页面布局重构)
7. [实时音高页专项设计](#7-实时音高页专项设计)
8. [组件级动画策略](#8-组件级动画策略)
9. [BDD 验收场景](#9-bdd-验收场景)
10. [实施计划](#10-实施计划)

---

## 1. 设计目标

| 维度 | 目标 |
|------|------|
| **用户体验** | 每个页面切换、评分展示、操作反馈都有丝滑 GSAP 动画，但不是为了动而动 |
| **布局合理** | 消除大面积空白、不合理的大模块/按钮，每个元素大小经过编排 |
| **可测试性** | 动画行为有 BDD 场景覆盖，JS 逻辑有单元测试 |
| **可维护性** | 动画配置统一在 Controller 层，页面不再散落 GSAP 代码 |
| **包容性** | prefers-reduced-motion 完全支持 |
| **性能** | 所有动画在 compositor 线程运行；入场 < 600ms，微交互 < 300ms；60fps 目标 |

## 2. 当前问题分析

### 2.1 布局问题

| 页面 | 问题 | 严重度 |
|------|------|--------|
| **首页 (HomePage)** | 侧边栏 320px 固定，右侧大量留白；welcome-section 顶部 padding 32px + 大 emoji 48px 占用首屏空间 | P1 |
| **演唱页 (SingPage)** | 实时评分面板 4 项横向铺开 → 实际数值 "--" 时大片空白；Canvas 高度 200px 相对较小相比控制区 | P1 |
| **报告页 (ReportPage)** | 总分环形 + 五维进度条 + 雷达图 + 音高曲线纵向堆叠，页面过长，缺少 Tab 切换或折叠 | P2 |
| **设置页 (SettingsPage)** | 未知，需检查 | P2 |
| **对比页 (ComparePage)** | compare-grid 双列在桌面合理，但差距指标卡片 padding:12px 显示偏挤 | P2 |

### 2.2 动效问题

| 问题 | 说明 | 严重度 |
|------|------|--------|
| 动画代码分散 | 每个 Page 的 mount() 中各自写 gsap.timeline()，重复模式多 | P1 |
| 缺少统一出场动画 | Router 切换时只有旧页 fadeOut，新页无明显入场 | P1 |
| 无动画队列控制 | 快速切换页面时动画冲突（旧的动画未 kill） | P1 |
| prefers-reduced-motion | 仅 CSS animations.css 中有媒体查询，GSAP 侧无控制 | P1 |
| 没有 Timeline 默认配置 | easing/duration 各页面不一致 | P2 |


## 3. GSAP 技能参考总览

本设计充分利用以下 GSAP 官方技能：

| 技能 | 核心内容 | 本设计中的应用 |
|------|---------|---------------|
| **gsap-core** | gsap.to()/from()/fromTo()，easing，stagger，immediateRender | 基础动画实现，全局默认配置 |
| **gsap-timeline** | Timeline 创建/嵌套/position 参数/labels | Animation Controller 使用 Timeline 统一编排入场/出场 |
| **gsap-performance** | 优先 transform + opacity，will-change，quickTo()，批量读写 | 所有动画遵循 compositor-only 原则 |
| **gsap-utils** | clamp，mapRange，normalize，random，snap，wrap | 评分映射，实时数据归一化显示 |
| **gsap-plugins** | Flip（列表布局变化动画），Draggable（可拖拽对比），ScrollToPlugin | 页面内卡片重排、对比滑块、滚动到结果区域 |
| **gsap-scrolltrigger** | 滚动触发动画，scrub，pinning | 报告页长滚动场景，评分卡片滚动激发（移动端） |
| **gsap-react** | useGSAP hook，refs，cleanup | 暂不涉及，本设计纯 vanilla，但保留未来 React 化接口 |

### 3.1 核心性能准则（来自 gsap-performance）

`javascript
// 全局默认
gsap.defaults({
  ease: 'power2.out',
  overwrite: 'auto'
});
gsap.config({ force3D: true });

// 禁止动画的属性：width, height, top, left, margin, padding（触发 layout）
// 始终使用：x, y, scale, rotation, opacity（保持在 compositor 层）
// 大量元素：使用 stagger 而非逐个 tween
// 频繁更新：使用 gsap.quickTo() 避免创建大量 tween
`

## 4. Animation Controller 层

### 4.1 架构位置

`
app.js → 初始化 AnimationController → 挂载到 window.__ac
       → 每个 Page 通过 BaseComponent.animateIn() 自动调用
       → Router 切换时由 router 调用 ac.leave() + ac.enter()
`

### 4.2 核心 API

`javascript
class AnimationController {
  // ─── 配置 ───
  enabled = true;              // 全局开关（绑定 reduced-motion）
  defaults = {                 // 全局默认
    ease: 'power2.out',
    duration: 0.4,
    overwrite: 'auto'
  };

  // ─── 页面级动画 ───
  enter(el, options = {})      // 页面入场：预设自动匹配
  leave(el, options = {})      // 页面出场：预设自动匹配

  // ─── 元素级动画 ───
  stagger(elements, options)   // Stagger 入场
  countUp(el, target, opts)    // 数字滚动（用 textContent + snap）
  fillBar(el, percent, opts)   // 进度条填充（用 scaleX）
  reveal(el, options)          // 元素 reveal（clip-path 或 opacity）

  // ─── 微交互 ───
  pulse(el, options)           // 脉冲提示
  shake(el, options)           // 抖动（错误提示）
  highlight(el, options)       // 高亮闪烁

  // ─── 控制 ───
  setEnabled(state)            // 开关
  killAll()                    // 杀死所有动画
  registerPreset(name, fn)     // 注册自定义预设
}
`

### 4.3 prefers-reduced-motion 策略

`javascript
const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');

// 初始化
ac.setEnabled(!motionQuery.matches);

// 监听变化
motionQuery.addEventListener('change', (e) => {
  ac.setEnabled(!e.matches);
  if (e.matches) {
    // 直接跳到最终状态
    document.querySelectorAll('.page, .card, .btn').forEach(el => {
      gsap.set(el, { clearProps: 'all' });
    });
  }
});
`

当 disabled 时：
- enter() 直接设置 opacity:1, transform:none，不产生 tween
- leave() 直接 remove 元素，不产生 tween
- countUp() 直接设置最终 textContent
- stagger() 直接设置所有元素最终状态


## 5. 预设动画方案

### 5.1 预设总表

| 预设 ID | 适用场景 | 效果 | gsap 实现 |
|---------|---------|------|-----------|
| page-enter | 页面入场（默认） | opacity 0→1, y: 8→0, 0.4s, power2.out | fromTo |
| page-leave | 页面出场（默认） | opacity 1→0, y: 0→-8, 0.2s, power2.in | to |
| page-enter-up | 从下方进入的页面 | opacity 0→1, y: 24→0, 0.5s, power3.out | fromTo |
| stagger-cards | 卡片列表 | y: 20→0, stagger: 0.08, 0.45s, power2.out | fromTo + stagger |
| stagger-list | 文本列表行 | x: -12→0, stagger: 0.05, 0.3s, power2.out | fromTo + stagger |
| score-reveal | 评分组件 | 数字滚动 + 进度条 stagger + 环形动画串联 | Timeline |
| counter | 数字滚动 | textContent 0→target, snap, 1.2s, power3.out | to + snap |
| ar-fill | 进度条填充 | scaleX 0→1, 0.8s, power2.out | to |
| slide-left | 从右侧进入的面板 | x: 30→0, opacity 0→1, 0.35s | fromTo |
| slide-right | 从左侧进入的面板 | x: -30→0, opacity 0→1, 0.35s | fromTo |
| modal-mask | 模态背景 | opacity 0→0.5, 0.2s | to |
| modal-content | 模态内容弹出 | scale: 0.92→1, opacity 0→1, 0.3s, back.out(2) | fromTo |
| 	ooltip | 工具提示 | y: -4→0, opacity 0→1, 0.15s | fromTo |
| pulse | 提示脉冲动画 | scale 1→1.05→1, 0.6s, repeat: 2 | to + yoyo |
| shake | 输入错误抖动 | x: -4→4→-4→4→0, 0.4s | fromTo + keyframes |

### 5.2 预设注册示例

`javascript
// presets.js
export const presets = {
  'page-enter': (el, opts = {}) => ({
    from: { opacity: 0, y: 8 },
    to: { opacity: 1, y: 0, duration: opts.duration ?? 0.4, ease: 'power2.out' }
  }),
  'stagger-cards': (els, opts = {}) => ({
    from: { opacity: 0, y: 20 },
    to: { opacity: 1, y: 0, stagger: opts.stagger ?? 0.08, duration: opts.duration ?? 0.45, ease: 'power2.out' }
  }),
  // ...
};
`

## 6. 页面布局重构

### 6.1 首页 (HomePage)

**当前问题：**
- welcome-section 38% 首屏空间被浪费（大 emoji + 标题 + 说明 + 3个 tag）
- 侧边栏 320px 固定宽度，右侧大量空白
- action-card 两列布局，但"导入音频"和"快速录音"两个卡片内 padding 24px 偏大
- mode-selector 两列选项的 padding 16px 偏大

**重构方案：**

`
┌─────────────────────────────────────────────────┐
│  ┌───┐ 欢迎回来  🎵 专业声乐评估                │
│  │LOGO│ 上次分析: 2026-06-10                    │
│  └───┘        [特征标签] x 3                    │
├───────────────────────┬─────────────────────────┤
│  ┌─────────────────┐  │  ┌───────────────────┐  │
│  │  导入音频        │  │  │ 使用说明           │  │
│  │  MP3 WAV FLAC   │  │  │ 1. 导入...         │  │
│  └─────────────────┘  │  │ 2. 点击...         │  │
│  ┌─────────────────┐  │  │ 3. 查看...         │  │
│  │  快速录音        │  │  │ 4. 根据...         │  │
│  │  → 实时演唱      │  │  └───────────────────┘  │
│  └─────────────────┘  │  ┌───────────────────┐  │
│  ┌─────────────────┐  │  │ 五维评分           │  │
│  │  对比分析        │  │  │ 音准 35%          │  │
│  │                  │  │  │ 节奏 25%          │  │
│  └─────────────────┘  │  │ ...               │  │
│                       │  └───────────────────┘  │
│  模式选择 [快速] [专业]│                         │
│  分析进度条            │                         │
└───────────────────────┴─────────────────────────┘
`

**具体调整：**
1. welcome-section 顶部 padding 从 32px 缩减为 16px，emoji 从 48px 缩减为 32px
2. 侧边栏从 320px 缩减为 280px
3. action-card 的 padding 从 24px 缩减为 16~18px
4. 引入"历史记录预览"替代部分侧边栏空白（显示最近 3 条分析记录摘要）
5. 模式选择器的两列选项 padding 从 16px 缩减为 12px


### 6.2 演唱页 (SingPage)

这是实时音高+核心交互页面，需要最精细的设计。

**当前问题：**
- 实时评分面板 4 项在无录音时显示 "--"，占据一整行视觉重量
- 录音按钮 64x64 偏大（与移动端标准 48~56px 不符）
- Canvas 200px 高度相比下方控制区比例失调
- 歌曲信息与 header 之间 text-align:center 大段空白

**重构方案：**

`
┌──────────────────────────────────────────────┐
│  ← 返回     🎤 实时演唱     [参考曲目 ▼]     │  ← 上导航
├──────────────────────────────────────────────┤
│                                               │
│  ┌──────────────────────────────────────────┐ │
│  │         音高对比实时显示区                 │ │
│  │  ┌────────────────────────────────────┐  │ │
│  │  │       Canvas 音高曲线               │  │ │
│  │  │  (参考: 蓝色虚线 | 实时: 黄色实线)   │  │ │
│  │  │                                      │  │ │
│  │  │      [命中反馈动画 / 连击飘字]        │  │ │
│  │  └────────────────────────────────────┘  │ │
│  │                                          │ │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐   │ │
│  │  │ 音高  │ │ 音量  │ │ 命中率│ │ 时长  │   │ │
│  │  │ A3#   │ │ -12dB │ │ 87%  │ │ 01:23│   │ │
│  │  └──────┘ └──────┘ └──────┘ └──────┘   │ │
│  │       四组指标：仅录音时激活显示           │ │
│  └──────────────────────────────────────────┘ │
│                                               │
│  ┌──────────────────────────────────────────┐ │
│  │        [ 🔴 开始录音 ]                    │ │
│  │        或 [ ⏹ 停止录音 ]                  │ │
│  │        [ 📤 上传分析结果]                  │ │
│  └──────────────────────────────────────────┘ │
│                                               │
│  音乐律动背景 (Canvas 或 GSAP 粒子效果)       │
│                                               │
├──────────────────────────────────────────────┤
│  底部导航                                      │
└──────────────────────────────────────────────┘
`

**具体调整：**

| 项目 | 当前 | 调整后 |
|------|------|--------|
| Canvas 高度 | 200px | 280px (提升显示空间) |
| 录音按钮 | 64x64 (圆形) | 56x56 (圆形) |
| 评分面板布局 | flex 水平 4 项 | grid 2x2 (手机)/ 4 项水平(桌面) |
| 指标值字号 | 24px | 20px (桌面) / 18px (手机) |
| 无数据状态 | "--" 显示 | 灰色占位文本 "等待演唱..." |
| 顶部 header | margin-bottom 20px | 缩减为 12px |
| 实时指标面板 | margin-bottom 20px | 缩减为 12px |

**GSAP 动画序列：**

`
1. 页面入场：header→Canvas→控制面板 (Timeline + stagger 0.1)
2. 开始录音：按钮 pulse 动画 + 脉冲光环 (repeat: -1)
3. 实时音准命中 → hitFeedback() 弹出 "+PERFECT" 飘字
4. 连击 → comboBounce() 数字跳动 + 背景闪光
5. 停止录音 → 按钮 transition + 结果显示动画
6. 录音时长 → 数字计数器 (countUp 风格)
`

### 6.3 报告页 (ReportPage)

**当前问题：**
- 总分环形 + 五维进度条 + 雷达图 + 音高曲线 + 建议纵向堆叠，页面过长
- 缺少可折叠的章节组织

**重构方案：**

`
┌──────────────────────────────────────────────┐
│  ← 返回     📊 分析报告                       │
├──────────────────────────────────────────────┤
│                                               │
│  ┌──────────────────────────────────────────┐ │
│  │          总分 88.5                        │ │
│  │          [环形 ScoreRing]   "良好"        │ │
│  │          音准:82 节奏:90 ... (五维mini)   │ │
│  └──────────────────────────────────────────┘ │
│                                               │
│  ┌──────────────────────────────────────────┐ │
│  │  [📊 五维评分] [🎯 雷达图] [📈 音高曲线] │ │
│  │  ──── Tab 切换区 ────                    │ │
│  │  当前 Tab 内容区域                        │ │
│  └──────────────────────────────────────────┘ │
│                                               │
│  ┌──────────────────────────────────────────┐ │
│  │  [💡 改进建议] (可折叠)                   │ │
│  │  1. 音准方面...                          │ │
│  │  2. 节奏方面...                          │ │
│  └──────────────────────────────────────────┘ │
│                                               │
│  ┌──────────────────────────────────────────┐ │
│  │  操作栏: [再次分析] [对比] [分享]         │ │
│  └──────────────────────────────────────────┘ │
└──────────────────────────────────────────────┘
`

**关键调整：**

| 项目 | 当前 | 调整后 |
|------|------|--------|
| 总分区域 | 独立区块 | 精简为紧凑 header + ScoreRing |
| 五维/雷达/音高 | 3 个独立 card 纵向堆叠 | Tab 切换：一个 card 内切换 3 个视图 |
| 改进建议 | 独立的 card | 可折叠手风琴 |
| 页面长度 | ~1200px | ~700px (首屏全可见) |


## 7. 实时音高页专项设计

### 7.1 Canvas 音高曲线实时绘制 + GSAP 动效

实时音高显示是将声乐评估"做专业"的核心。设计原则：

1. **参考音高**（如有标准曲目）：蓝色半透明虚线，预先绘制完整曲线
2. **演唱音高**：明亮黄色实线，从左向右实时推进
3. **音准命中反馈**：当 |演唱 - 参考| < 阈值 → 命中特效（GSAP pulse）
4. **音高指示器**：右侧显示当前音名（如 A3, C4#），带 GSAP yoyo 微动

`javascript
// 实时画线 + GSAP 命中反馈（伪代码）
function onPitchDetected(freq, refFreq) {
  // 1. 绘制到 Canvas
  drawPitchPoint(ctx, freq, timestamp);

  // 2. 计算偏差
  const diff = Math.abs(freq - refFreq);
  const isHit = diff < threshold;

  // 3. 命中 → GSAP 动画反馈
  if (isHit && hitEl) {
    gsap.fromTo(hitEl, { opacity: 1, scale: 0.5 },
      { opacity: 0, scale: 1.5, duration: 0.4, ease: 'power2.out' });
  }

  // 4. 更新实时指标（使用 gsap.quickTo 避免频繁创建 tween）
  pitchValueTo(freq);
  volumeValueTo(volume);
}
`

### 7.2 录音按钮交互设计

`
状态: 待机 → 悬停 → 开始录音 → 录音中 → 停止 → 结果
动画:      scale  pulse     pulseCSS  停止动画  结果显示
          1.03   (repeat   缩放回1    入
                -1)                  场
`

录音按钮三种状态的 GSAP 实现：

`javascript
// 待机 → 录音中
function startRecordingAnimation(btnEl) {
  gsap.to(btnEl, {
    scale: 1,
    backgroundColor: '#ef4444',
    boxShadow: '0 0 0 0 rgba(239,68,68,0.4)',
    duration: 0.3,
    ease: 'power2.out'
  });
  // 脉冲光环
  gsap.fromTo(btnEl, { boxShadow: '0 0 0 0 rgba(239,68,68,0.4)' },
    { boxShadow: '0 0 0 12px rgba(239,68,68,0)', duration: 1.5, repeat: -1 });
}

// 录音中 → 停止
function stopRecordingAnimation(btnEl) {
  gsap.killTweensOf(btnEl);
  gsap.to(btnEl, {
    scale: 1,
    backgroundColor: 'var(--bg-elevated)',
    borderColor: '#ef4444',
    boxShadow: 'none',
    duration: 0.25,
    ease: 'power2.out'
  });
}
`

### 7.3 实时评分面板布局

四个指标使用 CSS grid epeat(4, 1fr) 桌面 / epeat(2, 1fr) 手机。每个指标单元：

`
┌─────────────┐
│ 音高         │  ← 标签 (11px, text-muted)
│ A3#          │  ← 值 (20px, 加粗, 色彩区分)
│ - 参考:B3    │  ← 副信息 (11px, text-muted) 仅录音时显示
└─────────────┘
`

- 未录音时：值显示 "· · ·"，副信息隐藏 → 面板高度收缩
- 录音时：值动画 transition (gsap.quickTo)
- 命中率高（>80%）：值颜色 green；低（<50%）：red


## 8. 组件级动画策略

### 8.1 BaseComponent 变更

`diff
class BaseComponent {
  async mount(params) {
    this.render(params);
    this.bindEvents();
+   this.animateIn();
  }

+ animateIn() {
+   const ac = window.__animationController;
+   if (ac && this.el) {
+     ac.enter(this.el, { preset: this.constructor.animationPreset || 'page-enter' });
+   }
+ }

  async beforeUnmount() {
+   const ac = window.__animationController;
+   if (ac && this.el) {
+     await ac.leave(this.el, { preset: this.constructor.animationPreset || 'page-leave' });
+   } else {
      if (this.el && typeof gsap !== 'undefined') {
        await gsap.to(this.el, { opacity: 0, duration: 0.15 }).then();
      }
+   }
  }
}
`

每个 Page 可以通过静态属性指定动画预设：

`javascript
export class SingPage extends BaseComponent {
  static animationPreset = 'page-enter-up';  // 从下方进入
  // ...
}

export class ReportPage extends BaseComponent {
  static animationPreset = 'score-reveal';   // 评分组件专属动画链
  // ...
}
`

### 8.2 Router 集成

`javascript
// router.js 中的 hash change 处理
async #handleRoute() {
  // ... 匹配路由 ...

  // 出场动画
  if (this.#currentPage) {
    await this.#currentPage.beforeUnmount();
  }

  // 挂载新页面
  const page = new PageClass(this.#container, { store, router, api });
  this.#currentPage = page;
  await page.mount(route.params);
}
`

### 8.3 组件级微交互对照表

| 组件 | 交互事件 | 动画效果 | 实现 |
|------|---------|---------|------|
| btn | click | scale 1→0.97→1, 0.15s | gsap.to + yoyo |
| btn | hover | scale 1→1.03, 0.15s | gsap.to |
| card | hover | y: 0→-2, shadow 增强 | gsap.to |
| toast | 出现 | y: -20→0, opacity 0→1, 0.3s, bounce | gsap.fromTo |
| toast | 消失 | y: 0→-20, opacity 1→0, 0.2s | gsap.to |
| modal | 打开 | mask opacity 0→0.5, content scale 0.92→1 | Timeline |
| modal | 关闭 | content scale 1→0.92, mask opacity 0.5→0, 0.15s | Timeline |
| progressBar | 更新 | scaleX width%, 0.3s, power2.out | gsap.to |
| scoreRing | 展示 | 弧线从 0 到 target, 1s, power3.out | gsap.to + attr |
| pitchCurve | 实时更新 | 新数据点从左向右推进 | Canvas 原生绘制 |
| comb 连击 | 增加 | 数字弹跳 scale 1→1.3→1, 0.3s | gsap.timeline + yoyo |
| nav dot 指示 | 切换 | dot x 滑动 0.2s + active color 渐变 | gsap.to |

## 9. 动画性能合约 (Performance Contract)

### 9.1 帧率要求

| 场景 | 最低 FPS | 目标 FPS | 降级后 FPS | 测量方式 |
|------|---------|---------|-----------|---------|
| 页面入场动画 | 30 | 60 | 即时显示 (跳过) | `requestAnimationFrame` 采样 |
| 评分数字滚动 | 30 | 60 | 直接设置 textContent | DevTools FPS |
| Canvas 实时音高 | 30 | 60 | 降低采样率 + 关抗锯齿 | Canvas `getContext` 测量 |
| 脉冲/抖动微交互 | 30 | 60 | 跳过 | 肉眼 + BDD |
| Toast 弹出/消失 | 30 | 60 | 即时显示/移除 | BDD timing |
| 模态打开/关闭 | 30 | 60 | 即时显示/移除 | BDD timing |

### 9.2 动画时长限制

| 动画类型 | 最小时长 | 默认时长 | 最大时长 | 说明 |
|---------|---------|---------|---------|------|
| 页面入场 | 0.3s | 0.4s | 0.6s | 超过 0.6s 用户感觉慢 |
| 页面出场 | 0.15s | 0.2s | 0.3s | 出场应比入场快 |
| 卡片 stagger | 0.3s | 0.45s | 0.8s | 取决于卡片数量 |
| 评分数字滚动 | 0.6s | 1.0s | 1.5s | 长数字可适当延长 |
| 进度条填充 | 0.3s | 0.6s | 1.0s | 配合数字滚动 |
| 微交互 (按钮/图标) | 0.1s | 0.15s | 0.3s | 反馈必须即时 |
| Toast 显示 | 0.2s | 0.3s | 0.4s | 不阻塞操作 |
| 脉冲动画 | 0.4s | 0.6s | 1.0s | repeat: 2 或 infinite |

### 9.3 GC 与内存

| 规则 | 说明 |
|------|------|
| **Timeline 自动清理** | 每个页面挂载时创建新 Timeline，`beforeUnmount` 时 `tl.kill()` |
| **gsap.context() 隔离** | 页面级动画使用 `gsap.context()` 包裹，unmount 时 `ctx.revert()` |
| **quickTo 复用** | 实时更新的属性 (音高值、音量值) 使用 `gsap.quickTo()` 而非每次创建新 tween |
| **无内存泄漏** | 连续 20 次页面切换后，GSAP 实例数应保持稳定 (≤ 每个页面的 Timeline 数 + stagger 数) |
| **Canvas 数据清理** | 音高曲线数据点 > 5000 时，按 2:1 降采样，保持最近 1000 个点高精度 |

### 9.4 prefers-reduced-motion 完整覆盖

```
当 prefers-reduced-motion: reduce 时：
  - AnimationController.setEnabled(false) 
  - 所有 enter() → 直接 gsap.set(el, {opacity: 1, clearProps: "transform"})
  - 所有 leave() → 直接 remove 元素 (无动画)
  - 所有 countUp() → 直接设置 textContent 为目标值
  - 所有 stagger() → 直接 gsap.set(els, {opacity: 1, y: 0})
  - 所有微交互 (pulse/shake/highlight) → 跳过
  - Canvas 实时绘制 → 保持功能，仅跳过装饰性粒子效果
  - 路由切换 → 瞬间切换，不等待
```

### 9.5 性能回归检测

| 检测项 | 方法 | 阈值 | 频率 |
|--------|------|------|------|
| 动画帧率 | Chrome DevTools Performance 录制 | ≥ 30fps | 每次 PR |
| 页面入场耗时 | `performance.now()` BDD 断言 | < 600ms | 每次 BDD 运行 |
| 内存增长 | `performance.memory.usedJSHeapSize` diff | < 50MB / 20 次切换 | 手动测试 |
| 主线程阻塞 | Long Tasks API | 无 > 50ms 的 task | Lighthouse CI |
| GSAP 实例泄漏 | `gsap.globalTimeline.getChildren().length` | 稳定不增长 | 手动测试 |

## 10. BDD 验收场景

### 9.1 animation.feature（新增场景）

`gherkin
@animation
Feature: GSAP 动效系统

  Scenario: 页面切换动画
    Given 用户在首页
    When 导航到演唱页
    Then 演唱页应在 600ms 内完成入场动画
    And 旧页面应先淡出再显示新页面

  Scenario: 录音按钮交互动画
    Given 用户在演唱页
    When 点击「开始录音」按钮
    Then 按钮应显示脉冲光环动画
    And 实时评分面板应激活显示

  Scenario: 评分数字滚动
    Given 报告页面已加载评分数据
    When 评分数据就绪
    Then 总分应从 0 滚动到目标值，时长约 1-1.5s
    And 五维进度条应依次填充

  Scenario: prefers-reduced-motion
    Given 用户系统启用了「减少动效」
    When 导航到任何页面
    Then 所有 GSAP 动画应跳过
    And 页面内容应立即显示

  Scenario: 快速切换页面
    Given 用户快速切换导航
    When 在 300ms 内触发两次导航
    Then 只有最后一次导航的动画应执行
    And 不应出现页面元素闪烁
`

### 9.2 单元测试覆盖

`
tests/unit/
  test_animation_controller.js    ← 新增
    ✓ AnimationController 初始化
    ✓ enter() 创建正确 tween
    ✓ leave() 创建正确 tween
    ✓ setEnabled(false) 跳过所有动画
    ✓ prefers-reduced-motion 自动检测
    ✓ 预设正确匹配
    ✓ stagger() 创建 stagger 参数

tests/bdd/
  steps/test_spa_steps.py         ← 增加动画步骤
    ✓ step: 页面应在 {time}ms 内完成入场动画
    ✓ step: 按钮应显示脉冲光环动画
    ✓ step: 总分应从 0 滚动到目标值
`



## 附录 A：GSAP 版本与依赖

> **注意**: 以下描述的是 v5.x 旧前端 (Vanilla JS) 的 GSAP 加载方式。v7.11 前端已改用 npm 包 (`"gsap": "^3.15.0"`) 并通过 `useGsap()` composable 管理。

旧前端曾使用 `web/static/lib/gsap/gsap.min.js`。如需 ScrollTrigger 插件：

`html
<!-- 当前：仅 core -->
<script src=\"/lib/gsap/gsap.min.js\"></script>
<!-- 如需插件 -->
<script src=\"/lib/gsap/ScrollTrigger.min.js\"></script>
`

注册方式：
`javascript
gsap.registerPlugin(ScrollTrigger, ScrollToPlugin);
`

## 附录 B：动画设计原则（BDD 可测试风格）

**原则 1：动画服务于流程，不是装饰**
每个动画必须有明确目的：引导注意、确认操作、提供反馈。如果去掉动画不影响用户完成流程，则不需要。

**原则 2：动画不可阻塞交互**
所有动画使用异步 Promise，但导航/操作无需等待动画完成。动画时长不可超过 600ms（页面入场）/ 300ms（微交互）。

**原则 3：减少动效模式必须完整支持**
AnimationController.setEnabled(false) 时：所有元素直接显示最终状态，不产生任何 tween。

**原则 4：Timeline 优于分散的 tween**
一个页面只应有一个 Timeline（由 Controller 管理）。避免手动控制多个 tween 的先后顺序。
