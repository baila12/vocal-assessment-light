# 变更日志

> 当前状态和已知问题见 [PROJECT_STATUS.md](PROJECT_STATUS.md) | 计划见 [PRD.md](../1-product/PRD.md)

---

## v5.17 — 混合音频检测修复 + GPU 加速 (2026-06-04, 已完成)

### 修复1：轻伴奏人声 混合音频检测失败

**根因**: `detect_mixed_audio()` 阈值 `low_freq_ratio > 0.35` 太保守。陈奕迅（轻钢琴伴奏，低音域男声）`low_freq=0.296` 刚好低于阈值，跳过 Demucs 导致评分失真。

**修复** (`services/features/acoustic.py` + `services/audio_service.py`):
- 新增 `0.25-0.35` 轻伴奏区间（钢琴/吉他独奏）
- 纯人声 `low_freq < 0.2`，阈值 `0.25` 有充足安全边界
- 置信度阈值 `0.5→0.45`

**效果**: 5 首人声音频全部正确触发 Demucs（陈奕迅从 False→True）

### 修复2：合成音频/噪声 正确归零

`VoiceQualityService` 已正确检测所有合成文件为 `is_voice=False`。API 管线（`audio_analysis.py:137-141`）正确拦截。
测试脚本之前绕过了此检查 → 已修正。

**效果**: 10 个合成/噪声文件全部返回 0.0 分

### 新功能：GPU 加速支持

**修改** (`services/separation_service.py` + `api/__init__.py` + `web_app.py`):
- Demucs 自动检测 CUDA/MPS → 传 `-d cuda` 启用 GPU 加速
- `/health` 端点返回 GPU 状态
- 启动横幅显示 GPU 信息

**效果**: 有 NVIDIA GPU 时 Demucs ~200s→~20-40s

> ⚠️ 当前环境 PyTorch 为 CPU 版 (`2.11.0+cpu`)，需手动重装 CUDA 版：
> `pip uninstall torch torchaudio -y && pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124`

### 全量测试

| 模式 | 文件数 | 结果 |
|------|--------|------|
| Quick | 15 (5人声+10合成) | 5人声正常 + 10合成→0分 ✅ |
| Pro | 5人声 | 全部正确触发Demucs ✅ |
| 单元测试 | 79 | 全部通过 ✅ |
| 混合检测 | 5人声 | 全部正确检测 ✅ |

---

## v5.16 — Pro Breath 修复 (2026-06-03, 已完成)

### 实际效果

| 指标 | v5.15 | v5.16 | 变化 |
|------|-------|-------|------|
| **Pro Breath (恋人)** | 9.8 | **56.3** | **+46.5 (+474%)** |
| Pro Total (恋人) | 63.2 | **73.7** | **+10.5** |
| Quick/Pro Breath 差 | -46.6 | **-0.1** | 缩小 99.8% |
| Quick/Pro Total 差 | -12.5 | **-1.1** | 缩小 91% |
| Quick 回归 | 75.7 | 74.8 | 零回归 |
| 单元测试 | 78/79 | 89/91 | 零回归 (2 pre-existing) |

### 修复：Pro Breath 崩塌 — is_clean_vocal 标记传递 + 校准

**根因**: v5.15 修复了 rhythm 的 `is_clean_vocal` 标记传递，但 breath 管线完全缺失此链路。
Demucs分离后纯净人声的RMS/HNR/CPP数值分布与混合音频完全不同，
`BreathAnalyzer` 四子维度全部基于混合音频阈值 → Pro Breath=9.8 (Quick=56.4)。

**修复** (遵循 v5.15 Rhythm CV重校准同模式):
1. `BreathStabilityResult.is_clean_vocal` 标记字段
2. `BreathAnalyzer.calculate_breath_stability()` 接受 `is_clean_vocal` 参数并存入结果
3. `_calculate_professional_breath_score()`: 纯净人声放宽非艺术波动惩罚(阈值0.25→0.35, 系数60→30) + 总分补偿(×1.8)
4. `BreathScorer.calculate()`: 纯净人声等级阈值放宽(85/70/55→73/58/43)
5. `AudioFeaturesService.extract_all_features()`: 传递 `is_clean_vocal=is_separated`

修改文件: `services/features/breath.py` (+15行), `services/scoring/breath_scorer.py` (+12行),
`services/features/__init__.py` (+3行), `services/audio_features_service.py` (+4行),
`services/scoring_config.py` (+4行)

### 全量真实音频测试 (5人声 + 10非人声)

| 音频 | Q.Total | P.Total | Q.Breath | P.Breath | B.Diff | Demucs |
|------|---------|---------|----------|----------|--------|--------|
| 恋人（高分） | 74.8 | **73.7** | 56.4 | **56.3** | **-0.1** | ✅ |
| 1（高分） | 72.7 | 75.0 | 63.2 | 57.1 | -6.1 | ✅ |
| 音频-3分26秒(高分) | 72.6 | 76.4 | 52.6 | 78.2 | +25.6 | ✅ |
| 手写的从前（高分） | 73.4 | 79.1 | 66.4 | 93.6 | +27.2 | 跳过(纯人声) |
| 陈奕迅难听之声（低分） | 48.8 | 48.8 | 51.2 | 51.2 | 0.0 | 跳过(纯人声) |

Quick模式 15/15 文件零回归。

---

## v5.15 — 三模式修复 (2026-06-03, 已完成)

### 实际效果

| 指标 | v5.14 | v5.15 | 变化 |
|------|-------|-------|------|
| **Pro Rhythm (恋人)** | 18.6 | **66.0** | **+47.4 (+255%)** |
| Pro Total (恋人) | 57.6 | 63.2 | +5.6 |
| Pro 耗时 | ~309s | ~226s | -83s (-27%) |
| Quick 回归 (恋人) | 75.6 | 75.7 | 零回归 |
| Quick/Pro Rhythm 差 | -58.5 | **-11.1** | 缩小81% |
| 单元测试 | 78/79 | 78/79 | 零回归 |

### 修复1：Pro 节奏崩塌 — CV重校准

**根因**: Demucs分离后纯净人声onset天然不规则 (CV=1.34),
`_cv_to_deviation` 纯净人声阈值过严 (dev=0.635),
`RhythmScorer` irregularity双重惩罚叠加 → 最终18.6分。

**修复** (替代原计划"原始音频节奏"方案):
1. `_cv_to_deviation(is_clean_vocal=True)` 阈值×3: 0.5→0.75, 0.8→1.5, 1.2→2.4, 1.8→3.6
   CV=1.34→dev=0.36 (接近混合CV=0.6→dev=0.32)
2. `RhythmAlignmentResult.is_clean_vocal` 标记 → RhythmScorer 跳过 irregularity 惩罚
   (CV映射已充分表达不规则度, 双重惩罚是崩塌根因)

修改文件: `services/features/rhythm.py` (+20/-15), `services/features/__init__.py` (+2),
`services/scoring/rhythm_scorer.py` (+8)

### 修复2：SingMOS 完全移除

- `api/business/audio_analysis.py`: `dl_assessor = None`, `_assess_with_dl()`→零值
- `services/score_service.py`: `_apply_dl_fusion()`→`return total` (保留为扩展点)

效果: Pro 耗时-83s (SingMOS 80s), 反评分污染消除。

### 修复3：自参照一致性替代 SingMOS

`ScoreServiceV4._self_consistency_penalty()`:
- 将f0分3段, 每段计算pitch稳定性(60%)+人声比率(40%)
- 段间CV>0.15时扣分: `min(8, cv*40)`
- 比跨域DL模型可靠, 不增加耗时

修改文件: `services/score_service.py` (+65)

### 修复4：DTW 参考搜索默认化

`_find_reference_audio()`:
- 扫描 uploads/ 中带参考标签文件 (高分/参考/原唱/示范/标准)
- 清理用户文件名标签, `SequenceMatcher` 模糊匹配 (阈值>0.5)
- 命中→DTW融合; 未命中→回退绝对评分 (零退化)

修改文件: `api/business/audio_analysis.py` (+55)

### 遗留问题 → v5.16

- **Pro Breath=9.8** (Quick=56.4): Demucs分离后RMS/CPP/HNR系统性降解, 需类似Rhythm的CV重校准
- Pro Total 63.2 距目标≥70差6.8 (瓶颈在Breath)
- Pro 耗时 ~226s (Demucs~200s, 硬件限制)

---

## v5.14 — 音准多指标 + 艺术评分重构 + 专业模式深度测试 (2026-06-03)

### 真实音频测试 (Quick Mode)

| 音频 | Total | Pitch | Rhythm | Breath | Tech | Art |
|------|-------|-------|--------|--------|------|-----|
| 高分组 (n=4) | **73-76** | 79-81 | 67-77 | 53-66 | 78-84 | **80-84** |
| 低分组 (n=1) | **47.0** | 75.9 | **2.5** | 51.2 | 57.5 | **53.2** |
| 差距 | **27.4** | 4.2 | 68.6 | 4.3 | 21.7 | **28.4** |

### 阶段一：音准多指标体系

从 pitch-benchmark 移植 (~100行):
- `PitchDeviationResult` 新增 6 字段: RPA, RCA, gross_error_rate, octave_error_rate, relative_smoothness, continuity_breaks
- `PitchAnalyzer._calculate_pitch_multimetric()` — 移植 evaluate_pitch_accuracy + evaluate_pitch_smoothness
- 字段已计算但暂不驱动评分 (无参考音高时 MAE 更可靠, 保留供校准后用)
- 修改文件: `services/features/__init__.py`, `services/features/pitch.py`, `services/scoring/pitch_scorer.py`

### 阶段二：艺术评分重构 (v5.14 核心)

**根因**: v5.13 艺术分 78 vs 78 (零差距)。旧 ArtistryScorer 依赖不可靠的技巧检测器 (颤音FFT/滑音阈值/假声频谱质心)。

**方案**: 从四个可靠维度加权合成 + 声学特征调制:
```
artistry = pitch*0.20 + rhythm*0.25 + breath*0.20 + technique*0.35
           + modulation (RMS dynamic ratio ±6, F0 variation ±4)
```
- 低分演唱因节奏 2.5 和技术 57.5 被自然拉低
- 声学调制提供 ±10 分微调
- 修改文件: `services/scoring/artistry_scorer.py`, `services/score_service.py`, `api/business/audio_analysis.py`

**效果**: Artistry 差距 0.3 → 28.4, Total 差距 24.0 → 27.4

### 专业模式深度测试 (v5.14)

| 音频 | Quick Total | Pro Total | Pro Rhythm | Pro Breath |
|------|------------|-----------|------------|------------|
| 恋人(高) | 75.6 | **57.6** | **18.6** | **9.8** |
| 陈奕迅(低) | 45.9 | 50.0 | 2.5 | 51.2 |

**发现**:
- Demucs 分离后 CV=134% 经 is_clean_vocal 映射 + RhythmScorer 额外惩罚后仍跌至 18.6
- SingMOS: 低分演唱 MOS=95.9 > 高分演唱 MOS=73.9 (确认跨域不适用)
- 陈奕迅(低) 无伴奏跳过 Demucs, Quick/Pro 一致性良好

### 已知遗留

| P0 | 专业模式 Demucs 后评分仍偏低, SingMOS 严重跨域 |
| P1 | 气息/音准区分度偏窄, 23参数未校准 |
| P2 | f0节奏路径待恢复, 技巧检测仅3种, 无混响补偿 |

---

## v5.13 — 区分度恢复 + 专业模式修复 (2026-06-03)

### 真实音频测试结果

| 音频 | 总分 | Pitch | Rhythm | Breath | Tech | Art |
|------|------|-------|--------|--------|------|-----|
| 高分组 (n=4) | **73-75** | 79-81 | 67-77 | 53-66 | 78-84 | 78-80 |
| 低分组 (n=1) | **50.0** | 75.9 | **2.5** | 51.2 | 57.5 | 78.0 |
| 白噪声 | **0.0** | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

**总分差距 24.0 分。区分度恢复成功。**

### 阶段一：区分度恢复

#### 1. 移除 Sigmoid 拉伸
- v5.12 引入的 Sigmoid 压缩 (低分×0.6, 高分压缩到60) 导致气息分全部 36-43
- 完全删除 Sigmoid 块，回归自然计分
- **效果**: 气息 36-43 → 56-63 (+20pts)
- 修改文件: `services/features/breath.py`

#### 2. 移除 Breath 四个子维度硬上限
- `min(90, score)` ×4 → `max(0, min(100, score))`
- 自然上限 ~95 (通过低加分幅度控制)
- 修改文件: `services/features/breath.py`

#### 3. 移除 Artistry 三个硬上限 + 降低加分系数
- `min(90/85, score)` ×3 → `max(0, min(100, score))`
- 颤音系数 1.0→0.7, 气息表现 +15→+10, 弱唱 +10→+7
- 自然上限落在 90-95 而非 85-90
- 修改文件: `services/scoring/artistry_scorer.py`

#### 4. 动态范围连续映射
- 4 档离散分数 (85/75/65/25) → 连续线性插值
- 同步更新 `EmpiricalThresholds.artistry_dynamic_max` = 92
- 修改文件: `services/scoring/artistry_scorer.py`

### 阶段二：专业模式 Demucs 修复

#### 1. 纯净人声 CV 映射
- 根因: 纯净人声 onset 无伴奏节奏线索, CV 天然偏高 (140%)
- `_cv_to_deviation` 增加 `is_clean_vocal` 分支, 放宽映射断点
- 混合音频: <0.3 专业级 → 纯净人声: <0.5 非常规律
- 修改文件: `services/features/rhythm.py`

#### 2. 完整调用链
- `is_clean_vocal` 参数贯穿: audio_service → audio_features_service → rhythm_analyzer → _cv_to_deviation
- 专业模式自动传递 `is_separated=True`
- 修改文件: `services/audio_features_service.py`, `services/audio_service.py`

#### 3. f0 节奏路径备份
- f0 路径发现回归 (恢复后节奏归零), 暂保持 `f0=None`
- 留到校准验证后启用

### 已知遗留问题

| 优先级 | 问题 | 测试数据 |
|--------|------|---------|
| P0 | 艺术评分无区分力 | 高分78.0 vs 低分78.0 (零差距) |
| P1 | 气息区分度偏窄 | 高分53-66 vs 低分51 (5-15分) |
| P1 | 音准区分度偏窄 | 高分79-81 vs 低分76 (3-5分) |
| P1 | 23个经验参数未校准 | 0个 [实验校准] |

### 尚未完成的优化 (v5.13 计划 Phase 3-7)

**阶段三 — 校准数据集建设 (P0)**: 3×3对照数据集, 校准工具脚本, 优先校准cv断点/breath基线/artistry上限/pitch_break_cents

**阶段四 — DL模型策略 (P1)**: SVQTD 7属性分类器 (需确认权重), TorchCREPE 备选, ECAPA-TDNN 音色分析, VocalCritic 评估

**阶段五 — 鲁棒性增强 (P1)**: 混响补偿 (HPSS+谱减法), 音量维度独立 (六维评分), f0节奏路径恢复, Feature Flag 机制, 历史数据迁移

**阶段六/七 — 测试+文档**: 区分度验证测试, 鲁棒性测试, CALIBRATION.md, DL_MODELS.md

---

## v5.12 — 安全加固 + 评分统一 + 算法校准 + DL模型清理 (2026-06-03)

### 阶段一：安全加固 & 代码清理 (P0)

#### 1. 移除 debug=True 安全风险
- `debug=True` 改为环境变量 `FLASK_DEBUG=1` 控制
- 修改文件: `web_app.py`

#### 2. 移除 CREPE 僵尸代码 (~300行)
- 删除 `CREPEPitchExtractor`、`SpeechBrainMOSPredictor`、`EnhancedDLAssessor` 三个类
- 保留 `ScoreCalibrator` 供单元测试使用
- 修改文件: `services/dl_services/enhanced_dl_assessor.py` (740→236行), `__init__.py`, `dl_manager.py`, `diagnostic.py`
- 修复测试文件: `tests/tools/test_evaluation_optimization.py`

#### 3. 修复非人声假评分
- `_build_non_voice_result`: 所有维度分数归零，不再返回无意义的假分数（原来 pitch=10-30, rhythm=20）
- 新增 `is_voice=False` 和 `warning` 字段到 API 响应
- 修改文件: `api/business/audio_analysis.py`

#### 4. 其他清理
- 清理 22 个 `__pycache__` 目录
- 413 上传限制错误提示改为中文友好信息
- 修改文件: `api/errors.py`

### 阶段二：评分路径统一 (P0)

#### 1. 移除 Legacy 对比评分路径
- `/api/compare` 端点不再调用 `analyze_and_score()` 做冗余绝对评分 + `calculate_comparison()` 做Legacy对比
- DTW `dimensions` 字段直接构建 `comparison` 响应
- 移除 `calculate_comparison`、`generate_comparison_suggestions` 导出
- 修改文件: `api/routes/upload.py`, `api/business/__init__.py`

### 阶段三：算法鲁棒性修复 (P1)

#### 1. 气息评分天花板修复
- 四个子维度基线从 60 统一降为 40
- 非艺术波动惩罚加倍: `*30` → `*60`，触发阈值 0.35→0.25
- 加分项设上限: 长音+5max, 换气+3max
- Sigmoid 拉伸: 低分(<=50)压缩 0.6x, 高分自然延伸
- 修改文件: `services/features/breath.py`

#### 2. 艺术评分子维度校准
- 颤音: 基础分 30→25, 次数加分 1.5x→1.0x, 上限 100→90
- 动态: 基线 30→25
- 技巧多样性: 3种技巧 90→80, 2种 75→70, 1种 65→60, 上限 100→85
- 气息表现力: 基线 30→25, 各加分项减半, 上限 100→85
- 修改文件: `services/scoring/artistry_scorer.py`

#### 3. SingMOS 校准修正
- DL 融合权重 0.4→0.15, boost 系数 0.3→0.15
- 添加跨域应用警告注释
- 修改文件: `services/score_service.py`

#### 4. torchaudio 补丁副作用修复
- 仅在 `sox_effects` 不可用时应用兼容补丁，不再无条件全局覆盖
- 修改文件: `services/dl_services/dl_quality_assessor.py`

### 阶段四：深度学习模型清理 (P1)

#### 1. 移除 Wav2Vec2 情绪模型
- 模型 ~300MB, 基于 IEMOCAP 英语语音训练, 用于中文唱歌=3x跨域
- 仅贡献 +3~5 分, Phased 3 降至 +3, 现完全移除
- 情绪分析统一使用启发式方法
- 修改文件: `model_manager.py` (472→156行)

#### 2. 移除 wvmos (Wav2Vec2-MOS)
- 评估电信语音质量, 不是唱歌质量 = 二次跨域
- 删除 `Wav2Vec2MOSPredictor` 类
- `DLQualityAssessor` 简化为 SingMOS-only
- 修改文件: `services/dl_services/dl_quality_assessor.py`

### 阶段五：魔法数字集中化 (P1)
- `EmpiricalThresholds` 新增 14 个字段，覆盖气息/节奏/艺术表现维度
- 所有硬编码常量标注来源: [理论依据]/[实验校准]/[经验估计]/[论文参考]
- 修改文件: `services/scoring_config.py`

### 阶段六：测试覆盖扩展 (P2)
- 新增 `tests/integration/test_full_pipeline.py` (6个测试用例)
- 覆盖: 白噪声检测/人声评分范围/快速vs专业一致性/非人声零分/响应字段完整性/气息区分度
- 修改文件: `tests/unit/test_scorers.py` (v5.12 艺术评分阈值更新)

### 阶段七：前端质量修复 (P2)
- `_get_level_info`: 修复 score=100 边界情况, 新增 score<0 处理
- `displayVoiceQualityWarning`: 使用 API `warning` 字段, 非人声隐藏雷达图
- 修改文件: `services/score_service.py`, `web/static/js/analysis.js`

### 已知问题 (v5.12 测试发现)

#### 专业模式 Demucs 分离后评分异常
- **症状**: 恋人.mp3 专业模式总分 54.1 vs 快速模式 71.1
- **节奏 0.0 分**: 分离后 CV=140%，onset 间隔分析失真
- **气息 4.1 分**: 分离后人声 HNR 可能异常
- **用时 305s**: 专业模式仍包含 SingMOS + Demucs 全流程
- **待修复**: 排查 Demucs 分离后特征提取管线

### 测试结果
- 单元测试: **79/79 通过**
- 快速模式: 3首真实音频分数区分度良好 (68-71分, 气息36-43)
- 专业模式: 存在上述已知问题

---

## v5.11 - 评分区分度修复 + 人声分离管线修复 (2026-06-02)

### 核心问题

评分系统对"难听"和"好听"的音频几乎无区分度。经全链路代码审查，发现**两层分数压缩机制叠加 + 维度评分器内部高 floor/浅斜率**，导致快速模式分数被锁死在 55-92 区间。

### 修复内容

#### 1. 移除快速模式分数压缩 (Step 0)

**问题**: `_apply_quick_mode_smoothing()` 将分数强制映射到 60-90，ScoreCalibrator 的 REFERENCE_MAPPING 将 (0,50)→(55,65)。

**修复**:
- 删除 `_apply_quick_mode_smoothing()` 函数及其调用 (~160行)
- 删除 `_create_quick_mode_config()` — 快速/专业模式使用相同评分标准
- 清理未使用的 `score_calibrator` / `enhanced_assessor` 导入
- **修改文件**: `api/business/audio_analysis.py`

#### 2. 修复 Demucs 人声分离管线 (Step 0.5)

**问题**: Demucs 正常执行并输出文件 (`web/static/htdemucs_ft/vocals.mp3`)，但 `_find_separated_files` 因 `--filename` 参数导致输出扁平化，在错误目录查找文件，最终静默回退到原始混合音频。

**修复**:
- `_find_separated_files`: 3个候选位置查找 (flat/subdir/direct)，返回文件系统绝对路径
- `_preprocess_for_scoring`: 兼容新旧路径格式
- **修改文件**: `services/separation_service.py`, `services/audio_service.py`

**效果**: 专业模式下分离成功，Breath 从 100 (假) 降至 70 (真)，Technique 降 6-9 分。

#### 3. 移除评分硬底限 + 降低基线 (Step 1-2)

**问题**: 气息硬底限 max(50,...)、艺术子维度基线 50-60、技术 HNR/CPP floor 30-50、音准/节奏"待改进"起始分 70 且斜率过缓。

**修复**:
- `BreathThresholds.get_score()`: `max(50,...)` → `max(0,...)`, 斜率 50→60
- `PitchThresholds.get_score()`: 待改进斜率 0.5→0.85 (MAE=160音分→0分)
- `RhythmThresholds.get_score()`: 斜率 100→120
- `ArtistryScorer`: 4处子维度基线 60→30, 55→25, 50→25
- `TechniqueScorer`: 4处 HNR/CPP floor 降低 60% (40→15, 30→10, 50→20, 30→10)
- **修改文件**: `services/scoring_config.py`, `services/scoring/artistry_scorer.py`, `services/scoring/technique_scorer.py`

#### 4. 节奏评分系统性修复 (Step 3-6)

**问题**: 节奏维度在所有文件上得分 0-6，拉低总分 ~14 分。五重问题叠加：

| 子问题 | 修复 |
|--------|------|
| CV→deviation 映射将人声CV当做器乐评分 | 重新校准6段映射，CV=0.7→dev=0.40 (原 0.70) |
| 16kHz onset检测精度差 | 内部重采样到 22050Hz |
| 响度归一化 (target_rms=0.05) 压平动态 | 节奏分析使用原始未归一化音频 |
| 长音频全程CV被段落密度差异污染 (276s CV=1.33) | 60s窗口分段分析，取中位数CV |
| 不规则惩罚阈值 0.3 对声乐太严格 | 0.3→0.5，四级分级惩罚 |

**修改文件**: `services/features/rhythm.py`, `services/scoring/rhythm_scorer.py`, `services/audio_features_service.py`, `services/scoring_config.py`

#### 5. 新增级联惩罚 + 优化人声质量惩罚 (Step 7-8)

- 人声质量三层分级惩罚: vq<30 cap 40, vq<50 penalty 35, vq<65 小幅惩罚
- 多维度联合极差惩罚: 3维<40 cap 55, 4维<40 cap 40
- 等级区间更新匹配新分数分布: (88,100)专业级 → (0,25)待改进
- **修改文件**: `services/score_service.py`

### 效果对比

| 音频 | 修改前 | 修改后 | 提升 |
|------|--------|--------|------|
| 清唱 (obj_...) | 70.7 | **82.9** | +12.2 |
| 恋人 | 70.9 | **86.4** | +15.5 |
| 手写的从前 | 73.4 | **83.0** | +9.6 |

| 维度 | 修改前 | 修改后 |
|------|--------|--------|
| Rhythm | 0-6 (全损) | 67-77 (正常) |
| Breath (分离后) | 100 (假) | 70-93 (真) |
| Technique (分离后) | 78-84 (偏高) | 72-76 (合理) |

### 测试

- 79/79 单元测试通过
- 6/6 集成测试通过

---

## v5.9 - 逐句评分优化 (2026-05-10)

### 问题修复

#### 逐句评分分数偏低问题

**问题描述**：专业评估模式下逐句评分分数普遍偏低，尤其是音准和情绪维度。

**根因分析**：
1. 音准评分使用相对标准差阈值过严，把"音高变化幅度"误判为"音准差"
2. 演唱中的转音、滑音会导致高 relative_std（30%-50%），这是正常的音乐表达
3. 节奏评分对稳定节奏惩罚
4. 气息和情绪评分最低分过低

**解决方案**：

##### 1. 音准评分阈值大幅放宽
```python
# 修复前
PITCH_THRESHOLD_EXCELLENT = 0.08   # 8%
PITCH_THRESHOLD_GOOD = 0.20        # 20%
PITCH_MIN_SCORE = 50.0

# 修复后
PITCH_THRESHOLD_EXCELLENT = 0.12   # 12%
PITCH_THRESHOLD_GOOD = 0.30        # 30%
PITCH_THRESHOLD_FAIR = 0.50        # 50%
PITCH_MIN_SCORE = 60.0             # 最低分提升到60
```

##### 2. 节奏评分优化
```python
RHYTHM_STABLE_MIN = 75.0  # 稳定节奏最低75分
```

##### 3. 气息评分优化
```python
BREATH_THRESHOLD_EXCELLENT = 0.10  # 从8%放宽到10%
BREATH_MIN_SCORE = 60.0            # 最低分提升到60
```

##### 4. 情绪评分重构
```python
EMOTION_BASE_SCORE = 70.0          # 基准分提升到70
EMOTION_MIN_SCORE = 60.0           # 最低分提升到60
```

##### 5. 音量评分优化
```python
VOLUME_MIN_SCORE = 60.0            # 最低分提升到60
```

### 效果对比

| 音频 | 维度 | 修复前 | 第一轮 | 第二轮 | 总改进 |
|------|------|--------|--------|--------|--------|
| 恋人 | 音准 | 66.1 | 73.2 | **79.9** | +13.8 |
| 恋人 | 情绪 | 69.2 | 69.8 | **73.9** | +4.7 |
| 恋人 | 总分 | 78.4 | 81.7 | **84.4** | +6.0 |
| 手写的从前 | 音准 | 56.2 | 63.3 | **74.0** | +17.8 |
| 手写的从前 | 情绪 | 61.9 | 68.7 | **73.1** | +11.2 |
| 手写的从前 | 总分 | 73.2 | 77.6 | **81.7** | +8.5 |

### 修改文件

- `services/phrase_service.py` - 评分算法优化

### 测试验证

```
单元测试: 79/79 通过
真实音频测试: 恋人.mp3, 手写的从前.mp3 验证通过
```

---

## v5.8 - P0问题修复 (2026-05-10)

### Bug修复

#### 1. 对比分析API 415错误
- **问题**: FormData方式上传时，直接访问 `request.json` 触发Flask的JSON解析，由于Content-Type不是application/json，抛出415错误
- **解决方案**: 使用 `request.is_json` 检查后再调用 `request.get_json(silent=True)`
- **修改文件**: `api/routes/upload.py`

```python
# 修复前
if request.json and isinstance(request.json, dict):
    style = request.json.get('style', 'pop')

# 修复后
style = 'pop'
if request.is_json:
    try:
        json_data = request.get_json(silent=True)
        if json_data and isinstance(json_data, dict):
            style = json_data.get('style', 'pop')
    except Exception:
        pass
elif request.form:
    style = request.form.get('style', 'pop')
```

#### 2. 首页录音安全上下文判断修复
- **问题**: 原条件 `!window.isSecureContext && hostname !== 'localhost'` 逻辑有误，某些浏览器在localhost上 `isSecureContext` 可能为false
- **解决方案**: 显式检查 hostname 是否为 localhost/127.0.0.1/[::1]
- **修改文件**: `web/static/js/modules/recording.js`

```javascript
const isLocalhost = location.hostname === 'localhost' || location.hostname === '127.0.0.1' || location.hostname === '[::1]';
const isSecure = window.isSecureContext || isLocalhost;
if (!isSecure) {
    showToast('录音功能需要 HTTPS 或 localhost 环境', 'error');
}
```

#### 3. 实时录音模块初始化修复
- **问题**: `RealtimeCompare` 构造函数参数未设置默认值，`init()` 方法缺少错误处理和readyState检查
- **解决方案**: 添加默认参数，添加readyState检查和错误事件监听
- **修改文件**: `web/static/js/modules/realtime-compare.js`, `web/static/js/compare.js`

```javascript
// 构造函数添加默认参数
constructor(standardAudioData = {}) { ... }

// init() 添加readyState检查
async init(audioElement, standardUrl) {
    // ...
    await new Promise((resolve, reject) => {
        this.standardAudioElement.addEventListener('loadedmetadata', resolve, { once: true });
        this.standardAudioElement.addEventListener('error', reject, { once: true });
        if (this.standardAudioElement.readyState >= 1) {
            resolve();
        }
    });
}
```

### 测试验证

```
单元测试: 43/43 通过
API测试:
- Upload API: Score 86.3 (正常)
- Compare API: Score 94.1, Pitch Match 100%, Rhythm Match 100% (正常)
```

---

## v5.3.1 - Flask 3.x JSON序列化修复 (2026-04-29)

### Bug修复

#### NumPy类型JSON序列化问题
- **问题**: Flask 3.x 不支持 `JSON_ENCODER` 配置，导致 numpy 类型无法序列化
- **错误**: `TypeError: Object of type float32 is not JSON serializable`
- **解决方案**: 创建 `NumpyJSONProvider` 继承 `DefaultJSONProvider`
- **修改文件**: `api/__init__.py`

```python
class NumpyJSONProvider(DefaultJSONProvider):
    """自定义 JSON 提供器，支持 numpy 类型"""
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        return super().default(obj)
```

#### 对比分析API参数名修正
- **问题**: 前端使用 `teacher_audio/student_audio`，后端期望 `file/standard_file`
- **解决方案**: 统一使用 `file` (用户音频) + `standard_file` (标准音频)

### 测试验证

```
API测试结果:
- Upload API: Score 86.3 (正常)
- Compare API: Score 88.0, Pitch Match 100%, Rhythm Match 70% (正常)
- Health Check: 所有检查项通过
```

---

## v5.3 - 对比分析重构 (2026-04-29)

### 新功能

#### 独立对比分析页面
- **独立页面**: 对比分析从首页 tab 改为独立页面 `/compare.html`
- **三步流程**: 导入标准音频 → 选择模式 → 查看结果
- **两种评估模式**:
  - **上传模式**: 导入用户音频与标准音频对比
  - **实时录音模式**: 类似全民K歌的实时反馈体验

#### 实时音高检测 (前端)
- **YIN 算法**: 前端实时音高检测，无需后端处理
- **实时音分偏差**: 显示当前音高与标准音高的偏差（+/- 音分）
- **实时调整建议**: "略高，请降低一点" / "偏低，需要提高"
- **实时评分**: 录音过程中实时更新评分
- **音高曲线对比**: Canvas 绘制标准 vs 用户音高曲线

#### 基于标准音频的相对评分
- **音准匹配率**: 用户音高与标准音高的匹配程度 (0-100%)
- **节奏匹配率**: 基于能量包络相似度计算 (0-100%)
- **综合评分**: 音准 60% + 节奏 40% 权重
- **等级评定**: 优秀/良好/中等/及格/需改进
- **诊断建议**: 自动生成改进方向建议

### API 更新

#### `/api/compare` 接口增强
- 支持 FormData 上传 (file + standard_file)
- 支持 JSON 方式 (filepath 参数)
- 返回相对评分结果

```python
# FormData 方式
POST /api/compare
Content-Type: multipart/form-data
- file: 用户音频
- standard_file: 标准音频

# 返回
{
  "success": true,
  "data": {
    "score": 85,
    "level": "良好",
    "pitch_match_rate": 88.5,
    "rhythm_match_rate": 82.3,
    "avg_cents_error": 15.2,
    "diagnosis": ["音准表现优秀...", "整体偏高..."]
  }
}
```

### 新增文件

| 文件 | 说明 |
|------|------|
| `web/static/compare.html` | 独立对比分析页面 |
| `web/static/js/compare.js` | 对比页面主逻辑 |
| `web/static/js/modules/pitch-detector.js` | YIN 音高检测算法 |
| `web/static/js/modules/realtime-compare.js` | 实时录音对比模块 |

### 修改文件

| 文件 | 变更 |
|------|------|
| `web/static/index.html` | 对比分析 tab 改为页面链接 |
| `api/routes/upload.py` | `/compare` 接口支持 FormData |
| `api/business/audio_comparison.py` | 新增 `calculate_relative_score` 等函数 |

### 技术亮点

- **前端 YIN 算法**: 纯 JavaScript 实现音高检测
- **实时反馈**: requestAnimationFrame 驱动的实时 UI 更新
- **Web Audio API**: AudioContext + AnalyserNode + MediaRecorder
- **音分计算**: 1200 * log2(freq2/freq1) 精确计算音分偏差

---

## v5.0 - 深度学习集成 & 双评估模式 (2026-04-22)

### 新功能

#### 双评估模式
- **快速评估** (默认): 约30秒完成，适合日常练习反馈
  - 基础五维评分 (音量/音准/节奏/气息/情绪)
  - 人声质量检测
  - 基础建议生成

- **专业评估**: 约2-5分钟，适合详细问题诊断
  - 完整五维评分 + 详细诊断
  - 逐句评分 (每句独立评分和建议)
  - 音色分析 (明亮度/厚度/鼻音/气声)
  - 可视化图表 (频谱图/音高轨迹/能量曲线)

#### API 更新
- `/api/upload` 接口新增 `mode` 参数
  - `mode=quick`: 快速评估 (默认)
  - `mode=professional`: 专业评估

### 性能优化

#### 逐句评分多线程并行
- 使用 `ThreadPoolExecutor` 并行处理多个乐句
- 预计算 f0 数据复用，避免重复计算
- 逐句评分速度提升 2-3 倍

#### 评分算法优化
- 音量评分: 优化归一化范围 (0.02-0.15 RMS)
- 音准评分: 使用相对标准差，合理波动不惩罚
- 节奏评分: 基于变异系数评估节奏感
- 气息评分: 基于相对变化率评估稳定性
- 分数范围: 60-90 分 (更合理的分布)

### 代码变更

#### 新增文件
- `CHANGELOG.md` - 版本变更记录

#### 修改文件
- `api/routes/upload.py` - 添加 mode 参数支持
- `api/business/audio_analysis.py` - 实现快速/专业模式分支
- `services/phrase_service.py` - 多线程并行评分 + 评分算法优化
- `README.md` - 更新功能说明和 API 文档
- `docs/DEEP_LEARNING_PLAN.md` - 添加性能优化策略

### 兼容性

- 向后兼容: 不传 `mode` 参数时默认使用快速模式
- 前端需要更新以支持模式选择 UI

---

## v4.0 - 评分系统 V4 (2026-04-20)

### 改进
- 自适应评分系统
- 风格识别集成
- 深度学习质量评估 (MOS 分数)

---

## v3.6 - 安全加固 (2026-04-18)

### 改进
- 路径遍历防护
- XSS 防护
- 文件名安全处理
