/**
 * 声乐评估系统 — SPA 主入口 (v3.0)
 *
 * 初始化顺序 (对齐 Vue createApp 模式):
 *   services → context → router → navigation → mount
 *
 * v7.0 迁移映射:
 *   createAppServices()  → createApp() + plugin installs
 *   createAppContext()   → app.provide()
 *   router.start()       → app.mount('#app')
 *   window.__appContext  → inject('appContext')
 *
 * @version 3.0 (v5.20+)
 */

import { AnimationController } from './js/animation/Controller.js';
import { Store } from './js/state/store.js';
import { HashRouter } from './router.js';
import { ApiClient } from './js/services/api.js';
import { AppContext } from './js/AppContext.js';
import { EventBus } from './js/EventBus.js';
import { HomePage } from './js/pages/HomePage.js';
import { SingPage } from './js/pages/SingPage.js';
import { ReportPage } from './js/pages/ReportPage.js';
import { HistoryPage } from './js/pages/HistoryPage.js';
import { ComparePage } from './js/pages/ComparePage.js';
import { SettingsPage } from './js/pages/SettingsPage.js';
import { SongLibraryPage } from './js/pages/SongLibraryPage.js';
import { TopNav, BottomNav, initResponsiveNav } from './js/components/Navigation.js';
import { showToast } from './js/components/Toast.js';

// ============================================================================
// 1. 创建应用服务 (→ Vue: createApp + plugins)
// ============================================================================

// 1a. GSAP + AnimationController
if (typeof gsap !== 'undefined') {
    gsap.defaults({ ease: 'power2.out', duration: 0.4, overwrite: 'auto' });
    gsap.config({ force3D: true });
}
const ac = new AnimationController(gsap, { detectReducedMotion: true });

// 1b. EventBus (→ Vue: mitt)
const events = new EventBus({ debug: false });

// 1c. Store (→ Vue: Pinia)
const store = new Store();
store.persist('preferences');
const savedTheme = localStorage.getItem('vocal_app_theme') || 'light';
if (savedTheme === 'dark') document.body.classList.add('dark-theme');
store.setState({ theme: savedTheme, evalMode: localStorage.getItem('vocal_app_evalMode') || 'quick' }, 'preferences');

// 1d. API Client (→ Vue: HTTP composable / Electron IPC)
const api = new ApiClient();

// ============================================================================
// 2. 依赖注入容器 (→ Vue: provide/inject)
// ============================================================================

const context = new AppContext({ store, router: null, api, ac, events });

// 全局兼容 — 旧代码仍可通过 window.__* 访问 (v7.0 移除)
window.__appContext = context;
window.__ac = ac;
window.__store = store;
window.__api = api;

// ============================================================================
// 3. Router (→ Vue: Vue Router)
// ============================================================================

const pageContainer = document.getElementById('pageContainer');
const router = new HashRouter(pageContainer);
router.register('#/', HomePage);
router.register('#/sing', SingPage);
router.register('#/sing/:songId', SingPage);
router.register('#/report', ReportPage);
router.register('#/report/:analysisId', ReportPage);
router.register('#/history', HistoryPage);
router.register('#/compare', ComparePage);
router.register('#/settings', SettingsPage);
router.register('#/songs', SongLibraryPage);

// 将 router 注册到 context
context.register('router', router);
window.__router = router;
router.useContext(context);

// ============================================================================
// 4. 路由守卫 + 全局事件 (→ Vue: router.beforeEach + mitt)
// ============================================================================

router.onBeforeNavigate((next, prev) => {
    if (window.__topNav) window.__topNav.setActive(next.hash);
    if (window.__bottomNav) window.__bottomNav.setActive(next.hash);
    store.setState({ current: next.hash, params: next.params, previous: prev?.hash || null }, 'route');
    events.emit('route:changed', { next, prev });
    return true;
});

// ============================================================================
// 5. Navigation (→ Vue: <RouterLink> + <NavBar>)
// ============================================================================

const topNav = new TopNav(document.getElementById('topNavContainer'));
topNav.render();
window.__topNav = topNav;

const bottomNav = new BottomNav(document.getElementById('bottomNavContainer'));
bottomNav.render();
window.__bottomNav = bottomNav;

// ============================================================================
// 6. 全局事件绑定 (→ Vue: Pinia watch / mitt)
// ============================================================================

// 分析进度 → 全局进度条
const globalBar = document.getElementById('globalProgressBar');
store.subscribe('analysis.progress', (p) => {
    if (p && globalBar) {
        ac.fillBar(globalBar, p.percent || 0, { duration: 0.3 });
    }
});
store.subscribe('analysis.status', (s) => {
    if (s === 'complete' && globalBar && typeof gsap !== 'undefined') {
        gsap.to(globalBar, {
            background: 'var(--success)',
            duration: 0.3,
            onComplete: () => gsap.to(globalBar, { scaleX: 0, duration: 0.3, delay: 1 })
        });
    }
});

// 分析完成 → 自动跳转报告页 (通过 EventBus 解耦)
events.on('analysis:complete', (result) => {
    const prefs = store.getState('preferences');
    if (prefs.autoPlay && result?.analysis_id && !store._analysisNavigated) {
        store._analysisNavigated = true;
        setTimeout(() => {
            router.navigate('#/report/' + result.analysis_id);
            store._analysisNavigated = false;
        }, 800);
    }
});
// 兼容旧 code path (store.on callback)
store.on('analysis:complete', (result) => {
    events.emit('analysis:complete', result);
});

// 网络状态变化
window.addEventListener('online', () => {
    events.emit('system:online');
    showToast('网络已恢复', 'success');
});
window.addEventListener('offline', () => {
    events.emit('system:offline');
    showToast('网络已断开，离线功能仍可用', 'warning');
});

// 全局错误
window.addEventListener('error', (e) => {
    if (!e.error?.handled) showToast('发生未知错误', 'error');
});

// ============================================================================
// 7. 启动应用 (→ Vue: app.mount('#app'))
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    initResponsiveNav();
    router.start();
    topNav.setActive(location.hash || '#/');
    bottomNav.setActive(location.hash || '#/');

    // 冻结 context — 运行时不再允许注册新服务
    context.freeze();

    events.emit('app:ready');
});
