/**
 * HistoryPage 鈥?鍘嗗彶璁板綍椤?(鎴愰暱鏇茬嚎 + 鎵归噺绠＄悊)
 *
 * 璺敱: #/history
 * 鍏ュ満: AnimationController page-enter (BaseComponent 鑷姩)
 *
 * @version 2.0
 */

import { BaseComponent } from '../components/BaseComponent.js';
import { showToast } from '../components/Toast.js';
import { confirm } from '../components/Modal.js';
import { ApiClient } from '../services/api.js';

export class HistoryPage extends BaseComponent {
    static animationPreset = 'page-enter';

    _api;
    _records = [];
    _filter = 'all';
    _selectionMode = false;
    _selectedIds = new Set();
    _growthChart = null;

    constructor(container, options = {}) {
        super(container, options);
        this._api = options.api || new ApiClient();
    }

    async mount(params) {
        this.render();
        this.bindEvents();
        await this._loadHistory();

        // Animate entrance with AnimationController
        if (this.ac) {
            const cards = this.el.querySelectorAll('.stats-grid > div');
            const items = this.el.querySelectorAll('.history-card');
            if (cards.length) this.ac.stagger(cards, { preset: 'slideUp', stagger: 0.08, duration: 0.5 });
            if (items.length) this.ac.stagger(items, { preset: 'slideUp-sm', stagger: 0.05, duration: 0.4 });
        } else if (typeof gsap !== 'undefined') {
            const cards = this.el.querySelectorAll('.stats-grid > div');
            const items = this.el.querySelectorAll('.history-card');
            const tl = gsap.timeline();
            if (cards.length) tl.fromTo(cards, { opacity: 0, y: 30 }, { opacity: 1, y: 0, stagger: 0.08, duration: 0.5, ease: 'power2.out' });
            if (items.length) tl.fromTo(items, { opacity: 0, y: 20 }, { opacity: 1, y: 0, stagger: 0.05, duration: 0.4, ease: 'power2.out' }, '-=0.2');
        }
    }

    render() {
        this.el = this.createElement('div', { id: 'page-history', className: 'page page-container' });

        this.el.innerHTML = `
        <div class="history-header" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;flex-wrap:wrap;gap:12px;">
            <h2 style="font-size:18px;font-weight:600;">评估历史</h2>
            <div class="filter-group" style="display:flex;gap:6px;">
                <button class="filter-btn active" data-filter="all">全部</button>
                <button class="filter-btn" data-filter="today">今天</button>
                <button class="filter-btn" data-filter="week">本周</button>
                <button class="filter-btn" data-filter="month">本月</button>
            </div>
        </div>

        <div id="batchBar" style="display:none;justify-content:space-between;align-items:center;padding:12px 16px;background:var(--bg-elevated);border-radius:8px;margin-bottom:16px;border:1px solid var(--border);">
            <div style="display:flex;align-items:center;gap:10px;">
                <button class="btn btn-secondary btn-sm" id="selectAllBtn">全选</button>
                <span id="selectedCount" style="color:var(--text-muted);font-size:12px;">已选择 0 条</span>
            </div>
            <div style="display:flex;gap:8px;">
                <button id="deleteSelectedBtn" class="btn btn-sm" style="background:#ef4444;color:#fff;border:none;border-radius:6px;cursor:pointer;padding:6px 12px;font-size:12px;" disabled>删除选中</button>
                <button class="btn btn-secondary btn-sm" id="cancelSelectionBtn">取消</button>
            </div>
        </div>

        <div style="display:flex;gap:10px;margin-bottom:16px;">
            <button class="btn btn-secondary btn-sm" id="batchModeBtn">☑️ 批量管理</button>
            <button class="btn btn-sm" id="deleteAllBtn" style="background:#ef4444;color:#fff;border:none;border-radius:6px;cursor:pointer;padding:8px 16px;font-size:13px;">🗑️ 清空全部</button>
        </div>

        <div class="card" style="margin-bottom:20px;">
            <div class="card-header"><span class="card-title">📱 成长曲线</span></div>
            <div class="card-body">
                <div style="height:250px;"><canvas id="growthChart"></canvas></div>
                <div class="stats-grid" style="margin-top:16px;">
                    <div style="text-align:center;"><div style="font-size:11px;color:var(--text-muted);">平均分</div><div id="avgScore" style="font-size:24px;font-weight:700;color:var(--primary);">--</div></div>
                    <div style="text-align:center;"><div style="font-size:11px;color:var(--text-muted);">最高分</div><div id="maxScore" style="font-size:24px;font-weight:700;color:var(--success);">--</div></div>
                    <div style="text-align:center;"><div style="font-size:11px;color:var(--text-muted);">最低分</div><div id="minScore" style="font-size:24px;font-weight:700;color:var(--danger);">--</div></div>
                    <div style="text-align:center;"><div style="font-size:11px;color:var(--text-muted);">练习次数</div><div id="totalCount" style="font-size:24px;font-weight:700;color:var(--accent-blue);">--</div></div>
                </div>
            </div>
        </div>

        <div class="card">
            <div class="card-header"><span class="card-title">📵 历史记录</span></div>
            <div class="card-body" id="historyList">
                <div class="empty-state" style="text-align:center;padding:40px 20px;color:var(--text-muted);">
                    <div style="font-size:36px;margin-bottom:12px;">📥</div>
                    <p>暂无评估记录</p>
                    <p style="font-size:13px;">开始你的第一次声乐评估吧</p>
                </div>
            </div>
        </div>
        `;
        this.container.appendChild(this.el);
    }

    bindEvents() {
        this.el.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', () => this._onFilter(btn.dataset.filter));
        });
        this.el.querySelector('#batchModeBtn')?.addEventListener('click', () => this._toggleSelectionMode());
        this.el.querySelector('#cancelSelectionBtn')?.addEventListener('click', () => this._toggleSelectionMode());
        this.el.querySelector('#selectAllBtn')?.addEventListener('click', () => this._selectAll());
        this.el.querySelector('#deleteSelectedBtn')?.addEventListener('click', () => this._deleteSelected());
        this.el.querySelector('#deleteAllBtn')?.addEventListener('click', () => this._deleteAll());
    }

    async _loadHistory() {
        try {
            const res = await this._api.getHistory();
            this._records = (res?.history || []).filter(r => {
                if (this._filter === 'all') return true;
                const now = new Date();
                const d = new Date(r.timestamp);
                if (this._filter === 'today') return d.toDateString() === now.toDateString();
                if (this._filter === 'week') return (now - d) < 7 * 24 * 60 * 60 * 1000;
                if (this._filter === 'month') return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
                return true;
            });
        } catch (e) {
            this._records = [];
        }
        this._renderList();
        this._drawGrowthChart();
        this._updateStats();
    }

    _renderList() {
        const container = this.el.querySelector('#historyList');
        if (this._records.length === 0) {
            container.innerHTML = '<div class="empty-state" style="text-align:center;padding:40px 20px;color:var(--text-muted);">' +
                '<div style="font-size:36px;margin-bottom:12px;">📥</div><p>暂无评估记录</p></div>';
            return;
        }

        container.innerHTML = this._records.map(r =>
            '<div class="history-card" data-id="' + r.id + '" style="display:flex;align-items:center;justify-content:space-between;padding:12px 0;border-bottom:1px solid var(--border);cursor:pointer;">'
            + (this._selectionMode
                ? '<input type="checkbox" class="history-checkbox" ' + (this._selectedIds.has(r.id) ? 'checked' : '') + ' style="margin-right:12px;">'
                : '')
            + '<div style="flex:1;">'
            + '<div style="font-weight:600;color:var(--text-primary);">' + this._escapeHtml(r.filename || '鏈煡鏂囦欢') + '</div>'
            + '<div style="font-size:12px;color:var(--text-muted);">'
            + (r.timestamp ? new Date(r.timestamp).toLocaleString("zh-CN") : "")
            + " " + (r.mode || "") + ""
            + '<div style="display:flex;align-items:center;gap:12px;">'
            + '<span style="font-size:20px;font-weight:700;color:var(--primary);">' + (r.total_score?.toFixed(1) || '--') + '</span>'
            + '<span class="btn-icon" data-action="delete-single" data-id="' + r.id + '">馃棏锔?/span>'
            + '</div></div>'
        ).join('');

        // 缁戝畾鐩戝惉
        container.querySelectorAll('.history-card').forEach(card => {
            if (this._selectionMode) {
                card.querySelector('.history-checkbox')?.addEventListener('change', (e) => {
                    const id = parseInt(card.dataset.id);
                    if (e.target.checked) this._selectedIds.add(id);
                    else this._selectedIds.delete(id);
                    this._updateSelectionUI();
                });
            }
            card.addEventListener('click', (e) => {
                if (e.target.closest('.btn-icon') || e.target.closest('.history-checkbox')) return;
                const analysisId = card.dataset.id;
                if (this.router) this.router.navigate('#/report/' + analysisId);
            });
        });
        container.querySelectorAll('[data-action="delete-single"]').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const id = parseInt(btn.dataset.id);
                const ok = await confirm('纭鍒犻櫎', '鍒犻櫎姝よ褰曪紵');
                if (ok) {
                    await this._api.deleteHistory(id);
                    showToast("Deleted","success");
                    await this._loadHistory();
                }
            });
        });
    }

    _drawGrowthChart() {
        if (typeof Chart === 'undefined') return;
        if (this._records.length === 0) return;
        const canvas = this.el.querySelector('#growthChart');
        if (!canvas) return;
        if (this._growthChart) this._growthChart.destroy();

        const ctx = canvas.getContext('2d');
        const sorted = [...this._records].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
        const labels = sorted.map((_, i) => '#' + (i + 1));
        const data = sorted.map(r => r.total_score || 0);

        this._growthChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [{
                    label: '璇勫垎瓒嬪娍', data,
                    borderColor: 'rgb(99, 102, 241)',
                    backgroundColor: 'rgba(99, 102, 241, 0.1)',
                    fill: true, tension: 0.3, pointRadius: 4,
                    pointBackgroundColor: 'rgb(99, 102, 241)'
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                scales: { y: { min: 0, max: 100, ticks: { stepSize: 20 } } },
                plugins: { legend: { display: false } }
            }
        });
    }

    _updateStats() {
        if (this._records.length === 0) {
            this.el.querySelector('#avgScore').textContent = '--';
            this.el.querySelector('#maxScore').textContent = '--';
            this.el.querySelector('#minScore').textContent = '--';
            this.el.querySelector('#totalCount').textContent = '0';
            return;
        }
        const scores = this._records.map(r => r.total_score || 0);
        this.el.querySelector('#avgScore').textContent = Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
        this.el.querySelector('#maxScore').textContent = Math.round(Math.max(...scores));
        this.el.querySelector('#minScore').textContent = Math.round(Math.min(...scores));
        this.el.querySelector('#totalCount').textContent = this._records.length;
    }

    async _onFilter(filter) {
        this._filter = filter;
        this.el.querySelectorAll('.filter-btn').forEach(b => b.classList.toggle('active', b.dataset.filter === filter));
        await this._loadHistory();
    }

    _toggleSelectionMode() {
        this._selectionMode = !this._selectionMode;
        this._selectedIds.clear();
        this.el.querySelector('#batchBar').style.display = this._selectionMode ? 'flex' : 'none';
        this.el.querySelector('#batchModeBtn').style.display = this._selectionMode ? 'none' : '';
        this._renderList();
        this._updateSelectionUI();
    }

    _selectAll() {
        const allIds = this._records.map(r => r.id);
        this._selectedIds = new Set(allIds.length === 0 || this._selectedIds.size === allIds.length ? [] : allIds);
        this._renderList();
        this._updateSelectionUI();
    }

    _updateSelectionUI() {
        const deleteBtn = this.el.querySelector('#deleteSelectedBtn');
        if (deleteBtn) {
            deleteBtn.disabled = this._selectedIds.size === 0;
            deleteBtn.textContent = '删除选中 (' + this._selectedIds.size + ')';
        }
    }

    async _deleteSelected() {
        if (this._selectedIds.size === 0) return;
        const ok = await confirm('纭鍒犻櫎', '纭畾删除选中鐨?' + this._selectedIds.size + ' 鏉¤褰曪紵');
        if (ok) {
            await this._api.deleteHistoryBatch([...this._selectedIds]);
            showToast("Deleted","success");
            this._selectedIds.clear();
            this._toggleSelectionMode();
            await this._loadHistory();
        }
    }

    async _deleteAll() {
        const ok = await confirm('确认清空', '确定要清空全部历史记录吗？此操作不可恢复。');
        if (ok) {
            await this._api.deleteHistoryAll();
            showToast("已清空全部记录", "success");
            await this._loadHistory();
        }
    }

    _escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    destroy() {
        if (this._growthChart) {
            this._growthChart.destroy();
            this._growthChart = null;
        }
        super.destroy();
    }
}

export default HistoryPage;
