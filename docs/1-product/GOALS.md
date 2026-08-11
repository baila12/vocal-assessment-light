# 产品目标与设计原则 v7.14

> 更新: 2026-08-10 | 功能详情见 [PRD.md](PRD.md) | 架构见 [ARCHITECTURE.md](../2-technical/ARCHITECTURE.md)

---

## 一、产品定位

**离线声乐评估系统 (VAS)** — 纯本地、无服务器、无需登录的专业声乐评估桌面应用。

### 核心价值

| 维度 | 说明 |
|------|------|
| **隐私保护** | 全离线运行，所有数据本地存储，不上传云端 |
| **专业评估** | 六维评分 + 音色加减分 + Demucs 人声分离 + DTW 参考对比 |
| **即开即用** | 一键启动，浏览器访问 |
| **双模式** | Quick (~20s 快速反馈) / Pro (完整诊断 + 可视化) |

---

## 二、功能全景

```
离线声乐评估系统 v7.14
│
├── 模块1: 音频采集
│   ├── 多格式上传 (WAV/MP3/FLAC/OGG/M4A/AAC, 拖拽)
│   ├── 麦克风实时录音 (AudioWorklet → WebSocket)
│   └── 50MB 文件上限
│
├── 模块2: 评分分析 ★核心
│   ├── 六维评分 (音准13% / 节奏12% / 气息22% / 技术25% / 肌肉15% / 艺术13%)
│   ├── 评分权重可配置 (ScoringWeights 值对象, 单一数据来源, v7.11)
│   ├── 风格预设 (流行/美声/民族/说唱, 4 套权重, v7.11)
│   ├── 权重 API (GET /api/v1/scoring/presets + POST /api/v1/scoring/apply-weights, v7.11)
│   ├── 音色加减分 (+3~-5, clamp[0,100])
│   ├── Quick 模式 (~20s, 无 Demucs/无 DL)
│   ├── Pro 模式 (~155s CPU / ~55s GPU, 完整管线)
│   ├── Demucs 人声分离 (htdemucs_ft, GPU 自动检测)
│   ├── DTW 对比分析 (三级对齐, 仅用于音准/节奏)
│   ├── 风格自适应 (流行/美声/民族/说唱)
│   ├── 逐句评分 (Pro 模式)
│   ├── 跨维度修正 (5 项因果链)
│   ├── 底线规则 (连续跑调/脱离节拍/严重漏气)
│   └── Feature Flag 机制 (9 个高级算法 + 维度独立开关)
│
├── 模块3: 可视化
│   ├── 频谱图 + 基音轨迹 + 能量曲线
│   ├── 六维雷达图 (Chart.js)
│   └── 音高曲线对比 (DTW 叠加)
│
├── 模块4: 曲库管理 (v7.9 后端 + v7.10 前端, 均已完成)
│   ├── 标准曲库 CRUD (POST/GET/GET id/DELETE, SQLite)
│   ├── 前端卡片网格页 (SongsView, #/songs, 搜索/风格·难度筛选/上传/删除/试听, v7.10)
│   └── 音频播放白名单 + 目录锁 is_relative_to 安全加固 (v7.10)
│
├── 模块5: 历史与导出
│   ├── 历史记录 (分页/筛选/批量删除, JSON 存储)
│   ├── 成长曲线 (评分趋势)
│   └── 报告导出 (PDF/图片)
│
├── 模块6: 实时流式评分
│   ├── WebSocket 二进制帧 (Float32Array → numpy.frombuffer 零拷贝)
│   ├── 每 2s incremental score
│   └── 录音完成 → <1s 轻量评分
│
└── 模块7: 安全
    ├── Security Headers (CSP, X-Content-Type, X-Frame, HSTS)
    ├── Rate Limit (120/min global, 20/min upload, 10/min WS)
    ├── Max Body Size (50MB)
    └── Error Response (无原始 traceback 泄露)
```

---

## 三、设计原则

### 3.1 架构原则

| 原则 | 实现 |
|------|------|
| **离线优先** | 零外网依赖，所有计算本地完成 |
| **DDD 分层** | domain → application → infrastructure → interfaces，单向依赖 |
| **绞杀者模式 (v7.6 完成)** | 纯 FastAPI 架构，Flask 已全部移除 |
| **单一职责** | 每个 scorer/extractor 独立可测，互不依赖 |
| **零硬编码** | 所有阈值/路径/端口从配置注入，不设硬编码兜底 |
| **不可变数据** | 所有 Features 和 Value Objects 使用 frozen dataclass |

### 3.2 评分原则

| 原则 | 说明 |
|------|------|
| **文献驱动** | 每个算法必须有论文依据，禁止凭直觉发明方法 |
| **可解释评分** | 每个维度分数有理有据，诊断信息可追溯 |
| **保守使用 DL** | DL 仅用于 Demucs 人声分离和风格分类，评分用经典信号处理 |
| **区分度优先** | 分数必须能区分水平差异 |
| **启发式标注** | 肌肉力量、音色等代理指标明确标注 HEURISTIC |
| **Feature Flag 门控** | 新算法默认关闭，验证后开启，保证回退路径 |

### 3.3 性能原则

| 原则 | 说明 |
|------|------|
| **可降级架构** | Pro→Quick, GPU→CPU, DTW→绝对评分 |
| **可测量** | 每个特征提取器有独立耗时预算 |
| **进度透明** | WebSocket 流式推送 incremental score |

### 3.4 用户体验原则

| 原则 | 说明 |
|------|------|
| **低门槛** | 一键上传即可获得评分，无需配置 |
| **渐进深度** | Quick 快速反馈 → Pro 深度诊断 |
| **可操作反馈** | 不只给分数，还给出具体改进建议 |
| **隐私可见** | 明确告知用户所有数据在本地 |

---

## 四、测试策略

| 层级 | 方法 | 当前 |
|------|------|:---:|
| 单元测试 (DDD 全套) | pytest, domain + infrastructure + middleware + alignment + flag + WS 会话 | 575 tests ✅ |
| FastAPI 集成 (API 层) | pytest, assessment + songs + scoring + songs_pitch + song_match + compare | 73 tests ✅ |
| WebSocket 集成 | pytest, ws_score + ws_pitch_update | 17 tests ✅ |
| 扩展测试 | pytest, DTW/repos | 21 tests ✅ |
| BDD | pytest-bdd, 18 step files, 21 .feature files, 187 scenarios collected (121 API 级 + 66 browser) | ⚠️ 见 PROJECT_STATUS (21 既有失败: Flask 遗留 step 文件) |
| 真实音频回归 | pytest, 5 基准文件, 28 tests | ⚠️ 24 PASS + 4 FAIL (breath 基线漂移, 既有) |
| **生产代码合计** | | **686 tests 100% GREEN** (unit 575 + API 73 + WS 17 + 扩展 21) |
| **后端 collected** | | **714 tests** (686 + 真实音频 28; 实测 710 passed) |
| 前端测试 | Vitest, 297 tests, vue-tsc 0 errors | ✅ |

---

## 五、技术栈

| 层 | 技术 |
|------|------|
| 后端 | FastAPI + uvicorn |
| 音频处理 | librosa + parselmouth + pyworld |
| DL 框架 | PyTorch + ONNX Runtime + Demucs |
| 前端 | Vue 3.5 + TypeScript + Vite 5 |
| UI | Element Plus 2.14 |
| 状态管理 | Pinia 2.3 |
| 桌面 | Electron 28 (配置就绪) |
| 数据 | JSON + SQLite |
| 测试 | pytest 714 (collected) + Vitest 297 |

---

## 六、参考

| 文档 | 路径 |
|------|------|
| 产品需求文档 | [PRD.md](PRD.md) |
| 系统架构 | [ARCHITECTURE.md](../2-technical/ARCHITECTURE.md) |
| 评分算法 | [SCORING.md](../2-technical/SCORING.md) |
| 算法改进计划 | [SCORING_ALGORITHM_IMPROVEMENT_PLAN.md](../2-technical/SCORING_ALGORITHM_IMPROVEMENT_PLAN.md) |
| 性能优化计划 | [PERFORMANCE_ANALYSIS_AND_OPTIMIZATION.md](../2-technical/PERFORMANCE_ANALYSIS_AND_OPTIMIZATION.md) |
| API 文档 | [API_CONTRACT.md](../2-technical/API_CONTRACT.md) |
| 项目状态 | [PROJECT_STATUS.md](../4-process/PROJECT_STATUS.md) |
| 变更日志 | [CHANGELOG.md](../4-process/CHANGELOG.md) |
