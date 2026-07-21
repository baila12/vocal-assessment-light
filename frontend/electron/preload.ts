/**
 * Electron Preload — Phase 5 实现
 *
 * 通过 contextBridge 暴露 API:
 * - window.BACKEND_URL: 动态后端地址 (随机端口)
 * - window.electronAPI.onBackendUrl: 监听端口变更
 */
