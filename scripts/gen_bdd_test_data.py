"""BDD 测试数据生成脚本 — v7.12

背景:
    upload.feature 场景依赖 tests/test_data/audio/vocal/vocals.wav (真实人声 WAV),
    但 vocal/ 目录仅有 MP3 无 WAV, 导致 vocal_wav_file 后备策略失效 → 场景预存失败。

    Step 后备策略 (tests/bdd/steps/test_upload_steps.py):
      - vocals.wav         → 后备 vocal/*.wav (无 WAV → 断言失败)  ← 本脚本修复
      - mixed_vocal.mp3    → 后备 vocal/*.mp3 (存在) ✅
      - noise.wav          → 后备 non_vocal/*.wav (存在) ✅
      - synthetic.wav      → 后备 non_vocal/*.wav (存在) ✅

    故仅需生成 vocals.wav; 其余文件后备策略已覆盖。

用法:
    python scripts/gen_bdd_test_data.py
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VOCAL_DIR = PROJECT_ROOT / "tests" / "test_data" / "audio" / "vocal"

SAMPLE_RATE = 44100


def _load_mono(path: Path):
    """librosa 加载为单声道浮点数组."""
    import librosa
    y, _ = librosa.load(str(path), sr=SAMPLE_RATE, mono=True)
    return y


def _write_wav(y, path: Path) -> None:
    """写入 16-bit PCM WAV."""
    import soundfile as sf
    sf.write(str(path), y, SAMPLE_RATE, subtype="PCM_16")
    print(f"生成: {path.relative_to(PROJECT_ROOT)} ({len(y) / SAMPLE_RATE:.1f}s, {SAMPLE_RATE}Hz PCM16)")


# 截取前 N 秒 — 保持 BDD 场景响应时间 < 30s (Quick 模式 60s 音频可稳定完成)
MAX_SECONDS = 60.0


def gen_vocals_wav() -> None:
    """从现有高分人声 MP3 转换 vocals.wav (截取前 60s)."""
    VOCAL_DIR.mkdir(parents=True, exist_ok=True)
    target = VOCAL_DIR / "vocals.wav"
    if target.exists():
        print(f"已存在: {target.relative_to(PROJECT_ROOT)} (跳过)")
        return

    # 首选高分人声, 否则任意 MP3
    candidates = [VOCAL_DIR / "1（高分）.mp3", VOCAL_DIR / "恋人（高分）.mp3"]
    source = next((p for p in candidates if p.exists()), None)
    if source is None:
        mp3s = sorted(VOCAL_DIR.glob("*.mp3"))
        source = mp3s[0] if mp3s else None
    if source is None:
        print("错误: vocal/ 目录无 MP3, 无法生成 vocals.wav")
        sys.exit(1)

    y = _load_mono(source)
    max_samples = int(MAX_SECONDS * SAMPLE_RATE)
    if len(y) > max_samples:
        y = y[:max_samples]
        print(f"截取前 {MAX_SECONDS:.0f}s (原 {len(y) / SAMPLE_RATE:.1f}s)")
    _write_wav(y, target)
    print(f"来源: {source.relative_to(PROJECT_ROOT)}")


def main() -> None:
    gen_vocals_wav()
    print("完成.")


if __name__ == "__main__":
    main()
