# 声乐评估系统 — 性能深度分析与优化计划

> 版本: v1.1 | 日期: 2026-07-28 (审计更新: 2026-08-02) | 基于 v7.3.1 源码完整追踪
>
> **架构演进说明**: v7.6 起 Flask 已移除, API 路由统一到 FastAPI `/api/v1/`。本文管线分析基于 v7.3.1, 核心性能瓶颈 (Demucs/PYIN/HPSS) 及优化建议在 v7.11 依然有效 (v7.9 歌曲库后端 + v7.10 前端 + v7.11 评分权重均不改变音频分析管线复杂度)。
>
> **关联文档**: [SCORING.md](SCORING.md) | [ARCHITECTURE.md](ARCHITECTURE.md) | [SCORING_ALGORITHM_IMPROVEMENT_PLAN.md](SCORING_ALGORITHM_IMPROVEMENT_PLAN.md)

---

## 目录

1. [管线全貌: 端到端数据流](#一管线全貌)
2. [逐组件复杂度分析](#二逐组件复杂度分析)
3. [内存剖析](#三内存剖析)
4. [GPU 利用率分析](#四gpu-利用率分析)
5. [瓶颈识别与根因](#五瓶颈识别)
6. [优化方案矩阵](#六优化方案矩阵)
7. [Quick 模式专项优化](#七quick-模式专项优化)
8. [Pro 模式专项优化](#八pro-模式专项优化)
9. [实施路线图](#九实施路线图)

---

## 一、管线全貌

### 1.1 端到端请求流

```
HTTP POST /api/upload  (或 /api/v1/assessment)
│
├─ 1. 文件接收 & 验证
│     └─ MaxBodySizeMiddleware (50MB guard)
│     └─ 扩展名白名单检查
│     └─ 保存到 uploads/
│
├─ 2. 音频分析 (AudioService.analyze)         ← 耗时主体
│     │
│     ├─ 2a. librosa.load (O(n), ~1-2s)
│     ├─ 2b. 降采样 44.1k→16k (O(n), ~0.5s)
│     ├─ 2c. 音量分析 (_analyze_volume) (O(n), <0.5s)
│     ├─ 2d. PYIN f0 (_analyze_pitch) (O(n×fmin_eggs), ~5s)  ← Quick 瓶颈 #1
│     ├─ 2e. Chroma 快速替代 (_analyze_tonal_clarity_fast) (O(n), <0.1s)
│     ├─ 2f. 节奏分析 (_analyze_rhythm) (O(n×n_fft), ~2s)
│     ├─ 2g. 人声清晰度 (_analyze_voice_clarity) (O(n×n_fft), ~1s)
│     ├─ 2h. 颤音检测 (_detect_vibrato) (O(n), <0.1s)
│     ├─ 2i. 波形/音高曲线/频谱图/RMS (O(n), ~1s)
│     │
│     ├─ 2j. [Pro only] 混合音频检测 + Demucs 分离     ← Pro 瓶颈 #1
│     │     ├─ detect_mixed_audio (HPSS + 5-feature vote, ~6s)
│     │     └─ Demucs subprocess (htdemucs_ft, 120s CPU / 25s GPU)
│     │         └─ 重新提取 f0 (再 +5s)
│     │
│     └─ 2k. [Pro only] DL 模型推理
│           ├─ VoiceQualityDetector (PYIN + HPSS, ~1s)
│           ├─ SingingStyleClassifier (ONNX INT8, ~0.5s)
│           ├─ SelfReferencedDTW (O(m×n) DTW, ~3-8s)
│           └─ StyleAnalyzer (heuristic + DL, ~1s)
│
├─ 3. DDD 特征提取 (DddFeatureExtractionOrchestrator)  ← 后台计算
│     │
│     ├─ 3a. normalize_loudness (O(n), <0.05s)
│     ├─ 3b. L0: acoustic (HNR+CPP+HPSS+voicing) (~6s)
│     ├─ 3c. L1: pitch + rhythm (并行机会, 0s 串行)
│     ├─ 3d. L2: breath + technique + timbre (~2s)
│     ├─ 3e. L3: muscle + artistry (~0.5s)
│     └─ 3f. [optional] audiofeat (130+ features, ~3-5s)
│
├─ 4. 评分计算 (ScoringOrchestrator)          ← <0.5s
│     └─ 6 scorers + weighted total + level + timbre
│
├─ 5. [Pro only] 辅助分析
│     ├─ 可视化生成 (matplotlib, ~8s)
│     ├─ 音色分析 (v7.16: TimbreService 已删, 由 DDD calculate_ddd timbre_detail 组装, 零额外耗时)
│     ├─ 逐句评分 (PhraseService, ~5s — v7.16 经用户决策推迟迁移)
│     └─ 建议生成 (v7.16: AdviceService 已删, 由 DDD AdviceGenerator 生成, 零额外耗时)
│
└─ 6. 响应构建 + 历史保存 (<0.1s)
```

### 1.2 耗时分布 (以 3min 44.1kHz 音频为基准, 16GB RAM + SSD)

#### Quick 模式 (~20s CPU)

```
librosa.load    ██ 1.5s
降采样           █ 0.5s
PYIN f0         ██████████ 5s        ← 25% — 最大单点瓶颈
onset strength  ████ 2s
HNR + CPP       ██████ 3s
RMS + breath    ██ 1s
频谱/波形/RMS    ██ 1s
DDD acoustic    ██████ 3s
DDD breath+tech ███ 1.5s
DDD 其他        █ 0.5s
评分计算         █ 0.5s
响应构建         █ 0.5s
────────────────────────────────────
Total           ███████████████████████████████ 20s
```

#### Pro 模式 (~155s CPU / ~55s GPU)

```
Quick 全部       ████████████████████ 20s
混合检测+HPSS    ██████ 6s
Demucs 分离      ████████████████████████████████████████████████████████████ 120s  ← 77%
  (GPU:          █████████████ 25s)                                              ← 45%
重新 PYIN f0     ██████ 5s
DL 模型推理      █████ 3-5s
可视化           ████████ 8s
音色分析         ██ 2s
逐句评分         █████ 5s
建议生成         █ 1s
────────────────────────────────────────────────────────────────────────
Total CPU        ████████████████████████████████████████████████████████████████████████ 155s
Total GPU        ████████████████████████████████████████████████ 55s
```

---

## 二、逐组件复杂度分析

### 2.1 音频 I/O

| 组件 | 算法 | 时间复杂度 | 空间复杂度 | 实测耗时 |
|------|------|:---------:|:---------:|:-------:|
| `librosa.load` | 解码 + 重采样到原始 sr | O(n) | O(n) | 1-2s |
| `librosa.resample` (44.1k→16k) | Kaiser 窗 FIR | O(n × L) L=滤波器长度 | O(n) | 0.3-0.5s |

**当前状态**: ✅ 已优化。降采样到 16kHz 将后续所有处理量减少 63.7%。

### 2.2 基频提取 (f0)

| 组件 | 算法 | 时间复杂度 | 空间复杂度 | 实测耗时 |
|------|------|:---------:|:---------:|:-------:|
| `librosa.yin` | YIN 自相关 | O(n × fmin_eggs) ≈ O(n × sr/fmin) | O(hop_frames) | 5-8s |
| `torchcrepe.predict` | CREPE CNN | O(n × model_layers) | O(n + model_params ~50MB) | 3-5s (CPU) / <1s (GPU) |

**当前状态**: ⚠️ 最大 Quick 瓶颈。YIN 在 16kHz 时 `fmin_eggs = sr/fmin = 16000/80 = 200`，每帧做 200 次自相关。TorchCREPE fallback 硬编码 `device='cpu'`——即使 CUDA 可用也不用。

### 2.3 HPSS 分离

| 组件 | 算法 | 时间复杂度 | 实测耗时 |
|------|------|:---------:|:-------:|
| `librosa.effects.hpss` | 中值滤波 (kernel 31) | O(n × kernel) | 5.9s |

**当前状态**: ✅ 已优化 (v6.2)。原先每次调用 5.9s × 3 = 17.7s，现改为预计算一次后复用。

**⚠️ 仍存在问题**: Pro 模式下 HPSS 至少调用 2 次——一次在 `detect_mixed_audio` 中，一次在 `AcousticExtractor` 中。第 2 次是重复计算。

### 2.4 Demucs 人声分离

| 组件 | 算法 | 实测耗时 | 内存峰值 |
|------|------|:-------:|:-------:|
| `demucs htdemucs_ft` | Hybrid Transformer Demucs | 120s CPU / 25s GPU | ~800MB |
| `demucs htdemucs` | Hybrid Transformer Demucs (full) | 300s+ CPU / 60s GPU | ~1.2GB |

**当前状态**: ❌ 最大 Pro 瓶颈。Demucs 通过**进程内 Python API** 调用 (`from demucs import separate; separate.main([...])`, 见 `backend/infrastructure/audio/demucs_separator.py`)——非子进程 CLI, 无额外进程启动开销; 但存在:
- **模型冷启动重载**: 每次分离请求重新加载 htdemucs_ft 权重 (~800MB), CPU 加载 + 推理合计 120s / GPU 25s
- **文件系统传递**: 分离结果经输出目录写入再读取 (vocals.wav/no_vocals.wav), 未走内存通道
- 无跨请求模型复用 (每次调用重新 `import demucs` + GPU 检测), 无法利用 in-process GPU 共享

**优化方向**: 将 Demucs 模型提升为进程级单例 (懒加载, 首次加载后跨请求复用), 消除每次请求的权重重载开销; 分离调用无显式超时兜底, 短音频可按需裁剪处理预算。

### 2.5 DDD 特征提取

| 层级 | 提取器 | 主要操作 | 复杂度 | 实测耗时 |
|:----:|------|------|:---------:|:-------:|
| — | `normalize_loudness` | RMS计算 + 增益 | O(n) | <0.05s |
| L0 | `AcousticExtractor` | HNR + CPP + HPSS + Voicing + Mixed | O(n × n_fft) | ~3-6s |
| L1 | `PitchExtractor` | MAE/RPA/RCA/Gross/Octave/Smooth/Breaks | O(k) k=帧数 | ~0.1s |
| L1 | `RhythmExtractor` | Onset CV + irregularity | O(k) | ~0.2s |
| L2 | `BreathExtractor` | 长音/动态/气口/气声 | O(k) | ~0.5s |
| L2 | `TechniqueExtractor` | 颤音/滑音/假声/断奏/连奏 | O(k) | ~0.5s |
| L2 | `TimbreExtractor` | Centroid/Cluster/Harmonic/Nasality | O(1) 聚合 | <0.01s |
| L3 | `MuscleExtractor` | body/facial proxies | O(1) 聚合 | <0.01s |
| L3 | `ArtistryExtractor` | vibrato/dynamic/phrase/crescendo | O(1) 聚合 | <0.01s |
| — | `audiofeat` (optional) | 130+ 特征 (CPPS/GNE/Jitter/...) | O(n) | 3-5s |

**关键发现**: L1 (Pitch + Rhythm) 互不依赖，可并行但当前串行。L2 (Breath + Technique + Timbre) 共享 Acoustic 依赖，也可并行。

### 2.6 深度学习模型推理

| 模型 | 框架 | 复杂度 | 实测耗时 | GPU 可用? |
|------|------|:---------:|:-------:|:---------:|
| VoiceQualityDetector | librosa PYIN | O(n) | ~1s | ❌ (无 PyTorch) |
| SingingStyleClassifier | ONNX INT8 | O(n × model) | ~0.5s | ❌ (CPU ONNX) |
| SelfReferencedDTW | scipy DTW O(m×n) | O(n²) for segment pairing | 3-8s | ❌ |
| StyleAnalyzer | heuristic + DL | O(n) | ~1s | 部分 |

**关键发现**: ONNX 模型在 CPU 上运行。没有使用 ONNX Runtime GPU 后端。

### 2.7 评分计算

| 组件 | 算法 | 复杂度 | 实测耗时 |
|------|------|:---------:|:-------:|
| 6 个 Scorer | 纯数学 (exp, 分段线性, clamp) | O(1) | <0.1s |
| ScoringDomainService | 加权求和 + timbre.apply() | O(1) | <0.01s |
| ScoreLevel.from_score() | 区间查表 | O(1) | <0.01s |
| **总计** | | | **<0.5s** |

**评分计算不是瓶颈**。计算量对现代 CPU 微不足道。

### 2.8 辅助分析 (Pro only)

| 组件 | 算法 | 实测耗时 | 可跳过? |
|------|------|:-------:|:------:|
| 可视化 (matplotlib) | 频谱图 + 音高图 + 能量图 | ~8s | ✅ 异步生成 |
| 音色分析 | 多维度特征 | ~2s | ✅ |
| 逐句评分 | 分段 f0 + 节奏 + 情绪 | ~5s | ✅ |
| 建议生成 | 规则引擎 | ~1s | ✅ 低优先级 |

---

## 三、内存剖析

### 3.1 稳态内存 (FastAPI 常驻)

| 组件 | 内存 | 说明 |
|------|:----:|------|
| Python 基础 + FastAPI | ~80MB | uvicorn + starlette + pydantic |
| librosa 首次 import | ~15MB | 延迟加载 |
| ONNX Runtime + 模型 | ~50MB | 延迟初始化 (AudioDLHelpers) |
| **基线总计** | **~145MB** | |

### 3.2 峰值内存 (处理 3min 44.1kHz 请求时)

| 阶段 | 临时分配 | 说明 |
|------|:-----:|------|
| librosa.load (原始采样率) | ~30MB | 3min stereo 44.1kHz float32 |
| 降采样到 16kHz | ~11MB | 替换原数组 |
| PYIN f0 中间结果 | ~80MB | librosa.pyin 内部缓存 |
| HPSS (harmonic + percussive) | ~22MB | 两份 16kHz float32 |
| AcousticExtractor 中间结果 | ~30MB | FFT + 倒谱 + 多频带 HNR |
| [Pro] Demucs subprocess | **~800MB** | 独立进程, PyTorch + model weights |
| [Pro] 重新 PYIN f0 | ~80MB | 基于纯净人声重算 |
| **Quick 峰值** | **~170MB** | |
| **Pro 峰值** | **~1050MB** | Demucs 子进程独享 800MB |

### 3.3 内存问题

1. **Demucs 子进程 800MB 无法复用**: 每次分离启动新进程，加载完整 PyTorch + 模型权重
2. **PYIN 调用两次** (Pro 模式): 分离前后各一次，`~80MB × 2` 峰值叠加
3. **无流式处理**: 始终加载完整音频到内存，不支持 10min+ 长音频
4. **无中间缓存清理**: numpy 数组依赖 GC，峰值内存 = 所有中间结果的总和

---

## 四、GPU 利用率分析

### 4.1 GPU 检测状态

```python
# backend/main.py — 启动时检测
torch.cuda.is_available() → True/False
torch.backends.mps.is_available() → True/False (Apple Silicon)
```

### 4.2 各组件 GPU 利用

| 组件 | GPU 可用 | 当前使用 | 问题 |
|------|:------:|:------:|------|
| Demucs (子进程) | ✅ | ✅ 自动检测 CUDA | 子进程开销抵消部分加速 |
| TorchCREPE fallback | ✅ | ❌ `device='cpu'` 硬编码 | 浪费 GPU 加速 |
| ONNX Style Classifier | ✅ | ❌ CPU EP only | ONNX Runtime CUDA EP 未配置 |
| audiofeat | ✅ | 部分 | PyTorch 后端可用但非全 GPU |
| librosa (YIN/HPSS/PYIN) | ❌ | ❌ | 纯 CPU numpy/scipy |

### 4.3 GPU 加速潜力

| 优化 | 当前耗时 | 优化后 | 节省 |
|------|:-----:|:-----:|:---:|
| TorchCREPE → GPU | 3-5s (CPU) | <1s (GPU) | -3s |
| Demucs → Python API (GPU共享) | 120s subprocess | 20s in-process | -100s (含进程开销) |
| ONNX → CUDA EP | 0.5s (CPU) | <0.1s (GPU) | -0.4s |
| **GPU 加速总计** | | | **~103s** |

---

## 五、瓶颈识别

### 5.1 按影响排序

| # | 瓶颈 | 影响模式 | 当前耗时 | 根因 |
|---|------|:------:|:-----:|------|
| **B1** | Demucs 子进程分离 | Pro | **120s** | 子进程开销 + 无 GPU 共享 + 文件 I/O |
| **B2** | PYIN f0 提取 | Quick/Pro | **5-8s** | librosa.yin 纯 CPU O(n×200) |
| **B3** | HPSS 重复计算 | Pro | **+5.9s** | `detect_mixed_audio` + `AcousticExtractor` 各算一次 |
| **B4** | DDD L1/L2 串行提取 | Quick/Pro | **无并行 → 浪费 ~2s** | Pitch+Rhythm 无依赖，Breath+Tech+Timbre 无依赖 |
| **B5** | SelfReferencedDTW O(n²) | Pro | **3-8s** | 分段配对 DTW 对长音频呈平方增长 |
| **B6** | 可视化 matplotlib | Pro | **8s** | 同步阻塞，3 张高清图 |
| **B7** | PYIN 重复计算 | Pro | **+5s** | Demucs 分离后重新提取（必要但可缓存中间结果） |
| **B8** | audiofeat (可选) | Quick/Pro | **+3-5s** | 130+ 特征一次性全算，实际只用 10+ |

### 5.2 瓶颈依赖图

```
Quick 模式:
  PYIN f0 (5s) ─────────────────── 阻塞全部后续特征提取
    ├─ Acoustic (3s)
    │   ├─ Breath + Technique + Timbre (可并行, 串行浪费 1s)
    │   └─ Muscle + Artistry
    ├─ Pitch (0.1s)
    └─ Rhythm (0.2s)

Pro 模式 (额外):
  Demucs (120s) ─────────────────── 阻塞后续全部计算
    └─ PYIN f0 (5s) ─────────────── 重算（必要）
      └─ (同 Quick 后续)

  可视化 (8s) ───────────────────── 与评分计算无关, 可异步
  逐句评分 (5s) ─────────────────── 与评分计算无关, 可异步
  音色分析 (2s) ─────────────────── 与评分计算无关, 可异步
```

---

## 六、优化方案矩阵

### 6.1 总览

| # | 优化项 | 影响 | 难度 | 风险 | 预期节省 |
|---|--------|:--:|:--:|:--:|:-----:|
| O1 | Demucs → Python API in-process | Pro P0 | 中 | 中 | **-100s GPU / -30s CPU** |
| O2 | FCPE 替换 PYIN (GPU) | Quick/Pro P0 | 低 | 低 | **-4s (Quick), -3s (Pro)** |
| O3 | HPSS 结果缓存复用 | Pro P0 | 低 | 低 | **-5.9s** |
| O4 | L1+L2 并行提取 | Quick/Pro P1 | 低 | 低 | **-2s** |
| O5 | 可视化异步生成 | Pro P1 | 低 | 低 | **-8s (响应时间)** |
| O6 | PYIN 中间结果缓存 | Pro P1 | 低 | 低 | -5s (分离后跳过已计算的 acoustic/pitch) |
| O7 | DTW 快速路径 | Pro P1 | 中 | 中 | **-3-5s** |
| O8 | audiofeat 按需提取 | Quick/Pro P2 | 低 | 低 | **-2-3s** |
| O9 | 流式处理长音频 | Quick/Pro P2 | 高 | 中 | O(n) 内存 → O(1) |
| O10 | ONNX CUDA EP | Pro P2 | 低 | 低 | -0.4s |
| O11 | 模型常驻预加载 | 启动 P2 | 低 | 低 | -2s 冷启动 |

### 6.2 O1: Demucs Python API (最大优化)

**当前**: `subprocess.run(['demucs', ...])` → 启动新进程 → 加载 PyTorch (~3s) → 加载模型权重 (~800MB) → 分离 → 写入文件 → 父进程重新 `librosa.load` 文件

**方案**: 使用 `demucs` Python API 直接调用:

```python
# 替代方案: in-process Demucs
from demucs import pretrained
from demucs.apply import apply_model
import torch

class InProcessDemucsSeparator:
    def __init__(self):
        self._model = None  # 延迟加载, 首次 ~3s
    
    def _get_model(self):
        if self._model is None:
            self._model = pretrained.get_model('htdemucs_ft')
            if torch.cuda.is_available():
                self._model.cuda()
        return self._model
    
    def separate(self, audio_path: str) -> tuple[np.ndarray, int]:
        # 加载音频 → tensor
        wav, sr = librosa.load(audio_path, sr=44100, mono=True)
        x = torch.from_numpy(wav).float().unsqueeze(0).unsqueeze(0)
        
        # GPU 推理
        if torch.cuda.is_available():
            x = x.cuda()
        
        with torch.no_grad():
            sources = apply_model(self._get_model(), x)
        
        # vocals = sources[0] (htdemucs_ft "vocals" stem)
        vocals = sources[0, 0].cpu().numpy()
        return vocals, sr
```

**收益**:
- 消除子进程启动 + PyTorch 加载 (~3s)
- 模型权重常驻内存 (复用, 非每次重加载)
- 数据通过 tensor 传递 (非文件 I/O)
- GPU 共享 (与 TorchCREPE 等共用 CUDA context)
- 预期: 120s → 20s (GPU) / 90s → 50s (CPU)

**风险**: 内存常驻 ~800MB，需在 startup 时确认可用 RAM。Demucs PyTorch 版本与项目 torch 版本兼容性。

---

### 6.3 O2: FCPE 替换 YIN (Quick 瓶颈)

**当前**: `librosa.yin` 纯 CPU, O(n × 200)，每帧 200 次自相关计算。

**文献**: TECH_RESEARCH 推荐 `torchfcpe` (A 级, 96.79% RPA, 77x faster than YIN)。

```python
# 当前 (audio_service.py:329):
f0 = librosa.yin(audio_data, fmin=80, fmax=1200, sr=sr, hop_length=512)

# 优化方案 (FCPE GPU):
import torchfcpe
audio_tensor = torch.from_numpy(audio_data).float().unsqueeze(0).unsqueeze(0)
if torch.cuda.is_available():
    audio_tensor = audio_tensor.cuda()
f0 = torchfcpe.predict(audio_tensor, sr=sr, hop_length=512)
```

**收益**: 5-8s → <1s (GPU) / ~2s (CPU)
**风险**: 低 (TECH_RESEARCH 已验证，pip install 即用)

---

### 6.4 O3: HPSS 缓存复用

**当前**: Pro 模式下 HPSS 计算 2 次——`detect_mixed_audio` (在 `_preprocess_for_scoring` 中) 和 `AcousticExtractor.extract` (在 DDD 管线中)。

**方案**: 在 AudioAnalysisResult 中缓存 HPSS 结果，DDD 提取器从缓存读取。

```python
# audio_service.py — _preprocess_for_scoring 中:
result._hpss_harmonic = y_harmonic  # 🆕 缓存
result._hpss_percussive = y_percussive

# ddd_feature_orchestrator.py — extract_all 中:
# 从 analysis_result 读取缓存 (如果存在)
hpss = getattr(context, '_hpss_harmonic', None)
```

**收益**: -5.9s (消除重复 HPSS)
**风险**: 低 (纯缓存，逻辑不变)

---

### 6.5 O4: L1+L2 并行提取

**当前**: DDD 提取器严格串行 (L0→L1→L2→L3)，但 L1 内部 (Pitch + Rhythm) 和 L2 内部 (Breath + Technique + Timbre) 互不依赖。

**方案**: 使用 `concurrent.futures.ThreadPoolExecutor` 并行提取：

```python
# ddd_feature_orchestrator.py — extract_all:
from concurrent.futures import ThreadPoolExecutor, as_completed

# L1 并行
with ThreadPoolExecutor(max_workers=2) as pool:
    future_pitch = pool.submit(self._pitch.extract, y, sr, f0, voiced_flags)
    future_rhythm = pool.submit(self._rhythm.extract, y, sr, f0=f0, ...)
    pitch = future_pitch.result()
    rhythm = future_rhythm.result()

# L2 并行 (依赖 L0 acoustic)
with ThreadPoolExecutor(max_workers=3) as pool:
    future_breath = pool.submit(self._breath.extract, y, sr, acoustic, ...)
    future_tech = pool.submit(self._technique.extract, y, sr, acoustic, ...)
    future_timbre = pool.submit(self._timbre.extract, acoustic, ...)
    breath = future_breath.result()
    technique = future_tech.result()
    timbre = future_timbre.result()
```

**收益**: L1 0.3s → 0.2s, L2 1.5s → 0.6s, **总计 -1~2s**
**风险**: 低 (numpy 操作释放 GIL，线程安全)

---

### 6.6 O5: 可视化异步生成

**当前**: matplotlib 同步渲染 3 张图（频谱图 + 音高图 + 能量图），阻塞 HTTP 响应 ~8s。

**方案**: Pro 模式立即返回评分，可视化通过 WebSocket 或轮询异步推送。

```python
# api/business/audio_analysis.py:
if mode == 'professional':
    # 同步返回评分 (不含可视化)
    response = build_response(score_result)
    # 异步生成可视化
    background_tasks.add_task(generate_visualizations, filepath, result_id)
```

**收益**: HTTP 响应时间 -8s (Pro)
**风险**: 低 (前端已有 WebSocket 连接用于 streaming score)

---

### 6.7 O7: DTW 快速路径

**当前**: `SelfReferencedDTW` 对全曲做分段 DTW，每个音符段与前后段配对计算，复杂度 O(n²) 对长音频呈平方增长。

**方案**:
1. 限制最大配对窗口 (如 ±5 音符，而非全部)
2. 长音频 (>2min) 使用代表性采样 (每 4 个音符取 1 个)
3. 快速路径: 音符数 < 10 → 直接评分; > 50 → 代表性采样

**收益**: 3-8s → 1-2s
**风险**: 中 (可能影响 DTW 精度，需评估快速路径与完整路径的一致性)

---

### 6.8 优化效果预估汇总

#### Quick 模式 (目标: 20s → 8-10s)

```
当前:      ████████████████████ 20s

O2 FCPE:   ████████████████ 16s   (-4s PYIN→FCPE)
O4 并行:   ██████████████ 14s     (-2s L1+L2 并行)
O8 audio:  █████████████ 13s      (-1s 按需提取)
        再加上以下优化:
O11 预加载: ████████████ 12s       (-1s 冷启动消除)
─────────────────────────────────
目标:      ██████████ 8-10s        (2x 加速)
```

#### Pro 模式 (目标: 155s CPU → 40-50s CPU / 55s GPU → 20-25s GPU)

```
当前 CPU:  ████████████████████████████████████████████████████████████████████████ 155s

O1 Demucs: ████████████████████████████████ 65s     (-90s 消除子进程+文件I/O)
O3 HPSS:   ██████████████████████████████ 59s       (-6s 复用)
O2 FCPE:   █████████████████████████████ 55s        (-4s FCPE替换PYIN)
O5 异步:   ██████████████████████████ 47s           (-8s 可视化响应异步)
O6 缓存:   █████████████████████████ 45s             (-2s 中间结果缓存)
O7 DTW:    ████████████████████████ 42s              (-3s 快速路径)
O4 并行:   ██████████████████████ 40s                (-2s 并行提取)
────────────────────────────────────────────────────
目标 CPU:  ████████████████████ 40-50s               (3x 加速)
目标 GPU:  ██████████ 20-25s                          (2.5x 加速)
```

---

## 七、Quick 模式专项优化

### 7.1 Quick 模式设计意图 vs 实际

| 设计意图 | 实际实现 | 差距 |
|---------|---------|:--:|
| FeatureFlags.for_quick() 关闭多频带 HNR | 传入 `FeatureFlags()` 全开 | Quick 做了 Pro 同等计算 |
| 跳过 Demucs 分离 | ✅ 正确跳过 | — |
| "快速练习反馈 ~30s" | 实际 ~20s | 已达到 |
| **目标: ~10s** | — | 需 O2+O4+O8 |

### 7.2 Quick 快速路径

```python
# 新增: FeatureFlags.for_quick() 正确实现
@staticmethod
def for_quick() -> 'DimensionFlags':
    return DimensionFlags(
        enable_multiscale_hnr=False,       # 跳过 4-band HNR
        enable_reverb_compensation=False,   # 跳过混响补偿
        enable_praat_cpp=True,             # 保留 (已有快速截断)
        enable_voicing_detection=True,      # 保留 (低成本)
        enable_torchcrepe_fallback=False,   # FCPE 替代后不需要 fallback
        enable_audiofeat=False,            # 跳过 130+ 特征
        enable_ddd_feature_extraction=True, # 保持
    )
```

---

## 八、Pro 模式专项优化

### 8.1 Pro 管线重构 — 异步流水线

```
当前 (同步, 串行):
  Upload → Analyze(120s) → Extract(10s) → Score(0.5s) → Visualize(8s) → Response
  ════════════════════════════════════════════════════════════════
  Response after: ~140-170s

优化后 (异步, 流水线):
  Upload → Analyze(50s) → Extract(5s) → Score(0.5s) → Response
                              │                          ═══════
                              └─ Visualize(8s) ─→ WS push   Response after: ~55s
                              └─ Phrase(5s) ──→ WS push     (评分立即可见)
                              └─ Timbre(2s) ──→ WS push
```

### 8.2 模型预加载 (启动时)

```python
# backend/main.py — lifespan startup:
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 预加载模型 (后台线程, 不阻塞启动)
    import threading
    def preload_models():
        # Demucs
        from demucs.pretrained import get_model
        app.state.demucs_model = get_model('htdemucs_ft')
        # FCPE
        import torchfcpe
        # warmup
    threading.Thread(target=preload_models, daemon=True).start()
    yield
```

---

## 九、实施路线图

### Phase P0: 零风险快速收益 (1-2 天)

```
Day 1: O3 HPSS 缓存复用
  ├── audio_service.py: 缓存 HPSS 结果到 result dict
  ├── ddd_feature_orchestrator.py: 读取缓存
  └── 验证: Quick mode 时间不变, Pro mode -5.9s

Day 1-2: O4 L1+L2 并行提取
  ├── ddd_feature_orchestrator.py: ThreadPoolExecutor
  ├── 验证: Quick mode -2s
  └── 验证: 所有 DDD 测试 GREEN (120 tests)

Day 2: O5 可视化异步
  ├── api/business/audio_analysis.py: background_tasks
  └── 前端: WebSocket 接收可视化完成通知
```

### Phase P1: 中风险显著收益 (3-5 天)

```
Day 3-4: O2 FCPE 替换 PYIN
  ├── pip install torchfcpe
  ├── audio_service.py: FCPE 优先路径 + YIN fallback
  ├── FeatureFlags: enable_fcpe (默认 True)
  └── 验证: f0 一致性测试 (FCPE vs PYIN 输出差异 <5%)

Day 4-5: O1 Demucs Python API
  ├── services/separation_service.py: 新增 InProcessDemucsSeparator
  ├── backend/main.py: lifespan 预加载
  └── 验证: 分离质量一致性 + 内存监控
```

### Phase P2: 深度优化 (5-10 天)

```
Week 2: O7 DTW 快速路径
  ├── services/dl_services/self_referenced_dtw.py: 窗口限制
  └── 验证: 一致性测试 (fast DTW vs full DTW 相关度 >0.95)

Week 2: O8 audiofeat 按需提取
  ├── 仅提取 scorers 实际使用的 10+ 特征 (非 130+)
  └── 验证: 启用 audiofeat 时评分一致性

Week 2-3: O10 ONNX CUDA EP + O11 模型预加载
  ├── ONNX Runtime GPU 后端配置
  └── lifespan 预加载所有模型
```

### 测试策略

| Phase | 修改文件 | 影响测试 | 性能验证 |
|-------|:-------:|------|------|
| P0 | 3 | 120 (DDD domain + infra) | Quick mode 计时 → 目标 18s |
| P1 | 4 | 290 (全部 DDD + 中间件) | Quick 目标 10s, Pro GPU 目标 25s |
| P2 | 5 | 按需 | Pro CPU 目标 45s |

### 回退策略

每个优化独立开关，通过 FeatureFlags 控制:
- `enable_fcpe`: FCPE→YIN 回退
- `enable_inprocess_demucs`: Python API→subprocess 回退
- `enable_parallel_extraction`: 并行→串行 回退
- `enable_dtw_fast_path`: 快速→完整 DTW 回退

---

## 附录: 性能监控指标

### A.1 关键指标

| 指标 | Quick 当前 | Quick 目标 | Pro CPU 当前 | Pro CPU 目标 | Pro GPU 目标 |
|------|:--------:|:--------:|:----------:|:----------:|:----------:|
| 端到端响应时间 | 20s | **10s** | 155s | **45s** | **25s** |
| 首次可用结果 (评分) | 20s | 10s | 155s | **55s** | 25s |
| 内存峰值 | 170MB | 170MB | 1050MB | **850MB** | 850MB |
| CPU 利用率 (评分期间) | 100% (1核) | 80% (多核) | 100% (1核) | 60% (多核) | 30% |

### A.2 实测基准

优化后需在以下硬件上重测基准:
- CPU: 16GB RAM + SSD (最坏情况)
- GPU: NVIDIA GTX 1060+ (典型开发环境)
- Apple Silicon: M1/M2 (可选)
