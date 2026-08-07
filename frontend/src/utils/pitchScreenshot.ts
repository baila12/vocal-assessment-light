/**
 * 音准对比截图导出 — v7.13 Phase 5 导出音准对比截图
 *
 * 纯函数, 零 Vue 依赖, 可直接 Vitest 测试。
 * 对齐 pitch-realtime.feature:
 *   - "导出 PNG 格式截图"
 *   - "右下角水印: 当前时间戳 / 总时长"
 *   - "导出分辨率应为 DPR 物理分辨率" (离屏 1:1 复制源物理像素)
 */

/** 秒 → "MM:SS" (≥1 小时 → "HH:MM:SS"), 不足两位补零; 负值/NaN → "00:00" */
export function formatTimestamp(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds <= 0) return '00:00'
  const total = Math.floor(seconds)
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const secs = total % 60
  const pad = (n: number): string => String(n).padStart(2, '0')
  if (hours > 0) return `${pad(hours)}:${pad(minutes)}:${pad(secs)}`
  return `${pad(minutes)}:${pad(secs)}`
}

/**
 * 截图当前 canvas → PNG dataUrl。
 * 离屏 canvas 以 1:1 复制源物理像素 (保留 DPR 分辨率), 右下角叠加
 * "当前时间 / 总时长" 水印。canvas null → ''。
 */
export function captureCanvasToDataUrl(
  canvas: HTMLCanvasElement | null,
  currentTime: number,
  totalDuration: number,
): string {
  if (!canvas) return ''

  const offscreen = document.createElement('canvas')
  offscreen.width = canvas.width
  offscreen.height = canvas.height
  const ctx = offscreen.getContext('2d')
  if (!ctx) return ''

  // 1:1 复制源像素 (DPR 原分辨率)
  ctx.drawImage(canvas, 0, 0)

  // 右下角水印
  const label = `${formatTimestamp(currentTime)} / ${formatTimestamp(totalDuration)}`
  const fontSize = 14
  const padX = 12
  const padY = 10
  ctx.font = `${fontSize}px sans-serif`
  ctx.textAlign = 'right'
  ctx.textBaseline = 'bottom'
  const textWidth = ctx.measureText(label).width
  const boxW = textWidth + padX * 2
  const boxH = fontSize + padY
  ctx.fillStyle = 'rgba(0, 0, 0, 0.55)'
  ctx.fillRect(offscreen.width - boxW, offscreen.height - boxH, boxW, boxH)
  ctx.fillStyle = '#ffffff'
  ctx.fillText(label, offscreen.width - padX, offscreen.height - padY)

  return offscreen.toDataURL('image/png')
}

/**
 * 下载 PNG 截图 — 临时 <a download> 触发下载后清理。
 * canvas null 或截图失败 → no-op。
 */
export function downloadCanvasPng(
  canvas: HTMLCanvasElement | null,
  currentTime: number,
  totalDuration: number,
  filename = 'pitch-compare.png',
): void {
  if (!canvas) return
  const url = captureCanvasToDataUrl(canvas, currentTime, totalDuration)
  if (!url) return

  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}
