# 声乐评估系统 - 淡色版

基于 Flask 的本地 Web 应用，提供音频评估、实时录音、比对分析等功能。

## 功能特性

### 核心功能
- **六维评分** - 音准(13%)/节奏(12%)/气息(22%)/发声技术(25%)/肌肉力量(15%)/艺术表现(13%) + 音色加减分
- **双评估模式** - 快速评估(~30秒) / 专业评估(~2-5分钟)
- **实时可视化** - 波形、频谱、音量实时显示
- **人声质量检测** - 自动识别非人声音频
- **三特征可视化** - 频谱图、基音轨迹、能量曲线
- **音色分析** - 明亮度、厚度、鼻音、气声分析
- **逐句评分** - 按乐句分段评分（专业模式）
- **人声分离** - Demucs 模型分离伴奏与人声
- **对比分析** - 独立页面，支持上传模式和实时录音模式
- **实时音高检测** - YIN 算法前端实时音高检测
- **录音功能** - 实时录音并分析
- **成长曲线** - 历史评分趋势图
- **导出报告** - PDF/图片格式报告

### 对比分析功能

独立对比分析页面 (`/compare.html`)，提供两种评估模式：

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
| 基础评分 | ✓ 五维评分 | ✓ 五维评分 |
| 评分配置 | 宽松阈值 | 标准阈值 |
| 分数范围 | 60-90分(平滑) | 0-100分 |
| 逐句评分 | ✗ | ✓ |
| 音色分析 | ✗ | ✓ |
| 可视化图表 | ✗ | ✓ |
| DL质量评估 | ✗ | ✓ |
| 音乐风格分析 | ✗ | ✓ |
| 适用场景 | 快速练习反馈 | 详细问题诊断 |

### 技术特点
- **纯离线运行** - 无需联网，保护隐私
- **安全加固** - 路径遍历防护、XSS防护
- **大文件支持** - 10MB+ 音频文件处理
- **中文支持** - 完整的中文文件名支持
- **前端音高检测** - YIN 算法实时检测，无需后端

## 快速开始

### 环境要求
- Python 3.8+
- conda 环境: pytorch2

### 启动服务
```bash
cd "C:\Users\jack\Desktop\临时文件\声乐\vocal_assessment_light"
C:/Users/jack/anaconda3/envs/pytorch2/python.exe web_app.py
```

### 访问地址
- 本地: http://localhost:5000
- 局域网: http://<your-ip>:5000
- 对比分析: http://localhost:5000/compare.html

## 项目结构

```
vocal_assessment_light/
├── api/                  # API 层 (Flask 蓝图)
│   ├── routes/           # 路由定义
│   └── business/         # 业务逻辑
│       └── audio_comparison.py  # 对比分析 + 相对评分
├── services/             # 服务层 (业务逻辑)
│   └── dl_services/      # 深度学习服务
│       └── model_manager/  # 模型管理模块
├── repositories/         # 数据层 (仓储模式)
├── config/               # 配置管理
├── core/                 # 核心算法
│   └── workers/          # 后台任务模块
│       ├── signals.py    # Qt 信号定义
│       ├── cache.py      # 音频缓存
│       ├── audio_loader.py   # 音频加载任务
│       ├── assessment_task.py # 评估任务
│       ├── emotion_analyzer.py # 情绪分析
│       └── manager.py    # 线程管理器
├── web/static/           # 前端资源
│   ├── compare.html      # 对比分析页面
│   └── js/
│       ├── compare.js    # 对比页面主逻辑
│       └── modules/
│           ├── pitch-detector.js      # YIN 音高检测
│           └── realtime-compare.js    # 实时录音对比
├── tests/                # 测试代码
├── web_app.py            # 应用入口
└── PROJECT_STATUS.md     # 项目状态文档
```

## API 接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/upload` | POST | 上传并分析音频，支持 `mode` 参数: `quick`(快速) / `professional`(专业) |
| `/api/analyze` | POST | 分析已存在音频 |
| `/api/compare` | POST | 对比分析两个音频，支持 JSON 和 FormData |
| `/api/separate` | POST | 人声分离 |
| `/api/report` | POST | 生成报告 |
| `/api/history` | GET | 获取历史记录 |
| `/api/audio` | GET | 获取音频文件 |

### 上传接口参数

```
POST /api/upload
Content-Type: multipart/form-data

参数:
- file: 音频文件 (必需)
- mode: 评估模式 (可选，默认: quick)
  - quick: 快速评估，跳过逐句评分、音色分析、可视化
  - professional: 专业评估，完整分析
```

### 对比分析接口

```
POST /api/compare
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

### E2E 测试
```bash
pytest tests/e2e/ -v
```

### 单元测试
```bash
pytest tests/unit/ -v
```

## 版本历史

- **v7.5** - P1-2b 音色八维剖面 + P0 评分异常修复 (Artistry F0 CV / Technique HNR 单调 / CPPS-HF 解耦 / Muscle 校准)
- **v7.4** - 评分算法 P0/P1 修复：CPPS 主特征 + ZCR/Centroid 咬字 + 颤音 fallback + 权重新分配 + 音色门控修复 + 肌肉五维代理
- **v7.3** - audiofeat 评分闭环 + Comparison DDD + 安全修复 + BDD 增强
- **v7.2** - audiofeat 增强特征提取 (22 特征)
- **v7.1** - DDD 绞杀者内移完成 (13/13 模块自包含)
- **v7.0** - FastAPI + Vue 3 + Element Plus 全栈重构
- **v5.9** - 逐句评分大幅优化：阈值放宽、最低分提升、音准+13.8分
- **v5.8** - P0问题修复：API 415错误、录音功能、DTW对齐引擎
- **v5.4.1** - 代码架构重构：模块化拆分 workers/model_manager，修复索引越界bug
- **v5.4** - 对比分析页面重构：双音频并排布局、E2E测试完善
- **v5.3.1** - Flask 3.x JSON序列化修复，NumPy类型支持
- **v5.3** - 对比分析重构：独立页面、实时录音模式、YIN 音高检测
- **v5.2** - 快速模式性能优化(~33秒)，评分公正性改进
- **v5.1** - 风格自适应评分系统
- **v5.0** - 深度学习集成 + 快速/专业评估模式
- **v4.0** - 评分系统 V4（自适应评分）
- **v3.6** - 安全加固与稳定性修复
- **v3.5** - 前端页面分离重构
- **v3.4** - 评分系统重构（扣分制）
- **v3.3** - 专业评估增强
- **v3.2** - 人声分离
- **v3.1** - 架构重构 + 功能增强
- **v3.0** - 离线版完整实现

## 许可证

MIT License
