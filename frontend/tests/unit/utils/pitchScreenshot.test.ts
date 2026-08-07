/**
 * pitchScreenshot 单元测试 — v7.13 Phase 5 导出音准对比截图
 *
 * 对齐 pitch-realtime.feature "导出音准对比截图":
 *   - "导出 PNG 格式截图"
 *   - "右下角水印: 当前时间戳 / 总时长"
 *   - "导出分辨率应为 DPR 物理分辨率"
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import {
  formatTimestamp,
  captureCanvasToDataUrl,
  downloadCanvasPng,
} from '@/utils/pitchScreenshot'

/** mock 2d context — 记录 drawImage/fillText 调用 */
function mockCtx(): Record<string, unknown> {
  return {
    fillRect: vi.fn(),
    fillText: vi.fn(),
    drawImage: vi.fn(),
    save: vi.fn(),
    restore: vi.fn(),
    measureText: vi.fn().mockReturnValue({ width: 120 }),
    textAlign: '',
    textBaseline: '',
    fillStyle: '',
    font: '',
  }
}

/** 构造源 canvas (物理像素 800x450 = DPR2 下的 400x225 逻辑) */
function makeSourceCanvas(): HTMLCanvasElement {
  const canvas = document.createElement('canvas')
  canvas.width = 800
  canvas.height = 450
  return canvas
}

/** 让 document.createElement 路由 'canvas' → mock 离屏 canvas, 'a' → mock anchor */
function mockCreateElement(dataUrl: string): {
  ctx: Record<string, unknown>
  anchor: { click: ReturnType<typeof vi.fn>; href: string; download: string }
} {
  const ctx = mockCtx()
  const fakeCanvas = {
    width: 0,
    height: 0,
    getContext: vi.fn().mockReturnValue(ctx),
    toDataURL: vi.fn().mockReturnValue(dataUrl),
  }
  const anchor = { click: vi.fn(), href: '', download: '' }
  vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
    if (tag === 'canvas') return fakeCanvas as unknown as HTMLCanvasElement
    if (tag === 'a') return anchor as unknown as HTMLAnchorElement
    return document.createElement(tag)
  })
  return { ctx, anchor }
}

afterEach(() => vi.restoreAllMocks())

describe('formatTimestamp', () => {
  it('83s → "01:23"', () => {
    expect(formatTimestamp(83)).toBe('01:23')
  })

  it('秒数不足两位补零; 0 → "00:00"', () => {
    expect(formatTimestamp(0)).toBe('00:00')
    expect(formatTimestamp(5)).toBe('00:05')
    expect(formatTimestamp(65)).toBe('01:05')
  })

  it('≥1 小时 → 小时:分:秒', () => {
    expect(formatTimestamp(3661)).toBe('01:01:01')
  })

  it('负值 → "00:00"; 小数向下取整', () => {
    expect(formatTimestamp(-3)).toBe('00:00')
    expect(formatTimestamp(83.9)).toBe('01:23')
  })
})

describe('captureCanvasToDataUrl', () => {
  it('离屏 1:1 复制源物理像素 (保留 DPR) + 右下角水印 → PNG dataUrl', () => {
    const { ctx } = mockCreateElement('data:image/png;base64,PHNob3Q=')
    const source = makeSourceCanvas()
    const url = captureCanvasToDataUrl(source, 83, 225)

    expect(url).toBe('data:image/png;base64,PHNob3Q=')
    // 离屏 canvas 尺寸 = 源物理像素 (DPR 原分辨率)
    expect(ctx.drawImage).toHaveBeenCalledWith(source, 0, 0)
  })

  it('水印包含 "01:23 / 03:45" 格式', () => {
    const { ctx } = mockCreateElement('data:image/png;base64,PHNob3Q=')
    captureCanvasToDataUrl(makeSourceCanvas(), 83, 225)
    const fillTextMock = ctx.fillText as unknown as ReturnType<typeof vi.fn>
    expect(fillTextMock).toHaveBeenCalled()
    const texts = fillTextMock.mock.calls.map((c: unknown[]) => c[0] as string)
    expect(texts.some((t) => t.includes('01:23'))).toBe(true)
    expect(texts.some((t) => t.includes('03:45'))).toBe(true)
  })

  it('canvas null → 返回空串 (优雅降级)', () => {
    expect(captureCanvasToDataUrl(null, 0, 0)).toBe('')
  })
})

describe('downloadCanvasPng', () => {
  it('触发 <a download> 点击下载并清理', () => {
    const { anchor } = mockCreateElement('data:image/png;base64,PHNob3Q=')
    const source = makeSourceCanvas()
    const bodyAppend = vi.spyOn(document.body, 'appendChild').mockReturnValue({} as Node)
    const bodyRemove = vi.spyOn(document.body, 'removeChild').mockReturnValue({} as Node)

    downloadCanvasPng(source, 83, 225, 'pitch-compare.png')

    expect(anchor.click).toHaveBeenCalled()
    expect(bodyAppend).toHaveBeenCalled()
    expect(bodyRemove).toHaveBeenCalled()
  })

  it('canvas null → no-op (不抛错)', () => {
    expect(() => downloadCanvasPng(null, 0, 0)).not.toThrow()
  })
})
