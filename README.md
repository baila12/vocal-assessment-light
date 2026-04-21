# 声乐评估系统 - 淡色版

基于 Flask 的本地 Web 应用，提供音频评估、实时录音、比对分析等功能。

## 功能特性

### 核心功能
- **音频分析** - 五维评分（音量/音准/节奏/气息/情绪）
- **实时可视化** - 波形、频谱、音量实时显示
- **人声质量检测** - 自动识别非人声音频
- **三特征可视化** - 频谱图、基音轨迹、能量曲线
- **音色分析** - 明亮度、厚度、鼻音、气声分析
- **逐句评分** - 按乐句分段评分
- **人声分离** - Demucs 模型分离伴奏与人声
- **对比分析** - 与标准音频对比评分
- **录音功能** - 实时录音并分析
- **成长曲线** - 历史评分趋势图
- **导出报告** - PDF/图片格式报告

### 技术特点
- **纯离线运行** - 无需联网，保护隐私
- **安全加固** - 路径遍历防护、XSS防护
- **大文件支持** - 10MB+ 音频文件处理
- **中文支持** - 完整的中文文件名支持

## 快速开始

### 环境要求
- Python 3.8+
- conda 环境: pytorch1

### 启动服务
```bash
cd "C:\Users\jack\Desktop\临时文件\声乐\vocal_assessment_light"
C:/Users/jack/anaconda3/envs/pytorch1/python.exe web_app.py
```

### 访问地址
- 本地: http://localhost:5000
- 局域网: http://<your-ip>:5000

## 项目结构

```
vocal_assessment_light/
├── api/                  # API 层 (Flask 蓝图)
├── services/             # 服务层 (业务逻辑)
├── repositories/         # 数据层 (仓储模式)
├── config/               # 配置管理
├── core/                 # 核心算法
├── web/static/           # 前端资源
├── tests/                # 测试代码
├── web_app.py            # 应用入口
└── PROJECT_STATUS.md     # 项目状态文档
```

## API 接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/upload` | POST | 上传并分析音频 |
| `/api/analyze` | POST | 分析已存在音频 |
| `/api/separate` | POST | 人声分离 |
| `/api/report` | POST | 生成报告 |
| `/api/history` | GET | 获取历史记录 |
| `/api/audio` | GET | 获取音频文件 |

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

- **v3.6** - 安全加固与稳定性修复
- **v3.5** - 前端页面分离重构
- **v3.4** - 评分系统重构（扣分制）
- **v3.3** - 专业评估增强
- **v3.2** - 人声分离
- **v3.1** - 架构重构 + 功能增强
- **v3.0** - 离线版完整实现

## 许可证

MIT License
