/**
 * AudioWorklet 重采样处理器
 *
 * 浏览器原生采样率 (48kHz) → 16kHz 降采样
 * 每 2048 samples (~128ms) 输出一个 Float32Array
 *
 * 注册为 "downsample-processor", 由 useAudioContext 加载。
 */
class DownsampleProcessor extends AudioWorkletProcessor {
  private buffer: Float32Array[]
  private bufferSize: number

  constructor() {
    super()
    this.buffer = []
    this.bufferSize = 0
  }

  process(
    inputs: Float32Array[][],
    _outputs: Float32Array[][],
    _parameters: Record<string, Float32Array>
  ): boolean {
    const input = inputs[0]
    if (!input || input.length === 0) return true

    const channel = input[0]
    if (!channel) return true

    // 48kHz → 16kHz: 每3个sample取1个 (48/16=3)
    const downsampleRatio = 3
    const TARGET_SAMPLES = 2048

    for (let i = 0; i < channel.length; i += downsampleRatio) {
      this.buffer.push(channel[i])
      this.bufferSize++

      if (this.bufferSize >= TARGET_SAMPLES) {
        // 输出 Float32Array 到主线程
        const output = new Float32Array(this.buffer.slice(0, TARGET_SAMPLES))
        this.port.postMessage(output)

        // 保留剩余样本
        this.buffer = this.buffer.slice(TARGET_SAMPLES)
        this.bufferSize = this.buffer.length
      }
    }

    return true // 保持处理器活跃
  }
}

registerProcessor('downsample-processor', DownsampleProcessor)
