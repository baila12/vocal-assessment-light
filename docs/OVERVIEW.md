# 项目概览

## 项目位置
`C:\Users\jack\Desktop\临时文件\声乐\vocal_assessment_light\`

## 当前版本: v5.8 (2026-05-08)

## 核心定位
**纯离线、无服务器、无需登录的本地 Web 应用** - 基于 Flask 本地服务，所有分析在本地完成，无需联网，保护用户隐私。

## 算法评估: 6/10

> 2026-05-26 完成核心算法审计。详见 [SCORING.md](SCORING.md#算法评估-v59-审计)

**优点**: 模块化架构、风格感知评分、气息四子维度专业评估、可配置化

**核心缺陷**:
1. 未先做人声分离就分析混合音频 → HNR/CPP/RMS 失真
2. DTW 对比引擎未接入评分主流程 → 缺少参考基准
3. librosa beat_track 对非标准节奏失效
4. Wav2Vec2 情绪模型域不匹配 (语音→唱歌)

## 版本历史概览

| 版本 | 日期 | 主要变更 |
|------|------|---------|
| v5.9 | 2026-05-26 | **算法审计** — 完成评分系统全面评估，发现2P0+4P1+4P2待处理 |
| v5.9 | 2026-05-10 | 逐句评分优化（音准+13.8，情绪+11.2） |
| v5.8 | 2026-05-08 | **对比分析三级DTW算法重构** - 相同音频得分从88分提升至≥95分 |
| v5.7 | 2026-05-01 | 对比分析页面重构、E2E测试完善 |
| v5.6.1 | 2026-04-28 | API响应修复、采样率同步 |
| v5.6 | 2026-04-28 | 混合音频检测、气息诊断优化 |
| v5.4 | 2026-04-27 | 评分系统优化、模型诊断 |
| v5.3.1 | 2026-04-29 | Flask 3.x JSON序列化修复 |
| v5.3 | 2026-04-23 | 对比分析重构、实时录音模式 |
| v5.2.1 | 2026-04-23 | 快速模式性能优化 (~33秒) |
| v5.2 | 2026-04-22 | 模块化重构完成 |
| v5.0 | 2026-04-22 | 深度学习集成、双评估模式 |

详细变更记录见 [CHANGELOG.md](CHANGELOG.md)

## 运行环境

```bash
conda activate pytorch2
cd "C:\Users\jack\Desktop\临时文件\声乐\vocal_assessment_light"
python web_app.py
# 访问 http://localhost:5000
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Flask 3.0, librosa, scipy, numpy, matplotlib |
| 深度学习 | transformers, torchcrepe, speechbrain, demucs |
| 前端 | ES6 Modules, Chart.js, Web Audio API, Canvas |
| 测试 | pytest, Playwright |
