# 声乐评估系统 - 项目状态

## 当前版本: v5.9 (2026-05-26)

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

## 快速参考

### 技术栈
Flask 3.0 | librosa | transformers | Chart.js | pytest

### 已完成
- ✅ 五维评分系统
- ✅ 双评估模式 (快速~33秒 / 专业~180秒)
- ✅ 深度学习集成 (Wav2Vec2, CREPE, SingMOS, Demucs)
- ✅ 对比分析 (三级DTW对齐引擎)
- ✅ 人声分离 (Demucs)
- ✅ 录音功能
- ✅ 核心算法审计 (v5.9, 评分 6/10)

### 算法审计 (v5.9 - 2026-05-26)

详见 [SCORING.md](SCORING.md#算法评估-v59-审计)

**严重缺陷 (P0)**:
- 🔴 未先做人声分离就分析混合音频
- 🔴 DTW 对比引擎未接入评分主流程

**待改进 (P1)**:
- 🟡 librosa beat_track 对非标准节奏失效
- 🟡 Wav2Vec2 情绪模型域不匹配
- 🟡 魔法数字泛滥且无校准
- 🟡 无响度归一化

### 最新修复 (v5.8)
- ✅ 对比分析API 415错误
- ✅ 首页录音安全上下文判断
- ✅ 实时录音模块初始化

### 相关文档
- [CHANGELOG.md](CHANGELOG.md) - 详细变更记录
- [README.md](../README.md) - 用户指南
