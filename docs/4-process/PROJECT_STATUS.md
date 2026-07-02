# 项目状态

> 更新: 2026-06-05 | 当前版本: **v5.17** | 下一版本: **v5.18**

---

## 运行

```bash
conda activate pytorch2
python web_app.py
# http://localhost:5000
```

**技术栈**: Flask 3.0 | librosa | PyTorch | Demucs | Chart.js | pytest | Playwright

---

## 三模式现状

| 模式 | 触发方式 | CPU 耗时 | GPU 耗时 | 适用场景 |
|------|---------|----------|----------|---------|
| **Quick** | `/api/upload?mode=quick` | ~15-20s | ~15-20s | 快速练习反馈 |
| **Professional** | `/api/upload?mode=professional` | ~130-170s | ~30-50s | 详细问题诊断 |
| **Compare (DTW)** | `/api/compare` 或自动搜索 | ~45s | ~45s | 参考对比评分 |

> ⚠️ 当前 PyTorch 为 CPU 版。安装 CUDA 版后 Pro 模式可快 3-4×。`/health` 端点可查看 GPU 状态。

---

## 真实音频测试结果

### Quick 模式基线 (v5.17)

| 音频 | 总分 | 音准 | 节奏 | 气息 | 技巧 | 艺术 |
|------|------|------|------|------|------|------|
| 恋人（高分） | **74.8** | 79.6 | 77.1 | 56.4 | 84.0 | 75.9 |
| 手写的从前（高分） | **73.4** | 80.8 | 66.6 | 66.4 | 77.6 | 73.2 |
| 1（高分） | **72.7** | 80.7 | 66.8 | 63.2 | 77.5 | 72.6 |
| 音频-3分26秒(高分) | **72.6** | 79.3 | 71.9 | 52.6 | 84.0 | 73.8 |
| 陈奕迅难听之声（低分） | **48.8** | 75.9 | **2.5** | 51.2 | 57.5 | 46.2 |
| 白噪声 | **0.0** | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

**高分均值 73.4 vs 低分 48.8 — 区分度 24.6 分。**

### Quick vs Pro 一致性 (v5.17)

| 音频 | Quick | Pro | 差距 | Pro Demucs |
|------|-------|-----|------|-----------|
| 恋人（高分） | 74.8 | 73.7 | -1.1 | ✅ |
| 1（高分） | 72.7 | 75.0 | +2.3 | ✅ |
| 手写的从前（高分） | 73.4 | 79.1 | +5.7 | 跳过(纯人声) |
| 音频-3分26秒(高分) | 72.6 | 76.4 | +3.8 | ✅ |
| 陈奕迅（低分） | 48.8 | 48.8 | 0.0 | 跳过(纯人声) |

**Quick/Pro 总分离散 < 6 分 — 一致性良好。**

---

## 已完成功能 (按版本)

| 版本 | 日期 | 核心变更 |
|------|------|---------|
| v5.17 | 06-04 | 混合音频检测修复 (阈值0.35→0.25) + GPU加速 + 合成音频归零验证 |
| v5.16 | 06-03 | Pro Breath 修复: is_clean_vocal标记传递链 → 9.8→56.3 (+474%) |
| v5.15 | 06-03 | Pro Rhythm CV重校准 + SingMOS移除 + DTW自动搜索 + 自参照一致性 |
| v5.14 | 06-03 | 音准多指标体系 + 艺术评分重构 (区分度 0.3→28.4) |
| v5.13 | 06-03 | Sigmoid+硬上限移除 → 区分度恢复 + Demucs CV映射修复 |
| v5.12 | 06-03 | 安全加固 + DL清理(-654行) + 评分统一 + 算法校准 + 魔法数字集中化 |
| v5.11 | 06-02 | 评分区分度(0-100全范围) + Demucs管线修复 + 节奏CV分段 |
| v5.10 | 05-26 | DTW参考评分融合 + 自参照DTW + 响度归一化 |

详细变更见 [CHANGELOG.md](CHANGELOG.md)。

---

## 已知问题

### P0 (严重) — 全部已修复 ✅

| 问题 | 版本 | 效果 |
|------|------|------|
| Pro 节奏崩塌 (18.6 vs Quick 77.1) | ✅ v5.15 | 18.6→66.0 (+255%) |
| SingMOS 严重跨域 (低分>高分) | ✅ v5.15 | 移除，自参照一致性替代 |
| DTW 参考评分未默认化 | ✅ v5.15 | 独立上传自动搜索 |
| Pro Breath 崩塌 (9.8 vs Quick 56.4) | ✅ v5.16 | 9.8→56.3 (+474%) |

### P1 (功能缺陷) — 4 项待处理

| 问题 | 说明 | 计划 |
|------|------|------|
| **气息评分区分度偏窄** | 高分 53-66 vs 低分 51 (仅 5-15 分) | 校准数据集 (v6.0) |
| **音准评分区分度偏窄** | 高分 79-81 vs 低分 76 (仅 3-5 分) | DTW 可缓解 + 校准 |
| **23 个经验参数未校准** | 全部 [经验估计], 0 个 [实验校准] | 校准数据集 (v6.0) |
| **Pro 模式耗时过长** | CPU ~130-170s (Demucs 占 ~80%) | GPU 加速已就绪 (v5.17) |

### P2 (优化) — 5 项待处理

| 问题 | 说明 |
|------|------|
| f0 节奏路径待恢复 | v5.13 回退到 f0=None，需校准验证后启用 |
| 技巧检测仅 3 种 | 颤音/滑音/假声 vs 论文 7-15 种 |
| 无混响补偿 | 不同录音环境 HNR/CPP 不可比 |
| 音量维度未独立 | 与 Breath 合并，缺独立 SPL 评估 |
| 核心/服务层代码重叠 | legacy 模块待清理 |

---

## 下一版本: v5.18 计划

### 阶段一: 开源算法移植 (P1)

| # | 任务 | 来源 | Feature Flag |
|---|------|------|-------------|
| 1 | 多尺度 HNR (短/中/长窗 + 稳定性) | de Krom 1993 (VoiceLab) | `enable_multiscale_hnr` |
| 2 | Praat CPP (parselmouth 替换手动FFT倒谱) | VoiceLab | `enable_praat_cpp` |
| 3 | Voicing detection 评估 (recall/FA) | pitch-benchmark | `enable_voicing_detection` |
| 4 | TorchCREPE 备选接入 (PYIN 降级时) | CREPE_MIR-1K | `enable_torchcrepe_fallback` |

### 阶段二: Feature Flag 机制 (P1)

```python
@dataclass
class FeatureFlags:
    enable_dtw_reference_search: bool = True
    enable_self_consistency: bool = True
    enable_multiscale_hnr: bool = False
    enable_praat_cpp: bool = False
    enable_torchcrepe_fallback: bool = False
    enable_voicing_detection: bool = False
```

### 阶段三: 验证 (P1)

- 三模式一致性测试 (Quick/Pro/Compare)
- DTW 参考搜索功能测试
- 全量回归测试 (目标 ≥ 95% 通过率)
- 真实音频 Quick + Pro 验证

---

## 后续路线图

### v6.0: 校准数据集 + 六维评分

| 任务 | 优先级 | 工作量 |
|------|--------|--------|
| 3×3 对照数据集 (3首歌 × 3水平) | P0 | 2天 |
| 校准工具脚本 + 校准报告 | P0 | 2天 |
| 优先校准: CV断点, Breath基线, Artistry上限 | P0 | 1天 |
| 音量维度独立 (六维评分) | P1 | 2天 |
| 混响补偿 (HPSS+谱减法) | P1 | 2天 |
| f0 节奏路径恢复 (校准验证后) | P1 | 1天 |

### v6.1+: 算法增强

| 任务 | 优先级 |
|------|--------|
| SVQTD 7属性分类器接入 | P2 |
| ECAPA-TDNN 音色分析 (明亮度/厚度) | P2 |
| 歌曲模板系统 | P2 |

---

## 性能基准

### 端到端模式性能

| 指标 | v5.15 | v5.16 | v5.17 | v5.18 目标 |
|------|-------|-------|-------|-----------|
| Quick 耗时 | ~40s | ~15-20s | ~15-20s | < 30s ✅ |
| Pro 耗时 (CPU) | ~226s | ~130-170s | ~130-170s | < 180s (已达) |
| Pro 耗时 (GPU) | — | — | ~30-50s | < 60s ✅ |
| 内存峰值 (Quick) | ~800MB | ~800MB | ~800MB | < 400MB |
| 内存峰值 (Pro) | ~1.2GB | ~1.2GB | ~1.2GB | < 800MB |
| 首次启动 | ~8s | ~8s | ~8s | < 10s ✅ |

### 特征提取阶段耗时 (3min 音频, 44.1kHz)

| 特征提取器 | v5.17 实际 | 预算 | 状态 |
|-----------|-----------|------|------|
| voice_quality | ~1.5s | < 2s | ✅ |
| PYIN f0 | ~5-7s | < 8s | ✅ |
| onset strength | ~2-3s | < 3s | ✅ |
| HNR + CPP | ~2-3s | < 3s | ✅ |
| RMS + breath 四维度 | ~1-2s | < 2s | ✅ |
| technique 检测 | ~2-3s | < 3s | ✅ |
| acoustic 混合检测 | ~0.5s | < 1s | ✅ |
| 自参照一致性 | ~0.5s | < 1s | ✅ |
| 评分计算 | ~0.5s | < 1s | ✅ |
| Phrase 逐句 | ~3-5s | < 5s | ✅ |
| Visualization | ~6-8s | < 10s | ✅ |
| Demucs (CPU) | ~100-130s | < 140s | ✅ |
| Demucs (GPU) | — (无GPU) | < 30s | ⏳ 需重装 CUDA 版 PyTorch |

### 前端性能

| 指标 | v5.17 实际 | 目标 | 状态 |
|------|-----------|------|------|
| FCP (首屏) | ~1.8s (未优化) | < 1.5s | ⏳ |
| TBT | ~300ms (inline styles) | < 200ms | ⏳ |
| 路由切换 | ~200ms (含旧 CSS 动画) | < 300ms (含 GSAP) | ✅ |
| GSAP 动画帧率 | — (未测量) | ≥ 30fps | ⏳ 待测量 |
| Canvas 实时绘制 | — (未启用) | ≥ 30fps | ⏳ v6.0 |
| JS Bundle | ~280KB (未 gzip) | < 300KB gzip | ⚠️ 需确认 |
| CSS 总体积 | ~45KB (含 inline) | < 50KB gzip | ⚠️ inline style 过多 |

### 模式一致性

| 指标 | v5.15 | v5.16 | v5.17 | 目标 |
|------|-------|-------|-------|------|
| Quick/Pro Rhythm 差 | -11.1 | -4.4 | -4.4 | < 5 ✅ |
| Quick/Pro Breath 差 | -46.6 | **-0.1** | **-0.1** | < 5 ✅ |
| Quick/Pro Total 差 | -12.5 | -1.1 | -1.1 | < 10% ✅ |
| 单元+集成测试 | 78/79 | 89/91 | 89/91 (98%) | ≥ 95% |

### 未测量指标 (v5.18 待建立)

| 指标 | 计划测量方式 |
|------|------------|
| 内存泄漏 (连续 10 次 Pro) | `tracemalloc` diff |
| DTW 对齐耗时 vs 音频长度 | 基准音频 × 3 个长度 |
| 文件上传吞吐 | 50MB 文件计时 |
| 历史记录查询 (1000条) | JSON 反序列化计时 |
| 报告 PDF 生成 (含图表) | `time.perf_counter()` |
| 前端动画帧率 | Chrome DevTools Performance |
| 长时间使用内存 | 30min + 50次页面切换 |

---

## 验收状态

```
✅ 非人声检测归零 (白噪声 → 0分, 10/10)
✅ 合成音频归零验证
✅ 评分区分度 0-100 全范围
✅ 艺术评分区分度 28.4 分 (v5.14)
✅ Quick/Pro Total 分差 < 10%
✅ Quick/Pro Breath 分差 < 5
✅ Quick/Pro Rhythm 分差 < 5
✅ SingMOS 完全移除 (v5.15)
✅ DTW 参考搜索默认化 (v5.15)
✅ Pro Rhythm 崩塌修复 (v5.15)
✅ Pro Breath 崩塌修复 (v5.16)
✅ 混合音频检测 (轻伴奏) (v5.17)
✅ GPU 加速支持 (v5.17)
⏳ Feature Flag 机制 (v5.18)
⏳ 多尺度 HNR (v5.18)
⏳ Praat CPP (v5.18)
⏳ 单元测试覆盖率 ≥ 80%
⏳ Pro 模式 CPU < 120s (受 Demucs 硬件限制)
⏳ 气息区分度 ≥ 20 (需校准数据集)
⏳ 音准区分度 ≥ 10 (DTW + 校准)
```

---

## 参考文档

| 文档 | 路径 |
|------|------|
| 产品需求文档 | [PRD.md](../1-product/PRD.md) |
| 产品目标 | [GOALS.md](../1-product/GOALS.md) |
| 系统架构 | [ARCHITECTURE.md](../2-technical/ARCHITECTURE.md) |
| 评分算法 | [SCORING.md](../2-technical/SCORING.md) |
| TDD 规范 | [TDD.md](../3-quality/TDD.md) |
| BDD 规范 | [BDD.md](../3-quality/BDD.md) |
| 变更日志 | [CHANGELOG.md](CHANGELOG.md) |
