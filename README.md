# 声乐评估系统 v7.9

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
- **标准歌曲库** - 上传/浏览/搜索/筛选参考歌曲，支持重复检测 (v7.9)
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
│   │   ├── assessment/   # 7 scorers (六维+音色)
│   │   ├── audio/        # 10 特征提取模块
│   │   ├── comparison/   # 对比分析领域
│   │   └── songs/        # 歌曲库领域 (v7.9)
│   ├── application/      # 编排层
│   ├── infrastructure/   # 基础设施 (SQLite 仓储)
│   ├── interfaces/       # API + WebSocket
│   └── main.py           # 应用入口 (:8000)
├── frontend/             # Vue 3 + Element Plus SPA
│   └── src/views/        # 5 页面 (Home/Report/History/Compare/Sing)
├── api/business/         # 共享业务逻辑 (audio_analysis)
├── services/             # 服务层
│   └── dl_services/      # 深度学习 (style/VAD/DTW)
├── docs/                 # 文档 (产品/技术/质量/流程)
└── tests/                # 475 tests (unit 406 + integration 33 + extended 36)
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
| `/api/v1/history` | GET/POST/DELETE | 历史记录 CRUD |
| `/api/v1/songs` | POST/GET/GET/DELETE | 歌曲库管理 (v7.9) |
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
```

### 对比分析接口

```
POST /api/v1/compare
Content-Type: multipart/form-data

参数:
- file: 用户音频文件 (必需)
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
pytest tests/unit/domain/ tests/unit/infrastructure/ tests/unit/test_middleware.py tests/unit/test_ddd_alignment.py tests/unit/test_ddd_extraction_flag.py tests/unit/test_flag_bridge.py -v

# 集成测试
pytest tests/integration/ -v

# 扩展测试
pytest tests/extended/ -v

# 前端测试
cd frontend && npx vitest run
```

## 版本历史

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
- **v5.x** — 旧版 (Flask + Vanilla JS + PyQt5), 详见 [CHANGELOG](docs/4-process/CHANGELOG.md)

## 许可证

MIT License
