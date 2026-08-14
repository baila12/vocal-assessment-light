# 声乐评估系统 v7.17

基于 FastAPI + Vue 3 的本地 Web 应用，提供六维声乐评分、实时录音、对比分析、歌曲库管理等功能。

## 功能特性

### 核心功能
- **六维评分** - 音准(13%)/节奏(12%)/气息(22%)/发声技术(25%)/肌肉力量(15%)/艺术表现(13%) + 音色加减分
- **双评估模式** - 快速评估(~30秒) / 专业评估(~2-5分钟)
- **实时可视化** - 波形、频谱、音量实时显示
- **人声质量检测** - 自动识别非人声音频
- **音色分析** - 明亮度、厚度、鼻音、气声八维分析
- **逐句评分** - 按乐句分段评分（专业模式）
- **人声分离** - Demucs 模型分离伴奏与人声
- **对比分析** - DTW 对齐对比，支持上传模式和实时录音模式
- **实时音高检测** - 前端实时音高检测
- **录音功能** - 实时录音并分析
- **成长曲线** - 历史评分趋势图
- **标准歌曲库** - 上传/浏览/搜索/筛选/试听参考歌曲，卡片网格前端页面 (v7.9 后端 + v7.10 前端)
- **选歌录音** - 曲库选歌 → `/sing/:songId` 演唱页 → 录音携带参考歌曲 (v7.12 MVP; v7.13 增强)
- **参考音高线** - 选歌后加载歌曲 F0 曲线，录音 Canvas 叠加标准参考虚线 (v7.13)
- **实时音高推送** - WebSocket 每 2s 增量推送 pitch_update，用户音高曲线实时渲染 (v7.13)
- **选歌后上传对比** - 上传已有录音与选中标准歌曲 DTW 对比 (v7.13)
- **音准偏差着色** - 音准对比 Canvas 逐帧偏差着色 (≤25 绿 / 25-50 橙 / >50 红), 静音灰虚线, 八度跳变 ⚠️ 标记, 无参考蓝色单曲线 (v7.13 Phase 2)
- **音准回放控制** - 录音后回放: 播放/暂停/点击拖拽跳转/倍速 (0.5x/1x/1.5x)/A-B 循环, 滚动窗口播放位置居中 (v7.13 Phase 2)
- **录音中实时对比** - 演唱中 live 模式: 用户音高圆点 2s 淡出 + 偏差背景色带 + 当前偏差值/趋势箭头 (v7.13 Phase 3)
- **录音后回放分析** - 回放时问题段落红色高亮 + 逐句评分药丸 + 音准统计面板 (精准/略偏/跑调, 最高/最低音) (v7.13 Phase 4)
- **对比分析双轨叠加** - CompareView 标准虚线 + 用户动态着色实线双轨叠加, 偏差三色填色 + 底部热力图条 + 缩略导航条, 点击跳转 (v7.13 Phase 5)
- **性能降级保护** - 低帧率自动降级渲染 (抗锯齿关/着色降频/网格关), UI 性能模式指示器 + 手动切回 (v7.13 Phase 5)
- **对比截图与快捷键** - 音准对比 PNG 截图导出 (时间戳水印 + DPR 原分辨率) + 键盘快捷键 (Space/←→/R/S/1/2) (v7.13 Phase 5)
- **上传自动匹配** - 上传演唱录音 → 自动匹配歌曲库标准歌曲 → 返回最佳匹配 + Top-3 候选 → 一键 DTW 对比; 无匹配优雅回退绝对评分 (v7.14)
- **导出报告** - PDF/图片格式报告

### 对比分析功能

独立对比分析页面 (Vue SPA `/compare`)，提供两种评估模式：

| 模式 | 说明 | 特点 |
|------|------|------|
| **上传模式** | 导入标准音频 + 用户音频 | 基于标准音频的相对评分 |
| **实时录音模式** | 类似全民K歌 | 实时音准偏差显示、调整建议 |

#### 实时录音模式特性
- 播放标准音频同时录音
- 实时显示音分偏差（+/- 音分）
- 实时调整建议（略高/偏低等）
- 实时评分更新
- 音高曲线对比图（标准 vs 用户）

### 评估模式对比

| 特性 | 快速评估 | 专业评估 |
|------|---------|---------|
| 总耗时 | ~30-40秒 | ~3-5分钟 |
| 基础评分 | ✓ 六维评分 | ✓ 六维评分 |
| 评分配置 | 宽松阈值 | 标准阈值 |
| 分数范围 | 60-90分(平滑) | 0-100分 |
| 逐句评分 | ✗ | ✓ |
| 音色分析 | ✗ | ✓ |
| 可视化图表 | ✗ | ✓ |
| DL质量评估 | ✗ | ✗ (已移除) |
| 音乐风格分析 | ✗ | ✓ |
| 适用场景 | 快速练习反馈 | 详细问题诊断 |

### 技术特点
- **纯离线运行** - 无需联网，保护隐私
- **安全加固** - 路径遍历防护、XSS防护、速率限制
- **大文件支持** - 50MB+ 音频文件处理
- **中文支持** - 完整的中文文件名支持
- **前端音高检测** - 实时检测，无需后端

## 快速开始

### 环境要求
- Python 3.8+
- conda 环境: pytorch2

### 启动服务
```bash
cd "C:\Users\jack\Desktop\临时文件\声乐\vocal_assessment_light"
python backend/main.py              # FastAPI :8000
```
## 项目结构

```
vocal_assessment_light/
├── backend/              # FastAPI DDD 后端
│   ├── domain/           # 领域层
│   │   ├── assessment/   # 6 scorers (六维) + 音色调整
│   │   ├── audio/        # 10 特征提取模块
│   │   ├── comparison/   # 对比分析领域
│   │   ├── songs/        # 歌曲库领域 (v7.9)
│   │   ├── songs_pitch/  # 参考音高领域 (v7.13: F0 曲线 + 缓存)
│   │   └── song_match/   # 自动匹配领域 (v7.14: 特征/BPM/调性/置信度)
│   ├── application/      # 编排层
│   ├── infrastructure/   # 基础设施 (SQLite 仓储)
│   ├── interfaces/       # API + WebSocket
│   └── main.py           # 应用入口 (:8000)
├── frontend/             # Vue 3 + Element Plus SPA
│   └── src/views/        # 6 页面 (Home/Report/History/Compare/Sing/Songs)
├── api/business/         # 共享业务逻辑 (audio_analysis)
├── services/             # 服务层
│   └── dl_services/      # 深度学习 (style/VAD/DTW)
└── tests/                # 812 tests collected (unit 669 + API 77 + WS 17 + extended 21 + real-audio 28) + 前端 307 Vitest

> 注: 详细开发文档 (PROJECT_STATUS/CHANGELOG/评分算法/深度审查) 存放于本地 `docs/` 目录, 不纳入版本控制; 本仓库仅保留此 README。
```

## API 接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/v1/upload` | POST | 上传并分析音频，支持 `mode`: `quick` / `professional` |
| `/api/v1/analyze` | POST | 分析已存在音频 |
| `/api/v1/compare` | POST | DTW 对比分析两个音频 |
| `/api/v1/separate` | POST | Demucs 人声分离 |
| `/api/v1/extract-pitch` | POST | 基频提取 |
| `/api/v1/report` | POST | 生成评估报告 |
| `/api/v1/flags` | GET | Feature Flags 状态 |
| `/api/v1/scoring/presets` | GET | 评分权重预设 — 默认 + 4 风格 (v7.11) |
| `/api/v1/scoring/apply-weights` | POST | 维度分数+权重→总分/等级 — 纯前端重算 (v7.11) |
| `/api/v1/history` | GET/POST/DELETE | 历史记录 CRUD |
| `/api/v1/songs` | POST/GET/GET/DELETE | 歌曲库管理 (v7.9) |
| `/api/v1/songs/{song_id}/pitch` | GET | 歌曲参考音高 F0 曲线 (v7.13) |
| `/api/v1/songs/{song_id}/compare` | POST | 上传录音与选中歌曲 DTW 对比 (v7.13) |
| `/api/v1/songs/match` | POST | 上传录音自动匹配歌曲库标准歌曲 → 最佳匹配 + Top-N 候选 (v7.14) |
| `/api/v1/audio` | GET | 流式传输音频文件 |
| `/ws/v1/score` | WebSocket | 实时评分推送 |

### 上传接口参数

```
POST /api/v1/upload
Content-Type: multipart/form-data

参数:
- file: 音频文件 (必需)
- mode: 评估模式 (可选，默认: quick)
  - quick: 快速评估，跳过逐句评分、音色分析、可视化
  - professional: 专业评估，完整分析
- auto_match: 自动匹配歌曲库标准歌曲 (可选，默认: false) — 为 true 时响应注入 matched_song/matched_candidates/fallback_reason (v7.14)
```

### 自动匹配接口

```
POST /api/v1/songs/match
Content-Type: multipart/form-data

参数:
- file: 用户演唱录音 (必需)
- top_n: 候选数量 (可选，默认: 3)

返回:
{
  "success": true,
  "matched": true,
  "matched_song": { "id": "...", "title": "...", "artist": "...", "confidence": 0.94 },
  "candidates": [ { "song_id": "...", "title": "...", "artist": "...", "confidence": 0.94,
                    "factors": {"bpm": ..., "chroma": ..., "key": ..., "duration": ...},
                    "bpm_diff": 0.0, "key_diff_semitones": 0, "detected_key": "C" }, ... ],
  "fallback_reason": "",
  "detected_key": "C",
  "partial": false,
  "elapsed_ms": 234
}
```

置信度 = `0.30*bpm + 0.40*chroma + 0.15*key + 0.15*duration`, `MATCH_THRESHOLD = 0.60`; 无匹配时 `matched=false`, `fallback_reason ∈ {no_match, no_profiles, audio_too_short, timeout}`。

### 对比分析接口

```
POST /api/v1/compare
Content-Type: multipart/form-data

参数:
- user_file: 用户音频文件 (必需)
- standard_file: 标准音频文件 (必需)

返回:
{
  "success": true,
  "data": {
    "score": 85,              // 综合评分 (0-100)
    "level": "良好",          // 等级
    "pitch_match_rate": 88.5, // 音准匹配率
    "rhythm_match_rate": 82.3,// 节奏匹配率
    "avg_cents_error": 15.2,  // 平均音分偏差
    "diagnosis": [...]        // 诊断建议
  }
}
```

## 测试

```bash
# 单元测试
pytest tests/unit/domain/ tests/unit/infrastructure/ tests/unit/interfaces/ws/ tests/unit/test_middleware.py tests/unit/test_ddd_alignment.py tests/unit/test_ddd_extraction_flag.py tests/unit/test_flag_bridge.py -v

# 集成测试
pytest tests/integration/ -v

# 扩展测试
pytest tests/extended/ -v

# 前端测试
cd frontend && npx vitest run
```

## 版本历史

- **v7.17** — 评分校准 (高分音频 ≥80): A1 rhythm 混音映射重校准 (伴奏污染) + B1 pitch MAE 曲线放宽 + A2 tilt/hf 改质量组件 (修复气声比结构性封顶 65) + B3/B4 六维曲线校准 + **A4 pro 节拍锚定节奏** (用分离伴奏轨做节拍基准 + 人声轨做 vocal onset, 修复 pro 分离后 rhythm 崩坍 72→8.2); 4 个"高分"真实音频 total 79.9-82.6 (旧 63-65); BASELINE_V7_17 (2026-08-14)
- **v7.16** — P2-15 legacy 收敛全部 Phase 0/0b/1/2/3/5: 删死 `calculate()` 路径 (calculate_ddd 唯一生产评分路径) + 死字段 + `advice_service.py` (AdviceGenerator 迁入 DDD application 层) + **历史双写 bug 修复** (EventBus 自动保存写垃圾记录挤占槽位) + calculate_ddd 补全逐维诊断 + 音色单轨化 (删 TimbreService) + facade 折叠 (analyze_emotion/reference_path/flag 对齐); **Phase 4 (PhraseService 逐句评分) 经用户决策推迟** (2026-08-13)
- **v7.15** — 错误可见化 (H-B14/H-B15) + 后端静默错误修复 (M3/M4/M5) + uploads 自动清理 + 集成隔离修复 (deps 单例跨模块污染) + httpx2 迁移 (2026-08-12)
- **v7.14** — 上传音频自动匹配标准歌曲: 新增 song_match DDD 子域 (BPM/Krumhansl-Schmuckler 调性/chroma/duration 特征 + 确定性置信度 = 0.30bpm+0.40chroma+0.15key+0.15duration, 阈值 0.60) + POST /songs/match (Top-N 候选 + fallback_reason) + upload 可选 auto_match 注入 + SQLite 匹配特征持久化 (预算式预计算, 超时 partial) + 前端 CompareView 自动匹配区 (候选列表/置信度/BPM差/调性差 → 一键 DTW 对比) (2026-08-09)
- **v7.13** — 实时音准对比子系统 Phase 1-5: 参考音高 API (GET /songs/{song_id}/pitch) + 选歌录音增强 (参考线叠加/上传录音 DTW 对比/再来一首) + WS pitch_update 实时推送 + WS 权重 ScoringWeights 单一来源; Phase 2: 音准对比 Canvas 偏差着色 + 滚动窗口 + 回放控制 (播放/拖拽/倍速/A-B) + Y 轴音高/时间刻度; Phase 3: 录音中实时对比 (live 模式圆点/偏差色带/趋势); Phase 4: 录音后回放分析 (问题段落高亮/逐句评分/统计面板); Phase 5: CompareView 双轨叠加 (偏差三色填色/热力图/缩略条) + 性能降级 + 截图/快捷键 (2026-08-08)
- **v7.12** — 选歌录音 MVP (/sing/:songId + WS song_id + vocal_range) + BDD 基建修复 (vocals.wav 数据 + animations/sing-song-select 迁移 Vue 3 + KMP 崩溃修复) + dl_services 死代码清理 (2026-08-06)
- **v7.11** — 评分权重可配置: ScoringWeights 值对象 (单一来源) + 4 风格预设 + 权重面板 + 纯前端重算; BDD 浏览器基建修复 (2026-08-04)
- **v7.10** — 标准歌曲库前端页面: 卡片网格 + 搜索/筛选 + 上传 + 删除 + 试听; 音频播放修复 (songs_dir) (2026-08-04)
- **v7.9** — 标准歌曲库后端 (DDD + TDD + BDD): songs 领域 + 4 CRUD API + database BDD (2026-08-02)
- **v7.8** — GNE 接入 (AROC=0.886) + GSAP 全站动效 + 前后端对齐 (2026-08-01)
- **v7.7** — audiofeat 生产启用 + Flag 系统桥接修复 + 前端收束 (2026-07-31)
- **v7.6** — P1/P2 修复 + Rubato/AttackSlope + Flask 绞杀者完成 + ABI 9参数模型 + 文献权重对齐 (2026-07-31)
- **v7.5** — P1-2b 音色八维剖面 + P0 评分异常修复 (2026-07-29)
- **v7.4** — 评分算法 P0/P1 修复：CPPS + ZCR/Centroid + 颤音 fallback + 肌肉五维代理 (2026-07-28)
- **v7.3** — audiofeat 评分闭环 + Comparison DDD + 安全修复 (2026-07-27)
- **v7.2** — audiofeat 增强特征提取 (22 特征) (2026-07-26)
- **v7.1** — DDD 绞杀者内移完成 + 前后端对齐 (2026-07-24)
- **v7.0** — FastAPI + Vue 3 + Element Plus 全栈重构 (2026-07-22)
- **v5.x** — 旧版 (Flask + Vanilla JS + PyQt5)

## 许可证

MIT License
