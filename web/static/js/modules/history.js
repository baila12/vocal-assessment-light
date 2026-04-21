/**
 * 历史记录模块 v2.0
 * 支持分页、批量删除功能
 */

import { AppState } from './state.js';
import { Utils, showToast, escapeHtml } from './utils.js';

let growthChartInstance = null;

// 分页状态
const HistoryState = {
    currentPage: 1,
    totalPages: 1,
    total: 0,
    limit: 20,
    dateFilter: 'all',
    selectedIds: new Set(),
    selectionMode: false
};

function loadHistory() {
    const url = `/api/history?page=${HistoryState.currentPage}&limit=${HistoryState.limit}&date=${HistoryState.dateFilter}`;

    fetch(url)
        .then(r => r.json())
        .then(data => {
            // 更新分页状态
            HistoryState.total = data.total || 0;
            HistoryState.totalPages = data.total_pages || 1;
            HistoryState.currentPage = data.page || 1;

            const container = document.getElementById('historyGrid');
            if (!container || !data.history) return;

            // 绘制成长曲线
            drawGrowthChart(data.history);
            updateGrowthStats(data.history);

            // 渲染历史记录列表
            renderHistoryList(data.history, container);

            // 渲染分页控件
            renderPagination();

            // 更新批量操作栏
            updateBatchActionBar();
        })
        .catch(e => console.error('加载历史失败:', e));
}

/**
 * 渲染历史记录列表
 */
function renderHistoryList(history, container) {
    if (!history || history.length === 0) {
        container.innerHTML = '<p style="color:var(--text-muted);text-align:center;grid-column:1/-1;padding:40px;">暂无历史记录</p>';
        return;
    }

    container.innerHTML = history.map(h => {
        const isSelected = HistoryState.selectedIds.has(h.id);
        return `
            <div class="history-card ${isSelected ? 'selected' : ''}" data-id="${h.id}" onclick="window.handleHistoryCardClick(${h.id}, event)">
                ${HistoryState.selectionMode ? `
                    <input type="checkbox" class="history-checkbox" ${isSelected ? 'checked' : ''}
                           onclick="event.stopPropagation(); window.toggleHistorySelection(${h.id})">
                ` : ''}
                <div class="filename">${escapeHtml(h.filename) || '未知'}</div>
                <div class="score" style="color:${Utils.getScoreColor(h.total_score || 0)}">${Math.round(h.total_score || 0)}分</div>
                <div class="time">${formatTimestamp(h.timestamp)}</div>
                ${!HistoryState.selectionMode ? `
                    <button class="delete-btn" onclick="event.stopPropagation(); deleteHistoryRecord(${h.id})" title="删除">×</button>
                ` : ''}
            </div>
        `;
    }).join('');
}

/**
 * 格式化时间戳
 */
function formatTimestamp(timestamp) {
    if (!timestamp) return '';
    try {
        const date = new Date(timestamp);
        if (isNaN(date.getTime())) return timestamp;
        return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours()}:${String(date.getMinutes()).padStart(2, '0')}`;
    } catch {
        return timestamp;
    }
}

/**
 * 渲染分页控件
 */
function renderPagination() {
    let paginationContainer = document.getElementById('historyPagination');

    // 如果不存在，创建分页容器
    if (!paginationContainer) {
        const historyGrid = document.getElementById('historyGrid');
        if (historyGrid && historyGrid.parentElement) {
            paginationContainer = document.createElement('div');
            paginationContainer.id = 'historyPagination';
            paginationContainer.style.cssText = 'display:flex;justify-content:center;align-items:center;gap:8px;margin-top:20px;padding:10px;flex-wrap:wrap;';
            historyGrid.parentElement.appendChild(paginationContainer);
        } else {
            return;
        }
    }

    if (HistoryState.totalPages <= 1) {
        paginationContainer.innerHTML = `<span style="color:var(--text-muted);font-size:12px;">共 ${HistoryState.total} 条记录</span>`;
        return;
    }

    const prevDisabled = HistoryState.currentPage <= 1 ? 'disabled' : '';
    const nextDisabled = HistoryState.currentPage >= HistoryState.totalPages ? 'disabled' : '';

    // 生成页码按钮
    let pageButtons = '';
    const maxVisiblePages = 5;
    let startPage = Math.max(1, HistoryState.currentPage - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(HistoryState.totalPages, startPage + maxVisiblePages - 1);

    if (endPage - startPage < maxVisiblePages - 1) {
        startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }

    if (startPage > 1) {
        pageButtons += `<button class="page-btn" onclick="window.goToHistoryPage(1)">1</button>`;
        if (startPage > 2) {
            pageButtons += `<span style="color:var(--text-muted);">...</span>`;
        }
    }

    for (let i = startPage; i <= endPage; i++) {
        const isActive = i === HistoryState.currentPage ? 'active' : '';
        pageButtons += `<button class="page-btn ${isActive}" onclick="window.goToHistoryPage(${i})">${i}</button>`;
    }

    if (endPage < HistoryState.totalPages) {
        if (endPage < HistoryState.totalPages - 1) {
            pageButtons += `<span style="color:var(--text-muted);">...</span>`;
        }
        pageButtons += `<button class="page-btn" onclick="window.goToHistoryPage(${HistoryState.totalPages})">${HistoryState.totalPages}</button>`;
    }

    paginationContainer.innerHTML = `
        <button class="page-btn" ${prevDisabled} onclick="window.goToHistoryPage(${HistoryState.currentPage - 1})">‹ 上一页</button>
        ${pageButtons}
        <button class="page-btn" ${nextDisabled} onclick="window.goToHistoryPage(${HistoryState.currentPage + 1})">下一页 ›</button>
        <span style="color:var(--text-muted);font-size:12px;margin-left:10px;">共 ${HistoryState.total} 条</span>
    `;

    addPaginationStyles();
}

/**
 * 添加分页样式
 */
function addPaginationStyles() {
    if (document.getElementById('paginationStyle')) return;

    const styleEl = document.createElement('style');
    styleEl.id = 'paginationStyle';
    styleEl.textContent = `
        .page-btn {
            padding: 6px 12px;
            border: 1px solid var(--border);
            background: var(--bg-elevated);
            color: var(--text-primary);
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.2s;
        }
        .page-btn:hover:not(:disabled) {
            background: var(--primary);
            color: white;
            border-color: var(--primary);
        }
        .page-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .page-btn.active {
            background: var(--primary);
            color: white;
            border-color: var(--primary);
        }
        .history-card.selected {
            border: 2px solid var(--primary);
            background: rgba(59, 130, 246, 0.1);
        }
        .history-checkbox {
            position: absolute;
            top: 8px;
            left: 8px;
            width: 18px;
            height: 18px;
            cursor: pointer;
        }
    `;
    document.head.appendChild(styleEl);
}

/**
 * 跳转到指定页
 */
function goToHistoryPage(page) {
    if (page < 1 || page > HistoryState.totalPages) return;
    HistoryState.currentPage = page;
    loadHistory();
}

/**
 * 切换选择模式
 */
function toggleSelectionMode() {
    HistoryState.selectionMode = !HistoryState.selectionMode;
    HistoryState.selectedIds.clear();
    loadHistory();
    updateBatchActionBar();
    updateBatchModeButtons();
}

/**
 * 更新批量模式按钮显示状态
 */
function updateBatchModeButtons() {
    const enterBatchBtn = document.getElementById('enterBatchModeBtn');
    const deleteAllBtn = document.getElementById('deleteAllBtn');

    if (HistoryState.selectionMode) {
        // 批量模式下隐藏入口按钮
        if (enterBatchBtn) enterBatchBtn.style.display = 'none';
        if (deleteAllBtn) deleteAllBtn.style.display = 'none';
    } else {
        // 非批量模式下显示入口按钮
        if (enterBatchBtn) enterBatchBtn.style.display = 'inline-flex';
        if (deleteAllBtn) deleteAllBtn.style.display = 'inline-flex';
    }
}

/**
 * 切换记录选择
 */
function toggleHistorySelection(recordId) {
    if (HistoryState.selectedIds.has(recordId)) {
        HistoryState.selectedIds.delete(recordId);
    } else {
        HistoryState.selectedIds.add(recordId);
    }

    // 更新卡片样式
    const card = document.querySelector(`.history-card[data-id="${recordId}"]`);
    if (card) {
        card.classList.toggle('selected', HistoryState.selectedIds.has(recordId));
        const checkbox = card.querySelector('.history-checkbox');
        if (checkbox) {
            checkbox.checked = HistoryState.selectedIds.has(recordId);
        }
    }

    updateBatchActionBar();
}

/**
 * 全选/取消全选
 */
function toggleSelectAll() {
    const cards = document.querySelectorAll('.history-card');
    const allSelected = cards.length > 0 && cards.length === HistoryState.selectedIds.size;

    if (allSelected) {
        HistoryState.selectedIds.clear();
    } else {
        cards.forEach(card => {
            const id = parseInt(card.dataset.id);
            if (!isNaN(id)) {
                HistoryState.selectedIds.add(id);
            }
        });
    }

    // 更新所有卡片的选中状态
    cards.forEach(card => {
        const id = parseInt(card.dataset.id);
        const isSelected = HistoryState.selectedIds.has(id);
        card.classList.toggle('selected', isSelected);
        const checkbox = card.querySelector('.history-checkbox');
        if (checkbox) {
            checkbox.checked = isSelected;
        }
    });

    // 更新全选按钮文字
    const selectAllBtn = actionBar?.querySelector('button[onclick*="toggleSelectAll"]');
    if (selectAllBtn) {
        selectAllBtn.textContent = cards.length === HistoryState.selectedIds.size ? '取消全选' : '全选';
    }

    updateBatchActionBar();
}

/**
 * 更新批量操作栏
 */
function updateBatchActionBar() {
    const actionBar = document.getElementById('batchActionBar');
    const selectedCountEl = document.getElementById('selectedCount');
    const deleteSelectedBtn = document.getElementById('deleteSelectedBtn');

    if (!actionBar) return;

    if (!HistoryState.selectionMode) {
        actionBar.style.display = 'none';
        return;
    }

    const selectedCount = HistoryState.selectedIds.size;
    actionBar.style.display = 'flex';

    // 更新已选数量
    if (selectedCountEl) {
        selectedCountEl.textContent = `已选择 ${selectedCount} 条`;
    }

    // 更新删除按钮
    if (deleteSelectedBtn) {
        deleteSelectedBtn.textContent = `删除选中 (${selectedCount})`;
        deleteSelectedBtn.disabled = selectedCount === 0;
    }
}

/**
 * 删除选中的记录
 */
function deleteSelectedRecords() {
    const ids = Array.from(HistoryState.selectedIds);
    if (ids.length === 0) {
        showToast('请先选择要删除的记录', 'warning');
        return;
    }

    if (!confirm(`确定要删除选中的 ${ids.length} 条记录吗？`)) return;

    fetch('/api/history/batch', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: ids })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showToast(`成功删除 ${data.deleted_count} 条记录`, 'success');
            HistoryState.selectedIds.clear();
            loadHistory();
        } else {
            showToast(data.error || '删除失败', 'error');
        }
    })
    .catch(e => {
        console.error('批量删除失败:', e);
        showToast('删除失败', 'error');
    });
}

/**
 * 删除所有记录
 */
function deleteAllRecords() {
    if (!confirm('确定要删除所有历史记录吗？此操作不可恢复！')) return;
    if (!confirm('再次确认：删除所有记录？')) return;

    fetch('/api/history/all', { method: 'DELETE' })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showToast(`成功删除 ${data.deleted_count} 条记录`, 'success');
            loadHistory();
        } else {
            showToast(data.error || '删除失败', 'error');
        }
    })
    .catch(e => {
        console.error('删除全部失败:', e);
        showToast('删除失败', 'error');
    });
}

/**
 * 处理历史卡片点击
 */
function handleHistoryCardClick(recordId, event) {
    if (HistoryState.selectionMode) {
        toggleHistorySelection(recordId);
    } else {
        viewHistoryDetail(recordId);
    }
}

function viewHistoryDetail(recordId) {
    fetch('/api/history/' + recordId)
        .then(r => r.json())
        .then(data => {
            if (data.success && data.record) {
                sessionStorage.setItem('analysisResult', JSON.stringify(data.record));
                showToast('正在加载历史记录...', 'info');
                setTimeout(() => { window.location.href = '/analysis.html'; }, 500);
            } else {
                showToast('记录不存在', 'error');
            }
        })
        .catch(e => {
            console.error('获取记录详情失败:', e);
            showToast('获取记录失败', 'error');
        });
}

function deleteHistoryRecord(recordId) {
    if (!confirm('确定要删除这条记录吗？')) return;
    fetch('/api/history/' + recordId, { method: 'DELETE' })
        .then(r => r.json())
        .then(data => {
            if (data.success) { showToast('删除成功', 'success'); loadHistory(); }
            else { showToast(data.error || '删除失败', 'error'); }
        })
        .catch(e => { console.error('删除失败:', e); showToast('删除失败', 'error'); });
}

function drawGrowthChart(historyData) {
    const canvas = document.getElementById('growthChart');
    if (!canvas || typeof Chart === 'undefined') return;
    const ctx = canvas.getContext('2d');
    if (growthChartInstance) growthChartInstance.destroy();
    if (!historyData || historyData.length === 0) {
        growthChartInstance = new Chart(ctx, {
            type: 'line',
            data: { labels: ['暂无数据'], datasets: [{ label: '总分', data: [0], borderColor: '#94a3b8' }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
        });
        return;
    }
    const sortedData = [...historyData].sort((a, b) => new Date(a.timestamp || 0) - new Date(b.timestamp || 0));
    const labels = sortedData.map((h, i) => {
        const date = new Date(h.timestamp);
        return isNaN(date.getTime()) ? '#' + (i + 1) : (date.getMonth() + 1) + '/' + date.getDate();
    });
    const scores = sortedData.map(h => Math.round(h.total_score || 0));
    const trendLine = calculateTrendLine(scores);
    growthChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [
                { label: '总分', data: scores, borderColor: '#3b82f6', backgroundColor: 'rgba(59, 130, 246, 0.1)', fill: true, tension: 0.3 },
                { label: '趋势', data: trendLine, borderColor: '#10b981', borderDash: [5, 5], fill: false, pointRadius: 0 }
            ]
        },
        options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true, max: 100 } } }
    });
}

function calculateTrendLine(data) {
    if (data.length < 2) return data;
    const n = data.length;
    let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;
    for (let i = 0; i < n; i++) { sumX += i; sumY += data[i]; sumXY += i * data[i]; sumX2 += i * i; }
    const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
    const intercept = (sumY - slope * sumX) / n;
    return data.map((_, i) => slope * i + intercept);
}

function updateGrowthStats(historyData) {
    if (!historyData || historyData.length === 0) {
        document.getElementById('avgScore').textContent = '--';
        document.getElementById('maxScore').textContent = '--';
        document.getElementById('minScore').textContent = '--';
        document.getElementById('totalCount').textContent = '0';
        return;
    }
    const scores = historyData.map(h => h.total_score || 0);
    document.getElementById('avgScore').textContent = Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
    document.getElementById('maxScore').textContent = Math.round(Math.max(...scores));
    document.getElementById('minScore').textContent = Math.round(Math.min(...scores));
    document.getElementById('totalCount').textContent = scores.length;
}

// 导出全局函数供HTML调用
window.goToHistoryPage = goToHistoryPage;
window.toggleSelectionMode = toggleSelectionMode;
window.toggleHistorySelection = toggleHistorySelection;
window.toggleSelectAll = toggleSelectAll;
window.deleteSelectedRecords = deleteSelectedRecords;
window.deleteAllRecords = deleteAllRecords;
window.handleHistoryCardClick = handleHistoryCardClick;

export {
    loadHistory,
    viewHistoryDetail,
    deleteHistoryRecord,
    drawGrowthChart,
    calculateTrendLine,
    updateGrowthStats,
    toggleSelectionMode,
    deleteSelectedRecords,
    deleteAllRecords
};
