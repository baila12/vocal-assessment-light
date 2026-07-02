/**
 * SongLibraryPage — 标准曲库页
 *
 * 路由: #/songs
 * 功能: 浏览、搜索、筛选、导入、删除标准音频
 *
 * @version 1.0
 */

import { BaseComponent } from '../components/BaseComponent.js';
import { showToast } from '../components/Toast.js';
import { StandardAudioSelector } from '../components/StandardAudioSelector.js';
import { ApiClient } from '../services/api.js';

export class SongLibraryPage extends BaseComponent {
    static animationPreset = 'page-enter';

    /** @type {StandardAudioSelector} */
    _selector;

    /** @type {Array} */
    _songs = [];

    /** @type {boolean} */
    _loading = true;

    /** @type {Object|null} */
    _importFormData = null;

    _api;

    constructor(container, options = {}) {
        super(container, options);
        this._api = options.api || window.__api || new ApiClient();

        // Override store as getter/setter on instance (BaseComponent sets it as plain property)
        let _store = this.store;
        Object.defineProperty(this, 'store', {
            get() { return _store; },
            set(v) {
                _store = v;
                if (v && v.get) {
                    const songs = v.get('songs');
                    if (songs && Array.isArray(songs)) {
                        this._songs = songs;
                        this._loading = false;
                        if (this.el) {
                            if (songs.length === 0) {
                                this._showEmpty();
                            } else {
                                this._showContent(songs);
                            }
                        }
                    }
                }
            },
            configurable: true, enumerable: true
        });
    }

    async mount(params) {
        this.render();
        this.bindEvents();
        await this._loadSongs();
        this._animateIn();
    }

    // ========================================================================
    // Render
    // ========================================================================

    render() {
        this.el = this.createElement('div', { id: 'page-songs', className: 'page page-container' });

        this.el.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;flex-wrap:wrap;gap:12px;">
            <h2 style="font-size:18px;font-weight:600;">📚 标准曲库</h2>
            <div style="display:flex;gap:8px;">
                <button id="importSongBtn" class="btn btn-primary" style="padding:8px 16px;border:none;border-radius:var(--radius-md);background:var(--primary);color:#fff;font-size:13px;cursor:pointer;font-weight:600;display:flex;align-items:center;gap:6px;">
                    <span style="font-size:16px;">+</span> 导入音频
                </button>
            </div>
        </div>

        <!-- 加载状态 -->
        <div id="songsLoading" style="text-align:center;padding:60px 0;color:var(--text-muted);">
            <div style="font-size:36px;margin-bottom:12px;">⏳</div>
            <p>加载曲库中...</p>
        </div>

        <!-- 空状态 -->
        <div id="songsEmpty" style="display:none;text-align:center;padding:60px 20px;">
            <div style="font-size:48px;margin-bottom:16px;">📭</div>
            <h3 style="color:var(--text-primary);margin-bottom:8px;">曲库为空</h3>
            <p style="color:var(--text-muted);margin-bottom:24px;">还没有导入任何标准歌曲</p>
            <button id="importFirstSongBtn" class="btn btn-primary" style="padding:12px 24px;border:none;border-radius:var(--radius-md);background:var(--primary);color:#fff;font-size:14px;cursor:pointer;font-weight:600;">
                + 导入第一首标准歌曲
            </button>
        </div>

        <!-- 曲库内容 -->
        <div id="songsContent" style="display:none;">
            <div id="songsSelectorContainer"></div>
        </div>
        `;

        this.container.appendChild(this.el);

        // If store was injected before render (test pattern), populate content now
        if (this.store && !this._loading && this._songs.length > 0) {
            this._showContent(this._songs);
        } else if (this.store && !this._loading && this._songs.length === 0) {
            this._showEmpty();
        }
    }

    bindEvents() {
        this.el.querySelector('#importSongBtn')?.addEventListener('click', () => this._openImportModal());
        this.el.querySelector('#importFirstSongBtn')?.addEventListener('click', () => this._openImportModal());
    }

    // ========================================================================
    // Data loading
    // ========================================================================

    async _loadSongs() {
        this._loading = true;
        this._showLoading();

        try {
            // 先尝试从 API 加载，回退到 mock 数据
            let songs = [];
            try {
                const res = await this._api.getSongList();
                songs = res?.songs || [];
            } catch (e) {
                // API 不可用 — 尝试 mock 数据
                songs = window.__mockSongs || [];
            }

            this._songs = songs;
            this._loading = false;

            if (songs.length === 0) {
                this._showEmpty();
            } else {
                this._showContent(songs);
            }

            // 动画入场
            this._animateIn();

        } catch (e) {
            this._loading = false;
            this._showEmpty();
            showToast('加载曲库失败: ' + e.message, 'error');
        }
    }

    // ========================================================================
    // UI state
    // ========================================================================

    _showLoading() {
        const loading = this.el.querySelector('#songsLoading');
        const empty = this.el.querySelector('#songsEmpty');
        const content = this.el.querySelector('#songsContent');

        if (loading) loading.style.display = '';
        if (empty) empty.style.display = 'none';
        if (content) content.style.display = 'none';
    }

    _showEmpty() {
        const loading = this.el.querySelector('#songsLoading');
        const empty = this.el.querySelector('#songsEmpty');
        const content = this.el.querySelector('#songsContent');

        if (loading) loading.style.display = 'none';
        if (empty) empty.style.display = '';
        if (content) content.style.display = 'none';
    }

    _showContent(songs) {
        const loading = this.el.querySelector('#songsLoading');
        const empty = this.el.querySelector('#songsEmpty');
        const content = this.el.querySelector('#songsContent');

        if (loading) loading.style.display = 'none';
        if (empty) empty.style.display = 'none';
        if (content) content.style.display = '';

        // 渲染选择器 (inline 模式, 只展示不选)
        const container = this.el.querySelector('#songsSelectorContainer');
        if (!container) return;

        this._selector = new StandardAudioSelector(container, {
            mode: 'inline',
            onSelect: (song) => {
                // 在曲库页选择歌曲 → 跳转到演唱页
                if (this.router) {
                    this.router.navigate('#/sing/' + song.id);
                }
            }
        });
        this._selector.setSongs(songs);
        this._selector.render();

        // 替换选择器的"导入链接"行为
        const importBtn = container.querySelector('button:last-child');
        if (importBtn) {
            importBtn.textContent = '+ 导入新标准音频';
            importBtn.onclick = () => this._openImportModal();
        }
    }

    // ========================================================================
    // Import modal
    // ========================================================================

    _openImportModal() {
        // 创建导入弹窗
        const overlay = document.createElement('div');
        overlay.className = 'import-modal';
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.4);z-index:var(--z-modal);display:flex;align-items:center;justify-content:center;padding:24px;';

        const card = document.createElement('div');
        card.style.cssText = 'background:var(--bg-card);border-radius:var(--radius-lg);padding:24px;max-width:480px;width:100%;box-shadow:var(--shadow-xl);';

        card.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
            <h3 style="font-size:16px;font-weight:600;margin:0;">导入标准音频</h3>
            <button id="closeImportBtn" style="border:none;background:none;font-size:20px;cursor:pointer;color:var(--text-muted);">✕</button>
        </div>
        <form id="importForm" style="display:flex;flex-direction:column;gap:14px;">
            <div>
                <label style="display:block;font-size:13px;font-weight:500;color:var(--text-secondary);margin-bottom:4px;">音频文件 *</label>
                <input type="file" id="importAudioFile" accept="audio/*,.mp3,.wav,.flac,.ogg,.m4a" required
                       style="width:100%;padding:8px;border:1px solid var(--border);border-radius:var(--radius-md);background:var(--bg-primary);font-size:13px;">
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                <div>
                    <label style="display:block;font-size:13px;font-weight:500;color:var(--text-secondary);margin-bottom:4px;">歌曲名 *</label>
                    <input type="text" id="importSongTitle" required placeholder="例如: 月亮代表我的心"
                           style="width:100%;padding:8px 12px;border:1px solid var(--border);border-radius:var(--radius-md);background:var(--bg-primary);font-size:13px;">
                </div>
                <div>
                    <label style="display:block;font-size:13px;font-weight:500;color:var(--text-secondary);margin-bottom:4px;">歌手 *</label>
                    <input type="text" id="importArtist" required placeholder="例如: 邓丽君"
                           style="width:100%;padding:8px 12px;border:1px solid var(--border);border-radius:var(--radius-md);background:var(--bg-primary);font-size:13px;">
                </div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                <div>
                    <label style="display:block;font-size:13px;font-weight:500;color:var(--text-secondary);margin-bottom:4px;">难度</label>
                    <select id="importDifficulty"
                            style="width:100%;padding:8px 12px;border:1px solid var(--border);border-radius:var(--radius-md);background:var(--bg-primary);font-size:13px;">
                        <option value="初级">初级</option>
                        <option value="中级">中级</option>
                        <option value="高级">高级</option>
                    </select>
                </div>
                <div>
                    <label style="display:block;font-size:13px;font-weight:500;color:var(--text-secondary);margin-bottom:4px;">风格</label>
                    <select id="importStyle"
                            style="width:100%;padding:8px 12px;border:1px solid var(--border);border-radius:var(--radius-md);background:var(--bg-primary);font-size:13px;">
                        <option value="流行">流行</option>
                        <option value="民谣">民谣</option>
                        <option value="美声">美声</option>
                        <option value="R&B">R&B</option>
                        <option value="摇滚">摇滚</option>
                        <option value="爵士">爵士</option>
                    </select>
                </div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                <div>
                    <label style="display:block;font-size:13px;font-weight:500;color:var(--text-secondary);margin-bottom:4px;">BPM (可选)</label>
                    <input type="number" id="importBpm" placeholder="自动检测"
                           style="width:100%;padding:8px 12px;border:1px solid var(--border);border-radius:var(--radius-md);background:var(--bg-primary);font-size:13px;">
                </div>
                <div>
                    <label style="display:block;font-size:13px;font-weight:500;color:var(--text-secondary);margin-bottom:4px;">调性 (可选)</label>
                    <input type="text" id="importKey" placeholder="例如: C Major"
                           style="width:100%;padding:8px 12px;border:1px solid var(--border);border-radius:var(--radius-md);background:var(--bg-primary);font-size:13px;">
                </div>
            </div>
            <div id="importError" style="display:none;padding:8px 12px;background:#fef2f2;color:#ef4444;border-radius:var(--radius-md);font-size:13px;"></div>
            <div style="display:flex;justify-content:flex-end;gap:10px;margin-top:4px;">
                <button type="button" id="cancelImportBtn" class="btn btn-secondary"
                        style="padding:8px 20px;border-radius:var(--radius-md);border:1px solid var(--border);background:transparent;color:var(--text-primary);cursor:pointer;font-size:13px;">取消</button>
                <button type="submit" id="submitImportBtn" class="btn btn-primary"
                        style="padding:8px 20px;border-radius:var(--radius-md);border:none;background:var(--primary);color:#fff;cursor:pointer;font-size:13px;font-weight:600;">开始导入</button>
            </div>
        </form>
        `;

        overlay.appendChild(card);
        document.body.appendChild(overlay);

        // 绑定事件
        overlay.querySelector('#closeImportBtn')?.addEventListener('click', () => overlay.remove());
        overlay.querySelector('#cancelImportBtn')?.addEventListener('click', () => overlay.remove());
        overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });

        const form = overlay.querySelector('#importForm');
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await this._handleImport(form, overlay);
        });
    }

    async _handleImport(form, overlay) {
        const fileInput = form.querySelector('#importAudioFile');
        const titleInput = form.querySelector('#importSongTitle');
        const artistInput = form.querySelector('#importArtist');
        const errorEl = form.querySelector('#importError');

        // 客户端校验
        if (!fileInput.files || !fileInput.files[0]) {
            errorEl.textContent = '请选择音频文件';
            errorEl.style.display = '';
            return;
        }
        if (!titleInput.value.trim()) {
            errorEl.textContent = '请输入歌曲名';
            errorEl.style.display = '';
            titleInput.focus();
            return;
        }
        if (!artistInput.value.trim()) {
            errorEl.textContent = '请输入歌手名';
            errorEl.style.display = '';
            artistInput.focus();
            return;
        }

        // 文件大小检查
        const file = fileInput.files[0];
        if (file.size > 50 * 1024 * 1024) {
            errorEl.textContent = '文件过大 (超过 50MB)，建议压缩后导入';
            errorEl.style.display = '';
            return;
        }

        errorEl.style.display = 'none';

        // 禁用提交按钮
        const submitBtn = form.querySelector('#submitImportBtn');
        submitBtn.disabled = true;
        submitBtn.textContent = '导入中...';

        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('title', titleInput.value.trim());
            formData.append('artist', artistInput.value.trim());
            formData.append('difficulty', form.querySelector('#importDifficulty')?.value || '初级');
            formData.append('style', form.querySelector('#importStyle')?.value || '流行');
            formData.append('bpm', form.querySelector('#importBpm')?.value || '');
            formData.append('key', form.querySelector('#importKey')?.value || '');

            // 尝试 API 导入
            try {
                await this._api.request('POST', '/api/songs/upload', {
                    body: formData, isFormData: true, timeout: 120000
                });
            } catch (e) {
                // API 不可用 — 模拟导入
                const newSong = {
                    id: titleInput.value.trim().replace(/\s+/g, '_'),
                    title: titleInput.value.trim(),
                    artist: artistInput.value.trim(),
                    difficulty: form.querySelector('#importDifficulty')?.value || '初级',
                    style: form.querySelector('#importStyle')?.value || '流行',
                    duration: 0,
                    bpm: form.querySelector('#importBpm')?.value || '',
                    key: form.querySelector('#importKey')?.value || ''
                };
                this._songs.push(newSong);
            }

            overlay.remove();
            showToast('已成功导入「' + titleInput.value.trim() + '」', 'success');

            // 刷新列表
            await this._loadSongs();

        } catch (e) {
            errorEl.textContent = '导入失败: ' + e.message;
            errorEl.style.display = '';
            submitBtn.disabled = false;
            submitBtn.textContent = '开始导入';
        }
    }

    // ========================================================================
    // Animation
    // ========================================================================

    _animateIn() {
        const ac = this.ac;
        if (ac && this.el) {
            const cards = this.el.querySelectorAll('.song-card');
            if (cards.length > 0) {
                ac.stagger(cards, { preset: 'slideUp-sm', stagger: 0.05 });
            }
        }
    }

    destroy() {
        this._selector?.destroy();
        super.destroy();
    }
}

export default SongLibraryPage;

// Expose for tests
if (typeof window !== 'undefined') {
  window.__SongLibraryPage = SongLibraryPage;
}
