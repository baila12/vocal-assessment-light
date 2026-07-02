/**
 * SettingsPage — 设置页 (主题、模式、偏好、动画控制)
 *
 * 路由: #/settings
 * 新增: 减少动效开关直接绑定 AnimationController.setEnabled()
 *
 * @version 2.0
 */

import { BaseComponent } from '../components/BaseComponent.js';
import { showToast } from '../components/Toast.js';

export class SettingsPage extends BaseComponent {
    static animationPreset = 'page-enter';

    async mount(params) {
        this.render();
        this.bindEvents();
    }

    render() {
        this.el = this.createElement('div', { id: 'page-settings', className: 'page page-container' });

        const prefs = this.store?.getState('preferences') || {};
        const isReduced = this.ac?.reducedMotion || false;
        const userDisabledAnim = localStorage.getItem('vocal_app_reducedMotion') === 'true';
        const animDisabled = userDisabledAnim || isReduced;

        this.el.innerHTML = `
        <h2 style="font-size:18px;font-weight:600;margin-bottom:20px;">⚙️ 设置</h2>

        <div class="card" style="margin-bottom:16px;">
            <div class="card-header"><span class="card-title">🎨 外观</span></div>
            <div class="card-body">
                <div class="setting-row" style="display:flex;justify-content:space-between;align-items:center;padding:12px 0;">
                    <div><div style="font-weight:500;">深色模式</div><div style="font-size:12px;color:var(--text-muted);">切换暗色主题</div></div>
                    <label class="toggle">
                        <input type="checkbox" id="themeToggle" >
                        <span class="toggle-slider"></span>
                    </label>
                </div>
                <div class="setting-row" style="display:flex;justify-content:space-between;align-items:center;padding:12px 0;">
                    <div><div style="font-weight:500;">减少动效</div><div style="font-size:12px;color:var(--text-muted);">关闭 GSAP 动画效果（尊重系统偏好）</div></div>
                    <label class="toggle">
                        <input type="checkbox" id="reducedMotionToggle" >
                        <span class="toggle-slider"></span>
                    </label>
                </div>
            </div>
        </div>

        <div class="card" style="margin-bottom:16px;">
            <div class="card-header"><span class="card-title">🔊 音频</span></div>
            <div class="card-body">
                <div class="setting-row" style="display:flex;justify-content:space-between;align-items:center;padding:12px 0;">
                    <div><div style="font-weight:500;">默认评估模式</div><div style="font-size:12px;color:var(--text-muted);">分析时使用的默认模式</div></div>
                    <select id="defaultMode" style="padding:6px 12px;border-radius:6px;border:1px solid var(--border);background:var(--bg-primary);color:var(--text-primary);font-size:13px;">
                        <option value="quick" >快速模式</option>
                        <option value="professional" >专业模式</option>
                    </select>
                </div>
            </div>
        </div>

        <div class="card" style="margin-bottom:16px;">
            <div class="card-header"><span class="card-title">📊 报告</span></div>
            <div class="card-body">
                <div class="setting-row" style="display:flex;justify-content:space-between;align-items:center;padding:12px 0;">
                    <div><div style="font-weight:500;">自动播放</div><div style="font-size:12px;color:var(--text-muted);">分析完成后自动跳转到报告页</div></div>
                    <label class="toggle">
                        <input type="checkbox" id="autoPlayToggle" >
                        <span class="toggle-slider"></span>
                    </label>
                </div>
            </div>
        </div>

        <div class="card" style="margin-bottom:16px;">
            <div class="card-header"><span class="card-title">📚 曲库</span></div>
            <div class="card-body">
                <div style="display:flex;justify-content:space-between;align-items:center;padding:12px 0;">
                    <div><div style="font-weight:500;">管理标准曲库</div><div style="font-size:12px;color:var(--text-muted);">导入、浏览、删除标准歌曲</div></div>
                    <a href="#/songs" style="padding:6px 14px;border-radius:var(--radius-md);background:var(--primary-ghost);color:var(--primary);text-decoration:none;font-size:13px;font-weight:500;">前往曲库 →</a>
                </div>
            </div>
        </div>

        <div class="card">
            <div class="card-header"><span class="card-title">ℹ️ 关于</span></div>
            <div class="card-body" style="text-align:center;padding:20px;color:var(--text-muted);font-size:13px;">
                <p>声乐评估系统 v2.1</p>
                <p style="margin-top:4px;">Flask + SPA · GSAP Animation Controller</p>
                <p style="margin-top:4px;">🔒 所有数据本地处理</p>
                <p style="margin-top:8px;font-size:11px;">
                    <span id="animStatus" style="color:">
                        
                    </span>
                </p>
            </div>
        </div>
        `;

        this.container.appendChild(this.el);
    }

    bindEvents() {
        // 深色模式
        this.el.querySelector('#themeToggle')?.addEventListener('change', (e) => {
            const isDark = e.target.checked;
            document.body.classList.toggle('dark-theme', isDark);
            localStorage.setItem('vocal_app_theme', isDark ? 'dark' : 'light');
            if (this.store) this.store.setState({ theme: isDark ? 'dark' : 'light' }, 'preferences');
            showToast(isDark ? '深色模式已启用' : '浅色模式已启用', 'success');
        });

        // 减少动效 — 绑定 AnimationController
        this.el.querySelector('#reducedMotionToggle')?.addEventListener('change', (e) => {
            const disabled = e.target.checked;
            if (window.__ac) {
                window.__ac.setEnabled(!disabled);
            }
            localStorage.setItem('vocal_app_reducedMotion', disabled ? 'true' : 'false');
            const status = this.el.querySelector('#animStatus');
            if (status) {
                status.textContent = disabled ? '○ 动效已禁用' : '● 动效已启用';
                status.style.color = disabled ? 'var(--text-muted)' : 'var(--success)';
            }
            showToast(disabled ? '已减少动效' : '动效已启用', 'success');
        });

        // 默认模式
        this.el.querySelector('#defaultMode')?.addEventListener('change', (e) => {
            localStorage.setItem('vocal_app_evalMode', e.target.value);
            if (this.store) this.store.setState({ evalMode: e.target.value }, 'preferences');
            showToast('默认模式已更新', 'success');
        });

        // 自动播放
        this.el.querySelector('#autoPlayToggle')?.addEventListener('change', (e) => {
            if (this.store) this.store.setState({ autoPlay: e.target.checked }, 'preferences');
        });
    }

    destroy() {
        super.destroy();
    }
}

export default SettingsPage;
