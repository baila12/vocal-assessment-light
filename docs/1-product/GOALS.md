# 产品目标与设计原则

> 更新: 2026-07-20 | v6.2.1 → vNext | 本文档定义产品愿景、设计原则和功能全景。功能详情见 [PRD.md](PRD.md)，评分算法见 [SCORING.md](../2-technical/SCORING.md)。

---

## 一、产品定位

**离线声乐评估系统 (VAS)** — 纯本地化、无服务器、无需登录的专业声乐评估 Web 应用。

### 核心价值

| 维度 | 说明 |
|------|------|
| **隐私保护** | 全离线运行，所有数据本地存储，不上传云端 |
| **专业评估** | 六维评分 (音准/节奏/气息/发声技术/肌肉力量/艺术) + 音色加减分(clamp[0,100]) + Demucs 人声分离 + DTW 参考对比 |
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
├── 模块1: 全局基础 [启动<10s, 内存空闲<200MB]
│   ├── Flask 服务一键启动
│   ├── 目录自动初始化 (uploads/cache/history)
│   ├── 端口自动检测 (5000-5005)
│   └── 异常统一处理
├── 模块2: 音频采集 [上传<3s(50MB), 录音延迟<50ms]
│   ├── 麦克风实时录音 (⚠️ 有bug)
│   ├── 本地音频导入 (拖拽 + 文件选择)
│   ├── 多格式支持 (WAV/MP3/FLAC/OGG/M4A/AAC)
│   └── 音频播放控制 (倍速/循环/进度)
├── 模块3: 评分分析 ★核心 [Quick<30s, Pro<180s/60s(GPU)]
│   ├── 六维评分 (音准/节奏/气息/发声技术/肌肉力量/艺术 + 音色加减分)  [评分计算<3s]
│   ├── 三评估模式 (Quick/Pro/Compare)
│   ├── 人声分离 (Demucs htdemucs_ft)  [CPU<140s, GPU<30s]
│   ├── 逐句评分 (Pro 模式)  [<5s]
│   ├── 风格自适应 (流行/美声/民族/说唱)  [配置加载<50ms]
│   ├── DTW 对比分析 (三级对齐引擎)  [<40s]
│   ├── 自参照一致性 (替代 DL 模型)  [<1s]
│   ├── Feature Flag 机制 (✅ v5.18, 激活 v6.2.1)  [判断开销<1ms]
│   ├── 算法校准: 多尺度HNR + Praat CPP (✅ v5.18, 激活 v6.2.1)  [增量<5s]
│   └── ★ 标准歌曲数据库 + 自动匹配 (⏳ v6.3, 增强层)  [匹配<5s]
├── 模块4: 可视化 [图表生成<10s, Canvas≥30fps]
│   ├── 频谱图 + 基音轨迹 + 能量曲线
│   ├── 五维雷达图 (Chart.js)
│   ├── ★ 实时音准对比 (Canvas, 类似全民K歌) — v6.0
│   │   ├── 双曲线叠加: 标准虚线 + 用户实线 (绿/橙/红着色)
│   │   ├── 偏差色带 + 热力图 + 统计面板
│   │   ├── 录音中实时反馈: 圆点 + 偏差数字 + 趋势箭头
│   │   └── 性能自适应: ≥30fps, 低性能自动降级
│   └── 音高曲线对比 (DTW 叠加)
├── 模块5: 历史与成长 [查询<100ms, 导出<5s]
│   ├── 历史记录存储 (IndexedDB + JSON)
│   ├── 分页查询 + 筛选 + 删除
│   ├── 成长曲线 (评分趋势)
│   └── 报告导出 (PDF/图片)
└── 模块6: 系统设置 (待实现) [页面加载<300ms]
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
| ★ 六维评分重构 (音准/节奏降权 + 咬字+气声比 + 肌肉力量 + 音色加减分) | 📋 vNext | 设计阶段 |
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
| Feature Flag 机制 | — | ✅ v5.18 (激活 v6.2.1) | — |
| **多尺度 HNR** (短/中/长窗 + HNR稳定性) | [VoiceLab](https://github.com/VoiceLab) / de Krom 1993 | ✅ v5.18 (激活 v6.2.1) | `enable_multiscale_hnr` |
| **Praat CPP** (parselmouth 替换手动FFT倒谱) | [Praat](https://github.com/praat/praat) / [parselmouth](https://github.com/YannickJadoul/Parselmouth) | ✅ v5.18 (激活 v6.2.1) | `enable_praat_cpp` |
| Voicing detection 评估 (recall/FA) | [pitch-benchmark](https://github.com/) | ✅ v5.18 (激活 v6.2.1) | `enable_voicing_detection` |
| TorchCREPE 备选 (PYIN 降级时启用) | [CREPE](https://github.com/marl/crepe) (~5MB) | ✅ v5.18 (激活 v6.2.1) | `enable_torchcrepe_fallback` |
| 校准数据集 (3×3) + 校准工具脚本 | — | v6.0 | — |
| **SVQTD 7属性歌唱分类器** | 论文 [2210.17367v2](https://arxiv.org/abs/2210.17367) | ⏳ v6.3+ | `enable_svqtd` (deferred) |
| **ECAPA-TDNN 音色分析** (明亮度/厚度) | [SpeechBrain](https://github.com/speechbrain/speechbrain) | ⏳ v6.3+ | `enable_ecapa_timbre` (deferred) |
| 音量维度独立 | — | ✅ v5.19 | — |
| ~~混响补偿 (HPSS谐波分离+谱减法)~~ | ✅ v6.0: `ReverbCompensator` 已接入 `AudioFeaturesService`, Feature Flag 控制 | ✅ v6.0 | `enable_reverb_compensation` |
| 混合音频检测文献驱动重构 | ✅ v6.0: 五特征融合 (HPSS+子带平坦度+高频+谐波度+全频平坦度) | ✅ v6.0 | — |

> **移植优先级**: 多尺度HNR > Praat CPP > Voicing detection > TorchCREPE。前两个直接提升 Breath/Technique 区分度；后两个是备选增强。所有移植通过 Feature Flag 默认关闭，逐个验证后开启。

**轨道A — 标准曲库增强层** (匹配成功时提供 DTW 对比，失败时回退到轨道B):

| 功能 | 目标版本 |
|------|---------|
| ★ 标准歌曲数据库 (SQLite) | v6.0 |
| ★ 上传自动匹配标准歌曲 | v6.0 |
| ★ 选歌 → 录音 → DTW 对比 | v6.0 |
| ★ 曲库管理 (添加/搜索/筛选/删除) | v6.0 |

**轨道C — 桌面应用 + 前端现代化** (v7.0):

> **v6.3**: PyQt5 旧桌面代码已删除 (`core/`, `widgets/`, `windows/`, `styles/`, `utils/`)。
> **v7.0 方向**: Vue 3 + Element Plus + Electron。

| 功能 | 目标版本 |
|------|---------|
| ★ Element Plus 组件库 (替代 emoji + 内联样式) | v7.0 |
| ★ Element Plus Icons (替代 120+ 表情符号) | v7.0 |
| ★ Vue 3 Composition API 前端重构 | v7.0 |
| ★ Electron 桌面应用打包 | v7.0 |
| ★ 原生窗口 + 系统托盘 + 自动更新 | v7.0 |
| ★ 内嵌 Python 环境 (PyInstaller) | v7.0 |
| ★ electron-builder 跨平台打包 | v7.0 |

---

## 四、设计原则

### 4.1 架构原则

| 原则 | 说明 |
|------|------|
| **离线优先** | 零外网依赖，所有计算本地完成 |
| **分层架构** | API → Service → Repository → Config，单向依赖 |
| **单一职责** | 评分器/特征提取器/服务 各自独立 |
| **可配置化** | 所有阈值集中在 `scoring_config.py`，Feature Flag 控制实验功能 |
| **性能可测量** | 每个特征提取器有独立计时，每个模式有端到端超时监控 |

### 4.2 性能设计原则 (新增)

| 原则 | 说明 |
|------|------|
| **性能与功能同步设计** | 新功能设计时必须附带性能预算，不在事后优化 |
| **可降级架构** | 所有重量级操作有轻量回退路径 (Pro→Quick, GPU→CPU, DTW→绝对评分) |
| **进度透明** | 所有 > 3s 的操作通过 SSE 推送进度，不阻塞 UI |
| **缓存优先** | 匹配结果、特征提取、风格配置均可缓存，基于内容哈希失效 |
| **局部化计算** | 录音实时分析在 chunk 到达时增量计算，避免录制完成后从头分析 |

### 4.2 用户体验原则

| 原则 | 说明 |
|------|------|
| **低门槛开始** | 一键上传即可获得评分，无需配置 |
| **渐进式深度** | Quick 模式满足快速反馈 → Pro 模式提供深度诊断 |
| **可操作反馈** | 不只给分数，还给出具体改进建议 |
| **隐私可见** | 明确告知用户所有数据在本地，不离开电脑 |

### 4.3 算法原则 (CRITICAL)

| 原则 | 说明 |
|------|------|
| **🔬 文献驱动 (最高优先级)** | 算法设计必须有理论根据。每个特征、阈值、方法必须来自已发表论文、教科书或权威文献。**禁止凭直觉发明方法**。流程: 查论文 → 理解原理 → 移植/适配 → 验证。优先复现论文中已验证的方法而非自行创造。 |
| **可解释评分** | 每个维度分数有理有据，不黑盒 |
| **保守使用 DL** | 深度学习仅用于语音分离 (Demucs)，评分用经典信号处理 |
| **校准驱动** | 阈值通过校准数据集确定，不做经验硬编码 |
| **区分度优先** | 分数必须能区分水平差异，不搞人人 80 分的虚假安慰 |

### 4.4 文献驱动开发流程

```
新功能/算法需求
    │
    ├─[1] 搜索论文 (Google Scholar / IEEE Xplore / ISMIR / DAFx / ICASSP)
    │      ├─ 关键词: singing voice, vocal assessment, HPSS, spectral features, ...
    │      └─ 输出: 论文题录 + PDF (存放至 参考论文/)
    │
    ├─[2] 提取方法
    │      ├─ 公式 → 代码映射
    │      ├─ 参数 → 配置/Feature Flag
    │      └─ 适用范围 → 边界条件
    │
    ├─[3] TDD 实现
    │      ├─ RED: 写测试 (引用论文作为预期行为依据)
    │      ├─ GREEN: 实现 (代码注释标注论文引用行)
    │      └─ REFACTOR: 优化 (保持与原文一致)
    │
    └─[4] 真音频验证
           └─ tests/test_data/audio/vocal/ 中 5 首真实音频作为回归基线
```

---

## 五、参考文档

### 项目文档

| 文档 | 路径 |
|------|------|
| 产品需求文档 | [PRD.md](PRD.md) |
| 系统架构 | [ARCHITECTURE.md](../2-technical/ARCHITECTURE.md) |
| 评分算法 | [SCORING.md](../2-technical/SCORING.md) |
| TDD 规范 | [TDD.md](../3-quality/TDD.md) |
| BDD 规范 | [BDD.md](../3-quality/BDD.md) |
| 项目状态 | [PROJECT_STATUS.md](../4-process/PROJECT_STATUS.md) |

### 参考论文

> 目录: `参考论文/` (项目根目录)。论文按主题组织，每篇对应代码中的 `# Reference:` 标注。

| 论文 | 主题 | 路径 |
|------|------|------|
| Fitzgerald (2010). "Harmonic/Percussive Separation Using Median Filtering." DAFx | HPSS 理论基础 | [HPSS谐波冲击分离/Fitzgerald_2010_HPSS_Median_Filtering_DAFx.pdf](../../参考论文/HPSS谐波冲击分离/Fitzgerald_2010_HPSS_Median_Filtering_DAFx.pdf) |
| Driedger, Müller, Disch (2014). "Extending Harmonic-Percussive Separation of Audio Signals." ISMIR | HPSS 三元分解 H+P+R | [HPSS谐波冲击分离/Driedger_Muller_Disch_2014_Extending_HPSS_ISMIR.pdf](../../参考论文/HPSS谐波冲击分离/Driedger_Muller_Disch_2014_Extending_HPSS_ISMIR.pdf) |
| Lehner, Schlüter, Widmer (2018). "Online, Loudness-Invariant Vocal Detection in Mixed Music Signals." TASLP 26(8) | 歌声检测特征选择 | [歌声检测SVD/Lehner_Schluter_Widmer_2018_TASLP.pdf](../../参考论文/歌声检测SVD/Lehner_Schluter_Widmer_2018_TASLP.pdf) |
| Driedger, Müller (2015). "Extracting Singing Voice from Music Recordings by Cascading Audio Decomposition Techniques." ICASSP | 级联歌声分离 | [歌声分离/Driedger_Muller_2015_Singing_Voice_Cascade_ICASSP.pdf](../../参考论文/歌声分离/Driedger_Muller_2015_Singing_Voice_Cascade_ICASSP.pdf) |
| Boll (1979). "Suppression of Acoustic Noise in Speech Using Spectral Subtraction." IEEE Trans. ASSP 27(2) | 谱减法 (ReverbCompensator) | ⚠️ IEEE 付费墙, 算法在 `services/features/reverb.py` |
| Berouti, Schwartz, Makhoul (1979). "Enhancement of Speech Corrupted by Acoustic Noise." ICASSP | 过减因子 α, 频谱地板 β | ⚠️ IEEE 付费墙, 算法在 `services/features/reverb.py` |

> **原则**: 每个算法模块的代码注释中必须标注 `# Reference:` 指向对应的论文和章节。新算法设计前先搜索 `参考论文/` 目录确认是否已有相关文献。
