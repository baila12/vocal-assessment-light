# 声乐评估系统 - 项目状态

## 当前版本: v5.12 (2026-06-03)

**纯离线、无服务器、无需登录的本地 Web 应用**

## 运行

```bash
conda activate pytorch2
python web_app.py
# http://localhost:5000
```

## 文档导航

| 文档 | 说明 |
|------|------|
| [OVERVIEW.md](OVERVIEW.md) | 项目概览、版本历史 |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 系统架构 |
| [API.md](API.md) | API接口 |
| [SCORING.md](SCORING.md) | **评分算法详解 + 算法审计报告** |
| [ISSUES.md](ISSUES.md) | 问题追踪 (含审计发现) |
| [ROADMAP.md](ROADMAP.md) | 开发计划 (四阶段) |
| [OPTIMIZATION_MODEL.md](OPTIMIZATION_MODEL.md) | 模型量化方案 |
| [OPTIMIZATION_COMPARE.md](OPTIMIZATION_COMPARE.md) | 对比分析优化 |
| [CHANGELOG.md](CHANGELOG.md) | 详细变更记录 |

## 快速参考

### 技术栈
Flask 3.0 | librosa | transformers | Chart.js | pytest

### 已完成
- ✅ 五维评分系统
- ✅ 双评估模式 (快速~35秒 / 专业~180秒)
- ✅ 深度学习集成 (SingMOS, Demucs)
- ✅ 对比分析 (三级DTW对齐引擎)
- ✅ 人声分离 (Demucs, v5.11 修复管线bug)
- ✅ 录音功能
- ✅ 核心算法审计 (v5.9, 评分 6/10)
- ✅ 评分区分度修复 (v5.11)
- ✅ **安全加固: debug=True 移除 (v5.12)**
- ✅ **CREPE/Wav2Vec2/wvmos 僵尸代码清理 (v5.12, -500行)**
- ✅ **评分路径统一: Legacy对比移除 (v5.12)**
- ✅ **气息评分天花板修复 + 艺术评分校准 (v5.12)**
- ✅ **DL融合权重降低 (v5.12, 0.4→0.15)**
- ✅ **魔法数字集中化 (v5.12, +14字段)**

### v5.12 已知问题

| 优先级 | 问题 | 说明 |
|--------|------|------|
| P0 | 专业模式 Demucs 分离后评分异常 | 节奏0.0分(CV=140%), 气息4.1分, 总分比快速模式低17分 |
| P1 | 专业模式耗时过长 | 305秒, SingMOS + Demucs 为主要瓶颈 |
| P1 | 节奏 CV 映射对纯净人声不适用 | _cv_to_deviation 在纯净人声上过于敏感 |
| P2 | Level/Stars 显示 "?" | v5.12 已修复 (边界情况)

### v5.11 评分区分度修复 (2026-06-02)

**问题**: 评分系统对好坏音频无区分度，所有分数被锁在 55-92 区间。

**修复** (详见 [CHANGELOG.md](CHANGELOG.md)):
1. 删除快速模式分数强制压缩 (ScoreCalibrator + smooth_score, ~160行)
2. 修复 Demucs 人声分离管线 (_find_separated_files 路径bug)
3. 移除5维度硬底限 + 降低基线分 + 提高斜率
4. 节奏评分系统性修复 (CV重映射 + 22kHz重采样 + 原始音频 + 分段中位数)
5. 新增级联惩罚 + 优化人声质量惩罚

**效果**:
| 音频 | 修改前 | 修改后 |
|------|--------|--------|
| 恋人 | 70.9 | **86.4** |
| 手写的从前 | 73.4 | **83.0** |
| 白噪声 | 60+ | **0.0** |

### 待修复 (v5.11 审计发现)

| 优先级 | 问题 | 说明 |
|--------|------|------|
| P0 | DTW 参考评分未默认化 | 对比引擎仅在 `/api/compare` 使用 |
| P1 | 气息评分 professional_breath_score=100 | 算法过于宽松 |
| P1 | 艺术评分 A=93-96 偏高 | 加分项未调整 |
| P1 | 响度归一化 target_rms=0.05 过激 | 节奏已豁免，气息/声学仍受影响 |
| P2 | Level/Stars 显示 "?" | API 响应构建问题 |

详见 [ISSUES.md](ISSUES.md)

### 算法审计 (v5.9 - 2026-05-26)

详见 [SCORING.md](SCORING.md#算法评估-v59-审计)

**已修复 (v5.11)**:
- ✅ 未先做人声分离就分析混合音频 → Demucs 管线已修复
- ✅ 节奏分析工具选择错误 → onset-CV 分段分析替代 beat_track

**仍待修复**:
- 🔴 DTW 参考评分未默认化
- 🟡 Wav2Vec2 情绪模型域不匹配
- 🟡 魔法数字泛滥且无校准
- 🟡 无响度归一化 (v5.10 已添加但 target_rms 需调优)
