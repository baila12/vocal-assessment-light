/**
 * 图表模块
 * 使用 Chart.js 进行数据可视化
 */

// 图表颜色配置
const CHART_COLORS = {
    primary: '#3b82f6',
    success: '#10b981',
    warning: '#f59e0b',
    danger: '#ef4444',
    purple: '#8b5cf6',
    cyan: '#06b6d4',
    gray: '#94a3b8'
};

// 图表默认配置
const CHART_DEFAULTS = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            display: true,
            position: 'bottom',
            labels: {
                padding: 16,
                usePointStyle: true,
                font: {
                    size: 12
                }
            }
        },
        tooltip: {
            backgroundColor: 'rgba(30, 41, 59, 0.9)',
            titleColor: '#fff',
            bodyColor: '#fff',
            borderColor: 'rgba(255, 255, 255, 0.1)',
            borderWidth: 1,
            cornerRadius: 8,
            padding: 12
        }
    },
    scales: {
        x: {
            grid: {
                display: false
            },
            ticks: {
                color: '#64748b',
                font: {
                    size: 11
                }
            }
        },
        y: {
            grid: {
                color: 'rgba(148, 163, 184, 0.1)'
            },
            ticks: {
                color: '#64748b',
                font: {
                    size: 11
                }
            }
        }
    }
};

// 图表实例存储
const chartInstances = {};

// 创建分数雷达图
function createScoreRadarChart(canvasId, scores) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    // 销毁已存在的图表
    if (chartInstances[canvasId]) {
        chartInstances[canvasId].destroy();
    }

    // v4.0 新维度标签：音准、节奏、气息、发声技术、艺术表现
    const labels = ['音准', '节奏', '气息', '发声技术', '艺术表现'];
    const dataValues = [
        scores.pitch || scores.pitch_score || 0,
        scores.rhythm || scores.rhythm_score || 0,
        scores.breath || scores.breath_score || 0,
        scores.technique || scores.technique_score || 0,
        scores.artistry || scores.artistry_score || scores.emotion || 0
    ];

    const data = {
        labels: labels,
        datasets: [{
            label: '得分',
            data: dataValues,
            backgroundColor: 'rgba(59, 130, 246, 0.2)',
            borderColor: CHART_COLORS.primary,
            borderWidth: 2,
            pointBackgroundColor: CHART_COLORS.primary,
            pointBorderColor: '#fff',
            pointBorderWidth: 2,
            pointRadius: 4
        }]
    };

    const options = {
        ...CHART_DEFAULTS,
        scales: {
            r: {
                beginAtZero: true,
                max: 100,
                ticks: {
                    stepSize: 20,
                    display: false
                },
                grid: {
                    color: 'rgba(148, 163, 184, 0.2)'
                },
                angleLines: {
                    color: 'rgba(148, 163, 184, 0.2)'
                },
                pointLabels: {
                    color: '#475569',
                    font: {
                        size: 12,
                        weight: '500'
                    }
                }
            }
        },
        plugins: {
            ...CHART_DEFAULTS.plugins,
            legend: {
                display: false
            }
        }
    };

    chartInstances[canvasId] = new Chart(ctx, {
        type: 'radar',
        data,
        options
    });

    return chartInstances[canvasId];
}

// 创建音量波形图
function createVolumeWaveformChart(canvasId, volumeData) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    if (chartInstances[canvasId]) {
        chartInstances[canvasId].destroy();
    }

    const labels = volumeData.map((_, i) => i);

    const data = {
        labels,
        datasets: [{
            label: '音量 (dB)',
            data: volumeData,
            borderColor: CHART_COLORS.primary,
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            fill: true,
            tension: 0.4,
            pointRadius: 0
        }]
    };

    const options = {
        ...CHART_DEFAULTS,
        plugins: {
            ...CHART_DEFAULTS.plugins,
            legend: {
                display: false
            }
        },
        scales: {
            ...CHART_DEFAULTS.scales,
            y: {
                ...CHART_DEFAULTS.scales.y,
                title: {
                    display: true,
                    text: '音量 (dB)',
                    color: '#64748b'
                }
            }
        }
    };

    chartInstances[canvasId] = new Chart(ctx, {
        type: 'line',
        data,
        options
    });

    return chartInstances[canvasId];
}

// 创建音高曲线图
function createPitchCurveChart(canvasId, pitchData) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    if (chartInstances[canvasId]) {
        chartInstances[canvasId].destroy();
    }

    const data = {
        labels: pitchData.times || pitchData.map((_, i) => i),
        datasets: [{
            label: '音高 (Hz)',
            data: pitchData.pitches || pitchData,
            borderColor: CHART_COLORS.purple,
            backgroundColor: 'rgba(139, 92, 246, 0.1)',
            fill: true,
            tension: 0.3,
            pointRadius: 0
        }]
    };

    const options = {
        ...CHART_DEFAULTS,
        plugins: {
            ...CHART_DEFAULTS.plugins,
            legend: {
                display: false
            }
        },
        scales: {
            ...CHART_DEFAULTS.scales,
            y: {
                ...CHART_DEFAULTS.scales.y,
                title: {
                    display: true,
                    text: '频率 (Hz)',
                    color: '#64748b'
                }
            }
        }
    };

    chartInstances[canvasId] = new Chart(ctx, {
        type: 'line',
        data,
        options
    });

    return chartInstances[canvasId];
}

// 创建历史趋势图
function createHistoryTrendChart(canvasId, historyData) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    if (chartInstances[canvasId]) {
        chartInstances[canvasId].destroy();
    }

    const data = {
        labels: historyData.map(item => item.date),
        datasets: [{
            label: '总分',
            data: historyData.map(item => item.totalScore),
            borderColor: CHART_COLORS.primary,
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            fill: true,
            tension: 0.4,
            pointRadius: 4,
            pointBackgroundColor: CHART_COLORS.primary
        }]
    };

    const options = {
        ...CHART_DEFAULTS,
        scales: {
            ...CHART_DEFAULTS.scales,
            y: {
                ...CHART_DEFAULTS.scales.y,
                beginAtZero: true,
                max: 100,
                title: {
                    display: true,
                    text: '分数',
                    color: '#64748b'
                }
            }
        }
    };

    chartInstances[canvasId] = new Chart(ctx, {
        type: 'line',
        data,
        options
    });

    return chartInstances[canvasId];
}

// 创建分数柱状图
function createScoreBarChart(canvasId, scores) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    if (chartInstances[canvasId]) {
        chartInstances[canvasId].destroy();
    }

    // v4.0 新维度标签
    const labels = ['音准', '节奏', '气息', '发声技术', '艺术表现'];
    const dataValues = [
        scores.pitch || scores.pitch_score || 0,
        scores.rhythm || scores.rhythm_score || 0,
        scores.breath || scores.breath_score || 0,
        scores.technique || scores.technique_score || 0,
        scores.artistry || scores.artistry_score || scores.emotion || 0
    ];

    const data = {
        labels: labels,
        datasets: [{
            label: '得分',
            data: dataValues,
            backgroundColor: [
                CHART_COLORS.primary,
                CHART_COLORS.purple,
                CHART_COLORS.cyan,
                CHART_COLORS.success,
                CHART_COLORS.warning
            ],
            borderRadius: 6,
            barThickness: 40
        }]
    };

    const options = {
        ...CHART_DEFAULTS,
        plugins: {
            ...CHART_DEFAULTS.plugins,
            legend: {
                display: false
            }
        },
        scales: {
            ...CHART_DEFAULTS.scales,
            y: {
                ...CHART_DEFAULTS.scales.y,
                beginAtZero: true,
                max: 100
            }
        }
    };

    chartInstances[canvasId] = new Chart(ctx, {
        type: 'bar',
        data,
        options
    });

    return chartInstances[canvasId];
}

// 创建特征可视化展示
function createFeatureVisualization(containerId, visualizationData) {
    const container = document.getElementById(containerId);
    if (!container || !visualizationData) {
        if (container) container.style.display = 'none';
        return null;
    }

    container.style.display = 'block';

    // 设置组合图
    const combinedImg = container.querySelector('.viz-combined img');
    if (combinedImg && visualizationData.combined) {
        combinedImg.src = visualizationData.combined;
        combinedImg.alt = '音频特征综合可视化';
    }

    // 设置单独的特征图
    const spectrogramImg = container.querySelector('.viz-spectrogram img');
    if (spectrogramImg && visualizationData.spectrogram) {
        spectrogramImg.src = visualizationData.spectrogram;
    }

    const pitchImg = container.querySelector('.viz-pitch img');
    if (pitchImg && visualizationData.pitch_trajectory) {
        pitchImg.src = visualizationData.pitch_trajectory;
    }

    const energyImg = container.querySelector('.viz-energy img');
    if (energyImg && visualizationData.energy) {
        energyImg.src = visualizationData.energy;
    }

    return container;
}

// 切换可视化标签页
function switchVisualizationTab(tabName) {
    const tabs = document.querySelectorAll('.viz-tabs .viz-tab');
    const panels = document.querySelectorAll('.viz-panel');

    tabs.forEach(tab => {
        if (tab.dataset.tab === tabName) {
            tab.classList.add('active');
        } else {
            tab.classList.remove('active');
        }
    });

    panels.forEach(panel => {
        if (panel.dataset.panel === tabName) {
            panel.classList.add('active');
        } else {
            panel.classList.remove('active');
        }
    });
}

// 销毁图表
function destroyChart(canvasId) {
    if (chartInstances[canvasId]) {
        chartInstances[canvasId].destroy();
        delete chartInstances[canvasId];
    }
}

// 销毁所有图表
function destroyAllCharts() {
    Object.keys(chartInstances).forEach(destroyChart);
}

// 导出
export {
    CHART_COLORS,
    CHART_DEFAULTS,
    createScoreRadarChart,
    createVolumeWaveformChart,
    createPitchCurveChart,
    createHistoryTrendChart,
    createScoreBarChart,
    createFeatureVisualization,
    switchVisualizationTab,
    destroyChart,
    destroyAllCharts
};
