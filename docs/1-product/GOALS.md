# 产品目标与设计原则

> 更新: 2026-06-05 | 本文档定义产品愿景、设计原则和功能全景。功能详情见 [PRD.md](PRD.md)，评分算法见 [SCORING.md](../2-technical/SCORING.md)。

---

## 一、产品定位

**离线声乐评估系统 (VAS)** — 纯本地化、无服务器、无需登录的专业声乐评估 Web 应用。

### 核心价值

| 维度 | 说明 |
|------|------|
| **隐私保护** | 全离线运行，所有数据本地存储，不上传云端 |
| **专业评估** | 五维评分 + Demucs 人声分离 + DTW 参考对比 |
| **即开即用** | 一键启动 Flask 服务，浏览器自动打开 |
| **三模式评估** | Quick (~15-20s) / Pro (~130-170s) / Compare (DTW) |

### 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | Flask 3.0 + librosa + scipy + numpy + matplotlib |
| 深度学习 | PyTorch + Demucs (htdemucs_ft) |
| 前端 | HTML5 + ES6 Modules + Chart.js + Web Audio API + Canvas |
| 存储 | IndexedDB (前端) + JSON 文件 (后端) |
| 测试 | pytest + Playwright + pytest-bdd |

---

## 二、功能模块全景

```
离线声乐评估系统
├── 模块1: 全局基础
│   ├── Flask 服务一键启动
│   ├── 目录自动初始化 (uploads/cache/history)
│   ├── 端口自动检测 (5000-5005)
│   └── 异常统一处理
├── 模块2: 音频采集
│   ├── 麦克风实时录音 (⚠️ 有bug)
│   ├── 本地音频导入 (拖拽 + 文件选择)
│   ├── 多格式支持 (WAV/MP3/FLAC/OGG/M4A/AAC)
│   └── 音频播放控制 (倍速/循环/进度)
├── 模块3: 评分分析 ★核心
│   ├── 五维评分 (音准/节奏/气息/技术/艺术)
│   ├── 三评估模式 (Quick/Pro/Compare)
│   ├── 人声分离 (Demucs htdemucs_ft)
│   ├── 逐句评分 (Pro 模式)
│   ├── 风格自适应 (流行/美声/民族/说唱)
│   ├── DTW 对比分析 (三级对齐引擎)
│   ├── 自参照一致性 (替代 DL 模型)
│   ├── Feature Flag 机制 (⏳ v5.18)
│   ├── 算法校准: 多尺度HNR + Praat CPP (⏳ v5.18-v6.0)
│   └── ★ 标准歌曲数据库 + 自动匹配 (⏳ v6.0, 增强层)
├── 模块4: 可视化
│   ├── 频谱图 + 基音轨迹 + 能量曲线
│   ├── 五维雷达图 (Chart.js)
│   ├── ★ 实时音准对比 (Canvas, 类似全民K歌) — v6.0
│   │   ├── 双曲线叠加: 标准虚线 + 用户实线 (绿/橙/红着色)
│   │   ├── 偏差色带 + 热力图 + 统计面板
│   │   ├── 录音中实时反馈: 圆点 + 偏差数字 + 趋势箭头
│   │   └── 性能自适应: ≥30fps, 低性能自动降级
│   └── 音高曲线对比 (DTW 叠加)
├── 模块5: 历史与成长
│   ├── 历史记录存储 (IndexedDB + JSON)
│   ├── 分页查询 + 筛选 + 删除
│   ├── 成长曲线 (评分趋势)
│   └── 报告导出 (PDF/图片)
└── 模块6: 系统设置 (待实现)
    ├── 评分参数自定义
    ├── 界面主题切换
    └── 数据备份恢复
```

---

## 三、功能清单

### ✅ 已实现

| 功能 | 版本 | 位置 |
|------|------|------|
| 多格式音频上传 + 拖拽 | v3.0 | `web/static/js/modules/` |
| 五维评分 (音准/节奏/气息/技术/艺术) | v4.0 | `services/scoring/` |
| Quick 模式 (~15-20s) | v5.2 | `services/audio_service.py` |
| Professional 模式 (Demucs分离) | v5.11 | `services/separation_service.py` |
| Compare 模式 (DTW三级对齐) | v5.8 | `services/comparison/` |
| 非人声检测 + 归零 | v5.11 | `services/voice_quality_service.py` |
| 混合音频检测 + 自动分离 | v5.17 | `services/features/acoustic.py` |
| 风格自适应评分 | v5.1 | `services/style_aware_scorer.py` |
| DTW 自动参考搜索 | v5.15 | `api/business/audio_analysis.py` |
| 自参照一致性 (替代 SingMOS) | v5.15 | `services/score_service.py` |
| Pro Rhythm CV 重校准 | v5.15 | `services/features/rhythm.py` |
| Pro Breath is_clean_vocal 校准 | v5.16 | `services/features/breath.py` |
| 可视化图表 (频谱/基频/能量/雷达) | v3.0 | `services/visualization_service.py` |
| 历史记录 (分页/筛选/删除) | v3.0 | `repositories/history_repository.py` |
| 报告导出 (PDF/图片) | v5.0 | `services/report_service.py` |
| GPU 加速 (Demucs CUDA/MPS) | v5.17 | `services/separation_service.py` |

### ⏳ 计划中 (双轨并行)

**轨道B — 开源算法移植 + 核心评分优化** (所有评分场景的基础设施):

| 功能 | 来源 | 目标版本 | Feature Flag |
|------|------|---------|-------------|
| Feature Flag 机制 | — | v5.18 | — |
| **多尺度 HNR** (短/中/长窗 + HNR稳定性) | [VoiceLab](https://github.com/VoiceLab) / de Krom 1993 | v5.18 | `enable_multiscale_hnr` |
| **Praat CPP** (parselmouth 替换手动FFT倒谱) | [Praat](https://github.com/praat/praat) / [parselmouth](https://github.com/YannickJadoul/Parselmouth) | v5.18 | `enable_praat_cpp` |
| Voicing detection 评估 (recall/FA) | [pitch-benchmark](https://github.com/) | v5.18 | `enable_voicing_detection` |
| TorchCREPE 备选 (PYIN 降级时启用) | [CREPE](https://github.com/marl/crepe) (~5MB) | v5.18 | `enable_torchcrepe_fallback` |
| 校准数据集 (3×3) + 校准工具脚本 | — | v6.0 | — |
| **SVQTD 7属性歌唱分类器** | 论文 [2210.17367v2](https://arxiv.org/abs/2210.17367) | v6.1 | `enable_svqtd` |
| **ECAPA-TDNN 音色分析** (明亮度/厚度) | [SpeechBrain](https://github.com/speechbrain/speechbrain) | v6.1 | `enable_ecapa_timbre` |
| 六维评分 (音量独立) | — | v6.1 | — |
| 混响补偿 (HPSS谐波分离+谱减法) | — | v6.1 | — |

> **移植优先级**: 多尺度HNR > Praat CPP > Voicing detection > TorchCREPE。前两个直接提升 Breath/Technique 区分度；后两个是备选增强。所有移植通过 Feature Flag 默认关闭，逐个验证后开启。

**轨道A — 标准曲库增强层** (匹配成功时提供 DTW 对比，失败时回退到轨道B):

| 功能 | 目标版本 |
|------|---------|
| ★ 标准歌曲数据库 (SQLite) | v6.0 |
| ★ 上传自动匹配标准歌曲 | v6.0 |
| ★ 选歌 → 录音 → DTW 对比 | v6.0 |
| ★ 曲库管理 (添加/搜索/筛选/删除) | v6.0 |

---

## 四、设计原则

### 4.1 架构原则

| 原则 | 说明 |
|------|------|
| **离线优先** | 零外网依赖，所有计算本地完成 |
| **分层架构** | API → Service → Repository → Config，单向依赖 |
| **单一职责** | 评分器/特征提取器/服务 各自独立 |
| **可配置化** | 所有阈值集中在 `scoring_config.py`，Feature Flag 控制实验功能 |

### 4.2 用户体验原则

| 原则 | 说明 |
|------|------|
| **低门槛开始** | 一键上传即可获得评分，无需配置 |
| **渐进式深度** | Quick 模式满足快速反馈 → Pro 模式提供深度诊断 |
| **可操作反馈** | 不只给分数，还给出具体改进建议 |
| **隐私可见** | 明确告知用户所有数据在本地，不离开电脑 |

### 4.3 算法原则

| 原则 | 说明 |
|------|------|
| **可解释评分** | 每个维度分数有理有据，不黑盒 |
| **保守使用 DL** | 深度学习仅用于语音分离 (Demucs)，评分用经典信号处理 |
| **校准驱动** | 阈值通过校准数据集确定，不做经验硬编码 |
| **区分度优先** | 分数必须能区分水平差异，不搞人人 80 分的虚假安慰 |

---

## 五、参考文档

| 文档 | 路径 |
|------|------|
| 产品需求文档 | [PRD.md](PRD.md) |
| 系统架构 | [ARCHITECTURE.md](../2-technical/ARCHITECTURE.md) |
| 评分算法 | [SCORING.md](../2-technical/SCORING.md) |
| TDD 规范 | [TDD.md](../3-quality/TDD.md) |
| BDD 规范 | [BDD.md](../3-quality/BDD.md) |
| 项目状态 | [PROJECT_STATUS.md](../4-process/PROJECT_STATUS.md) |
