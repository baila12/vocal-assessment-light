# 声乐评估系统 (VAS) — 产品需求文档 v7.13

> 版本: v7.13 | 日期: 2026-08-08 | 状态: 活跃开发
>
> **关联文档**: [GOALS.md](GOALS.md) | [ARCHITECTURE.md](../2-technical/ARCHITECTURE.md) | [SCORING.md](../2-technical/SCORING.md)

---

## 1. 产品概述

### 1.1 定位

**纯离线、本地运行的声乐六维评分桌面应用** — 一键启动，浏览器即用，所有数据留在本地。

### 1.2 目标用户

| 用户类型 | 特征 | 使用频率 | 核心诉求 |
|---------|------|:------:|------|
| 声乐学生 | 有规律练习习惯，需要量化反馈追踪进步 | 每天 1-3 次 | 详细诊断 + 历史进步曲线 |
| K歌爱好者 | 非专业背景，偶尔使用 | 每周 1-3 次 | 快速评分 + 直观反馈 |
| 声乐教师 | 专业背景，多学生管理 | 每天多次 | 对比分析 (DTW) + 客观评分辅助教学 |

### 1.3 核心价值

| 价值点 | 说明 |
|------|------|
| **纯离线隐私** | 所有数据本地存储，不上传云端，无需联网 |
| **六维专业评分** | 音准/节奏/气息/发声技术(咬字+气声比)/肌肉力量/艺术表现 + 音色加减分 |
| **浏览器即用** | 一键启动 FastAPI 服务，浏览器自动打开 |
| **人声分离** | Demucs 自动分离伴奏，在纯净人声上评分更准确 |
| **DTW 对比** | 与标准演唱逐帧对齐对比，知道「差在哪」而不只是「差多少」 |

---

## 2. 用户场景

### 场景 A：声乐学生日常练习

> 用户完成一段 3 分钟流行歌曲练习录音 → 打开系统，上传录音，选择 Quick 模式 → ~20s 内获得六维评分 + 雷达图 + 改进建议 → 历史记录自动保存

### 场景 B：专业用户深度诊断

> 用户录制带钢琴伴奏的完整演唱 → 选择 Professional 模式 → Demucs 自动分离人声 → 在纯净人声上计算六维评分 + 逐句评分 + 频谱图/基频图/能量图

### 场景 C：对比标准版本

> 用户有自己的演唱录音和原唱版本 → 使用对比分析功能上传两个音频 → DTW 逐帧对齐 → 音高曲线叠加对比，偏差区域高亮 → 自动诊断音准/节奏偏差

### 场景 D：非人声/噪声拦截

> 用户误上传白噪声/纯音乐/TTS 合成语音 → 系统检测 `is_voice=false` → 总分返回 0 → 前端显示「未检测到有效人声」

---

## 3. 功能需求

### 3.1 核心功能 (已实现)

| 功能 | 说明 |
|------|------|
| 多格式音频上传 | WAV/MP3/FLAC/OGG/M4A/AAC，支持拖拽 |
| 六维评分 | 音准 13% / 节奏 12% / 气息 22% / 发声技术(咬字+气声比) 25% / 肌肉力量 15% / 艺术 13% + 音色加减分(+3~-5)；权重单一来源 ScoringWeights 值对象, 可配置 (v7.11) |
| Quick 模式 | 跳过 Demucs 和 DL 模型，直接在原始音频上评分 (~20s) |
| Professional 模式 | Demucs 分离 → 纯净人声评分 + 逐句 + 可视化 (~155s CPU / ~55s GPU) |
| 非人声检测 | 白噪声/纯音乐/合成语音 → `is_voice=false` → score=0 |
| 混合音频自动分离 | 检测伴奏 → 自动触发 Demucs 人声分离 |
| DTW 对比分析 | 双音频三级对齐 (全局→句→音符)，音准/节奏偏差 |
| 历史记录 | 分页查询 + 日期筛选 + 批量删除 |
| 逐句评分 | Pro 模式自动分句 + 每句独立评分 |
| 可视化图表 | 频谱图 + 基音轨迹 + 能量曲线 + 六维雷达图 |
| 报告导出 | PDF / 图片格式 |
| 风格自适应评分 | 流行/美声/民族/说唱 四风格权重调整 (v7.11 实现为 ScoringWeights 风格预设 + API) |
| 评分权重面板 | 前端 ScoringWeightsPanel — 预设选择 + 六维滑块 + 总和校验 + 归一化 + 对比重算 (v7.11) |
| GPU 加速 | Demucs CUDA/MPS 自动检测 |

### 3.2 高级特征 (已实现)

| 功能 | 说明 | Feature Flag |
|------|------|:--:|
| 多尺度 HNR | de Krom 1993 四频带 HNR | `enable_multiscale_hnr` |
| Praat CPP | parselmouth 替换手动 FFT 倒谱 | `enable_praat_cpp` |
| Voicing detection | PYIN 自一致性评估 | `enable_voicing_detection` |
| TorchCREPE 备选 | PYIN 检测率 < 50% 时启用 | `enable_torchcrepe_fallback` |
| 混响补偿 | HPSS + 谱减法 | `enable_reverb_compensation` |
| 跨维度修正 | HNR→气息, Voicing→音准, 频谱倾斜→气声, 气息-音准耦合 | `enable_cross_dimension_modifiers` |
| Audiofeat 增强 | 130+ 声学特征 (CPPS/GNE/Jitter/Shimmer…) | `enable_audiofeat` |
| FCPE 基频提取 | 96.79% RPA, GPU 加速 | `enable_fcpe` |

### 3.3 安全特性 (v7.3.1)

| 机制 | 配置 |
|------|------|
| Security Headers | CSP, X-Content-Type, X-Frame, HSTS, Referrer-Policy |
| Rate Limit | 120/min global, 20/min upload, 10/min WebSocket |
| Max Body Size | 50MB (413 Payload Too Large) |
| Path Traversal 防护 | 文件名白名单 + resolved path 校验 |
| Error Response | 通用错误消息, 无原始 traceback 泄露 |

### 3.4 实时流式评分 (WebSocket)

- AudioWorklet → Float32Array → WebSocket 二进制帧 (16kHz, 2048 samples)
- 每 2s 计算 incremental score
- 录音完成 → 轻量评分 (<1s, 纯 NumPy, 无 DL)

### 3.5 近期新增 (v7.9 → v7.13)

| 功能 | 说明 |
|------|------|
| 标准曲库管理 | 后端 CRUD (POST/GET/GET id/DELETE, SQLite) (v7.9) + 前端卡片网格页 (SongsView, 搜索/筛选/上传/删除/试听) (v7.10) + 音频播放目录白名单修复 + 目录锁 is_relative_to 安全加固 (v7.10) |
| 评分权重可配置 | ScoringWeights 值对象 (frozen, 总和 100% + 单维 ≤50%) + 4 风格预设 (流行/美声/民族/说唱) + calculate_total 注入 weights + GET /api/v1/scoring/presets + POST /api/v1/scoring/apply-weights (v7.11) |
| 前端权重面板 | scoring.store.ts + ScoringWeightsPanel.vue (预设单选 + 六维滑块 + 实时总和校验 + 自动归一化 + 对比重算含 vs 原总分差值) + ReportView 集成 (v7.11) |
| BDD 基建修复 | conftest base_url :5000→:8000 (FastAPI 服务 frontend/dist) + api_client Flask→FastAPI TestClient + 前端 window.__store 测试钩子 (v7.11) |
| 选歌录音 MVP | 曲库选歌 → `/sing/:songId` → WS 携带 song_id; 后端 `SongMetadata.vocal_range` (v7.12) |
| 实时音准对比子系统 | 参考音高 API (GET /songs/{id}/pitch) + 上传录音 DTW 对比 (POST /songs/{id}/compare) + WS pitch_update 实时推送 + 音准偏差着色/滚动窗口/回放控制 + 录音中实时对比 + 录音后回放分析 + CompareView 双轨叠加/热力图/性能降级/截图/快捷键 (v7.13 Phase 1-5) |
| 自动曲库匹配 (auto-match) | 计划中：SQLite 预提取特征 + 自动匹配用户翻唱 |

### 3.6 计划中 (未实现)

| 功能 | 说明 |
|------|------|
| 非阻塞分析 | SSE 进度推送，分析中可播放音频，跨页面不中断 |
| Electron 桌面打包 | electron-builder + 嵌入式 Python，<2s 启动 |

---

## 4. 非功能需求

### 4.1 性能

| 指标 | Quick | Pro CPU | Pro GPU |
|------|:-----:|:------:|:------:|
| 端到端耗时 | ~20s | ~155s | ~55s |
| 内存峰值 | ~170MB | ~1050MB | ~800MB |
| 首次启动 | < 10s | < 10s | < 10s |
| 并发 | 单请求 | 单请求 | 单请求 |

**前端性能**:

| 指标 | 目标 |
|------|:---:|
| FCP | < 1.5s |
| SPA 路由切换 | < 300ms |
| GSAP 动画帧率 | ≥ 30fps |
| JS Bundle (gzip) | < 300KB |

**已知优化潜力**: Quick 模式可 2x 加速至 ~10s，Pro GPU 可 2.5x 加速至 ~22s。详见 [PERFORMANCE_ANALYSIS_AND_OPTIMIZATION.md](../2-technical/PERFORMANCE_ANALYSIS_AND_OPTIMIZATION.md)。

### 4.2 可靠性

| 指标 | 当前 |
|------|:---:|
| 非人声归零率 | 10/10 (100%) |
| 单元测试通过率 | 537/537 (100%) |
| Quick/Pro 同音频分差 | < 10% |

### 4.3 兼容性

| 平台 | 要求 |
|------|------|
| 操作系统 | Windows 10+ / macOS 12+ / Linux (Ubuntu 20.04+) |
| Python | 3.9 - 3.12 |
| 浏览器 | Chrome 90+ / Firefox 90+ / Edge 90+ |
| 硬件 | 8GB RAM 最低，16GB 推荐 (Demucs 需 ~800MB) |

### 4.4 不做

- 云端同步 / 用户账号系统
- 社交分享 / 排行榜 / 社区
- 实时 K歌打分 (需低延迟音频流水线)
- 移动端 App (iOS/Android)
- 多语言国际化 (仅简体中文)

---

## 5. 技术栈

| 层 | 当前 (v7.13) |
|------|------|
| 后端框架 | FastAPI (uvicorn, workers=1) |
| 音频处理 | librosa + parselmouth + pyworld |
| 深度学习 | PyTorch + ONNX Runtime + Demucs (htdemucs_ft) |
| f0 检测 | PYIN (librosa) + TorchCREPE fallback + FCPE |
| 前端框架 | Vue 3.5 + TypeScript + Vite 5 |
| UI 组件 | Element Plus 2.14 |
| 状态管理 | Pinia 2.3 |
| 路由 | Vue Router 4.6 (hash history) |
| 图表 | Chart.js 4.5 + vue-chartjs |
| 动画 | GSAP 3.15 |
| 桌面 | Electron 28 (配置就绪) |
| 数据存储 | JSON 文件 + SQLite (曲库) |
| 配置 | Pydantic Settings |
| 测试 | pytest 537 + Vitest 286 |

---

## 6. 版本路线

| 版本 | 日期 | 主题 |
|------|------|------|
| **v7.13** | **2026-08-08** | **实时音准对比子系统 Phase 1-5: 参考音高 API + WS pitch_update + 偏差着色/滚动/回放 + 录音中实时对比 + 回放分析 + CompareView 双轨叠加/热力图/性能降级/截图/快捷键** |
| **v7.12** | **2026-08-06** | **选歌录音 MVP (/sing/:songId + WS song_id + vocal_range) + BDD 基建修复 + dl_services 死代码清理** |
| v6.3 | 2026-07-20 | 项目结构重组 (删除 PyQt5, 清理根目录) |
| v7.0 | 2026-07-21 | FastAPI + Vue 3 + Element Plus + 六维评分 + DDD 四层 |
| v7.1 | 2026-07-23 | 绞杀者内部化 (13/13 提取器自包含) + FCPE 集成 |
| v7.2 | 2026-07-25 | audiofeat 增强特征 (22 特征) + 代码审查 |
| v7.3 | 2026-07-27 | audiofeat 评分闭环 + Comparison DDD + 安全加固 |
| v7.3.1 | 2026-07-28 | 信息泄露修复 (9处) + Flask 限速 + BDD 29 scenarios |
| v7.4 | 2026-07-29 | 六维权重重校准 (13/12/22/25/15/13) + 肌肉降权 + 气声 HNR 修复 + 咬字修复 |
| v7.5 | 2026-07-30 | 音色 8 维特征 + Muscle + Timbre HEURISTIC 标注 |
| v7.6 | 2026-07-31 | ABI + rubato + attack_slope + Flask 绞杀者完成 + 旧前端移除 |
| v7.7 | 2026-08-01 | Feature Flag 系统 + 维度独立开关 |
| v7.8 | 2026-08-01 | GNE 接入 + GSAP 动效系统 + 前后端对齐 |
| **v7.11** | **2026-08-04** | **评分权重可配置 (ScoringWeights 值对象 + 4 风格预设 + API) + 前端权重面板 + BDD 基建修复** |
| v7.10 | 2026-08-04 | 歌曲库前端页面 (卡片网格+搜索/筛选+上传/删除/试听) + 音频播放修复 |
| v7.9 | 2026-08-02 | 歌曲库后端 CRUD + 架构清理 |

---

## 7. 已知问题 & 改进计划

| 问题 | 影响 | 计划 |
|------|------|------|
| ~~气声比 HNR 权重过高 (70%)~~ | ~~Technique 系统性偏低~~ | ✅ v7.4 P0-1 已修复 |
| ~~咬字缺失 ZCR + Spectral Centroid~~ | ~~偏离文献方法~~ | ✅ v7.4 P0-2 已修复 |
| ~~音色置信度门控失效~~ | ~~音色维度完全禁用~~ | ✅ v7.4 P1-2a 已修复 |
| ~~肌肉权重 25% vs 文献建议 15%~~ | ~~启发式维度影响过大~~ | ✅ v7.4 P0-4 已修复 |
| ~~评分权重新硬编码 (6 个 weighted() 各自维护)~~ | ~~权重数据源分散, 不一致风险~~ | ✅ v7.11 ScoringWeights 值对象单一数据来源 |
| ~~BDD 浏览器基建指向已删除 Flask~~ | ~~conftest base_url :5000, api_client 旧 Flask~~ | ✅ v7.11 FastAPI TestClient + :8000 + window.__store 钩子 |
| Demucs 子进程开销 | Pro 模式耗时 155s | [性能优化](../2-technical/PERFORMANCE_ANALYSIS_AND_OPTIMIZATION.md) |
| ~~BDD animations.feature 旧架构~~ | ~~15 scenarios 针对已废弃 Vanilla JS~~ | ✅ v7.12 迁移 Vue 3 data-test (7 PASS + 9 XFAIL) |
| ~~选歌录音 (#/sing/:songId)~~ | ✅ v7.12 MVP (选歌+WS song_id+vocal_range); 实时音高参考线叠加/DTW 流式评分为后续增强 |
| ~~upload 38 场景测试数据缺失~~ | ~~vocals.wav 缺失预存失败~~ | ✅ v7.12 生成 vocals.wav + fixture 修复 (5 PASS + 3 SKIP) |

---

## 8. 参考文档

| 文档 | 路径 |
|------|------|
| 产品目标与设计原则 | [GOALS.md](GOALS.md) |
| 系统架构 | [ARCHITECTURE.md](../2-technical/ARCHITECTURE.md) |
| 评分算法 | [SCORING.md](../2-technical/SCORING.md) |
| 算法改进计划 | [SCORING_ALGORITHM_IMPROVEMENT_PLAN.md](../2-technical/SCORING_ALGORITHM_IMPROVEMENT_PLAN.md) |
| 性能分析 | [PERFORMANCE_ANALYSIS_AND_OPTIMIZATION.md](../2-technical/PERFORMANCE_ANALYSIS_AND_OPTIMIZATION.md) |
| API 接口 | [API.md](../2-technical/API.md) |
| 项目状态 | [PROJECT_STATUS.md](../4-process/PROJECT_STATUS.md) |
| 变更日志 | [CHANGELOG.md](../4-process/CHANGELOG.md) |
