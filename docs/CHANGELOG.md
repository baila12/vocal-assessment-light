# 更新日志

## v5.9 - 逐句评分优化 (2026-05-10)

### 问题修复

#### 逐句评分分数偏低问题

**问题描述**：专业评估模式下逐句评分分数普遍偏低，尤其是音准和情绪维度。

**根因分析**：
1. 音准评分使用相对标准差阈值过严，把"音高变化幅度"误判为"音准差"
2. 演唱中的转音、滑音会导致高 relative_std（30%-50%），这是正常的音乐表达
3. 节奏评分对稳定节奏惩罚
4. 气息和情绪评分最低分过低

**解决方案**：

##### 1. 音准评分阈值大幅放宽
```python
# 修复前
PITCH_THRESHOLD_EXCELLENT = 0.08   # 8%
PITCH_THRESHOLD_GOOD = 0.20        # 20%
PITCH_MIN_SCORE = 50.0

# 修复后
PITCH_THRESHOLD_EXCELLENT = 0.12   # 12%
PITCH_THRESHOLD_GOOD = 0.30        # 30%
PITCH_THRESHOLD_FAIR = 0.50        # 50%
PITCH_MIN_SCORE = 60.0             # 最低分提升到60
```

##### 2. 节奏评分优化
```python
RHYTHM_STABLE_MIN = 75.0  # 稳定节奏最低75分
```

##### 3. 气息评分优化
```python
BREATH_THRESHOLD_EXCELLENT = 0.10  # 从8%放宽到10%
BREATH_MIN_SCORE = 60.0            # 最低分提升到60
```

##### 4. 情绪评分重构
```python
EMOTION_BASE_SCORE = 70.0          # 基准分提升到70
EMOTION_MIN_SCORE = 60.0           # 最低分提升到60
```

##### 5. 音量评分优化
```python
VOLUME_MIN_SCORE = 60.0            # 最低分提升到60
```

### 效果对比

| 音频 | 维度 | 修复前 | 第一轮 | 第二轮 | 总改进 |
|------|------|--------|--------|--------|--------|
| 恋人 | 音准 | 66.1 | 73.2 | **79.9** | +13.8 |
| 恋人 | 情绪 | 69.2 | 69.8 | **73.9** | +4.7 |
| 恋人 | 总分 | 78.4 | 81.7 | **84.4** | +6.0 |
| 手写的从前 | 音准 | 56.2 | 63.3 | **74.0** | +17.8 |
| 手写的从前 | 情绪 | 61.9 | 68.7 | **73.1** | +11.2 |
| 手写的从前 | 总分 | 73.2 | 77.6 | **81.7** | +8.5 |

### 修改文件

- `services/phrase_service.py` - 评分算法优化

### 测试验证

```
单元测试: 79/79 通过
真实音频测试: 恋人.mp3, 手写的从前.mp3 验证通过
```

---

## v5.8 - P0问题修复 (2026-05-10)

### Bug修复

#### 1. 对比分析API 415错误
- **问题**: FormData方式上传时，直接访问 `request.json` 触发Flask的JSON解析，由于Content-Type不是application/json，抛出415错误
- **解决方案**: 使用 `request.is_json` 检查后再调用 `request.get_json(silent=True)`
- **修改文件**: `api/routes/upload.py`

```python
# 修复前
if request.json and isinstance(request.json, dict):
    style = request.json.get('style', 'pop')

# 修复后
style = 'pop'
if request.is_json:
    try:
        json_data = request.get_json(silent=True)
        if json_data and isinstance(json_data, dict):
            style = json_data.get('style', 'pop')
    except Exception:
        pass
elif request.form:
    style = request.form.get('style', 'pop')
```

#### 2. 首页录音安全上下文判断修复
- **问题**: 原条件 `!window.isSecureContext && hostname !== 'localhost'` 逻辑有误，某些浏览器在localhost上 `isSecureContext` 可能为false
- **解决方案**: 显式检查 hostname 是否为 localhost/127.0.0.1/[::1]
- **修改文件**: `web/static/js/modules/recording.js`

```javascript
const isLocalhost = location.hostname === 'localhost' || location.hostname === '127.0.0.1' || location.hostname === '[::1]';
const isSecure = window.isSecureContext || isLocalhost;
if (!isSecure) {
    showToast('录音功能需要 HTTPS 或 localhost 环境', 'error');
}
```

#### 3. 实时录音模块初始化修复
- **问题**: `RealtimeCompare` 构造函数参数未设置默认值，`init()` 方法缺少错误处理和readyState检查
- **解决方案**: 添加默认参数，添加readyState检查和错误事件监听
- **修改文件**: `web/static/js/modules/realtime-compare.js`, `web/static/js/compare.js`

```javascript
// 构造函数添加默认参数
constructor(standardAudioData = {}) { ... }

// init() 添加readyState检查
async init(audioElement, standardUrl) {
    // ...
    await new Promise((resolve, reject) => {
        this.standardAudioElement.addEventListener('loadedmetadata', resolve, { once: true });
        this.standardAudioElement.addEventListener('error', reject, { once: true });
        if (this.standardAudioElement.readyState >= 1) {
            resolve();
        }
    });
}
```

### 测试验证

```
单元测试: 43/43 通过
API测试:
- Upload API: Score 86.3 (正常)
- Compare API: Score 94.1, Pitch Match 100%, Rhythm Match 100% (正常)
```

---

## v5.3.1 - Flask 3.x JSON序列化修复 (2026-04-29)

### Bug修复

#### NumPy类型JSON序列化问题
- **问题**: Flask 3.x 不支持 `JSON_ENCODER` 配置，导致 numpy 类型无法序列化
- **错误**: `TypeError: Object of type float32 is not JSON serializable`
- **解决方案**: 创建 `NumpyJSONProvider` 继承 `DefaultJSONProvider`
- **修改文件**: `api/__init__.py`

```python
class NumpyJSONProvider(DefaultJSONProvider):
    """自定义 JSON 提供器，支持 numpy 类型"""
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        return super().default(obj)
```

#### 对比分析API参数名修正
- **问题**: 前端使用 `teacher_audio/student_audio`，后端期望 `file/standard_file`
- **解决方案**: 统一使用 `file` (用户音频) + `standard_file` (标准音频)

### 测试验证

```
API测试结果:
- Upload API: Score 86.3 (正常)
- Compare API: Score 88.0, Pitch Match 100%, Rhythm Match 70% (正常)
- Health Check: 所有检查项通过
```

---

## v5.3 - 对比分析重构 (2026-04-29)

### 新功能

#### 独立对比分析页面
- **独立页面**: 对比分析从首页 tab 改为独立页面 `/compare.html`
- **三步流程**: 导入标准音频 → 选择模式 → 查看结果
- **两种评估模式**:
  - **上传模式**: 导入用户音频与标准音频对比
  - **实时录音模式**: 类似全民K歌的实时反馈体验

#### 实时音高检测 (前端)
- **YIN 算法**: 前端实时音高检测，无需后端处理
- **实时音分偏差**: 显示当前音高与标准音高的偏差（+/- 音分）
- **实时调整建议**: "略高，请降低一点" / "偏低，需要提高"
- **实时评分**: 录音过程中实时更新评分
- **音高曲线对比**: Canvas 绘制标准 vs 用户音高曲线

#### 基于标准音频的相对评分
- **音准匹配率**: 用户音高与标准音高的匹配程度 (0-100%)
- **节奏匹配率**: 基于能量包络相似度计算 (0-100%)
- **综合评分**: 音准 60% + 节奏 40% 权重
- **等级评定**: 优秀/良好/中等/及格/需改进
- **诊断建议**: 自动生成改进方向建议

### API 更新

#### `/api/compare` 接口增强
- 支持 FormData 上传 (file + standard_file)
- 支持 JSON 方式 (filepath 参数)
- 返回相对评分结果

```python
# FormData 方式
POST /api/compare
Content-Type: multipart/form-data
- file: 用户音频
- standard_file: 标准音频

# 返回
{
  "success": true,
  "data": {
    "score": 85,
    "level": "良好",
    "pitch_match_rate": 88.5,
    "rhythm_match_rate": 82.3,
    "avg_cents_error": 15.2,
    "diagnosis": ["音准表现优秀...", "整体偏高..."]
  }
}
```

### 新增文件

| 文件 | 说明 |
|------|------|
| `web/static/compare.html` | 独立对比分析页面 |
| `web/static/js/compare.js` | 对比页面主逻辑 |
| `web/static/js/modules/pitch-detector.js` | YIN 音高检测算法 |
| `web/static/js/modules/realtime-compare.js` | 实时录音对比模块 |

### 修改文件

| 文件 | 变更 |
|------|------|
| `web/static/index.html` | 对比分析 tab 改为页面链接 |
| `api/routes/upload.py` | `/compare` 接口支持 FormData |
| `api/business/audio_comparison.py` | 新增 `calculate_relative_score` 等函数 |

### 技术亮点

- **前端 YIN 算法**: 纯 JavaScript 实现音高检测
- **实时反馈**: requestAnimationFrame 驱动的实时 UI 更新
- **Web Audio API**: AudioContext + AnalyserNode + MediaRecorder
- **音分计算**: 1200 * log2(freq2/freq1) 精确计算音分偏差

---

## v5.0 - 深度学习集成 & 双评估模式 (2026-04-22)

### 新功能

#### 双评估模式
- **快速评估** (默认): 约30秒完成，适合日常练习反馈
  - 基础五维评分 (音量/音准/节奏/气息/情绪)
  - 人声质量检测
  - 基础建议生成

- **专业评估**: 约2-5分钟，适合详细问题诊断
  - 完整五维评分 + 详细诊断
  - 逐句评分 (每句独立评分和建议)
  - 音色分析 (明亮度/厚度/鼻音/气声)
  - 可视化图表 (频谱图/音高轨迹/能量曲线)

#### API 更新
- `/api/upload` 接口新增 `mode` 参数
  - `mode=quick`: 快速评估 (默认)
  - `mode=professional`: 专业评估

### 性能优化

#### 逐句评分多线程并行
- 使用 `ThreadPoolExecutor` 并行处理多个乐句
- 预计算 f0 数据复用，避免重复计算
- 逐句评分速度提升 2-3 倍

#### 评分算法优化
- 音量评分: 优化归一化范围 (0.02-0.15 RMS)
- 音准评分: 使用相对标准差，合理波动不惩罚
- 节奏评分: 基于变异系数评估节奏感
- 气息评分: 基于相对变化率评估稳定性
- 分数范围: 60-90 分 (更合理的分布)

### 代码变更

#### 新增文件
- `CHANGELOG.md` - 版本变更记录

#### 修改文件
- `api/routes/upload.py` - 添加 mode 参数支持
- `api/business/audio_analysis.py` - 实现快速/专业模式分支
- `services/phrase_service.py` - 多线程并行评分 + 评分算法优化
- `README.md` - 更新功能说明和 API 文档
- `docs/DEEP_LEARNING_PLAN.md` - 添加性能优化策略

### 兼容性

- 向后兼容: 不传 `mode` 参数时默认使用快速模式
- 前端需要更新以支持模式选择 UI

---

## v4.0 - 评分系统 V4 (2026-04-20)

### 改进
- 自适应评分系统
- 风格识别集成
- 深度学习质量评估 (MOS 分数)

---

## v3.6 - 安全加固 (2026-04-18)

### 改进
- 路径遍历防护
- XSS 防护
- 文件名安全处理
