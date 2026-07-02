/**
 * StandardAudioSelector — 标准音频选择器 (可复用组件)
 *
 * 用于 SingPage 和 ComparePage 中从曲库选择标准歌曲。
 * 支持 inline 和 modal 两种模式。
 *
 * 状态: loading → list/empty → selected
 *
 * @version 1.0
 */

import { BaseComponent } from '../components/BaseComponent.js';
import { showToast } from '../components/Toast.js';

export class StandardAudioSelector extends BaseComponent {
    static defaultPreset = 'slideUp';

    /** @type {'inline'|'modal'} */
    #mode;

    /** @type {Function} */
    #onSelect;

    /** @type {string|null} */
    #excludeId;

    /** @type {Array} */
    #songs = [];

    /** @type {string} */
    #searchQuery = '';

    /** @type {string} */
    #difficultyFilter = 'all';

    /** @type {string} */
    #styleFilter = 'all';

    /** @type {boolean} */
    #loading = true;

    /** @type {Object|null} */
    #selectedSong = null;

    /** @type {number} */
    #page = 0;

    /** @type {number} */
    #pageSize = 20;

    /** @type {boolean} */
    #showDetail = false;

    /**
     * @param {Element} container
     * @param {Object} options
     * @param {'inline'|'modal'} [options.mode='inline']
     * @param {Function} [options.onSelect] - (song) => void
     * @param {string} [options.excludeSongId] - 排除的歌曲 ID
     */
    constructor(container, options = {}) {
        super(container, options);
        this.#mode = options.mode || 'inline';
        this.#onSelect = options.onSelect || (() => {});
        this.#excludeId = options.excludeSongId || null;
    }

    // ========================================================================
    // Public
    // ========================================================================

    /**
     * 设置歌曲列表 (注入 mock 数据或真实 API 返回)
     * @param {Array} songs
     */
    setSongs(songs) {
        this.#songs = songs.filter(s => s.id !== this.#excludeId);
        this.#loading = false;
        this.#page = 0;
        if (this.el) this._renderList();
    }

    /**
     * 设置加载状态
     * @param {boolean} loading
     */
    setLoading(loading) {
        this.#loading = loading;
        if (this.el) this._renderList();
    }

    /**
     * 获取当前选中
     * @returns {Object|null}
     */
    getSelected() {
        return this.#selectedSong;
    }

    /**
     * 清除选中
     */
    clearSelection() {
        this.#selectedSong = null;
        if (this.el) this._renderList();
    }

    // ========================================================================
    // Render
    // ========================================================================

    render() {
        if (this.#mode === 'modal') {
            this._renderModal();
        } else {
            this._renderInline();
        }
    }

    _renderInline() {
        this.el = this.createElement('div', {
            className: 'standard-audio-selector',
            style: {
                width: '100%',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px'
            }
        });

        // 搜索 + 筛选栏
        this.el.appendChild(this._renderToolbar());

        // 列表区域
        this._listContainer = this.createElement('div', {
            className: 'selector-list',
            style: { flex: '1', overflowY: 'auto', maxHeight: '400px' }
        });
        this.el.appendChild(this._listContainer);

        // 导入按钮
        const importBtn = this.createElement('button', {
            className: 'btn btn-secondary btn-sm',
            style: {
                padding: '8px 16px',
                fontSize: '13px',
                border: '1px dashed var(--border)',
                background: 'transparent',
                color: 'var(--primary)',
                borderRadius: 'var(--radius-md)',
                cursor: 'pointer',
                width: '100%'
            },
            onClick: () => {
                if (this.router) this.router.navigate('#/songs');
            }
        }, '+ 导入新标准音频');
        this.el.appendChild(importBtn);

        this.container.appendChild(this.el);
        this._renderList();
    }

    _renderModal() {
        this.el = this.createElement('div', {
            className: 'selector-overlay',
            style: {
                position: 'fixed', inset: '0',
                background: 'rgba(0,0,0,0.4)',
                zIndex: 'var(--z-modal)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                padding: '24px'
            },
            onClick: (e) => { if (e.target === this.el) this.close(); }
        });

        const card = this.createElement('div', {
            style: {
                background: 'var(--bg-card)',
                borderRadius: 'var(--radius-lg)',
                padding: '24px',
                maxWidth: '560px',
                width: '100%',
                maxHeight: '80vh',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
                boxShadow: 'var(--shadow-xl)'
            }
        });

        // 头部
        const header = this.createElement('div', {
            style: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' }
        });
        header.appendChild(this.createElement('h3', { style: { fontSize: '16px', fontWeight: '600', margin: '0' } }, '选择标准歌曲'));
        const closeBtn = this.createElement('button', {
            style: { border: 'none', background: 'none', fontSize: '20px', cursor: 'pointer', color: 'var(--text-muted)' },
            onClick: () => this.close()
        }, '✕');
        header.appendChild(closeBtn);
        card.appendChild(header);

        // 搜索
        card.appendChild(this._renderToolbar());

        // 列表
        this._listContainer = this.createElement('div', {
            style: { flex: '1', overflowY: 'auto', minHeight: '200px' }
        });
        card.appendChild(this._listContainer);

        // 底部
        const footer = this.createElement('div', {
            style: { display: 'flex', justifyContent: 'flex-end', gap: '8px', borderTop: '1px solid var(--border)', paddingTop: '12px' }
        });
        const cancelBtn = this.createElement('button', {
            className: 'btn btn-secondary',
            style: { padding: '8px 16px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', background: 'transparent', color: 'var(--text-primary)', cursor: 'pointer', fontSize: '13px' },
            onClick: () => this.close()
        }, '取消');
        footer.appendChild(cancelBtn);

        this._confirmBtn = this.createElement('button', {
            className: 'btn btn-primary',
            style: { padding: '8px 16px', borderRadius: 'var(--radius-md)', border: 'none', background: 'var(--primary)', color: '#fff', cursor: 'pointer', fontSize: '13px', fontWeight: '600', opacity: '0.5' },
            disabled: true,
            onClick: () => {
                if (this.#selectedSong) {
                    this.#onSelect(this.#selectedSong);
                    this.close();
                }
            }
        }, '确认选择');
        footer.appendChild(this._confirmBtn);
        card.appendChild(footer);

        this.el.appendChild(card);
        document.body.appendChild(this.el);
        this._renderList();
    }

    _renderToolbar() {
        const toolbar = this.createElement('div', {
            style: { display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }
        });

        // 搜索框
        const searchInput = this.createElement('input', {
            id: 'songSearch',
            type: 'text',
            placeholder: '搜索歌曲或歌手...',
            style: {
                flex: '1', minWidth: '150px',
                padding: '8px 12px',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-primary)',
                color: 'var(--text-primary)',
                fontSize: '13px',
                outline: 'none'
            },
            onInput: (e) => {
                this.#searchQuery = e.target.value;
                this.#page = 0;
                this._renderList();
            }
        });
        toolbar.appendChild(searchInput);

        // 难度筛选
        const diffSelect = this.createElement('select', {
            id: 'difficultyFilter',
            style: {
                padding: '8px 10px',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-primary)',
                color: 'var(--text-primary)',
                fontSize: '12px',
                outline: 'none'
            },
            onChange: (e) => {
                this.#difficultyFilter = e.target.value;
                this.#page = 0;
                this._renderList();
            }
        });
        ['all', '初级', '中级', '高级'].forEach(d => {
            const opt = this.createElement('option', { value: d }, d === 'all' ? '全部难度' : d);
            diffSelect.appendChild(opt);
        });
        toolbar.appendChild(diffSelect);

        // 风格筛选
        const styleSelect = this.createElement('select', {
            id: 'styleFilter',
            style: {
                padding: '8px 10px',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-primary)',
                color: 'var(--text-primary)',
                fontSize: '12px',
                outline: 'none'
            },
            onChange: (e) => {
                this.#styleFilter = e.target.value;
                this.#page = 0;
                this._renderList();
            }
        });
        ['all', '流行', '民谣', '美声', 'R&B', '摇滚', '爵士'].forEach(s => {
            const opt = this.createElement('option', { value: s }, s === 'all' ? '全部风格' : s);
            styleSelect.appendChild(opt);
        });
        toolbar.appendChild(styleSelect);

        return toolbar;
    }

    // ========================================================================
    // List rendering
    // ========================================================================

    _renderList() {
        if (!this._listContainer) return;

        if (this.#loading) {
            this._renderLoading();
            return;
        }

        // 过滤
        let filtered = this.#songs.filter(s => {
            // 搜索
            if (this.#searchQuery) {
                const q = this.#searchQuery.toLowerCase();
                if (!s.title.toLowerCase().includes(q) && !(s.artist || '').toLowerCase().includes(q)) {
                    return false;
                }
            }
            // 难度
            if (this.#difficultyFilter !== 'all' && s.difficulty !== this.#difficultyFilter) return false;
            // 风格
            if (this.#styleFilter !== 'all' && s.style !== this.#styleFilter) return false;
            return true;
        });

        // 分页
        const totalFiltered = filtered.length;
        const start = this.#page * this.#pageSize;
        const pageItems = filtered.slice(start, start + this.#pageSize);

        this._listContainer.innerHTML = '';

        if (pageItems.length === 0) {
            this._renderEmptyState(totalFiltered === 0 ? 'empty' : 'no-results');
            return;
        }

        // 卡片列表
        const list = this.createElement('div', {
            style: { display: 'flex', flexDirection: 'column', gap: '6px' }
        });

        pageItems.forEach(song => {
            const isSelected = this.#selectedSong?.id === song.id;
            const card = this.createElement('div', {
                className: 'song-card' + (isSelected ? ' selected' : ''),
                dataset: { songId: song.id },
                style: {
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '10px 12px',
                    borderRadius: 'var(--radius-md)',
                    background: isSelected ? 'var(--primary-ghost)' : 'var(--bg-elevated)',
                    border: isSelected ? '1px solid var(--primary)' : '1px solid transparent',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                },
                onClick: () => this._handleCardClick(song)
            });

            // 左侧信息
            const info = this.createElement('div', { style: { flex: '1', minWidth: '0' } });

            const titleRow = this.createElement('div', {
                style: { display: 'flex', alignItems: 'center', gap: '8px' }
            });

            // 歌名 (高亮搜索)
            if (this.#searchQuery) {
                const q = this.#searchQuery;
                const idx = song.title.toLowerCase().indexOf(q.toLowerCase());
                if (idx >= 0) {
                    const before = song.title.slice(0, idx);
                    const match = song.title.slice(idx, idx + q.length);
                    const after = song.title.slice(idx + q.length);
                    titleRow.innerHTML = '<span style="font-weight:600;font-size:14px;color:var(--text-primary);">'
                        + escapeHtml(before)
                        + '<span class="search-highlight" style="background:var(--primary-light);color:var(--primary);border-radius:2px;padding:0 2px;">'
                        + escapeHtml(match) + '</span>'
                        + escapeHtml(after) + '</span>';
                } else {
                    titleRow.appendChild(this.createElement('span', {
                        style: { fontWeight: '600', fontSize: '14px', color: 'var(--text-primary)' }
                    }, escapeHtml(song.title)));
                }
            } else {
                titleRow.appendChild(this.createElement('span', {
                    style: { fontWeight: '600', fontSize: '14px', color: 'var(--text-primary)' }
                }, escapeHtml(song.title)));
            }

            // 难度标签
            const diffColor = song.difficulty === '初级' ? '#22c55e'
                : song.difficulty === '中级' ? '#f59e0b' : '#ef4444';
            titleRow.appendChild(this.createElement('span', {
                style: {
                    fontSize: '10px', padding: '2px 6px', borderRadius: '10px',
                    background: diffColor + '20', color: diffColor,
                    fontWeight: '600', whiteSpace: 'nowrap'
                }
            }, song.difficulty || ''));
            info.appendChild(titleRow);

            // 副信息: 歌手 · 风格 · 时长
            const duration = song.duration ? Math.floor(song.duration / 60) + ':' + String(song.duration % 60).padStart(2, '0') : '';
            const meta = this.createElement('div', {
                style: { fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }
            }, (song.artist || '未知') + ' · ' + (song.style || '') + (duration ? ' · ' + duration : ''));
            info.appendChild(meta);

            card.appendChild(info);

            // 右侧操作: 选择 / 已选
            if (isSelected) {
                card.appendChild(this.createElement('span', {
                    style: { fontSize: '12px', color: 'var(--primary)', fontWeight: '600', whiteSpace: 'nowrap' }
                }, '✓ 已选'));
            } else {
                card.appendChild(this.createElement('button', {
                    className: 'btn-select-song',
                    style: {
                        padding: '4px 12px', fontSize: '12px', borderRadius: 'var(--radius-sm)',
                        border: '1px solid var(--primary)', background: 'transparent',
                        color: 'var(--primary)', cursor: 'pointer', fontWeight: '500', whiteSpace: 'nowrap'
                    },
                    onClick: (e) => { e.stopPropagation(); this._handleSelect(song); }
                }, '选择'));
            }

            list.appendChild(card);

            // 详情展开 (如果当前卡片被选中且有 showDetail)
            if (isSelected && this.#showDetail && (song.key || song.bpm)) {
                const detail = this.createElement('div', {
                    className: 'song-detail',
                    style: {
                        padding: '10px 12px', marginTop: '-4px',
                        background: 'var(--bg-primary)', borderRadius: '0 0 var(--radius-md) var(--radius-md)',
                        fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.8'
                    }
                });
                const items = [];
                if (song.key) items.push('调性: ' + song.key);
                if (song.bpm) items.push('BPM: ' + song.bpm);
                if (song.range) items.push('音域: ' + song.range);
                detail.textContent = items.join('  |  ');

                // 预览播放器
                if (song.previewUrl) {
                    const audio = this.createElement('audio', {
                        controls: true,
                        style: { width: '100%', marginTop: '6px', height: '32px' }
                    });
                    audio.innerHTML = '<source src="' + song.previewUrl + '" type="audio/mpeg">';
                    detail.appendChild(audio);
                }

                this._listContainer.appendChild(detail);
            }
        });

        this._listContainer.appendChild(list);

        // 分页控件
        if (totalFiltered > this.#pageSize) {
            this._renderPagination(totalFiltered);
        }

        // 统计
        const stats = this.createElement('div', {
            id: 'songStats',
            style: { fontSize: '11px', color: 'var(--text-muted)', textAlign: 'center', padding: '4px 0' }
        }, '共 ' + totalFiltered + ' 首歌曲'
            + (this.#searchQuery || this.#difficultyFilter !== 'all' || this.#styleFilter !== 'all' ? ' (筛选)' : ''));
        this._listContainer.appendChild(stats);
    }

    _renderLoading() {
        if (!this._listContainer) return;
        this._listContainer.innerHTML = '';
        for (let i = 0; i < 5; i++) {
            const skeleton = this.createElement('div', {
                className: 'skeleton',
                style: {
                    height: '48px', marginBottom: '8px',
                    background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)',
                    animation: 'pulse 1.5s infinite'
                }
            });
            this._listContainer.appendChild(skeleton);
        }
    }

    _renderEmptyState(reason) {
        if (!this._listContainer) return;
        this._listContainer.innerHTML = '';

        const empty = this.createElement('div', {
            id: reason === 'empty' ? 'selectorEmpty' : 'searchEmpty',
            style: { textAlign: 'center', padding: '40px 20px', color: 'var(--text-muted)' }
        });

        if (reason === 'empty') {
            empty.innerHTML = '<div style="font-size:36px;margin-bottom:12px;">📭</div>'
                + '<p style="font-weight:500;">曲库为空</p>'
                + '<p style="font-size:12px;">请先导入标准歌曲</p>';
        } else {
            empty.innerHTML = '<div style="font-size:36px;margin-bottom:12px;">🔍</div>'
                + '<p style="font-weight:500;">未找到匹配歌曲</p>'
                + '<p style="font-size:12px;">尝试其他关键词或筛选条件</p>';
        }

        this._listContainer.appendChild(empty);
    }

    _renderPagination(total) {
        const totalPages = Math.ceil(total / this.#pageSize);
        const currentPage = this.#page + 1;

        const pagination = this.createElement('div', {
            id: 'pageIndicator',
            style: { display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '12px', padding: '8px 0', fontSize: '12px', color: 'var(--text-muted)' }
        });

        const prevBtn = this.createElement('button', {
            style: {
                padding: '4px 12px', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)',
                background: this.#page === 0 ? 'var(--bg-elevated)' : 'var(--bg-primary)',
                color: this.#page === 0 ? 'var(--text-muted)' : 'var(--text-primary)',
                cursor: this.#page === 0 ? 'default' : 'pointer', fontSize: '12px'
            },
            disabled: this.#page === 0,
            onClick: () => { if (this.#page > 0) { this.#page--; this._renderList(); } }
        }, '← 上一页');
        pagination.appendChild(prevBtn);

        pagination.appendChild(this.createElement('span', {}, '第 ' + currentPage + ' 页 / 共 ' + totalPages + ' 页'));

        const nextBtn = this.createElement('button', {
            id: 'nextPageBtn',
            style: {
                padding: '4px 12px', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)',
                background: this.#page >= totalPages - 1 ? 'var(--bg-elevated)' : 'var(--bg-primary)',
                color: this.#page >= totalPages - 1 ? 'var(--text-muted)' : 'var(--text-primary)',
                cursor: this.#page >= totalPages - 1 ? 'default' : 'pointer', fontSize: '12px'
            },
            disabled: this.#page >= totalPages - 1,
            onClick: () => { if (this.#page < totalPages - 1) { this.#page++; this._renderList(); } }
        }, '下一页 →');
        pagination.appendChild(nextBtn);

        this._listContainer.appendChild(pagination);
    }

    // ========================================================================
    // Actions
    // ========================================================================

    _handleCardClick(song) {
        if (this.#selectedSong?.id === song.id) {
            // 切换详情展开/收起
            this.#showDetail = !this.#showDetail;
        } else {
            this.#selectedSong = song;
            this.#showDetail = true;
        }
        this._renderList();
    }

    _handleSelect(song) {
        this.#selectedSong = song;
        this.#showDetail = false;
        if (this.#mode === 'modal') {
            // Modal 模式: 启用确认按钮
            if (this._confirmBtn) {
                this._confirmBtn.disabled = false;
                this._confirmBtn.style.opacity = '1';
            }
            this._renderList();
        } else {
            // Inline 模式: 直接回调
            this.#onSelect(song);
            this._renderList();
        }
    }

    close() {
        if (this.el && this.el.parentNode) {
            this.el.remove();
        }
    }

    destroy() {
        this.close();
        super.destroy();
    }
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

export default StandardAudioSelector;
