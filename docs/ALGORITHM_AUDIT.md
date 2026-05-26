# 核心算法审计报告

> 审计日期: 2026-05-26 | 版本: v5.9 | 审计结论: **6/10**

---

## 审计范围

本次审计覆盖 `services/features/` (特征提取) + `services/scoring/` (评分计算) + `services/score_service.py` (总分协调) + `services/scoring_config.py` (阈值配置)。

共 12 个源码文件，~2000 行 Python 代码。

---

## 总体结论

架构设计良好但核心信号处理链路存在根本性问题。

### 评分卡

| 维度 | 得分 | 评价 |
|------|------|------|
| 架构设计 | 8/10 | 模块化好，可测试，可配置 |
| 音准算法 | 6/10 | 音分偏差计算正确，但缺调性感知 |
| 节奏算法 | 4/10 | 选错工具，对非流行乐基本无效 |
| 气息算法 | 7/10 | 四子维度专业，但依赖RMS |
| 技术算法 | 5/10 | HNR/CPP领域知识正确，但混合音频上不可靠 |
| 艺术算法 | 3/10 | 情绪模型域不匹配，评分基本随机 |
| 综合评分 | **6/10** | — |

---

## 详细发现

### 1. 信号处理链路缺陷 (P0)

**问题**: 评分主流程 (`ScoreServiceV4.calculate()`) 在原始音频上直接计算所有特征。原始音频可能包含:
- 伴奏乐器 (钢琴、鼓、吉他等)
- 环境噪声
- 混响

这些信号污染了 HNR (谐波噪声比)、CPP (倒谱峰值)、RMS (能量) 特征。

**证据**: `services/audio_service.py` 中 Demucs 人声分离已实现但仅在"人声分离"功能中使用，未接入评分流程。`technique_scorer.py` 中的 1.5x HNR 修正系数是亡羊补牢式的补丁。

**影响**: 技术评分维度 (~18% 权重) 在带伴奏音频上系统性不可靠。

**修复**: 在 `AudioService` 中增加 `_preprocess_for_scoring()` 步骤 — 若检测到混合音频 → 先跑 Demucs → 在纯净人声上计算特征。

### 2. DTW 参考评分未默认化 (P0)

**问题**: `services/comparison/` 实现了完整的三级DTW对齐引擎 (全局→句→音符)，单元测试 15/15 通过，但仅在 `/api/compare` 端点中使用。评分主流程 (`ScoreServiceV4.calculate()`) 仍然是纯绝对评分。

**影响**: 无法区分"唱得差"和"歌曲难"。初学者唱简单歌得分可能高于专业歌手唱复杂作品。

**修复**: 当用户提供了参考音频时，`ScoreServiceV4.calculate()` 应优先走 DTW 对比路径。

### 3. 节奏分析工具选择错误 (P1)

**问题**: `librosa.beat.beat_track` 假设:
- 恒定 BPM
- 4/4 拍号
- 清晰的节拍起音

实际唱歌场景中:
- 无伴奏独唱没有节奏乐器提供 beat 参考
- 艺术歌曲大量使用 Rubato (弹性速度)
- 民乐/戏曲使用非西方节奏体系

**代码位置**: `services/features/rhythm.py:72-73`

```python
tempo, beat_frames = librosa.beat.beat_track(
    onset_envelope=onset_env, sr=self.sample_rate, hop_length=self.hop_length
)
```

**修复方向**: 优先使用参考音频对比 (DTW) 的节奏维度。无参考时降级为 onset 密度/规律性评估。

### 4. 情绪评分域不匹配 (P1)

**问题**: 情绪模型训练数据是 IEMOCAP (英语对话语音，4类情感)。唱歌的情感表达通过:
- 音色变化 (而不是语调)
- 动态范围 (而不是音量)
- 颤音质量和密度
- 音高装饰

这些信号与语音情感信号完全不同。

**代码位置**: `services/scoring/artistry_scorer.py:89-114`

评分公式: `emotion_score = 60 + max_prob*20 + entropy_bonus`

- `max_prob` 通常在 0.25-0.40 之间 (模型对任何输入都不太确定)
- 因此情感分基本在 65-73 之间，几乎无区分度
- 占 14% 权重但无法提供有效信号

**修复方向**: Phase 3 替换为基于声乐特征的评分 (颤音质量+动态范围+音色变化+技巧多样性)。

### 5. 魔法数字审计 (P1)

以下阈值在代码中硬编码，无理论或实验依据:

| 值 | 位置 | 说明 |
|------|------|------|
| `PITCH_BREAK > 200 cents` | `pitch.py:84` | 音高断层阈值 |
| `PITCH_WOBBLE > 30` | `pitch_scorer.py:69` | 长音波动惩罚阈值 |
| `RHYTHM_IRREGULARITY > 0.3` | `rhythm_scorer.py:57` | 不规则度惩罚阈值 |
| `ONSET_OFF_BEAT > 0.3` | `rhythm.py:218` | 脱拍判定阈值 |
| `BASELINE_SCORE = 60` | `breath.py` 多处 | 气息各子维度基线分 |
| `SOFT_THRESHOLD = 0.6 * rms_mean` | `breath.py:222` | 弱唱判定阈值 |
| `HNR_MIXED_CORRECTION = 1.5x` | `technique_scorer.py:116` | 混合音频修正系数 |

**建议**: 全部提取到 `ScoringConfig`，标注为 `# 经验值 - 未经实验验证`。

### 6. 录音条件敏感性

RMS、HNR、CPP 均受以下因素影响:
- 麦克风距离 (近距离效应增强低频)
- 增益设置 (削波/底噪)
- 房间声学 (混响)
- 环境噪声

当前无任何归一化处理。不同设备录制的同一首歌会得到不同分数。

**修复**: Phase 2 引入 LUFS (EBU R128) 响度归一化。

### 7. 纯器乐段未处理

`AudioService` 将整段音频送入分析器。歌曲的前奏、间奏、尾奏 (纯器乐) 会被当作"没有音高的演唱"处理，拖低音准和气息评分。

Silero VAD (`models/voice_quality/silero_vad.onnx`) 已集成但仅用于"是否为人声"的二分类，未用于分段。

**修复**: 在特征提取前先用 VAD 标记人声段，仅在有声段计算评分特征。

---

## 测试覆盖

| 测试文件 | 测试数 | 通过 | 覆盖内容 |
|---------|--------|------|---------|
| `test_scorers.py` | 21 | 21 | 各维度评分器边界值测试 |
| `test_features.py` | 17 | 17 | 特征提取器基本功能 |
| `test_score_calibrator.py` | 14 | 14 | 评分配置和校准 |
| `test_comparison_dtw.py` | 15 | 15 | DTW对比引擎 |
| `test_services.py` | 6 | 6 | 服务层基本功能 |
| `test_repositories.py` | 6 | 6 | 数据层 |

**未覆盖**: 
- 真实多风格音频的端到端评分验证
- 混合音频 vs 纯净人声的评分对比
- 跨录音条件的评分一致性

---

## 附录: 源码文件索引

| 层 | 文件 | 行数 | 职责 |
|------|------|------|------|
| 特征 | `services/features/pitch.py` | 94 | 音分偏差计算 |
| 特征 | `services/features/rhythm.py` | 229 | 节拍对齐分析 |
| 特征 | `services/features/breath.py` | 419 | 气息四子维度分析 |
| 特征 | `services/features/technique.py` | 201 | 颤音/滑音/假声检测 |
| 特征 | `services/features/acoustic.py` | — | HNR/CPP 声学测量 |
| 评分 | `services/scoring/pitch_scorer.py` | 86 | 音准评分 |
| 评分 | `services/scoring/rhythm_scorer.py` | 76 | 节奏评分 |
| 评分 | `services/scoring/breath_scorer.py` | 144 | 气息评分 |
| 评分 | `services/scoring/technique_scorer.py` | 211 | 技术评分 |
| 评分 | `services/scoring/artistry_scorer.py` | 135 | 艺术评分 |
| 评分 | `services/scoring/critical_rules.py` | 74 | 底线规则 |
| 配置 | `services/scoring_config.py` | 377 | 阈值/权重配置 |
| 协调 | `services/score_service.py` | 377 | 总分加权+DL融合 |
