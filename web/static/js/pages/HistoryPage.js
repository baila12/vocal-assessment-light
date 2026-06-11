/**
 * HistoryPage — 历史记录页 (成长曲线 + 批量管理)
 *
 * 路由: #/history
 *
 * @version 1.0
 */

import { BaseComponent } from '../components/BaseComponent.js';
import { showToast } from '../components/Toast.js';
import { confirm } from '../components/Modal.js';
import { ApiClient } from '../services/api.js';
import { staggerSlideUp, staggerFadeIn } from '../effects/entrances.js';

export class HistoryPage extends BaseComponent {
    /** @type {ApiClient} */
    #api;

    /** @type {Array} */
    #records = [];

    /** @type {string} */
    #filter = 'all';

    /** @type {boolean} */
    #selectionMode = false;

    /** @type {Set<number>} */
    #selectedIds = new Set();

    /** @type {Chart|null} */
    #growthChart = null;

    constructor(container, options = {}) {
        super(container, options);
        this.#api = options.api || new ApiClient();
    }

    async mount(params) {
        this.render();
        this.bindEvents();
        await this.#loadHistory();

        // GSAP 入场
        if (typeof gsap !== 'undefined') {
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

        <!-- 批量操作栏 -->
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

        <!-- 操作按钮 -->
        <div style="display:flex;gap:10px;margin-bottom:16px;">
            <button class="btn btn-secondary btn-sm" id="batchModeBtn">☑️ 批量管理</button>
            <button class="btn btn-sm" id="deleteAllBtn" style="background:#ef4444;color:#fff;border:none;border-radius:6px;cursor:pointer;padding:8px 16px;font-size:13px;">🗑️ 清空全部</button>
        </div>

        <!-- 成长曲线 -->
        <div class="card" style="margin-bottom:20px;">
            <div class="card-header"><span class="card-title">📈 成长曲线</span></div>
            <div class="card-body">
                <div style="height:250px;"><canvas id="growthChart"></canvas></div>
                <div class="stats-grid" style="margin-top:16px;">
                    <div style="text-align:center;"><div style="font-size:11px;color:var(--text-muted);">平均分</div><div id="avgScore" style="font-size:24px;font-weight:700;color:var(--primary);">--</div></div>
                    <div style="text-align:center;"><div style="font-size:11px;color:var(--text-muted);">最高分</div><div id="maxScore" style="font-size:24px;font-weight:700;color:var(--success);">--</div></div>
                    <div style="text-align:center;"><div style="font-size:11px;color:var(--text-muted);">最低分</div><div id="minScore" style="font-size:24px;font-weight:700;color:var(--danger);">--</div></div>
                    <div style="text-align:center;"><div style="font-size:11px;color:var(--text-muted);">练习次数</div><div id="totalCount" style="font-size:24px;font-weight:700;color:var(--purple);">--</div></div>
                </div>
            </div>
        </div>

        <!-- 历史列表 -->
        <div class="history-grid" id="historyGrid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px;"></div>

        <!-- 空状态 -->
        <div id="historyEmpty" style="display:none;text-align:center;padding:40px;color:var(--text-muted);">暂无评估记录</div>`;

        this.container.appendChild(this.el);
    }

    bindEvents() {
        // 筛选按钮
        this.el.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', () => this.#onFilter(btn.dataset.filter));
        });

        // 批量模式
        this.el.querySelector('#batchModeBtn')?.addEventListener('click', () => this.#toggleSelectionMode());
        this.el.querySelector('#cancelSelectionBtn')?.addEventListener('click', () => this.#toggleSelectionMode());
        this.el.querySelector('#selectAllBtn')?.addEventListener('click', () => this.#selectAll());
        this.el.querySelector('#deleteSelectedBtn')?.addEventListener('click', () => this.#deleteSelected());

        // 清空全部
        this.el.querySelector('#deleteAllBtn')?.addEventListener('click', async () => {
            const ok = await confirm('确认清空', '确定要删除所有历史记录吗？此操作不可撤销。');
            if (ok) {
                await this.#api.deleteHistoryBatch(this.#records.map(r => r.id));
                showToast('已清空所有记录', 'success');
                await this.#loadHistory();
            }
        });
    }

    // ========================================================================
    // 数据加载
    // ========================================================================

    async #loadHistory() {
        try {
            const data = await this.#api.getHistory(this.#filter);
            this.#records = data.history || [];
            this.#renderList();
            this.#drawGrowthChart();
            this.#updateStats();
        } catch (e) {
            showToast('加载历史记录失败: ' + e.message, 'error');
        }
    }

    #renderList() {
        const grid = this.el.querySelector('#historyGrid');
        const empty = this.el.querySelector('#historyEmpty');
        if (!grid) return;

        if (this.#records.length === 0) {
            grid.innerHTML = '';
            if (empty) empty.style.display = 'block';
            return;
        }

        if (empty) empty.style.display = 'none';

        grid.innerHTML = this.#records.map(r => {
            const score = Math.round(r.total_score || 0);
            const color = score >= 90 ? '#22c55e' : score >= 80 ? '#3b82f6' : score >= 70 ? '#f59e0b' : score >= 60 ? '#f97316' : '#ef4444';
            const checked = this.#selectedIds.has(r.id) ? 'checked' : '';
            return `
            <div class="history-card" data-id="${r.id}" style="background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius-lg);padding:16px;cursor:pointer;position:relative;">
                ${this.#selectionMode ? `<input type="checkbox" class="select-checkbox" data-id="${r.id}" ${checked} style="position:absolute;top:12px;left:12px;width:18px;height:18px;cursor:pointer;">` : ''}
                <div class="filename" style="font-size:14px;font-weight:500;margin-bottom:8px;${this.#selectionMode ? 'margin-left:28px;' : ''}">${this.#escapeHtml(r.filename || '未知')}</div>
                <div style="font-size:28px;font-weight:700;color:${color};margin-bottom:4px;">${score}分</div>
                <div class="time" style="font-size:12px;color:var(--text-muted);">${r.timestamp || ''}</div>
                <button class="delete-btn" data-id="${r.id}" style="position:absolute;top:12px;right:12px;width:24px;height:24px;border:none;background:transparent;color:var(--text-muted);cursor:pointer;font-size:16px;border-radius:var(--radius-sm);">×</button>
            </div>`;
        }).join('');

        // 绑定事件
        grid.querySelectorAll('.history-card').forEach(card => {
            card.addEventListener('click', (e) => {
                if (e.target.classList.contains('select-checkbox')) return;
                if (e.target.classList.contains('delete-btn')) return;

                if (this.#selectionMode) {
                    const id = parseInt(card.dataset.id);
                    this.#toggleSelect(id);
                } else {
                    const id = card.dataset.id;
                    if (this.router) this.router.navigate(`#/report/${id}`);
                }
            });
        });

        grid.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const id = parseInt(btn.dataset.id);
                await this.#api.deleteHistory(id);
                showToast('已删除', 'success');
                await this.#loadHistory();
            });
        });

        grid.querySelectorAll('.select-checkbox').forEach(cb => {
            cb.addEventListener('change', (e) => {
                const id = parseInt(cb.dataset.id);
                if (cb.checked) this.#selectedIds.add(id);
                else this.#selectedIds.delete(id);
                this.#updateSelectionUI();
            });
        });
    }

    #drawGrowthChart() {
        if (typeof Chart === 'undefined') return;
        if (this.#records.length === 0) return;

        const canvas = this.el.querySelector('#growthChart');
        if (!canvas) return;

        if (this.#growthChart) this.#growthChart.destroy();

        const ctx = canvas.getContext('2d');
        const sorted = [...this.#records].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
        const labels = sorted.map((_, i) => `#${i + 1}`);
        const data = sorted.map(r => r.total_score || 0);

        this.#growthChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [{
                    label: '评分趋势',
                    data,
                    borderColor: 'rgb(99, 102, 241)',
                    backgroundColor: 'rgba(99, 102, 241, 0.1)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 4,
                    pointBackgroundColor: 'rgb(99, 102, 241)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { min: 0, max: 100, ticks: { stepSize: 20 } }
                },
                plugins: { legend: { display: false } }
            }
        });
    }

    #updateStats() {
        if (this.#records.length === 0) {
            this.el.querySelector('#avgScore').textContent = '--';
            this.el.querySelector('#maxScore').textContent = '--';
            this.el.querySelector('#minScore').textContent = '--';
            this.el.querySelector('#totalCount').textContent = '0';
            return;
        }
        const scores = this.#records.map(r => r.total_score || 0);
        this.el.querySelector('#avgScore').textContent = Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
        this.el.querySelector('#maxScore').textContent = Math.round(Math.max(...scores));
        this.el.querySelector('#minScore').textContent = Math.round(Math.min(...scores));
        this.el.querySelector('#totalCount').textContent = this.#records.length;
    }

    // ========================================================================
    // 交互
    // ========================================================================

    async #onFilter(filter) {
        this.#filter = filter;
        this.el.querySelectorAll('.filter-btn').forEach(b => b.classList.toggle('active', b.dataset.filter === filter));
        await this.#loadHistory();
    }

    #toggleSelectionMode() {
        this.#selectionMode = !this.#selectionMode;
        this.#selectedIds.clear();
        this.el.querySelector('#batchBar').style.display = this.#selectionMode ? 'flex' : 'none';
        this.el.querySelector('#batchModeBtn').style.display = this.#selectionMode ? 'none' : '';
        this.#renderList();
        this.#updateSelectionUI();
    }

    #selectAll() {
        const allIds = this.#records.map(r => r.id);
        if (this.#selectedIds.size === allIds.length) {
            this.#selectedIds.clear();
        } else {
            this.#selectedIds = new Set(allIds);
        }
        this.#renderList();
        this.#updateSelectionUI();
    }

    #toggleSelect(id) {
        if (this.#selectedIds.has(id)) this.#selectedIds.delete(id);
        else this.#selectedIds.add(id);
        this.#renderList();
        this.#updateSelectionUI();
    }

    #updateSelectionUI() {
        this.el.querySelector('#selectedCount').textContent = `已选择 ${this.#selectedIds.size} 条`;
        const deleteBtn = this.el.querySelector('#deleteSelectedBtn');
        if (deleteBtn) {
            deleteBtn.disabled = this.#selectedIds.size === 0;
            deleteBtn.textContent = `删除选中 (${this.#selectedIds.size})`;
        }
    }

    async #deleteSelected() {
        if (this.#selectedIds.size === 0) return;
        const ok = await confirm('确认删除', `确定删除选中的 ${this.#selectedIds.size} 条记录？`);
        if (ok) {
            await this.#api.deleteHistoryBatch([...this.#selectedIds]);
            showToast(`已删除 ${this.#selectedIds.size} 条`, 'success');
            this.#selectedIds.clear();
            this.#toggleSelectionMode();
            await this.#loadHistory();
        }
    }

    #escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    destroy() {
        if (this.#growthChart) {
            this.#growthChart.destroy();
            this.#growthChart = null;
        }
        super.destroy();
    }
}

export default HistoryPage;
