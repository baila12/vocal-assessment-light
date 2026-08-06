# BDD 测试数据

> v7.12 | 生成脚本: [scripts/gen_bdd_test_data.py](../../scripts/gen_bdd_test_data.py)

## 目录

```
tests/test_data/
├── audio/
│   ├── vocal/          # 人声演唱 (真实录音, MP3 + WAV)
│   │   ├── vocals.wav  # ← v7.12 生成 (60s, 44100Hz PCM16, 从高分人声 MP3 转换)
│   │   └── *.mp3       # 真实人声 (5 个, 含高分/低分)
│   └── non_vocal/      # 非人声 (白噪声/合成/TTS, WAV)
```

## 为什么需要 vocals.wav

`upload.feature` 的 Quick 评分场景依赖 `tests/test_data/audio/vocal/vocals.wav`。
Step 后备策略 `vocal/*.wav` 在 vocal/ 目录无 WAV 时失效 → 场景预存失败。

## 生成

```bash
python scripts/gen_bdd_test_data.py
```

从现有高分人声 MP3 (`1（高分）.mp3`) 转换, 截取前 60s (保证 Quick 模式响应 < 30s),
输出 16-bit PCM 44100Hz WAV。已生成时跳过 (幂等)。

## 其他文件后备策略

| 文件 | Step 后备 | 状态 |
|------|-----------|:--:|
| `vocals.wav` | `vocal/*.wav` (无 WAV 失败) | ✅ 脚本生成 |
| `mixed_vocal.mp3` | `vocal/*.mp3` | ✅ 现有 MP3 |
| `noise.wav` | `non_vocal/*.wav` | ✅ 现有 |
| `synthetic.wav` | `non_vocal/*.wav` | ✅ 现有 |

## 真实音频回归

`tests/integration/test_real_audio_regression.py` 使用 `vocal/*.mp3` 5 个基准文件
(含高分/低分), 验证评分区分度 (BASELINE_V7_6)。
