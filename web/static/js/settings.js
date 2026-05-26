/**
 * 设置页面模块
 */

const SETTINGS_KEY = 'vocal_settings';

// 默认设置
const defaultSettings = {
    defaultMode: 'quick',
    strictness: 'normal',
    pitchTolerance: 50,
    autoSave: true,
    theme: 'light',
    showCharts: true,
    showDiagnosis: true
};

// 当前设置
let currentSettings = { ...defaultSettings };

// 初始化
function init() {
    loadSettings();
    applySettings();
    loadDataStats();
}

// 加载设置
function loadSettings() {
    try {
        const saved = localStorage.getItem(SETTINGS_KEY);
        if (saved) {
            currentSettings = { ...defaultSettings, ...JSON.parse(saved) };
        }
    } catch (e) {
        console.error('加载设置失败:', e);
    }

    // 应用到 UI
    document.getElementById('defaultMode').value = currentSettings.defaultMode;
    document.getElementById('strictness').value = currentSettings.strictness;
    document.getElementById('pitchTolerance').value = currentSettings.pitchTolerance;
    document.getElementById('autoSave').classList.toggle('active', currentSettings.autoSave);
    document.getElementById('showCharts').classList.toggle('active', currentSettings.showCharts);
    document.getElementById('showDiagnosis').classList.toggle('active', currentSettings.showDiagnosis);

    // 主题
    document.querySelectorAll('.theme-option').forEach(el => {
        el.classList.toggle('active', el.classList.contains(currentSettings.theme));
    });
}

// 应用设置
function applySettings() {
    if (currentSettings.theme === 'dark') {
        document.body.classList.add('dark-theme');
    } else {
        document.body.classList.remove('dark-theme');
    }
}

// 切换开关设置
function toggleSetting(id) {
    const el = document.getElementById(id);
    const isActive = el.classList.toggle('active');
    currentSettings[id] = isActive;
}

// 设置主题
function setTheme(theme) {
    currentSettings.theme = theme;
    document.querySelectorAll('.theme-option').forEach(el => {
        el.classList.toggle('active', el.classList.contains(theme));
    });
    applySettings();
}

// 保存设置
function saveSettings() {
    // 从 UI 读取值
    currentSettings.defaultMode = document.getElementById('defaultMode').value;
    currentSettings.strictness = document.getElementById('strictness').value;
    currentSettings.pitchTolerance = parseInt(document.getElementById('pitchTolerance').value) || 50;

    // 保存到 localStorage
    try {
        localStorage.setItem(SETTINGS_KEY, JSON.stringify(currentSettings));
        showToast('设置已保存', 'success');
    } catch (e) {
        console.error('保存设置失败:', e);
        showToast('保存失败', 'error');
    }
}

// 加载数据统计
function loadDataStats() {
    fetch('/api/history?limit=1000')
        .then(r => r.json())
        .then(data => {
            const total = data.total || 0;
            document.getElementById('totalRecords').textContent = total;

            // 计算平均分
            if (data.history && data.history.length > 0) {
                const avg = data.history.reduce((sum, h) => sum + (h.total_score || 0), 0) / data.history.length;
                document.getElementById('avgScore').textContent = Math.round(avg);
            } else {
                document.getElementById('avgScore').textContent = '--';
            }

            // 存储大小估算
            const storageUsed = JSON.stringify(data).length;
            const sizeKB = Math.round(storageUsed / 1024);
            document.getElementById('totalSize').textContent = sizeKB > 1024
                ? Math.round(sizeKB / 1024) + ' MB'
                : sizeKB + ' KB';
        })
        .catch(e => {
            console.error('加载统计失败:', e);
            document.getElementById('totalRecords').textContent = '0';
            document.getElementById('avgScore').textContent = '--';
            document.getElementById('totalSize').textContent = '0 KB';
        });
}

// 导出数据
function exportData() {
    fetch('/api/history?limit=1000')
        .then(r => r.json())
        .then(data => {
            const exportData = {
                version: '5.8',
                exportDate: new Date().toISOString(),
                settings: currentSettings,
                history: data.history || []
            };

            const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'vocal_assessment_export_' + new Date().toISOString().slice(0, 10) + '.json';
            a.click();
            URL.revokeObjectURL(url);
            showToast('数据已导出', 'success');
        })
        .catch(e => {
            console.error('导出失败:', e);
            showToast('导出失败', 'error');
        });
}

// 导入数据
function importData(event) {
    const file = event.target.files[0];
    if (!file) return;

    // 添加大小限制 (10MB)
    if (file.size > 10 * 1024 * 1024) {
        showToast('文件过大，最大支持10MB', 'error');
        event.target.value = '';
        return;
    }

    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const data = JSON.parse(e.target.result);

            // 验证数据结构
            if (!data || typeof data !== 'object') {
                showToast('无效的数据格式', 'error');
                return;
            }

            if (!data.history) {
                showToast('无效的数据文件', 'error');
                return;
            }

            if (!Array.isArray(data.history)) {
                showToast('历史记录格式错误', 'error');
                return;
            }

            // 限制导入数量
            if (data.history.length > 5000) {
                showToast('记录数量超过限制（最多5000条）', 'error');
                return;
            }

            showToast('检测到 ' + data.history.length + ' 条记录，导入功能需要 API 支持', 'info');

            if (data.settings && typeof data.settings === 'object') {
                currentSettings = { ...defaultSettings, ...data.settings };
                localStorage.setItem(SETTINGS_KEY, JSON.stringify(currentSettings));
                loadSettings();
                applySettings();
            }
        } catch (err) {
            console.error('导入解析失败:', err);
            showToast('文件解析失败', 'error');
        }
    };
    reader.readAsText(file);
    event.target.value = '';
}

// 清除所有数据
function clearAllData() {
    if (!confirm('确定要清除所有历史记录吗？此操作不可恢复！')) return;
    if (!confirm('再次确认：删除所有数据？')) return;

    fetch('/api/history/all', { method: 'DELETE' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                showToast('已删除 ' + data.deleted_count + ' 条记录', 'success');
                loadDataStats();
            } else {
                showToast(data.error || '清除失败', 'error');
            }
        })
        .catch(e => {
            console.error('清除失败:', e);
            showToast('清除失败', 'error');
        });

    localStorage.removeItem(SETTINGS_KEY);
    currentSettings = { ...defaultSettings };
    loadSettings();
}

// Toast 提示
function showToast(message, type) {
    const wrap = document.getElementById('toastWrap');
    if (!wrap) return;

    const toast = document.createElement('div');
    toast.className = 'toast toast-' + type;
    toast.textContent = message;
    wrap.appendChild(toast);

    setTimeout(function() {
        toast.classList.add('fade-out');
        setTimeout(function() { toast.remove(); }, 300);
    }, 2000);
}

// 导出全局函数
window.toggleSetting = toggleSetting;
window.setTheme = setTheme;
window.saveSettings = saveSettings;
window.exportData = exportData;
window.importData = importData;
window.clearAllData = clearAllData;

// 初始化
document.addEventListener('DOMContentLoaded', init);