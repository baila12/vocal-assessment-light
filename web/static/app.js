/**
 * 声乐评估系统 — SPA 主入口 (v2.1)
 *
 * 初始化顺序:
 *   GSAP → AnimationController → Store → ApiClient → HashRouter → Navigation → 启动
 */
import { AnimationController } from './js/animation/Controller.js';
import { Store } from './js/state/store.js';
import { HashRouter } from './router.js';
import { ApiClient } from './js/services/api.js';
import { HomePage } from './js/pages/HomePage.js';
import { SingPage } from './js/pages/SingPage.js';
import { ReportPage } from './js/pages/ReportPage.js';
import { HistoryPage } from './js/pages/HistoryPage.js';
import { ComparePage } from './js/pages/ComparePage.js';
import { SettingsPage } from './js/pages/SettingsPage.js';
import { SongLibraryPage } from './js/pages/SongLibraryPage.js';
import { TopNav, BottomNav, initResponsiveNav } from './js/components/Navigation.js';
import { showToast } from './js/components/Toast.js';

// 0. GSAP 全局配置 + AnimationController
if (typeof gsap !== 'undefined') {
    gsap.defaults({
        ease: 'power2.out',
        duration: 0.4,
        overwrite: 'auto'
    });
    gsap.config({ force3D: true });
}

const ac = new AnimationController(gsap, { detectReducedMotion: true });
window.__ac = ac;

// 1. Store
const store = new Store();
store.persist('preferences');
const savedTheme = localStorage.getItem('vocal_app_theme') || 'light';
if (savedTheme === 'dark') document.body.classList.add('dark-theme');
store.setState({ theme: savedTheme, evalMode: localStorage.getItem('vocal_app_evalMode') || 'quick' }, 'preferences');
window.__store = store;

// 2. API
const api = new ApiClient();
window.__api = api;
window.addEventListener('online', () => showToast('网络已恢复', 'success'));
window.addEventListener('offline', () => showToast('网络已断开，离线功能仍可用', 'warning'));

// 3. Router
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
window.__router = router;

router.onBeforeNavigate((next, prev) => {
    if (window.__topNav) window.__topNav.setActive(next.hash);
    if (window.__bottomNav) window.__bottomNav.setActive(next.hash);
    store.setState({ current: next.hash, params: next.params, previous: prev?.hash || null }, 'route');
    return true;
});

// 4. Navigation
const topNav = new TopNav(document.getElementById('topNavContainer'));
topNav.render();
window.__topNav = topNav;
const bottomNav = new BottomNav(document.getElementById('bottomNavContainer'));
bottomNav.render();
window.__bottomNav = bottomNav;

// 5. Global ProgressBar
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
store.on('analysis:complete', (result) => {
    const prefs = store.getState('preferences');
    if (prefs.autoPlay && result?.analysis_id && !store._analysisNavigated) {
        store._analysisNavigated = true;
        setTimeout(() => {
            router.navigate('#/report/' + result.analysis_id);
            store._analysisNavigated = false;
        }, 800);
    }
});

// 6. Start
document.addEventListener('DOMContentLoaded', () => {
    initResponsiveNav();
    router.start();
    topNav.setActive(location.hash || '#/');
    bottomNav.setActive(location.hash || '#/');
});

window.addEventListener('error', (e) => {
    if (!e.error?.handled) showToast('发生未知错误', 'error');
});
