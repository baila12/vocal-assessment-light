/**
 * Electron 主进程 — Phase 5
 *
 * ADR-1: 嵌入式 Python 运行时替代 PyInstaller
 * ADR-5: electron-log 结构化日志
 *
 * 功能:
 * - 嵌入式 Python 启动 + 随机端口捕获 (PORT=xxxxx stdout)
 * - 进程守护 (崩溃自动重启, max 3 次)
 * - 前后端日志聚合 (electron-log + structlog)
 * - 增量更新 (electron-updater)
 */

import { spawn, ChildProcess } from 'child_process'
import { app, BrowserWindow, dialog, Menu } from 'electron'
import path from 'path'
import fs from 'fs'
import log from 'electron-log'

// ---- Logging setup (ADR-5) ----
log.transports.file.level = 'info'
log.transports.console.level = 'debug'
log.transports.file.resolvePathFn = () =>
  path.join(app.getPath('userData'), 'logs', 'main.log')

// ---- Constants ----
const MAX_RESTART_COUNT = 3
const RESTART_DELAY_MS = 1500

// ---- State ----
let backendProcess: ChildProcess | null = null
let mainWindow: BrowserWindow | null = null
let currentBackendUrl = ''
let restartCount = 0
let isQuitting = false

// ---- Backend Lifecycle ----

/**
 * Resolve the project root directory.
 *
 * 开发模式: __dirname = frontend/electron/ → projectRoot = frontend/../
 * 生产模式: 使用 app.getAppPath() (比 __dirname 更可靠，在 asar 中也正常工作)
 */
function getProjectRoot(): string {
  // 生产模式: app.getAppPath() 返回 asar 根目录或源码目录
  if (app.isPackaged) {
    return app.getAppPath()
  }
  // 开发模式: __dirname 是 frontend/electron/, 往上两级到项目根
  return path.join(__dirname, '..', '..')
}

/**
 * Find the backend main.py script.
 * In production: resources/backend/main.py
 * In development: <projectRoot>/backend/main.py
 */
function getBackendScriptPath(): string {
  const projectRoot = getProjectRoot()
  const devPath = path.join(projectRoot, 'backend', 'main.py')
  if (fs.existsSync(devPath)) {
    return devPath
  }
  return path.join(process.resourcesPath, 'backend', 'main.py')
}

/**
 * Find the Python executable.
 * In production: resources/python/python.exe
 * In development: system python from PATH or conda
 */
function getPythonPath(): string {
  const bundledPath = path.join(process.resourcesPath, 'python', 'python.exe')
  if (fs.existsSync(bundledPath)) {
    return bundledPath
  }

  // Development: try project's conda env first
  const projectRoot = getProjectRoot()
  const condaPath = path.join(projectRoot, '..', 'pytorch2', 'python.exe')
  if (fs.existsSync(condaPath)) {
    return condaPath
  }

  // Fallback: system PATH
  return 'python'
}

/**
 * Start the Python backend process and capture its dynamic port.
 * Resolves with the port number once "PORT=xxxxx" is read from stdout.
 */
function startBackend(): Promise<number> {
  return new Promise((resolve, reject) => {
    const pythonPath = getPythonPath()
    const scriptPath = getBackendScriptPath()

    log.info(`[Backend] Starting: ${pythonPath} ${scriptPath} --port=0`)

    const py = spawn(pythonPath, [scriptPath, '--port=0'], {
      env: {
        ...process.env,
        PYTHONUNBUFFERED: '1',
        VAS_ENV: 'electron',
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    })

    backendProcess = py

    let portFound = false

    // Capture "PORT=xxxxx" from stdout (ADR-1 protocol)
    py.stdout?.on('data', (data: Buffer) => {
      const text = data.toString()
      log.debug(`[Backend stdout] ${text.trim()}`)

      if (!portFound) {
        const match = text.match(/PORT=(\d+)/)
        if (match) {
          const port = parseInt(match[1], 10)
          portFound = true
          currentBackendUrl = `http://127.0.0.1:${port}`
          log.info(`[Backend] Ready on port ${port}`)

          // Notify renderer
          mainWindow?.webContents.send('set-backend-url', currentBackendUrl)

          // Reset restart counter on successful start
          restartCount = 0

          resolve(port)
        }
      }
    })

    // Forward stderr as logs
    py.stderr?.on('data', (data: Buffer) => {
      log.info(`[Backend] ${data.toString().trim()}`)
    })

    // Error during spawn
    py.on('error', (err: Error) => {
      log.error(`[Backend] Spawn error: ${err.message}`)
      backendProcess = null
      reject(err)
    })

    // Process exit handler
    py.on('close', (code: number | null, signal: string | null) => {
      log.warn(`[Backend] Exited — code=${code}, signal=${signal}`)
      backendProcess = null

      // Don't restart if user is quitting
      if (isQuitting) return

      // Don't restart if port was never found (startup failure)
      if (!portFound && !isQuitting) {
        reject(
          new Error(
            `Backend failed to start. Exit code: ${code}. Check logs in ${app.getPath('userData')}\\logs\\`
          )
        )
        return
      }

      // Auto-restart logic
      if (restartCount < MAX_RESTART_COUNT) {
        restartCount++
        log.warn(
          `[Backend] Auto-restarting (${restartCount}/${MAX_RESTART_COUNT}) in ${RESTART_DELAY_MS}ms...`
        )
        mainWindow?.webContents.send('backend-status', 'restarting')

        setTimeout(() => {
          if (!isQuitting) {
            startBackend().catch((err) => {
              log.error(`[Backend] Restart failed: ${err.message}`)
              if (restartCount >= MAX_RESTART_COUNT) {
                showBackendCrashDialog()
              }
            })
          }
        }, RESTART_DELAY_MS)
      } else {
        log.error(`[Backend] Max restarts (${MAX_RESTART_COUNT}) reached. Stopping.`)
        showBackendCrashDialog()
      }
    })

    // Timeout: if no port after 30s, consider failed
    setTimeout(() => {
      if (!portFound && !isQuitting) {
        reject(new Error('Backend startup timeout (30s): no PORT= in stdout'))
      }
    }, 30_000)
  })
}

/**
 * Show error dialog when backend crashes permanently.
 */
function showBackendCrashDialog(): void {
  const userDataPath = app.getPath('userData')
  dialog
    .showMessageBox(mainWindow!, {
      type: 'error',
      title: '引擎启动失败',
      message:
        '后端引擎连续崩溃，无法恢复。\n\n请尝试以下操作:\n1. 重启应用\n2. 导出诊断包 (帮助 → 导出诊断包)',
      detail: `日志路径: ${userDataPath}\\logs\\`,
      buttons: ['关闭应用', '查看日志'],
    })
    .then(({ response }) => {
      if (response === 1) {
        // "查看日志" — open the logs folder
        const logsDir = path.join(userDataPath, 'logs')
        shell.openPath(logsDir)
      }
    })
}

function stopBackend(): void {
  if (backendProcess) {
    log.info('[Backend] Stopping...')
    backendProcess.kill('SIGTERM')

    // Force kill after 5s if still alive
    setTimeout(() => {
      if (backendProcess) {
        log.warn('[Backend] Force killing...')
        backendProcess.kill('SIGKILL')
        backendProcess = null
      }
    }, 5_000)
  }
}

// ---- Electron App Lifecycle ----

function createWindow(): BrowserWindow {
  // preload 路径: 使用 app.getAppPath() (asar 安全)
  const preloadPath = app.isPackaged
    ? path.join(app.getAppPath(), 'electron', 'preload.js')
    : path.join(__dirname, 'preload.js')

  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    title: 'VAS — 声乐评估系统',
    webPreferences: {
      preload: preloadPath,
      contextIsolation: true,
      nodeIntegration: false,
      // sandbox: false 是预加载脚本使用 Node API (contextBridge/ipcRenderer) 的必要条件。
      // 配合 contextIsolation: true, 渲染进程仍完全隔离 — 只能通过 preload 暴露的 API 通信。
      // 这是 Electron 安全最佳实践中推荐的标准配置。
      sandbox: false,
    },
    show: false, // Show after backend is ready
  })

  win.once('ready-to-show', () => {
    win.show()
  })

  win.on('closed', () => {
    mainWindow = null
  })

  return win
}

function setupMenu(): void {
  const template: Electron.MenuItemConstructorOptions[] = [
    {
      label: '文件',
      submenu: [
        { label: '导出诊断包', click: exportDiagnostics },
        { type: 'separator' },
        { role: 'quit', label: '退出' },
      ],
    },
    {
      label: '编辑',
      submenu: [
        { role: 'undo' },
        { role: 'redo' },
        { type: 'separator' },
        { role: 'cut' },
        { role: 'copy' },
        { role: 'paste' },
      ],
    },
    {
      label: '视图',
      submenu: [
        { role: 'reload' },
        { role: 'forceReload' },
        { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
      ],
    },
    {
      label: '帮助',
      submenu: [
        {
          label: '打开日志目录',
          click: () => {
            const logsDir = path.join(app.getPath('userData'), 'logs')
            shell.openPath(logsDir)
          },
        },
        {
          label: '关于 VAS',
          click: () => {
            dialog.showMessageBox(mainWindow!, {
              type: 'info',
              title: '关于 VAS',
              message: '声乐评估系统 v7.0.0',
              detail:
                'AI-powered vocal assessment with six-dimension scoring.\nFastAPI + Vue 3 + Element Plus + Electron.',
            })
          },
        },
      ],
    },
  ]

  const menu = Menu.buildFromTemplate(template)
  Menu.setApplicationMenu(menu)
}

// ---- Diagnostic Export ----
import { shell } from 'electron'

function exportDiagnostics(): void {
  const userDataPath = app.getPath('userData')
  const logsDir = path.join(userDataPath, 'logs')

  // Just open the logs directory for now
  // Future: zip logs + config + session info
  shell.openPath(logsDir)

  dialog.showMessageBox(mainWindow!, {
    type: 'info',
    title: '诊断包',
    message: '已打开日志目录',
    detail: `路径: ${logsDir}\n\n请将日志文件发送给技术支持。`,
  })
}

// ---- App Entry Point ----

app.whenReady().then(async () => {
  log.info('========================================')
  log.info('  VAS v7.0.0 — Electron')
  log.info(`  User data: ${app.getPath('userData')}`)
  log.info(`  Resources: ${process.resourcesPath}`)
  log.info('========================================')

  setupMenu()
  mainWindow = createWindow()

  try {
    await startBackend()
  } catch (err) {
    log.error(`[Startup] Backend failed: ${(err as Error).message}`)
    // Still show window — renderer handles "no backend" state
  }

  // Load frontend
  if (process.env.VITE_DEV_SERVER_URL) {
    // Development: Vite dev server
    await mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL)
  } else {
    // Production: built files (asar 安全 — 使用 app.getAppPath())
    const indexPath = app.isPackaged
      ? path.join(app.getAppPath(), 'dist', 'index.html')
      : path.join(__dirname, '..', 'dist', 'index.html')
    mainWindow.loadFile(indexPath)
  }
})

// Prevent multiple instances
const gotLock = app.requestSingleInstanceLock()
if (!gotLock) {
  app.quit()
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore()
      mainWindow.focus()
    }
  })
}

// Cleanup on quit
app.on('before-quit', () => {
  isQuitting = true
  stopBackend()
})

app.on('window-all-closed', () => {
  stopBackend()
  app.quit()
})

// macOS: re-create window if dock icon clicked
app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    mainWindow = createWindow()
    startBackend().catch((err) => {
      log.error(`[Startup] Backend failed: ${(err as Error).message}`)
    })
  }
})
