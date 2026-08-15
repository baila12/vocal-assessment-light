# BDD 测试数据

> v7.19 | 生成脚本: [scripts/gen_bdd_test_data.py](../../scripts/gen_bdd_test_data.py)

## 目录

```
tests/test_data/
├── audio/
│   ├── vocal/          # 人声演唱 (真实录音, MP3 + WAV)
│   │   ├── vocals.wav  # ← v7.12 生成 (60s, 44100Hz PCM16, 从高分人声 MP3 转换)
│   │   └── *.mp3       # 真实人声 (5 个, 含高分/低分)
│   └── non_vocal/      # 非人声 (白噪声 + 合成语音)
│       ├── noise.wav        # 白噪声 (upload.feature '白噪声拦截' 场景)
│       └── synthetic.wav    # TTS 合成语音 (upload.feature '合成归零' 场景)
```

> v7.19 整理: 删除 8 个无引用孤儿 WAV (test_api_audio / test_audio__from_test_music /
> test_audio__root / test_compare_audio / 测试音频 / test_e2e_audio / clipped_test /
> simulated_voice); 将 `noise_test.wav`/`synthetic_test.wav` 重命名为 `noise.wav`/
> `synthetic.wav` — 旧文件名与 upload.feature 精确引用不匹配, 后备 glob 会静默
> 用错文件 (字母序第一的 clipped_test.wav)。

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
| `noise.wav` | `non_vocal/*.wav` | ✅ v7.19 重命名对齐 |
| `synthetic.wav` | `non_vocal/*.wav` | ✅ v7.19 重命名对齐 |

## 真实音频回归

`tests/integration/test_real_audio_regression.py` 使用 `vocal/*.mp3` 5 个基准文件
(含高分/低分), 验证评分区分度 (**BASELINE_V7_17**, v7.19 清理: 删除 V7_4/V7_6/V7_14 三个死基线, 补 muscle 断言, 标 @slow)。
