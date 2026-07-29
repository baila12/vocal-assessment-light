# 项目状态

> 更新: 2026-07-29 | 版本: **v7.5** | 分支: `feat/v7-fastapi-vue-refactor`

---

## 一、架构

```
Vue 3 SPA (frontend/dist/)  →  FastAPI (:8000)  ←  Flask /old (绞杀者)
                                      │
    ┌─────────────────────────────────┼──────────────────────────┐
    │  backend/ (DDD 四层)            │  旧服务层 (残留)           │
    │  domain/assessment/ (7 scorers) │  services/features/ (2) ⚠│
    │  domain/audio/ (13 模块自包含)   │  services/dl_services/ (11)│
    │  domain/comparison/ (v7.3)      │  services/audio_service.py │
    │  application/ (orchestrator)    │  api/business/ (bridge)   │
    │  infrastructure/audio/ (4)      │  api/routes/ (Flask, 残留)│
    │  interfaces/api/ + ws/          │  api/routes/rate_limit    │
    │  shared/ (EventBus, math_utils) │                           │
    └─────────────────────────────────┴──────────────────────────┘
```

### 评分路径 (v7.5: DDD 唯一路径 + audiofeat 增强 + P0/P1 修复)

| 路径 | 特征提取 | 评分 | 状态 |
|------|---------|------|:----:|
| **DDD 原生** | `DddFeatureExtractionOrchestrator` → 13 自包含模块 | `ScoringOrchestrator.calculate_ddd()` + audiofeat | ✅ 生产 |
| V4 回退 | `ScoreServiceV4` (五维) | — | ❌ v7.1.4 已移除 |

### v7.4 六维权重新分配 (v7.5 保持)

| 维度 | 旧权重 | 新权重 | 变化 | 说明 |
|------|:------:|:------:|:----:|------|
| Pitch (音准) | 10% | **13%** | +3% | 最可靠维度 (文献 A 级) |
| Rhythm (节奏) | 10% | **12%** | +2% | 中等可靠 (文献 B 级) |
| Breath (气息) | 20% | **22%** | +2% | 四子维度丰富 |
| Technique (发声技术) | 25% | **25%** | — | 咬字(50%) + 气声比(50%) |
| Muscle (肌肉力量) | 25% | **15%** | -10% | 文献建议降低启发式权重 |
| Artistry (艺术表现) | 10% | **13%** | +3% | 提升以激励 P0-3 修复效果 |
| **合计** | **100%** | **100%** | | |

### v7.5 评分算法改进

#### P1-2b: 音色八维剖面增强 (2026-07-29)

| 维度 | 声学基础 | 权重 | 评分函数 |
|------|---------|:--:|---------|
| Brightness (亮度) | Spectral Centroid | 12.5% | 单调 (亮=好) |
| Warmth (温暖度) | Harmonic Richness + Centroid + Flatness | 12.5% | 综合 |
| Nasality (鼻音) | Nasality Index | 12.5% | 反比 (高鼻音=低分) |
| Roughness (粗糙度) | Roughness + Inharmonicity | 12.5% | 反比 (高粗糙=低分) |
| **Hardness** 🆕 | Spectral Crest (2-5kHz) | 12.5% | 甜点曲线 7-11 |
| **Depth** 🆕 | Hammarberg Index + Spectral Slope | 12.5% | 单调 (深沉=好) |
| **Sharpness** 🆕 | Spectral Centroid / 4000 | 12.5% | 甜点曲线 1200-2800Hz |
| **Booming** 🆕 | Hammarberg ×0.6 + Richness ×0.4 | 12.5% | 综合 |

> P1-2b 仅在 `enable_audiofeat=True` 时激活。无 audiofeat 时保持三维护发式路径。

#### P0 评分异常修复 (2026-07-29)

| 编号 | 异常 | 根因 | 修复 | 影响 |
|:----:|------|------|------|------|
| **P0-1** | Artistry 区分度仅 1.8 分 | `pitch_cv` 传入颤音频率 Hz (5.0-8.0) 而非 F0 CV (0.01-0.20) | 在 orchestrator 中从真实 F0 数据计算 CV | Artistry 区分度 +26.4 pts |
| **P0-2** | Technique HNR>22 惩罚 | 语音病理阈值 (12-22dB) 不适用于歌声 (49-51dB) | HNR≥12 一律满分, 移除 >22 下降段 | 消除干净歌手系统倒扣 |
| **P0-3** | CPPS-HF 非单调区 | `hf_energy_ratio = cpp/5.0` 耦合, CPPS=3.5 得分高于 5.0 | HF 能量从真实频谱计算, 解耦 CPPS | 消除评分倒挂 |
| **P0-4** | Muscle formant/overtone 满分 | adapter→scorer 校准不匹配: 阈值 0.15/8 过低 | 重新校准 formant 阈值 (0.15→0.22), overtone 刻度 (计数→评分) | Muscle 区分度 +15.8 pts |

#### v7.4 评分算法改进 (2026-07-28, 保持不变)

| 编号 | 严重度 | 修复项 | 文件 | 状态 |
|:----:|:------:|--------|------|:----:|
| **P0-1** | CRITICAL | 气声比 CPPS 替代 HNR 主特征 (70%→25%, CPPS 40%) | `technique_scorer.py` | ✅ |
| **P0-2** | HIGH | 咬字接入 ZCR + Spectral Centroid + C-V 能量比 (Rathi & Hsu 2021) | `technique_scorer.py` + `technique_extractor.py` | ✅ |
| **P0-3** | HIGH | 无颤音 fallback (pitch_cv + dynamic_range, 上限 80) | `artistry_scorer.py` | ✅ |
| **P0-4** | HIGH | 肌肉权重 25%→15%，释放 10% 重新分配 | `value_objects.py` | ✅ |
| **P1-1** | MEDIUM | 肌肉五维代理重构 (MPT/Crest/SPR/F1-F2/Alpha) | `muscle_scorer.py` + `muscle_extractor.py` | ✅ |
| **P1-2a** | CRITICAL | 音色置信度门控修复 (旧 CPP→harmonic_stability 替代) | `timbre_extractor.py` + `timbre_adjuster.py` | ✅ |
| **P1-2b** | MEDIUM | 音色八维剖面增强 (hardness/depth/sharpness/booming) | `timbre_adjuster.py` | ✅ v7.5 |

### 安全中间件

| 中间件 | 层 | 配置 | 状态 |
|--------|-----|------|:--:|
| SecurityHeadersMiddleware | FastAPI | CSP, X-Content-Type, X-Frame, HSTS | ✅ |
| RateLimitMiddleware | FastAPI | 120/min global, 20/min upload, 10/min WS | ✅ |
| MaxBodySizeMiddleware | FastAPI | 50MB (对齐 Flask MAX_CONTENT_LENGTH) | ✅ |
| Flask rate_limit | Flask /old | @rate_limit(20,60) upload, @rate_limit(120,60) others | ✅ |
| Global Exception Handler | FastAPI | 防止原始 traceback 泄露 | ✅ |

### DDD domain/audio/ 自包含模块

| 层级 | 模块 | 核心算法 | 外部依赖 |
|------|------|---------|:--:|
| — | `audio_utils.py` | normalize_loudness + vocal_segments + filter | ✅ 纯函数 |
| — | `math_utils.py` (shared/) | safe_float + safe_clamp | ✅ 纯函数 |
| L0 | `acoustic_feature_extractor.py` | HNR + CPP + HPSS + voicing + mixed_audio | ✅ 零依赖 |
| L0 | `audiofeat_extractor.py` | CPPS/GNE/Jitter/Shimmer/等 22 特征 | ✅ audiofeat 1.1.1 |
| L1 | `pitch_extractor.py` | MAE/RPA/RCA/gross/octave/smoothness/breaks | ✅ 零依赖 |
| L1 | `rhythm_extractor.py` | onset CV + irregularity + off-beat + deviation | ✅ 零依赖 |
| L2 | `breath_extractor.py` | long_note + dynamic + design + technique + decay | ✅ 零依赖 |
| L2 | `technique_extractor.py` | vibrato + slides + falsetto + staccato + legato + ZCR/Centroid/C-V + **实谱 HF** 🆕 | ✅ 零依赖 |
| L2 | `timbre_extractor.py` | centroid + cluster + harmonic + nasality + 双源置信度 | ✅ 零依赖 |
| L3 | `muscle_extractor.py` | body/facial proxies + MPT/Crest/SPR/F1F2/Alpha | ✅ 零依赖 |
| L3 | `artistry_extractor.py` | vibrato + dynamic + phrase + crescendo + **真实 F0 CV** 🆕 | ✅ 零依赖 |
| — | `feature_types.py` | AcousticFeatures 冻结数据类 | ✅ 零依赖 |
| — | `feature_protocols.py` | 提取器 Protocol 接口 | ✅ 零依赖 |

### 评分增强路径 (v7.3 audiofeat + v7.4 P0/P1 + v7.5)

| Scorer | 增强方式 | 版本 |
|--------|---------|:----:|
| **BreathScorer** | CPPS/GNE/HNR_praat 增强气息评分 (±8 分) | v7.3 |
| **TechniqueScorer** | CPPS 主特征(40%) + HNR 单调(25%) + ZCR/Centroid/C-V + **真实 HF** 🆕 | v7.5 |
| **TimbreAdjuster** | 双源置信度 + **八维音色剖面** 🆕 (需 audiofeat) | v7.5 |
| **MuscleStrengthScorer** | **校准 formant/overtone 阈值** 🆕 + MPT/Crest/SPR/F1F2/Alpha | v7.5 |
| **ArtistryScorer** | **真实 F0 CV 替代 Hz** 🆕 + 无颤音 fallback | v7.5 |

### 绞杀者状态

13/13 模块完全自包含。旧 `services/features/` (原 12 files) 已缩减为 2 文件 (acoustic.py + types.py, 仍被 audio_service 使用, 已添加 DeprecationWarning)。

### 端口策略

开发 → 8000 | Electron → `--port=0` (OS 分配) | 生产 → FastAPI 服务 `frontend/dist/`

---

## 二、完成功能

### v7.5 (2026-07-29) — P1-2b 音色八维 + P0 评分异常修复

| 类别 | 项目 | 状态 |
|------|------|------|
| **P1-2b** | `_calc_hardness()`: spectral_crest 甜点曲线 (7-11) | ✅ |
| **P1-2b** | `_calc_depth()`: hammarberg_index + spectral_slope (含 slope=0 哨兵) | ✅ |
| **P1-2b** | `_calc_sharpness()`: centroid 甜点曲线 (1200-2800Hz) | ✅ |
| **P1-2b** | `_calc_booming()`: hammarberg×0.6 + harmonic_richness×0.4 | ✅ |
| **P1-2b** | `_calculate_enhanced()`: 四维→八维等权 12.5% 融合 | ✅ |
| **P0-1** | Artistry `pitch_cv`: orchestrator 从真实 F0 计算 CV (替代 vibrato_rate_avg Hz) | ✅ |
| **P0-1** | Artistry `pitch_cv`: feature_adapters fallback 使用 onset_density 代理 | ✅ |
| **P0-2** | Technique HNR: 移除 >22 惩罚段, 歌声 HNR≥12 一律满分 | ✅ |
| **P0-3** | Technique HF: 从真实频谱计算 >5kHz 能量比, 解耦 CPPS | ✅ |
| **P0-4** | Muscle formant: 阈值 0.15→0.22 (适配 hnr/60 输入范围) | ✅ |
| **P0-4** | Muscle overtone: 阈值 8→80 (计数刻度→评分刻度) | ✅ |
| **审计** | 全面审计所有 P0/P1 实现 vs 规格 + 文献交叉验证 | ✅ |
| **测试** | 新增 ~28 tests (22 timbre + 4 muscle + 2 artistry) | ✅ |

### v7.4 (2026-07-28) — 评分算法 P0/P1 修复 + 文献验证

| 类别 | 项目 | 状态 |
|------|------|------|
| **P0-1** | `_calc_breath_voice_ratio()`: CPPS 替代 HNR 主特征 (40% vs 70%) | ✅ |
| **P0-2** | `_calc_articulation()`: ZCR + Spectral Centroid + C-V 能量比 (Rathi & Hsu 2021) | ✅ |
| **P0-2** | `TechniqueFeatures`: 新增 zcr_mean/spectral_centroid/cv_energy_ratio 字段 | ✅ |
| **P0-2** | `LibrosaTechniqueExtractor`: ZCR/Centroid/C-V 提取逻辑 | ✅ |
| **P0-2** | `FeatureAdapterRegistry.to_technique()`: 新字段映射 | ✅ |
| **P0-3** | `_calc_vibrato()`: pitch_cv + dynamic_range fallback (上限 80) | ✅ |
| **P0-4** | `value_objects.py`: 6 个 `weighted()` 权重新分配 | ✅ |
| **P1-1** | `MuscleFeatures`: 新增 mpt_seconds/crest_factor/spr_ratio/f1f2_area/alpha_ratio | ✅ |
| **P1-1** | `LibrosaMuscleExtractor`: MPT/Crest/SPR/F1F2/Alpha 五维提取器 | ✅ |
| **P1-1** | `MuscleStrengthScorer`: `_apply_body_proxies()` + `_apply_facial_proxies()` | ✅ |
| **P1-2a** | `TimbreFeatures`: 新增 harmonic_stability 双源置信度 | ✅ |
| **P1-2a** | `TimbreAdjuster`: max(mfcc_cluster_purity, harmonic_stability/100) 置信度 | ✅ |
| **P1-2a** | `LibrosaTimbreExtractor`: 旧 CPP [0.01, 0.05] → harmonic_stability 替代门控 | ✅ |
| **测试** | 新增 ~25 tests (12 technique + 4 artistry + 3 timbre + 6 muscle) | ✅ |
| **回归** | 真实音频 baseline 更新至 V7_4 | ✅ |

### v7.3.1 (2026-07-28) — 安全审查修复 + Flask 限速 + BDD 增强

| 类别 | 项目 | 状态 |
|------|------|------|
| **CRITICAL** | `analyze_and_score` + `AudioAnalysisResult` + WebSocket 信息泄露修复 (9处) | ✅ |
| **HIGH** | FastAPI 新增 MaxBodySizeMiddleware (50MB) + mode 参数验证 | ✅ |
| **MEDIUM** | Flask `/old` 14 routes 全部添加速率限制 | ✅ |
| **P2** | `services/features/` 添加 DeprecationWarning + BDD 29 scenarios | ✅ |

### 更早版本

v7.3.0 ~ v7.0: 参见 [CHANGELOG.md](CHANGELOG.md)。

---

## 三、测试状态 (v7.5)

### 生产测试 (全部 GREEN)

| 套件 | 测试数 | 结果 | 说明 |
|------|:-----:|------|------|
| DDD 领域 (含 comparison + audiofeat) | 125 | ✅ 100% | 7 scorers + comparison scoring + value objects |
| DDD 基建 (extractors + orchestrator) | 112 | ✅ 100% | audiofeat + audio_utils + acoustic + pitch + rhythm + breath + technique + muscle |
| DDD 对齐 + Flag | 17 | ✅ 100% | alignment + extraction flag + SPA routes |
| 中间件 | 22 | ✅ 100% | SecurityHeaders + RateLimit + MaxBodySize |
| **DDD 合计** | **343** | **100% GREEN** | (~15s) |
| FastAPI 集成 | 20 | ✅ 100% | test_api_routes (独立进程) |
| Flask + WS 集成 | 14 | ✅ 100% | test_ws_score + test_api (独立进程) |
| 扩展测试 (DTW/repos/calibrator/SPA) | 51 | ✅ 100% | tests/extended/ (独立进程) |
| **生产代码总计** | **428** | **100% GREEN** | |

- v7.5 新增: ~28 tests (timbre 八维 22 + muscle 代理 4 + artistry 2)

### 真实音频回归

| 套件 | 测试数 | 结果 | 说明 |
|------|:-----:|------|------|
| 真实音频 Quick + Pro | 28 | ✅ 100% | v7.4 基线 (BASELINE_V7_4) — **v7.5 需更新基线** |
| TDD 未来特性 | 1 skip + 4 xfail | ⏭️ | 按需实现 |
| BDD | 13 step files | ✅ | 29 scenarios |

### 前端测试

| 套件 | 测试数 | 结果 |
|------|:-----:|------|
| Vitest (stores) | 33 | ✅ 100% |

### 真实音频评分 (v7.5 Quick 模式 — DDD 唯一路径)

| 音频文件 | Total | Pitch | Rhythm | Breath | Tech | Muscle | Art | Timbre |
|----------|:-----:|:-----:|:------:|:------:|:----:|:------:|:---:|:------:|
| 1（高分） | ~74 | ~71 | ~71 | ~97 | ~45 | ~77 | ~82 | ~0 |

> **v7.4 → v7.5 变化**:
> - Muscle: 89→77 (-12): formant/overtone 校准修复生效, 不再系统性偏高
> - Artistry: 76→82 (+6): pitch_cv 从 Hz 修复为真实 F0 CV, 15% 权重恢复
> - Technique: 45→45 (稳定): HNR>22 惩罚移除 + CPPS-HF 解耦, 消除倒挂
>
> **v7.5 权重**: pitch=13%, rhythm=12%, breath=22%, technique=25%, muscle=15%, artistry=13%
>
> **Timbre**: audiofeat 默认禁用 (enable_audiofeat=False), 音色调整在生产环境始终为 0。

---

## 四、已知问题

### 架构残留

| 优先级 | 残留 | 说明 |
|--------|------|------|
| **P2** | `services/features/acoustic.py` | ⚠ 已添加 DeprecationWarning，仍被 audio_service 使用 |
| **P2** | `services/features/types.py` | ⚠ 已添加 DeprecationWarning，仍被测试引用 |
| **P2** | `services/dl_services/` (11 files) | style classifier, VAD, DTW 仍在使用 |
| **P2** | `api/routes/` (Flask, ~700 行) | ✅ 已添加限速，仍与 FastAPI 端点重复 |

### 功能未完成

| 优先级 | 项目 | 说明 |
|--------|------|------|
| **P1** | Muscle v7.4 proxies 激活 | 在 adapter 路径中为死代码 (哨兵默认值), 需接入真实特征管道 |
| **P1** | Artistry crescendo_quality 饱和 | 累积公式导致几乎所有歌手达到 100, 区分度低 |
| **P1** | Artistry is_artistic_fluctuation 连续化 | 当前为布尔值, +30 几乎人人触发 |
| **P2** | CPPS/HNR 阈值改为歌声特定 | 当前使用语音病理范围 (3/5/8/12dB, 12-22dB), 文献 (Buckley 2023, Titze 2024) 建议歌声特定阈值 |
| **P2** | PyArmor 代码保护 | ADR-8, 构建脚本就绪 |
| **P2** | electron-builder 完整打包 | 配置就绪, 未执行 |
| **P2** | timbral_models 集成 | Python 3.12 兼容性问题, 待上游修复 |
| **P2** | Flask 路由最终移除 | DeprecationWarning + rate_limit 就绪，等待绞杀者完成 |
| **P2** | ABI 9 参数模型 | Barsties 2017, 需 Parselmouth 实现 |
| **P2** | Artistry rubato/attack slope | 文献 (Kondo 2025, Tan 2020) 验证的核心表达特征, 缺失 |

### 测试遗留

| 问题 | 数量 | 说明 |
|------|------|------|
| BDD v6.0 规划 features 未实现 | ~20 steps | auto-match/database/pitch-realtime/等 8 个 features |
| 集成测试不可混跑 | — | Flask + FastAPI 测试需独立进程 (C 扩展冲突) |
| 真实音频基线需更新 | — | v7.5 评分参数变更, BASELINE_V7_4 需更新至 V7_5 |

---

## 五、快速参考

### 关键文件

| 文件 | 说明 |
|------|------|
| `backend/domain/assessment/timbre_adjuster.py` | v7.5 — 八维音色剖面 (P1-2b) + 双源置信度门控 |
| `backend/domain/assessment/technique_scorer.py` | v7.5 — CPPS 主特征 + ZCR/Centroid + HNR 单调 + 实谱 HF |
| `backend/domain/assessment/artistry_scorer.py` | v7.5 — 无颤音 fallback + 真实 F0 CV |
| `backend/domain/assessment/muscle_scorer.py` | v7.5 — 校准 formant/overtone + 五维代理 |
| `backend/domain/assessment/value_objects.py` | v7.4 — 六维权重新分配 |
| `backend/domain/audio/technique_extractor.py` | v7.5 — ZCR/Centroid/C-V + 实谱 HF 能量 |
| `backend/domain/audio/artistry_extractor.py` | v7.5 — F0 CV fallback 守卫 (>1.0 拒绝 Hz) |
| `backend/domain/audio/muscle_extractor.py` | v7.4 — MPT/Crest/SPR/F1F2/Alpha 提取 |
| `backend/domain/audio/timbre_extractor.py` | v7.4 — CPP 门控修复 |
| `backend/application/assessment/ddd_feature_orchestrator.py` | v7.5 — `_compute_pitch_cv()` 真实 F0 CV |
| `backend/application/assessment/feature_adapters.py` | v7.5 — pitch_cv onset_density fallback |
| `backend/application/assessment/scoring_orchestrator.py` | 评分编排 (calculate_ddd + audiofeat) |
| `backend/domain/assessment/feature_flags.py` | DimensionFlags (含 enable_audiofeat) |
| `backend/main.py` | v7.3.1 — 全局异常处理器 + MaxBodySizeMiddleware |
| `api/routes/rate_limit.py` | v7.3.1 — Flask token bucket 限速器 |
| `tests/conftest.py` | VAS_SKIP_GPU=1 + VAS_DISABLE_RATE_LIMIT=1 |
| `tests/unit/domain/test_timbre_adjuster.py` | v7.5 — 40 tests (含八维 22 tests) |
| `tests/unit/domain/test_muscle_scorer.py` | v7.5 — 29 tests (含代理 8 tests) |

### 启动命令

```bash
# 开发模式
cd frontend && npm run dev          # Vite :5173
python backend/main.py              # FastAPI :8000

# 默认测试 (343 tests, ~15s)
pytest tests/unit/domain/ tests/unit/infrastructure/ \
       tests/unit/test_middleware.py \
       tests/unit/test_ddd_alignment.py \
       tests/unit/test_ddd_extraction_flag.py

# 集成测试 (独立进程, ~20s)
pytest tests/integration/test_api_routes.py -v         # FastAPI (20 tests)
pytest tests/integration/test_ws_score.py \
       tests/integration/test_api.py -v                # Flask + WS (14 tests)

# 扩展测试 (独立进程, ~5s)
pytest tests/extended/ -v                              # DTW/repos/etc (51 tests)

# 真实音频回归 (独立进程, ~27min)
pytest tests/integration/test_real_audio_regression.py -v

# BDD 测试 (需要浏览器)
pytest tests/bdd/ -v -m "not browser"                  # API-level BDD
pytest tests/bdd/ -v -m "browser"                      # Browser BDD (needs Playwright)
```
