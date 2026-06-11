/**
 * SettingsPage — 设置页
 *
 * 路由: #/settings
 *
 * @version 1.0
 */

import { BaseComponent } from '../components/BaseComponent.js';
import { showToast } from '../components/Toast.js';
import { confirm } from '../components/Modal.js';

export class SettingsPage extends BaseComponent {
    async mount(params) {
        this.render();
        this.bindEvents();
    }

    render() {
        this.el = this.createElement('div', { id: 'page-settings', className: 'page page-container' });

        this.el.innerHTML = `
        <h2 style="font-size:18px;font-weight:600;margin-bottom:24px;">⚙️ 设置</h2>

        <!-- 主题 -->
        <div class="card" style="margin-bottom:20px;">
            <div class="card-header"><span class="card-title">🎨 主题</span></div>
            <div class="card-body">
                <div style="display:flex;gap:12px;">
                    <button class="theme-btn active" data-theme="light" style="flex:1;padding:16px;border:2px solid var(--border);border-radius:var(--radius-lg);background:var(--bg-card);cursor:pointer;text-align:center;">
                        <div style="font-size:24px;margin-bottom:4px;">☀️</div>
                        <div style="font-size:13px;font-weight:600;color:var(--text-primary);">浅色</div>
                    </button>
                    <button class="theme-btn" data-theme="dark" style="flex:1;padding:16px;border:2px solid var(--border);border-radius:var(--radius-lg);background:var(--bg-card);cursor:pointer;text-align:center;">
                        <div style="font-size:24px;margin-bottom:4px;">🌙</div>
                        <div style="font-size:13px;font-weight:600;color:var(--text-primary);">深色</div>
                    </button>
                </div>
            </div>
        </div>

        <!-- 偏好设置 -->
        <div class="card" style="margin-bottom:20px;">
            <div class="card-header"><span class="card-title">📋 偏好设置</span></div>
            <div class="card-body">
                <div style="margin-bottom:16px;">
                    <label style="display:flex;justify-content:space-between;align-items:center;">
                        <span style="font-size:14px;color:var(--text-primary);">默认评估模式</span>
                        <select id="defaultMode" style="padding:6px 12px;border:1px solid var(--border);border-radius:var(--radius-md);background:var(--bg-card);color:var(--text-primary);font-size:13px;">
                            <option value="quick">快速评估 (~30s)</option>
                            <option value="professional">专业评估 (~2-5min)</option>
                        </select>
                    </label>
                </div>
                <div style="margin-bottom:16px;">
                    <label style="display:flex;justify-content:space-between;align-items:center;">
                        <span style="font-size:14px;color:var(--text-primary);">分析完成自动跳转报告</span>
                        <input type="checkbox" id="autoPlay" style="width:18px;height:18px;">
                    </label>
                </div>
            </div>
        </div>

        <!-- 缓存管理 -->
        <div class="card" style="margin-bottom:20px;">
            <div class="card-header"><span class="card-title">🗂️ 缓存管理</span></div>
            <div class="card-body">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                    <span style="font-size:14px;color:var(--text-primary);">存储空间使用</span>
                    <span id="storageInfo" style="font-size:13px;color:var(--text-muted);">计算中...</span>
                </div>
                <button class="btn btn-secondary" id="clearCacheBtn" style="width:100%;">清除分析缓存</button>
            </div>
        </div>

        <!-- 版本信息 -->
        <div class="card">
            <div class="card-body" style="text-align:center;color:var(--text-muted);font-size:12px;">
                <p>声乐评估系统 v5.17</p>
                <p>Web UI v2.0 — SPA + GSAP</p>
            </div>
        </div>`;

        this.container.appendChild(this.el);

        // 恢复已保存的偏好
        this.#restorePreferences();
    }

    bindEvents() {
        // 主题切换
        this.el.querySelectorAll('.theme-btn').forEach(btn => {
            btn.addEventListener('click', () => this.#setTheme(btn.dataset.theme));
        });

        // 默认模式
        this.el.querySelector('#defaultMode')?.addEventListener('change', (e) => {
            const mode = e.target.value;
            if (this.store) this.store.setState({ evalMode: mode }, 'preferences');
            localStorage.setItem('vocal_app_preferences', JSON.stringify({
                ...JSON.parse(localStorage.getItem('vocal_app_preferences') || '{}'),
                evalMode: mode
            }));
        });

        // 自动跳转
        this.el.querySelector('#autoPlay')?.addEventListener('change', (e) => {
            if (this.store) this.store.setState({ autoPlay: e.target.checked }, 'preferences');
        });

        // 清除缓存
        this.el.querySelector('#clearCacheBtn')?.addEventListener('click', async () => {
            const ok = await confirm('清除缓存', '确定清除所有本地缓存数据？历史记录不会被删除。');
            if (ok) {
                localStorage.clear();
                showToast('缓存已清除', 'success');
                this.#updateStorageInfo();
            }
        });
    }

    #setTheme(theme) {
        document.body.classList.toggle('dark-theme', theme === 'dark');
        if (this.store) this.store.setState({ theme }, 'preferences');

        // 更新按钮状态
        this.el.querySelectorAll('.theme-btn').forEach(btn => {
            const isActive = btn.dataset.theme === theme;
            btn.classList.toggle('active', isActive);
            btn.style.borderColor = isActive ? 'var(--primary)' : 'var(--border)';
        });

        localStorage.setItem('vocal_app_theme', theme);
    }

    #restorePreferences() {
        // 主题
        const savedTheme = localStorage.getItem('vocal_app_theme') || 'light';
        this.#setTheme(savedTheme);

        // 评估模式
        const prefs = JSON.parse(localStorage.getItem('vocal_app_preferences') || '{}');
        const modeSelect = this.el.querySelector('#defaultMode');
        if (modeSelect && prefs.evalMode) modeSelect.value = prefs.evalMode;

        const autoPlay = this.el.querySelector('#autoPlay');
        if (autoPlay && prefs.autoPlay !== undefined) autoPlay.checked = prefs.autoPlay;

        this.#updateStorageInfo();
    }

    #updateStorageInfo() {
        let total = 0;
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            const val = localStorage.getItem(key);
            total += (key.length + val.length) * 2; // UTF-16
        }
        const kb = total / 1024;
        this.el.querySelector('#storageInfo').textContent = kb < 1024 ? `${kb.toFixed(1)} KB` : `${(kb / 1024).toFixed(1)} MB`;
    }
}

export default SettingsPage;
