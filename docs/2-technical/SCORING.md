# 评分算法文档

> 更新: 2026-07-28 | v7.3.1 — audiofeat 评分闭环 + Comparison DDD + 安全加固 + 真实音频基线更新
>
> **架构状态**: DDD 唯一评分路径; 13 自包含提取器; audiofeat 4 scorers 增强 (flag 门控, 默认关闭)
> **技术研究**: [TECH_RESEARCH.md](TECH_RESEARCH.md)
> **当前状态**: [PROJECT_STATUS.md](../4-process/PROJECT_STATUS.md)

---

## DDD 特征提取管线 (v7.1.3 自包含版)

评分管线的特征提取有两种路径:

| 路径 | 特征提取 | 特征→评分 | 状态 |
|------|---------|----------|:--:|
| **A (DDD 原生, 默认)** | `DddFeatureExtractionOrchestrator` → 10 自包含模块 | `calculate_ddd()` → DDD Scorers | ✅ 生产 |
| **B (适配器, 回退)** | `AudioFeaturesService` → `AudioFeaturesResult` | `FeatureAdapterRegistry` → DDD Scorers | flag |

路径 A 特点:
- 10 个 DDD 模块**完全自包含**, 零 `services/features/` 依赖 (v7.1.3)
- 算法逐位一致于 legacy 版本, 通过 33 个 TDD 一致性测试验证
- 预处理: `normalize_loudness()` (RMS→0.05) + 人声段过滤 — 全部内移到 `audio_utils.py`
- 所有 Features 数据类为 `@dataclass(frozen=True)` (不可变)
- `enable_ddd_feature_extraction=True` (默认) 启用; `False` 回退到路径 B

### DDD 提取器模块 (10/10 自包含)

| 层级 | 提取器 | 核心算法 | 外部依赖 |
|------|--------|---------|:--:|
| — | `audio_utils.py` | normalize_loudness + vocal_segments + filter | ✅ 纯函数 |
| L0 | `acoustic_feature_extractor.py` | HNR + CPP + HPSS + voicing + mixed_audio | ✅ |
| L1 | `pitch_extractor.py` | MAE/RPA/RCA/gross/octave/smoothness/breaks | ✅ |
| L1 | `rhythm_extractor.py` | onset CV + irregularity + off-beat + deviation | ✅ |
| L2 | `breath_extractor.py` | long_note + dynamic + design + technique + decay | ✅ |
| L2 | `technique_extractor.py` | vibrato + slides + falsetto + staccato + legato | ✅ |
| L2 | `timbre_extractor.py` | centroid + cluster + harmonic + nasality | ✅ |
| L3 | `muscle_extractor.py` | body/facial proxies (adapter 公式) | ✅ |
| L3 | `artistry_extractor.py` | vibrato + dynamic + phrase + crescendo | ✅ |
| — | `ddd_feature_orchestrator.py` | 拓扑编排 + normalize_loudness | ✅ |

### 六维权重 (v7.0 scoring formula)

| 维度 | 权重 | 子维度 | 说明 |
|------|:---:|------|------|
| pitch (音准) | **10%** | MAE指数衰减(40%)+RPA(25%)+RCA(10%)+Gross Error(15%)+Smoothness(5%)+Octave(5%) | v6 权重 28% |
| rhythm (节奏) | **10%** | onset CV + irregularity 惩罚 + is_clean_vocal 重校准 | v6 权重 20% |
| breath (气息) | **20%** | 长音支撑(40%)+动态控制(25%)+气口设计(20%)+气声技巧(15%) | — |
| technique (技术) | **25%** | 咬字清晰度(50%)+气声比(50%) | v6 权重 18% |
| muscle (肌肉) ⚠️ | **25%** | 身体力量(50%)+面部力量(50%) 启发式代理指标 | v7 新增 |
| artistry (艺术) | **10%** | vibrato_quality + dynamic_control + phrase_expression + pitch_variation | v6 权重 14% |
| timbre (音色) ⚠️ | **加减分** | brightness+warmth+nasality 综合调整, clamp[-5, +3] | 额外加减分 |

> **v6 vs v7 分数差异**: v7 总分比 v6 低 5-15 分, 原因是 pitch(28%→10%)+rhythm(20%→10%) 权重削减, 新增 muscle(25%) 启发式维度。这是设计决策, 非 bug。

### 对齐数据 (melody.wav, DDD vs Legacy)

| 维度 | DDD | Legacy | Δ |
|------|:---:|:---:|:---:|
| pitch | 90.3 | 90.0 | +0.3 |
| rhythm | 100.0 | 100.0 | 0.0 |
| breath | 34.2 | 35.5 | -1.3 |
| technique | 50.3 | 46.9 | +3.4 |
| muscle | 73.3 | 75.0 | -1.7 |
| artistry | 54.6 | 56.4 | -1.8 |
| **total** | **62.2** | **60.2** | **+2.0** |

### 真实音频评分 (v7.3 Quick 模式 — DDD 唯一路径 + audiofeat)

| 音频文件 | Total | Pitch | Rhythm | Breath | Tech | Muscle | Art | Timbre |
|----------|:-----:|:-----:|:------:|:------:|:----:|:------:|:---:|:------:|
| 恋人（高分） | **65.7** | 67 | 66 | 92 | 25 | 80 | 76 | 0 |
| 手写的从前（高分） | **61.7** | 70 | 42 | 94 | 19 | 76 | 77 | 0 |
| 1（高分） | **65.7** | 71 | 71 | 97 | 20 | 78 | 76 | 0 |
| 音频-3分26秒(高分) | **65.7** | 68 | 58 | 89 | 30 | 80 | 76 | 0 |
| 陈奕迅难听之声（低分） | **52.8** | 66 | 5 | 84 | 16 | 70 | 74 | 0 |

> **v5.19→v7.3 基线漂移**: technique 重构 (HNR/CPP→咬字+气声比) 导致该维度偏移 ~-30 分。高低分差从 20→12.9（六维权重稀释）。手写的从前 rhythm=42 受钢琴伴奏 onset 干扰。详见 [PROJECT_STATUS.md](../4-process/PROJECT_STATUS.md)。

---

## 评估模式全景图

系统支持 3 种评估模式 + 1 种演唱模式，算法路径如下：

### 模式定义

| 模式 | 触发方式 | 用途 |
|------|---------|------|
| **Quick** | `POST /api/upload?mode=quick` (默认) | 快速练习反馈 (~30-60s) |
| **Professional** | `POST /api/upload?mode=professional` | 详细诊断 (~2-5min) |
| **Compare** | `POST /api/compare` (双文件上传) | 参考音频对比 |
| **Sing** | SingPage 录音后调用 `uploadAudio(file, 'quick')` | 演唱评分 (始终 Quick) |

---

## 各模式算法对照表

### 1. 特征提取层

| 特征 | Quick | Professional | Compare (双方) | SingPage | FeatureFlags 要求 |
|------|-------|-------------|---------------|----------|-------------------|
| 音量分析 (RMS) | ✅ | ✅ | ✅ | ✅ | 无 |
| 音高检测 (PYIN) | ✅ | ✅ | ✅ | ✅ | 无 |
| Chroma 调性 | ✅ | ✅ | ✅ | ✅ | 无 |
| 节奏分析 (onset) | ✅ | ✅ | ✅ | ✅ | 无 |
| 人声清晰度 | ✅ | ✅ | ✅ | ✅ | 无 |
| 颤音检测 | ✅ | ✅ | ✅ | ✅ | 无 |
| 波形数据 | ✅ | ✅ | ✅ | ✅ | 无 |
| 音高曲线 | ✅ | ✅ | ✅ | ✅ | 无 |
| Log-Mel 频谱 | ✅ | ✅ | ✅ | ✅ | 无 |
| RMS 短时能量 | ✅ | ✅ | ✅ | ✅ | 无 |
| **混合音频检测 + Demucs 分离** | ❌ 跳过 | ✅ | ✅ | ❌ | 无 (quick_mode 跳过) |
| **TorchCREPE f0 备选** | ✅ (flag) | ✅ (flag) | ✅ (flag) | ✅ (flag) | `enable_torchcrepe_fallback` |
| **多频带 HNR (de Krom 1993)** | ❌ | ✅ | ✅ | ❌ | `enable_multiscale_hnr` |
| **Praat CPP** | ✅ | ✅ | ✅ | ✅ | `enable_praat_cpp` |
| **Voicing 检测** | ✅ | ✅ | ✅ | ✅ | `enable_voicing_detection` |
| **混响补偿** | ❌ | ✅ | ✅ | ❌ | `enable_reverb_compensation` |
| **Praat 声质 (jitter/shimmer/formants)** | ✅ | ✅ | ✅ | ✅ | `enable_praat_voice_quality` |

> **注意**: Quick 模式下 `FeatureFlags.for_quick()` 关闭 `enable_multiscale_hnr` 和 `enable_reverb_compensation`，但当前代码传入的是 `FeatureFlags()`(全开)，实际效果等于 Professional。需要按设计意图使用 `FeatureFlags.for_quick()`。

### 2. 深度学习层 (仅 Pro / Compare)

| 模型 | 框架 | 文件 | Quick | Pro/Compare | 状态 |
|------|------|------|-------|------------|------|
| 人声质量检测 | ONNX (Silero VAD) | `models/voice_quality/silero_vad.onnx` | ❌ | ✅ | 正常 |
| 唱法分类 | ONNX (INT8 量化) | `models/style_classifier/model_quantized.onnx` | ❌ | ✅ | 正常 |
| 自参照 DTW | librosa DTW | `services/dl_services/self_referenced_dtw.py` | ❌ | ✅ | 计算但未入评分 |
| 音乐风格分析 | Heuristic + DL | `services/dl_services/singing_style_classifier.py` | ❌ | ✅ | 部分 |
| **SingMOS (DL 质量评估)** | — | v5.15 移除, v7.1 代码删除 | ❌ | ❌ | ✅ 已完全移除 |

> **v7.1**: SingMOS 已在 v5.15 从评分管线移除, v7.1 彻底删除 `dl_quality_assessor.py` 文件。DL fusion (`_apply_dl_fusion`) 已从 `ScoreServiceV4` 中移除。

### 3. 评分计算层 (所有模式相同)

| 评分器 | 权重 | 输入特征 | 算法 |
|--------|------|---------|------|
| **PitchScorer** | 10% | `pitch_deviation` | MAE指数衰减(40%) + RPA(25%) + RCA(10%) + Gross Error(15%) + Smoothness(5%) + Octave(5%) |
| **RhythmScorer** | 10% | `rhythm_alignment` | Onset间隔CV + 中位数聚合 |
| **BreathScorer** | 20% | `breath_stability` | 四子维度: 长音支撑(40%)+动态控制(25%)+气口设计(20%)+气声技巧(15%) |
| **TechniqueScorer** | 25% | `articulation, breath_voice_ratio` | 两子维度: 咬字清晰度(50%) + 气声比(50%) |
| **MuscleStrengthScorer** | 25% | `body_muscle, facial_muscle` | 两子维度: 身体肌肉力量(50%) + 面部肌肉力量(50%) |
| **ArtistryScorer** | 10% | `vocal_technique, breath, emotion` | 颤音品质(30%)+动态控制(30%)+乐句表现力(25%)+音高变化(15%) |

> **额外加减分**: **TimbreAdjustment** — 音色评估 (±0)。在六维百分制总分计算后独立应用: 最多 +3 / 最多 -5，最终总分 clamp 到 [0, 100]。

| 修正机制 | 触发条件 | Quick | Pro | 说明 |
|---------|---------|-------|-----|------|
| **Cross-Dimension Modifiers** | `feature_flags.enable_cross_dimension_modifiers` | ✅ | ✅ | HNR→气息, Voicing→音准, 频谱倾斜→气声, Jitter→技术, 气息-音准耦合 |
| **DTW 参考评分** | `reference_path != None` | ✅ | ✅ | 仅 Compare 模式和 upload 带 reference 时触发 |
| **DL Fusion** | — | ❌ | ❌ | v7.1 已移除 |
| **Critical Rules** | 无条件 | ✅ | ✅ | 连续跑调(>5音符), 脱拍(>40%), 严重漏气(HNR<3dB) |
| **多维度联合惩罚** | 无条件 | ✅ | ✅ | 4维<40→上限40, 3维<40→上限55 |
| **人声质量惩罚** | 无条件 | ✅ | ✅ | VQ<30→上限40, VQ<65→扣分 |
| **唱法自适应权重** | `style_profile != None` | ❌ (Quick 无 DL) | ✅ (Pro 有) | 根据识别出的唱法调整五维权重 |

### 4. 辅助分析层

| 分析 | Quick | Pro | Compare |
|------|-------|-----|---------|
| **情绪分析** | 启发式 (RMS+频谱质心) | 启发式 (v5.12 移除 Wav2Vec2) | 启发式 |
| **可视化生成** | ❌ 跳过 | ✅ 特征图 (pitch/energy/spectrogram) | ❌ |
| **音色分析** | ❌ 跳过 | ✅ 音色特征 (明亮度/温暖度等) | ❌ |
| **逐句评分** | ❌ 跳过 | ✅ 分段音高+节奏+情绪 | ❌ |

---

## Quick 模式 vs Professional 模式 — 完整差异

### Quick 模式 (`mode='quick'`)

**设计原则**: Quick 模式应启用所有声学特征增强算法，仅跳过耗时的深度学习模型和辅助分析。

**FeatureFlags**: 当前传入 `FeatureFlags()`（全部 `True`），所有 7 个高级算法激活：
- ✅ 跨维度修正 (Cross-Dimension Modifiers)
- ✅ Praat 声质特征 (Jitter/Shimmer/Formants/Singer's Formant)
- ✅ 多频带 HNR (de Krom 1993, 4频带)
- ✅ Praat CPP (parselmouth PowerCepstrum)
- ✅ Voicing 检测 (PYIN 自一致性评估)
- ✅ 混响补偿 (HPSS + 谱减法)
- ✅ TorchCREPE f0 备选 (PYIN 检测率<50%时)

```
audio_service.analyze(quick_mode=True)
  ├── librosa.load → 降采样到 16kHz
  ├── ✅ 音量分析 (RMS)
  ├── ✅ PYIN 音高检测 (+ TorchCREPE fallback)
  ├── ✅ Chroma 调性分析
  ├── ✅ Onset 节奏分析
  ├── ✅ 人声清晰度评估
  ├── ✅ 颤音检测
  ├── ✅ 波形数据 / 音高曲线 / Log-Mel频谱 / RMS短时能量
  ├── ⛔ Demucs 人声分离 (跳过 — 耗时但仅对混合音频有益)
  ├── ✅ 高级特征提取 (FeatureFlags 全开)
  │     ├── ✅ HPSS 谐波/冲击分离
  │     ├── ✅ 人声段检测 (Vocal Segment Detection)
  │     ├── ✅ 混响补偿 (HPSS + Boll 1979 谱减法)
  │     ├── ✅ HNR / CPP 计算 (在补偿后人声段上)
  │     ├── ✅ 节奏对齐分析
  │     ├── ✅ 气息稳定性分析 (四子维度)
  │     ├── ✅ 音准偏差分析 (六指标多维度)
  │     ├── ✅ 发声技巧检测 (颤音/滑音/假声/断奏/连奏)
  │     ├── ✅ 多频带 HNR + 稳定性 (de Krom 1993)
  │     ├── ✅ Praat CPP (VoiceLab)
  │     ├── ✅ Voicing 检测
  │     ├── ✅ 混合音频检测 (五特征融合)
  │     ├── ✅ Praat 声质 (Jitter/Shimmer/Formants F1-F4/Singer's Formant)
  │     └── ✅ 频谱倾斜 (LTAS slope)
  └── ⛔ DL 深度学习分析 (全部跳过)
        ├── ⛔ 人声质量检测 (Silero VAD ONNX)
        ├── ⛔ 唱法分类 (Style Classifier ONNX)
        ├── ⛔ 自参照 DTW
        └── ⛔ 音乐风格分析

analyze_and_score()
  ├── ✅ 人声质量检测 (VoiceQualityService)
  ├── ✅ 情绪分析 → 启发式 (RMS + 频谱质心；v5.12 移除 Wav2Vec2)
  ├── ✅ 评分计算
  │     ├── ✅ 五维评分器 (Pitch/Rhythm/Breath/Technique/Artistry)
  │     ├── ✅ 跨维度修正 (5 项)
  │     ├── ✅ DTW 参考对比 (如提供 reference_path)
  │     ├── ✅ 底线规则 (CriticalRules)
  │     └── ✅ 多维度联合惩罚 + 人声质量惩罚
  ├── ✅ 建议生成
  ├── ⛔ DL 评估 → mos_score=0 (跳过)
  ├── ⛔ 可视化生成 (跳过)
  ├── ⛔ 音色分析 (跳过)
  └── ⛔ 逐句评分 (跳过)
```

### Professional 模式 (`mode='professional'`)

在 Quick 模式基础上**额外启用**:

```
audio_service.analyze(quick_mode=False)
  ├── (同上 Quick 全部特征)
  ├── ✅ Demucs 人声分离 (混合音频时)
  │     └── 重新提取 f0 + 更新音量 (基于纯净人声)
  ├── ✅ 高级特征提取 (同上全开)
  └── ✅ DL 深度学习分析
        ├── ✅ 人声质量检测 (Silero VAD ONNX → voice_quality)
        ├── ✅ 唱法分类 (Style Classifier ONNX → style_profile)
        │     └── 用识别出的 style 重新提取高级特征
        ├── ✅ 自参照 DTW → pitch_stability_dl
        └── ✅ 音乐风格分析 → music_style + style_profile

analyze_and_score()
  ├── (同上 Quick 全部步骤)
  ├── ✅ DL 评估 → SingMOS (torch.hub) → ⚠️ 静默失败返回 0
  ├── ✅ 可视化生成 (pitch/energy/spectrogram 图表)
  ├── ✅ 音色分析 (明亮度/温暖度/鼻音感等)
  └── ✅ 逐句评分 (分段音高+节奏+情绪)
```

### Quick vs Pro 差异总结

| 层级 | Quick 模式 | Professional 模式 |
|------|-----------|-------------------|
| **基础特征** (音量/音高/节奏/颤音) | ✅ 全部 | ✅ 全部 |
| **高级特征** (7 项 FeatureFlags) | ✅ 全部 | ✅ 全部 |
| **Demucs 人声分离** | ❌ 跳过 | ✅ 混合音频时启用 |
| **DL 模型** (VAD/分类/DTW/风格) | ❌ 全部跳过 | ✅ 全部启用 |
| **SingMOS** | ❌ | v5.15 移除, v7.1 代码删除 |
| **五维评分器** | ✅ 相同算法 | ✅ 相同算法 |
| **跨维度修正** | ✅ 相同 | ✅ 相同 |
| **唱法自适应权重** | ❌ (无 style_profile) | ✅ (来自 DL 唱法分类) |
| **可视化** | ❌ | ✅ |
| **音色分析** | ❌ | ✅ |
| **逐句评分** | ❌ | ✅ |
| **DTW 参考对比** | ✅ (如有 reference_path) | ✅ (如有 reference_path) |
| **耗时** | ~30-60s | ~2-5min |

### 分数差异来源

Quick 和 Pro 使用**完全相同的评分算法**。分数差异仅来自:
1. **特征质量**: Pro 通过 Demucs 获得更纯净的人声 → f0/HNR/CPP 更准确
2. **唱法权重**: Pro 通过 DL 唱法分类 → `StyleAwareScorer` 调整五维权重
3. **多频带 HNR**: Pro 通过 de Krom 1993 四频带 HNR 获得更精细的声带闭合评估
4. **混响补偿**: Pro 对 HNR/CPP 做房间声学归一化

---

## Compare 模式 — DTW 参考对比

### 完整流程

```
POST /api/compare
  ├── 接收 standard 音频 + user 音频
  ├── analyze_and_score(standard) → standard_result (Quick/Pro logic)
  ├── analyze_and_score(user) → user_result (Quick/Pro logic)
  ├── DTW 对齐: self_referenced_dtw.compare(standard, user)
  │     ├── 音高序列对齐 (DTW 路径)
  │     ├── 节奏对齐评分
  │     └── 逐音符偏差计算
  └── 返回 { standard, user, comparison }
```

### Compare 的 DTW 评分与 report 的 DTW 评分的区别

| | `/api/compare` | `score_service._apply_dtw_reference()` |
|---|---|---|
| 触发 | 前端 ComparePage | `upload` 时传 `reference_path` |
| 算法 | `self_referenced_dtw.compare()` | `dtw_aligner` + 融合 |
| 输出 | 独立对比分数 + 对齐曲线 | 融合到主评分 (调整音准/节奏) |
| 当前状态 | ⚠️ 前端字段名不匹配 | ✅ 可用 (需 reference_path) |

---

## SingPage 演唱模式

```
_recordAudio() → MediaRecorder → Blob
  └── _api.uploadAudio(blob, 'quick')  ← 始终 Quick!
        └── analyze_and_score(filepath, mode='quick')
              └── 等同于 Quick 模式 (无 DL, 无参考)
```

SingPage **始终使用 Quick 模式**。无论是否选择了曲库歌曲、是否上传了参考音频，`_uploadExistingRecording()` 和 `_simulateAnalysisResult()` 都硬编码 `mode='quick'`。

如果选择了曲库歌曲 (`_selectedSong != null`)：
- `_selectedSong` 的 `id` 会添加到 FormData (`reference_song_id`)
- **但后端上传路由没有处理 `reference_song_id` 参数** → 实际无效

---

## 深度学习模型启用状态

| 模型 | 框架 | 何时启用 | 当前状态 |
|------|------|---------|---------|
| **Silero VAD** | ONNX Runtime | Pro/Compare 模式 | ✅ 正常 (`_run_voice_quality_detection`) |
| **Style Classifier** | ONNX Runtime (INT8) | Pro/Compare 模式 | ✅ 正常 (`_run_singing_style_detection`) |
| **Self-Referenced DTW** | librosa DTW | Pro/Compare 模式 | ✅ 计算但不影响评分 |
| **Music Style** | Heuristic + DL | Pro/Compare 模式 | ⚠️ 部分工作 |
| **SingMOS** | — | — | v5.15 移除, v7.1 代码删除 |
| **Wav2Vec2 Emotion** | SpeechBrain/HF | v5.12 已移除 | ❌ 已替换为启发式 |
| **TorchCREPE** | PyTorch | PYIN detection_rate<50% | ✅ (需 FeatureFlags) |

---

## 六维评分体系 ★vNext (重构计划)

> **重大变更 (vNext)**: 五维 → 六维 + 音色加减分。音准/节奏降权至各10%，发声技术提权(20%→25%)并拆分为咬字清晰度+气声比两个子维度，新增肌肉力量维度(25%，身体+面部两子维度)，音色作为额外加减分项(最多+3/-5，clamp到[0,100])。

### 权重分配

| 维度 | 权重 | 子维度 |
|------|------|--------|
| 音准 (Pitch) | 10% | — (从30%降权) |
| 节奏 (Rhythm) | 10% | — (从20%降权) |
| 气息 (Breath) | 20% | 长音支撑 + 动态控制 + 气口设计 + 气声技巧 |
| 发声技术 (Technique) | 25% | 咬字清晰度(50%) + 气声比(50%) |
| 肌肉力量 (Muscle Strength) | 25% | 身体肌肉力量(50%) + 面部肌肉力量(50%) |
| 艺术表现 (Artistry) | 10% | 颤音品质 + 动态控制 + 乐句表现力 + 音高变化 |

**权重合计**: 10+10+20+25+25+10 = **100%** ✓

> **额外加减分**: 音色 (Timbre) — 在六维总分计算后独立应用，最多 **+3** / 最多 **-5**，最终总分 **clamp 到 [0, 100]**。音色不参与维度权重分配。

> 相关文档: [PRD](../1-product/PRD.md) | [架构](ARCHITECTURE.md) | [TDD](../3-quality/TDD.md) | [BDD](../3-quality/BDD.md)

### 权重配置机制 ★v6.0

#### 四层优先级 (高→低)

| 优先级 | 来源 | 存储位置 | 适用场景 |
|--------|------|---------|---------|
| 1 | 请求参数 `scoring_weights` | 请求体 | 对比分析手动调参 |
| 2 | 歌曲关联配置 | 曲库 `scoring_config` 字段 | 录入歌曲时保存 |
| 3 | 用户本地预设 | 前端 `localStorage` / JSON 文件 | 个人偏好 |
| 4 | 风格预设 | `config/styles.yaml` | 自动检测或手动选择 |

> **没有硬编码兜底**: 配置文件缺失或格式错误时，系统启动即报错 (`ConfigError`)，不静默降级。配置文件是唯一的真相来源 (Single Source of Truth)。

#### 风格预设权重表

| 风格 | Pitch | Rhythm | Breath | Tech | Muscle | Art | 联动阈值调整 |
|------|-------|--------|--------|------|--------|-----|------------|
| 流行 (默认) | 10% | 10% | 20% | 25% | 25% | 10% | 标准阈值, 与 config/default.py 一致 |
| 美声 | 12% | 8% | 25% | 25% | 20% | 10% | Pitch MAE≤10, Breath≥5s, Rhythm≤15% |
| 民族 | 12% | 10% | 18% | 22% | 20% | 18% | 滑音不计入跑调 |
| 说唱 | 5% | 25% | 10% | 25% | 15% | 20% | Pitch MAE放宽至≤25, 节奏权重加倍 |

#### 系统推荐算法

系统分析标准音频的 6 个维度的声学特征，按规则给出权重调整建议：

| 分析维度 | 检测方法 | 推荐规则 |
|---------|---------|---------|
| 音域 | 基频 min/max (半音) | 跨度 > 24 → Pitch +3% |
| 节奏 | BPM变异系数 + onset密度 | CV > 0.3 → Rhythm +3% |
| 长音 | ≥2s 连续高能量段占比 | > 30% → Breath +3% |
| 咬字 | 辅音清晰度 + 共振峰稳定性 | 清晰 → Technique +3% |
| 力量 | RMS峰值 + 泛音丰富度 | 充沛 → Muscle +3% |
| 动态 | RMS标准差 (dB) | > 20dB → Artistry +3% |

> 推荐结果含每项调整的文字理由。用户可一键应用或微调后保存为自定义预设。详见 BDD: [scoring-config.feature](../../tests/bdd/features/scoring-config.feature)。

#### 有参考时的双轨评分

```
六维绝对评分 (always)          DTW 对比指标 (有参考时)
├─ total_score (六维加权)       ├─ dtw_score (0-100)
├─ scores.pitch/rhythm/...      ├─ pitch_match_rate (%)
├─ level + stars                ├─ rhythm_match_rate (%)
├─ advice (基于各维度弱项)      ├─ problem_segments
└─ voice_quality                └─ alignment_confidence

两者互补, DTW 不替代六维。DTW 置信度低时以六维为准。
```

### 等级划分

| 分数区间 | 等级 | 星级 | 颜色 |
|---------|------|------|------|
| 88-100 | 专业级 | ★★★ | #22c55e |
| 78-88 | 优秀 | ★★☆ | #3b82f6 |
| 62-78 | 良好 | ★★ | #10b981 |
| 45-62 | 中等 | ★☆ | #f59e0b |
| 25-45 | 及格 | ★ | #f97316 |
| 0-25 | 待改进 | ☆ | #ef4444 |

---

## v6.1 评分公式变更 (2026-07-06)

### Technique: 基线归零

```
v5.x:  technique_score = 50 + vibrato 加分 + slide 加分
v6.1:  technique_score = 0  + vibrato 加分 + slide 加分 + falsetto 加分
```

HNR(40%) + CPP(30%) + technique_score(30%) = 技术维度总分。
技术维度仍由声带闭合质量主导; technique_score 仅反映技巧运用程度。

### Breath: 连续线性映射

```
v5.x:  if pitch_stability > 80:  score += 20  (步进加分)
v6.1:  score += pitch_stability * 0.40        (连续映射)

v5.x:  for each long_note: score += min(30, dur_s * 2.0)  (单句累加)
v6.1:  total_dur = sum(all long notes); score += min(30, total_dur * 2.0)  (总计)
```

所有子维度 (长音支撑/动态控制/气口设计/气声技巧) 从步进改为连续。

### Artistry: 独立声学信号

```
v5.14: artistry = pitch*0.20 + rhythm*0.25 + breath*0.20 + technique*0.35 + modulation(±10)
v6.1:  artistry = vibrato_expressiveness*0.30 + dynamic_expressiveness*0.30
                + phrase_expressiveness*0.25 + pitch_variation*0.15
```

每个子维度基于真实声学测量, 不再依赖其他维度分数。

---

## 各维度算法详解

### 1. 音准评分 ★v6.2

**特征提取** (`services/features/pitch.py`):
- F0 → MIDI (12 × log2(f0/440) + 69)
- 多指标体系 (v5.14引入, v6.2启用): MAE, RPA, RCA, gross_error_rate, octave_error_rate, relative_smoothness
- pitch_breaks: v6.2 修复 — 仅计数连续有声帧间跳变 + 排除八度跳变 (1000-1400音分, YIN八度混淆 [de Cheveigne 2002])

**评分** (`services/scoring/pitch_scorer.py`) — v6.2 多指标加权融合:

| 指标 | 权重 | 公式 | 文献 |
|------|------|------|------|
| MAE 指数衰减 | 40% | `100 × exp(−mae/40)` | Wager 2022 |
| RPA (Raw Pitch Accuracy) | 25% | `rpa × 100` — \|cents\|<50 帧比例 | Cao et al. 2008 |
| RCA (Raw Chroma Accuracy) | 10% | `rca × 100` — 八度折叠准确率 | Cao et al. 2008 |
| Gross Error 惩罚 | 15% | `100 − min(100, (rate−0.05)×200)` — \|cents\|>200 帧比例 | Sundberg 1987 |
| Smoothness | 5% | `max(0, 100−(cv−1.0)×50)` — f0相邻帧变化CV | Canazza et al. 2014 |
| Octave Error 惩罚 | 5% | `max(0, 100−rate×200)` | pitch-benchmark |

**v6.2 PYIN 校准依据**:
- YIN @ 16kHz 对非有声帧赋值随机 f0 (NaN率=0%), 产生 3.5x 虚假帧间跳变 (785 vs PYIN 226)
- 权重调整: 帧间指标 (smoothness 10%→5%) 受污染; 聚合指标 (MAE 35%→40%) 鲁棒
- 断层惩罚: 率阈值 ÷3.5 校正因子, 仅 >5% 真实率触发 (PYIN参考: 正常演唱 2-5%)
- 文献: de Cheveigne & Kawahara (2002) — YIN低SNR下误差率升高

**惩罚项**:
- 检测率 < 50%: 扣分 = (0.5 − rate) × 30
- 音高断层: 率阈值 `break_rate = breaks / est_pairs / 3.5`, 仅 >5% 时罚 ≤15 分
- 长音波动 > 30音分: 扣分 ≤10

### 2. 节奏评分

**特征提取** (`services/features/rhythm.py`):
- 双路径策略:
  1. 优先: 基频变化 onset 检测 (>100音分跳变视为音符起始)
  2. 降级: librosa onset_strength + beat_track
- 计算 onset 与最近节拍点的归一化偏差 (偏差/拍间隔)
- 统计: 平均偏差比、最大偏差比、脱离节拍段数、节奏不规则度 (beat intervals CV)

**评分** (`services/scoring/rhythm_scorer.py`):
- 基础分: 分段线性 (excellent≤0.12 → 100, good≤0.25, pass≤0.38)
- 惩罚: 不规则度>0.3 扣分、BPS 异常 (<0.5 或 >5)

**阈值**:

| 级别 | 偏差比例 | 说明 |
|------|---------|------|
| 专业级 | ≤12% 拍长 | 节拍精准 |
| 良好 | ≤25% 拍长 | 基本对齐 |
| 合格 | ≤38% 拍长 | 有一定偏差 |

### 3. 气息评分 (v5.16 纯净人声校准)

**特征提取** (`services/features/breath.py`):
- 四子维度评估体系:

| 子维度 | 权重 | 评估内容 |
|--------|------|---------|
| 长音支撑 | 40% | ≥3秒连续高能量段的数量和基频/泛音稳定性 |
| 动态控制 | 25% | 弱唱质量、渐强渐弱平滑度、动态范围 |
| 气口设计 | 20% | 干净换气点数量、乐句连贯性 |
| 气声技巧 | 15% | 风格适配 HNR 区间 (可控气声 vs 无效漏气) |

- 艺术化波动检测: RMS自相关 + 基频-能量相关性 → 区分有规律起伏 vs 随机抖动

**评分** (`services/scoring/breath_scorer.py`):
- 使用 `professional_breath_score` (加权综合 + 艺术化判定 + 奖励分)
- 正向加分为主: 长音优秀+5、弱唱优秀+5
- 严重问题才惩罚: 气息断层>3处 扣分

**v5.16 纯净人声校准** (Demucs分离后):
- 非艺术波动惩罚: 阈值 0.25→0.35, 惩罚系数 60→30 (纯净人声RMS波动天然更大, 无伴奏平滑)
- 总分补偿: ×1.8 (Demucs后四子维度RMS/HNR/CPP系统性降解)
- 等级阈值放宽: 专业级85→73, 良好70→58, 合格55→43
- 标记: `BreathStabilityResult.is_clean_vocal` → `BreathAnalyzer` → `BreathScorer`
- 效果: Pro Breath 9.8→56.3 (+474%), Quick/Pro Breath差 -46.6→-0.1

**HNR 风格阈值**:

| 风格 | 优秀区间 | 可接受最低 |
|------|---------|-----------|
| 流行 | 8-15 dB | 5 dB |
| 美声 | 20-30 dB | 15 dB |
| 民族 | 15-25 dB | 10 dB |
| 说唱 | 5-12 dB | 3 dB |

### 4. 发声技术评分 ★vNext (重构: 咬字清晰度 + 气声比)

> **vNext 变更**: 原 HNR/CPP/技巧完成度 体系替换为 咬字清晰度 + 气声比。原 HNR/CPP 信号部分归入气声比子维度，技巧完成度(颤音/滑音/假声)移至艺术表现维度。

**子维度 4a: 咬字清晰度 (Articulation Clarity) — 50%**

**特征提取** (新文件 `services/features/articulation.py`):
- 辅音清晰度: 高频瞬态能量检测 → 爆破音/摩擦音/鼻音的清晰程度
- 共振峰稳定性 (F1-F3): 元音段 formant 轨迹稳定性 → 咬字规范性
- 音节边界检测: onset strength 突变点 → 咬字节奏感
- 频谱质心变化率: 辅音-元音过渡段的频谱质心变化速率

**评分** (新文件 `services/scoring/technique_scorer.py`):
- 辅音清晰度(40%) + 共振峰稳定性(30%) + 音节边界清晰度(20%) + 过渡段质量(10%)
- 风格感知: 流行/R&B 咬字可松弛, 美声/民族 咬字需字正腔圆

**子维度 4b: 气声比 (Breath-to-Voice Ratio) — 50%**

**特征提取** (复用 + 增强):
- HNR (谐波噪声比): 反映声带闭合质量 — 低HNR=高气声比例
- CPP (倒谱峰值突出): 声门闭合周期峰值 — 验证HNR判断
- 高频噪声能量比 (>5kHz): 气声会产生额外高频噪声
- 频谱倾斜 (Spectral Tilt): 气声导致高频衰减斜率变化

**评分** (新文件 `services/scoring/technique_scorer.py`):
- HNR(35%) + CPP(25%) + 高频噪声比(20%) + 频谱倾斜(20%)
- 风格感知阈值: 美声HNR>20dB满分, 流行实声>12dB满分, 气声唱法>8dB正常
- 气声控制力: 可控气声(风格选择) vs 不可控漏气(技术缺陷) — 通过HNR稳定性区分
- 混合音频检测: 识别伴奏 → HNR应用1.5x修正系数

### 5. 肌肉力量评分 ★vNext (新增)

> **vNext 新增**: 反映演唱中的身体参与度。歌唱不仅是声带运动，更是全身协调 — 呼吸肌群(横膈膜/肋间肌)、核心肌群、面部肌肉共同作用。

**子维度 5a: 身体肌肉力量 (Body Muscle Strength) — 50%**

**特征提取** (新文件 `services/features/muscle_strength.py`):
- 气息支撑力: 长音 RMS 衰减率 — 横膈膜持续支撑能力
  - 衰减率 < 0.5 dB/s: 优秀 (强大核心支撑)
  - 衰减率 0.5-1.5 dB/s: 良好
  - 衰减率 > 1.5 dB/s: 需加强
- 动态爆发力: RMS 峰值上升速率 (dB/ms) — 核心肌群瞬间发力
- 音量维持能力: 高音量段 (> -6dBFS) 持续时间占比
- 气息-音量耦合度: 气息压力与输出音量的线性相关度

**评分** (新文件 `services/scoring/muscle_scorer.py`):
- 气息支撑力(40%) + 动态爆发力(25%) + 音量维持(20%) + 气息-音量耦合(15%)
- 身体力量充沛 → 长音稳、高音亮、弱唱不虚

**子维度 5b: 面部肌肉力量 (Facial Muscle Strength) — 50%**

**特征提取** (新文件 `services/features/muscle_strength.py`):
- 共振峰能量集中度: F1-F3 能量/总能量比 — 面部共鸣腔体调节
- 歌手共振峰 (Singer's Formant): 2.8-3.5kHz 能量簇 — 面罩共鸣强度
- 泛音丰富度: 谐波能量衰减斜率 — 面部肌肉微调共鸣
- 高频延伸: >8kHz 谐波存在性 — 面部共鸣的高频泛音

**评分** (新文件 `services/scoring/muscle_scorer.py`):
- 歌手共振峰(35%) + 共振峰集中度(25%) + 泛音丰富度(25%) + 高频延伸(15%)
- 面部肌肉参与度高 → 声音穿透力强、音色明亮、泛音丰富

**肌肉力量与气息的区分**:
- 气息(Breath): 评估"气息使用策略" — 长音设计、动态控制、气口安排、气声风格
- 肌肉力量(Muscle): 评估"身体机能基础" — 核心支撑、面部共鸣、发声耐力
- 两者互补: 好的气息策略 + 弱的肌肉力量 → 长音设计合理但支撑不足
- 两者互补: 差的气息策略 + 强的肌肉力量 → 本能发声但技巧欠缺

### 6. 音色调整 (Timbre Adjustment) ★vNext (新增 — 独立加减分)

> **vNext 新增**: 音色不参与百分制评分 (音色好坏有主观性)，但作为独立加减分项影响最终得分。优质音色可加分(最多+3)，明显音色缺陷可扣分(最多-5)。

**特征提取** (新文件 `services/features/timbre.py`):
- 音色明亮度: 频谱质心 + 高频能量比
- 音色温暖度: 低频谐波丰富度 (200-800Hz)
- 音色厚度: 谐波-噪声比 + 泛音密度
- 音色纯净度: 非谐波成分比例 + 杂音检测
- 音色独特性: 与通用音色模型的偏离度 (Statistical Timbre Model)
- 鼻音/喉音检测: 反共振峰检测 + 频谱窄带峰值

**加减分规则**:
| 条件 | 调整 | 说明 |
|------|------|------|
| 音色纯净 + 泛音丰富 + 明亮温暖 | **+3分** | 优质音色 |
| 音色纯净 + 泛音较丰富 | **+1~2分** | 良好音色 |
| 音色一般 (无特别优劣) | **0分** | 中性 |
| 轻度鼻音/喉音 + 泛音较少 | **-1~2分** | 轻微音色问题 |
| 明显杂音 + 鼻音/喉音重 | **-3~4分** | 音色缺陷 |
| 严重音色问题 (沙哑/闷/尖锐刺耳) | **-5分** | 严重影响听感 |

**设计原则**:
- 音色加减分在六维总分计算完成后独立应用
- 音色不参与维度权重分配 (独立于百分制)
- 加减分有上限 (+3/-5), 不对称设计: 扣分空间>加分空间
- 最终总分 **clamp 到 [0, 100]**，不会因音色加分超过100或扣分低于0
- 音色判断需标注置信度, 低置信时自动归零 (不加不减)

### 7. 艺术表现评分 ★v6.1

**评分** (`services/scoring/artistry_scorer.py`) — v6.1 独立声学信号:
- v6.1 重构: 不再从其他维度合成 (旧: Pitch×0.20+Rhythm×0.25+Breath×0.20+Tech×0.35)
- 四子维度独立评估: 颤音品质(30%) + 动态控制(30%) + 乐句处理(25%) + 音高变化(15%)
- 声学调制: 动态对比度 + 音高多样性 (来自原始 f0/音频)
- 情绪置信度来自启发式声学分析 (v5.12 已移除 Wav2Vec2 情绪模型)
- v6.2 已知限制: 区分度 1.9 (流行唱法下子维度变化小), 待 v6.3 引入音色模型

### 8. 跨维度评分修正 ★v6.2

**实现** (`services/scoring/score_modifiers.py` — 新文件)

设计原则: 仅施加有物理因果关系的修正 (非统计相关), 单项 ≤15%, 总修正 ≤25%.

| 修正 | 因果链 | 触发条件 | 幅度 | 文献 |
|------|--------|---------|------|------|
| HNR多频带CV → 气息 | 声带闭合不一致 → 气息支撑不足 | HNR CV > 0.15 | ≤15% | de Krom 1993 |
| Voicing置信度 → 音准 | 低置信度 → f0 不可靠 | confidence < 0.6 | 标记(不改分) | de Cheveigne 2002 |
| 频谱倾斜 → 气声技巧 | HNR低+倾斜平坦=艺术气声; HNR低+倾斜陡峭=漏气 | tilt > −10 (艺术) / tilt < −14 (漏气) | ≤15% | Sundberg 1987 |
| 气息-音准耦合 | pitch_wobble高 + HNR不稳定 → 气息不足 | wobble>40 + CV>0.20 | ≤15分 | Titze 1994 |

**接入点**: `ScoreServiceV4.calculate()` → 五维评分后, 加权总分前. 通过 `FeatureFlags.enable_cross_dimension_modifiers` 控制.

---

## 底线规则

| 规则 | 条件 | 惩罚 |
|------|------|------|
| 连续跑调 | ≥5个连续音符偏差>50音分 | 总分-20 |
| 脱离节拍 | 脱拍比例>40% | 总分上限70 |
| 严重漏气 | HNR<3dB | 总分上限50 |

实现: `services/scoring/critical_rules.py`

---

## DL 融合 (v7.1 已完全移除)

- **v5.15**: SingMOS 从评分管线移除
- **v7.1**: `_apply_dl_fusion()` 方法 + `_assess_with_dl()` 函数 + `dl_quality_assessor.py` 文件全部删除
- 当前评分完全基于声学信号处理 (无 DL 融合)

---

## 双评估模式

| 特性 | 快速评估 | 专业评估 |
|------|---------|---------|
| 耗时 | ~15-20s (CPU) | ~130-170s (CPU) / ~30-50s (GPU) |
| 阈值 | 标准 (与专业模式相同) | 标准 (0-100分) |
| 逐句评分 | ✗ | ✓ |
| 音色分析 | ✗ | ✓ |
| 可视化图表 | ✗ | ✓ |
| DL 质量评估 | ✗ (v5.15 已全局移除) | ✗ (v5.15 已全局移除) |
| 自参照一致性 | ✓ | ✓ |

### 算法复杂度与耗时分解

> 以 3 分钟 44.1kHz 单声道音频为基准 (~30MB WAV)。所有耗时在 16GB RAM + SSD 环境下测量。

| 算法 | 库 | 复杂度 | Quick 耗时 | Pro 耗时 | 内存 |
|------|-----|--------|-----------|---------|------|
| **Silero VAD** | PyTorch | O(n) 逐帧 | < 1s | < 1s | ~50MB (模型) |
| **PYIN f0** | librosa | O(n × fmin_eggs) | ~5s | ~8s | ~80MB |
| **Onset Strength** | librosa | O(n × n_fft) | ~2s | ~3s | ~40MB |
| **RMS 能量** | numpy | O(n) 向量化 | < 0.5s | < 1s | ~10MB |
| **HNR** (自相关法) | scipy | O(n × lag_max) | ~2s | ~3s | ~30MB |
| **CPP** (倒谱法) | numpy | O(n × n_fft × log(n_fft)) | ~1s | ~2s | ~30MB |
| **Chromaprint** | acoustid | O(n × n_fft) | 跳过 | 跳过 (仅匹配用) | — |
| **Demucs htdemucs_ft** | PyTorch | O(n × model_params) | 跳过 | ~120s CPU / ~25s GPU | ~800MB |
| **DTW** (全局) | scipy/numpy | O(m × n) | 跳过 | 跳过 (仅对比) | ~130MB |
| **自参照一致性** | numpy | O(n) 向量化 | < 1s | < 1s | ~5MB |
| **评分计算** (六维) | numpy | O(1) 聚合 | < 0.5s | < 1s | ~2MB |
| **可视化渲染** | matplotlib | O(n) 采样 | 跳过 | ~8s | ~50MB |

### Quick 模式耗时火焰图

```
VAD check       ██ 1s
PYIN f0         ██████████ 5s         ← 最大瓶颈 (31%)
Onset strength  ████ 2s
HNR + CPP       ██████ 3s
RMS + breath    ██ 1s
Technique       ██ 1s
Acoustic check  █ 0.5s
Scoring calc    █ 0.5s
Advice gen      █ 0.5s
Self-consistency █ 0.5s
────────────────────────────────
Total           ████████████████████████████ 15-20s
```

### v6.2 性能优化 (2026-07-07)

| 优化 | 方法 | v6.1 | v6.2 | 依据 |
|------|------|------|------|------|
| harmonicity 计算 | np.correlate O(N²) → FFT自相关 O(N log N) [Wiener-Khinchin] | 566.9s | <0.1s | cProfile: 97%总耗时 |
| HPSS 调用 | 预计算一次, 调用点复用 (3→1) | ~18s | ~6s | 实测单次HPSS 5.9s |
| 动态范围 | max/min → p95/p5 百分位 | 异常值 101.9dB | 正常 20-25dB | 物理上限 ~40dB |
| Praat VQ Quick | 截断到 60s (统计收敛足够) | ~5s | ~0.8s | 临床标准 3-5s |
| pitch_breaks | 仅连续帧+排八度+率阈值 | 无效(1000+) | 有效 | YIN vs PYIN 校准 |

**完整管道**: ~700s → ~54s (13x). 剩余瓶颈: audio_service.analyze() 内多步 librosa 操作.

### Pro 模式耗时火焰图 (CPU)

```
VAD check       █ 1s
Mixed detection █ 0.5s
Demucs separate ████████████████████████████████████████████████████████████ 120s ← 70%
PYIN f0         ████ 8s
Onset strength  ██ 3s
HNR + CPP       ███ 4s
RMS + breath    █ 1s
Technique       ██ 2s
Phrase scoring  ██ 5s
Visualization   █████ 8s
Scoring calc    █ 1s
Advice gen      █ 1s
Self-consistency █ 0.5s
────────────────────────────────────────────────────────────────────────
Total           ████████████████████████████████████████████████████████████████████████ 155-170s
```

> **核心瓶颈**: Demucs 占 70-78% 总耗时。GPU 加速是最有效的优化手段 (120s → 25s)。
> 其次为 PYIN f0 (8s) → 可考虑 TorchCREPE 备选或降低 hop_length。
> 可视化 (8s) 可通过降低 DPI 或异步生成优化。

---

## 算法评估 (v5.9 审计 → v5.17 状态)

> 原始审计: [算法审计报告](ALGORITHM_AUDIT.md) (v5.9, 审计结论 6/10)

### 已修复 (v5.11-v5.17)

| 问题 (v5.9) | 修复版本 | 方案 |
|------|------|------|
| [P0-1] 未先做人声分离 | v5.11 | Demucs 接入评分主流程 |
| [P0-2] DTW 未默认化 | v5.15 | `_find_reference_audio()` 自动搜索 |
| [P1-1] librosa beat_track 节奏 | v5.15 | CV 重校准 + 标记传递链 |
| [P1-2] Wav2Vec2 域不匹配 | v5.12 | 移除 + v5.14 复合评分替代 |
| 魔法数字散落 | v5.12 | `EmpiricalThresholds` +14 字段 |

### 仍待解决

| 问题 | 影响 | 状态 |
|------|------|------|
| 23 个经验参数未校准 | 全局一致性 | 🟡 v6.1 计划 |
| ~~无混响补偿~~ | ✅ v6.0: `ReverbCompensator` 已接入管线 | ✅ 已修复 |
| 未跳过纯器乐段 (前奏/间奏) | 拖低评分 | 🟡 Silero VAD 已集成 |
| 古典/戏曲风格无效 | Rubato/微分音 | 🟡 低优先级 |
| ~~混合音频检测误判~~ | ✅ v6.0: 文献驱动五特征融合, 0 误判 | ✅ 已修复 |

### 混合音频检测: 文献驱动重构 ★v6.0

#### 算法 (`services/features/acoustic.py:detect_mixed_audio`)

基于以下论文重新设计, 五特征加权投票:

| 特征 | 理论来源 | 权重 | 说明 |
|------|---------|------|------|
| HPSS 谐波能量比 | Fitzgerald (2010). DAFx | 0.25 | 中值滤波分离谐波/冲击成分 |
| 子带频谱平坦度 (1.5-3kHz) | Lehner et al. (2018). TASLP §4 | 0.30 | 文献证明最可靠的单特征 |
| 高频能量 (>5kHz) | — | 0.20 | 镲片/弦乐泛音指示 |
| 谐波度 (Harmonicity) | Lehner et al. (2018) | 0.15 | f0 整数倍能量集中度 (自相关法) |
| 全频带频谱平坦度 | — | 0.10 | 辅助特征 |

移除: 低频能量 (<300Hz) — Lehner 2018 证明受录音/房间/声部影响过大

**HPSS 门控** [Driedger et al. 2014 §3]:
- `hpss_ratio > 0.88`: 跳过 (极纯谐波 → 纯人声)
- `0.72-0.88`: 五特征加权评分
- `< 0.72`: 显著非谐波内容指示伴奏

**决策阈值**:
- `mixed_score > 0.55` → 高置信混合
- `mixed_score > 0.40` → 中置信混合
- `mixed_score > 0.30` → 灰区 (触发分离, 低置信)
- `≤ 0.30` → 纯人声

#### 真音频验证 (30s 片段, 前 30s 足以建立频谱统计)

| 音频 | HPSS | 子带平坦度 | 谐波度 | 判定 | 预期 |
|------|------|-----------|--------|------|------|
| 1（高分） | 0.799 | 0.159 | 0.277 | ✅ CLEAN | CLEAN |
| 恋人（高分） | 0.866 | 0.126 | 0.241 | ✅ CLEAN | CLEAN |
| 手写的从前（高分） | 0.883 | 0.102 | 0.173 | ⚠️ CLEAN | MIXED |

**已知局限**: 手写的从前(轻钢琴抒情歌) 前 30s HPSS ratio 0.883 > 0.88 门控阈值。
轻钢琴伴奏自身高度谐波, HPSS 无法将其与人声区分 [Driedger 2014 §3]。
此为信号处理方法的理论上限, Lehner 2018 最终转向 LSTM 解决此问题。全曲分析可能因后续段落不同而产生不同判定。

#### v5.17 → v6.0 改进

| 指标 | v5.17 | v6.0 |
|------|-------|------|
| 特征数量 | 2 (低频能量+全频平坦度) | 5 (HPSS+子带平坦度+高频+谐波度+全频平坦度) |
| 纯人声误判率 | 75% (3/4) | **0%** (0/4) |
| 文献依据 | 经验阈值 | Fitzgerald+Driedger+Lehner |

---

## 开发与测试原则 ★vNext

### 单一职责: 维度独立可测

**每个评分维度必须能独立测试，不依赖其他维度**:

| 原则 | 说明 |
|------|------|
| **独立输入** | 每个维度评分器仅接收该维度所需的特征数据，不依赖其他维度的评分结果 |
| **独立测试** | 测试音准只需提供 `pitch_deviation`，不需要完整音频管线；每个维度可单独跑、单独调试 |
| **独立配置** | 每个维度通过 `FeatureFlags` 独立开关，关闭某维度不影响其他维度计算 |
| **独立文件** | 一个维度 = 一个 scorer 文件 + 一个 feature 文件，不跨文件耦合 |

### 低耦合: 七维解耦 ★v7.0

| 维度 | 原则 | 本项目中体现 |
|------|------|------------|
| **代码耦合** | 每个 scorer 文件只负责一个维度的评分算法 | `pitch_scorer.py` 不 import `rhythm_scorer.py` |
| **数据耦合** | scorer 输入固定类型的 dataclass, 不依赖 dict 内部结构 | `PitchDeviationResult` (frozen dataclass) |
| **环境耦合** | scorer 不依赖文件系统/网络/全局配置 | 所有阈值从构造函数注入 `PitchThresholds` |
| **控制耦合** | scorer 之间不互相调用, 仅 ScoreServiceV4 调度 | `ScoreServiceV4.calculate()` 是唯一调度点 |
| **外部耦合** | 特征提取与评分分离, 通过 AudioFeaturesResult 通信 | `services/features/` → dataclass → `services/scoring/` |
| **时序耦合** | 评分维度计算顺序无关, 不存在"必须先算 Pitch 再算 Breath" | 任一维度可单独计算, 互不阻塞 |
| **UI 耦合** | 评分服务不感知前端框架 | 同一套 scorer 在 Flask/Vue/FastAPI 下完全相同 |

```
❌ 反模式:
  ArtistryScorer 内部调用 PitchScorer.get_score() → 改 Pitch 算法破坏 Artistry 测试
  scorer 依赖全局 config.SCORE_WEIGHTS → 测试无法隔离

✅ 正确模式:
  ScoreServiceV4 分别调用各 scorer, scorer 之间零引用
  每个 scorer 的阈值/权重通过构造函数注入, 测试时传 mock 即可
```

### 零硬编码 ★v7.0

```
❌ 禁止:  scorer 内部写死阈值数字 (如 if score > 85)
❌ 禁止:  特征提取器硬编码文件路径
❌ 禁止:  WebSocket 连接地址写死 localhost:5000

✅ 要求:  所有阈值从 ScoringConfig 读取 (单例注入)
✅ 要求:  所有路径从 Config 对象读取 (构造函数注入)
✅ 要求:  前端通过 window.BACKEND_URL 动态获取后端地址
```

### 测试效率

- **单维度测试**: 测试 Pitch 评分调整时只需跑 `pitch_scorer` 相关测试，不必跑完整的 6 维度管线
- **Mock 友好**: 每个 scorer 接收明确的输入类型，测试时构造输入即可，不需启动 Flask 或加载 DL 模型
- **并行开发**: 六个维度的算法可并行开发，互不阻塞

### Feature Flag 粒度

每个 Feature Flag 仅控制一个维度或一个子维度:

| Flag | 控制范围 | 关闭时行为 |
|------|---------|-----------|
| `enable_pitch` | PitchScorer | 该维度返回中性分 50 |
| `enable_rhythm` | RhythmScorer | 该维度返回中性分 50 |
| `enable_breath` | BreathScorer | 该维度返回中性分 50 |
| `enable_technique` | TechniqueScorer (咬字+气声比) | 该维度返回中性分 50 |
| `enable_muscle` | MuscleStrengthScorer (身体+面部) | 该维度返回中性分 50 |
| `enable_artistry` | ArtistryScorer | 该维度返回中性分 50 |
| `enable_timbre` | TimbreAdjustment | 音色加减分 = 0 |

> **设计意图**: 关一个维度不影响其余。权重自动重新归一化到 100%。

---



## DTW 角色: 特征提供者, 非评分引擎 ★v6.0

### 设计决策 (基于学术文献)

| 论文 | 结论 |
|------|------|
| Bohm 2017 (IJCNN) | DTW+声学特征融合 → 与人工听感相关度 0.87, 纯DTW仅 0.52 |
| Gupta 2021 (APSIPA) | DTW对齐后节奏评分相关度从 0.53 → 0.78, 但仅限节奏 |
| Santos & Masiero 2026 (arXiv) | 综述: DTW仅适用于音准对齐和节奏对齐, 其他维度无效 |

**核心结论**: DTW 只擅长两件事 — 音准对齐和节奏对齐。气息/技术/艺术给它打分是"用错了工具"。

### 架构: DTW 降级为偏差数据提供者

```
标准音频 ─┐
          ├─ DTW 三级对齐 → 仅产出偏差数据:
用户音频 ─┘    ├─ dtw_pitch_cents: [...]    逐帧音分偏差
               ├─ dtw_rhythm_offset: [...]  逐帧节拍偏移 (ms)
               ├─ dtw_warp_path: [...]      对齐路径
               └─ alignment_confidence: float  全局置信度
                                   │
                                   ▼
                          ScoreServiceV4 (唯一评分入口)
               ├─ pitch_scorer:  PYIN + dtw_pitch_cents 加权融合
               ├─ rhythm_scorer: onset + dtw_rhythm_offset (代替CV估算)
               ├─ breath_scorer:  RMS/HNR/CPP/长音/弱唱 (DTW不参与)
               ├─ technique_scorer: HNR/CPP/颤音/滑音 (DTW不参与)
               ├─ artistry_scorer: 四维复合 (DTW不参与)
               └─ critical_rules:  全局生效 (DTW不参与)
```

### 各维度融合公式

#### 音准: PYIN + DTW 加权

```
pitch_final = pitch_pyin × (1 - dtw_weight) + pitch_dtw × dtw_weight
dtw_weight  = alignment_confidence × 0.70   (上限 70%)
```

- PYIN 始终保有 ≥30% 权重 (绝对音准不被 DTW 完全覆盖)
- confidence < 0.3 → dtw_weight = 0 → 纯 PYIN

#### 节奏: Onset + DTW 加权

```
rhythm_final = rhythm_onset × (1 - dtw_weight) + rhythm_dtw × dtw_weight
dtw_weight   = alignment_confidence × 0.50   (上限 50%)
```

- 有 DTW 偏移时, 跳过 CV 估算 + irregularity 惩罚
- 无 DTW 时回退到现有 onset + CV 路径 (行为不变)

#### 气息/技术/艺术: DTW 不参与

| 维度 | 评估方法 | DTW 状态 |
|------|---------|---------|
| 气息 | 四子维度 (长音/动态/气口/气声) | ❌ 不参与 |
| 技术 | HNR/CPP/颤音/滑音/假声 | ❌ 不参与 |
| 艺术 | 四维复合 + 声学调制 | ❌ 不参与 |
| 关键规则 | 连续跑调/脱离节拍/严重漏气 | ❌ 不参与 (全局生效) |

### 改动范围

| 文件 | 改动 | 行数 |
|------|------|------|
| `services/comparison/scoring_engine.py` | 移除 _score_pitch/_score_rhythm/_score_breath/_score_volume | -120 |
| `services/scoring/pitch_scorer.py` | 新增 dtw_pitch_cents 可选参数 + 加权融合 | +35 |
| `services/scoring/rhythm_scorer.py` | 新增 dtw_rhythm_offset 可选参数 + 加权融合 | +30 |
| `api/business/audio_analysis.py` | compare 端点改调 ScoreServiceV4 | +15 |

### 不改动的文件 (四个文件零改动)

`breath_scorer.py`, `technique_scorer.py`, `artistry_scorer.py`, `critical_rules.py` — DTW 降级不涉及这四个文件, 逻辑和测试完全不变。仅 `pitch_scorer.py` 和 `rhythm_scorer.py` 新增 DTW 可选参数。
