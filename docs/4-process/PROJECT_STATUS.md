# 项目状态

> 更新: 2026-07-27 | 版本: **v7.2.1** | 分支: `feat/v7-fastapi-vue-refactor`

---

## 一、架构

```
Vue 3 SPA (frontend/dist/)  →  FastAPI (:8000)  ←  Flask /old (绞杀者)
                                      │
    ┌─────────────────────────────────┼──────────────────────────┐
    │  backend/ (DDD 四层)            │  旧服务层 (残留)           │
    │  domain/assessment/ (7 scorers) │  services/features/ (2)   │
    │  domain/audio/ (13 模块自包含)   │  services/dl_services/ (11)│
    │  application/ (orchestrator)    │  services/audio_service.py │
    │  infrastructure/audio/ (4)      │  api/business/ (bridge)   │
    │  interfaces/api/ + ws/          │  api/routes/ (Flask, 残留)│
    │  shared/ (EventBus, math_utils) │                           │
    └─────────────────────────────────┴──────────────────────────┘
```

### 评分路径 (v7.2: DDD 唯一路径)

| 路径 | 特征提取 | 评分 | 状态 |
|------|---------|------|:----:|
| **DDD 原生** | `DddFeatureExtractionOrchestrator` → 13 自包含模块 | `ScoringOrchestrator.calculate_ddd()` | ✅ 生产 |
| V4 回退 | `ScoreServiceV4` (五维) | — | ❌ v7.1.4 已移除 |

### DDD domain/audio/ 自包含模块 (v7.2 完成)

| 层级 | 模块 | 核心算法 | 外部依赖 |
|------|------|---------|:--:|
| — | `audio_utils.py` | normalize_loudness + vocal_segments + filter | ✅ 纯函数 |
| — | `math_utils.py` (shared/) | safe_float + safe_clamp | ✅ 纯函数 |
| L0 | `acoustic_feature_extractor.py` | HNR + CPP + HPSS + voicing + mixed_audio | ✅ 零依赖 |
| L0 | `audiofeat_extractor.py` | CPPS/GNE/Jitter/Shimmer/等 22 特征 | ✅ audiofeat 1.1.1 |
| L1 | `pitch_extractor.py` | MAE/RPA/RCA/gross/octave/smoothness/breaks | ✅ 零依赖 |
| L1 | `rhythm_extractor.py` | onset CV + irregularity + off-beat + deviation | ✅ 零依赖 |
| L2 | `breath_extractor.py` | long_note + dynamic + design + technique + decay | ✅ 零依赖 |
| L2 | `technique_extractor.py` | vibrato + slides + falsetto + staccato + legato | ✅ 零依赖 |
| L2 | `timbre_extractor.py` | centroid + cluster + harmonic + nasality | ✅ 零依赖 |
| L3 | `muscle_extractor.py` | body/facial proxies (adapter 公式) | ✅ 零依赖 |
| L3 | `artistry_extractor.py` | vibrato + dynamic + phrase + crescendo | ✅ 零依赖 |
| — | `feature_types.py` | AcousticFeatures 冻结数据类 | ✅ 零依赖 |
| — | `feature_protocols.py` | 提取器 Protocol 接口 | ✅ 零依赖 |

**绞杀者状态**: 13/13 模块完全自包含。旧 `services/features/` (原 12 files) 已缩减为 2 文件 (acoustic.py + types.py, 仍被 audio_service 使用)。

### 预处理管线

`normalize_loudness()` (RMS→0.05) + `filter_audio_to_vocal_segments()` — 统一预处理, 与旧管线一致。

### 端口策略

开发 → 8000 | Electron → `--port=0` (OS 分配) | 生产 → FastAPI 服务 `frontend/dist/`

---

## 二、完成功能

### v7.2.1 (2026-07-27) — 代码审查修复

| 类别 | 项目 | 状态 |
|------|------|------|
| **CRITICAL** | analysis_id 存入 history + UUID 查找支持 | ✅ |
| **CRITICAL** | history 字段 created_at 统一 + grade/v7 字段存储 | ✅ |
| **CRITICAL** | FastAPI UploadResponse 补全 timbre_adjustment + normalization | ✅ |
| **CRITICAL** | 修复 dl_services 裸 except: → except Exception: | ✅ |
| **HIGH** | 静默异常增加日志 (breath/technique/acoustic/audio_service) | ✅ |
| **HIGH** | 错误信息泄露修复 (str(e) → 通用消息) | ✅ |
| **HIGH** | 提取 shared/math_utils.py (safe_float/safe_clamp 去重) | ✅ |
| **HIGH** | 删除 _calc_rhythm_from_pitch 死代码 (53行) | ✅ |
| **MEDIUM** | DddFeatureSet frozen=True + API 超时 + WS 重连日志 | ✅ |
| **MEDIUM** | 前端不可变更新 + XSS 修复 + AudioPlayer/AudioContext 日志 | ✅ |
| **MEDIUM** | HistoryListResponse 类型修复 (records→history) | ✅ |
| **测试** | 226/226 DDD GREEN (含 106 infrastructure + 88 domain + 32 对齐/flag/SPA) | ✅ |

### v7.2.0 (2026-07-26) — audiofeat 增强特征提取

| 类别 | 项目 | 状态 |
|------|------|------|
| **新增** | `AudiofeatExtractor` + `AudiofeatFeatures` (22 声学特征) | ✅ |
| **特征** | CPPS, HNR_praat, GNE, Jitter, Shimmer, Closed Quotient, Soft Phonation, Vocal Fry | ✅ |
| **特征** | Spectral Centroid/Flatness/Crest/Entropy/Roughness, Harmonic Richness, Inharmonicity | ✅ |
| **集成** | `DddFeatureSet.audiofeat` + `enable_audiofeat` flag 门控 | ✅ |
| **Flag** | `DimensionFlags.enable_audiofeat` + `FeatureFlags.enable_audiofeat` | ✅ |
| **TDD** | 19/19 GREEN (初始化 + 提取 + 边缘情况 + flag 门控) | ✅ |

### v7.1.5 (2026-07-26) — 特征提取层绞杀者完成

| 类别 | 项目 | 状态 |
|------|------|------|
| **内联** | audio_service.py 内联 _extract_f0 + _extract_f0_crepe | ✅ |
| **删除** | services/audio_features_service.py (~500 行) | ✅ |
| **删除** | services/features/ 未使用分析器 10 文件 (~1,220 行) | ✅ |
| **保留** | services/features/acoustic.py + types.py (混合音频检测仍需要) | ✅ |
| **测试** | 更新 test_ddd_alignment/test_pitch/test_rhythm 移除 legacy 对比 | ✅ |

### v7.1.4 (2026-07-26) — 死代码清理

| 类别 | 项目 | 状态 |
|------|------|------|
| **删除** | services/scoring/ (8 files) + score_service.py + scoring_config.py | ✅ |
| **删除** | web/static/js/ (38 files) + css/ (10 files) + app.js + router.js | ✅ |
| **删除** | 14 个 Category-1 遗留测试文件 | ✅ |
| **简化** | api/business/audio_analysis.py → DDD 唯一评分路径 | ✅ |
| **简化** | services/__init__.py 移除 ScoreService 导出 | ✅ |
| **更新** | services/advice_service.py → v7 六维建议 | ✅ |

### v7.1.3 (2026-07-26) — DDD 绞杀者内移完成

详见 [CHANGELOG.md](CHANGELOG.md)。

---

## 三、测试状态

| 套件 | 结果 | 说明 |
|------|------|------|
| DDD 领域测试 | **88/88** | 7 个 scorer (pitch/rhythm/breath/technique/muscle/artistry/timbre) |
| DDD 基建测试 | **106/106** | 含 19 audiofeat + 18 audio_utils + 16 acoustic + 11 pitch + 10 rhythm + 8 breath + 6 technique + 4 batch4 + 4 orchestrator + 4 technique_extractor + 6 breath_extractor |
| DDD Flag 测试 | **11/11** | Flag 存在性 + 默认值 + 集成链路 |
| DDD 对齐/SPA | **21/21** | 7 alignment + 11 flag + 15 SPA routes (合并计数) |
| 综合系统测试 | **53/53** | 含 DDD scoring + extraction + upload + FCPE + history |
| 真实音频验证 | **12/12** | melody.wav + 5 文件批量 (DDD 唯一路径) |
| **DDD 合计** | **226/226** | **100% GREEN** |
| v6.x 单元测试 | ~79/79 | 预存失败 (rate-limit ×2) 不在 DDD 范围 |

### v7.2 新增测试

| 文件 | 测试数 | 覆盖 |
|------|--------|------|
| `tests/unit/infrastructure/test_audiofeat_extractor.py` | 19 | AudiofeatExtractor 初始化 + 22 特征 + 边缘情况 + flag |
| `tests/unit/infrastructure/test_audio_utils.py` | 18 | normalize_loudness + vocal_segments + filter |
| `tests/unit/infrastructure/test_acoustic_extractor.py` | 16 | HNR/CPP/HPSS/voicing |
| `tests/unit/infrastructure/test_pitch_extractor.py` | 11 | MAE/RPA/RCA/breaks/wobble |
| `tests/unit/infrastructure/test_rhythm_extractor.py` | 10 | onset CV/irregularity/off-beat |
| `tests/unit/infrastructure/test_breath_extractor.py` | 8 | 8 子评估器 |
| `tests/unit/infrastructure/test_technique_extractor.py` | 6 | vibrato/slides/falsetto/staccato/legato |
| `tests/unit/infrastructure/test_orchestrator.py` | 4 | DDD vs adapter 路径 |

---

## 四、评分对齐 (v7.1.3 验证, 当前 DDD 唯一路径)

melody.wav: DDD total=62.2 | 5 文件批量: DDD avg=63.8 | DDD 评分比 legacy 更准确 (legacy 有采样率 bug)

---

## 五、已知问题

### 架构残留

| 优先级 | 残留 | 说明 |
|--------|------|------|
| **P2** | `services/features/acoustic.py` | AcousticAnalyzer.detect_mixed_audio (audio_service 仍使用) |
| **P2** | `services/features/types.py` | AudioFeaturesResult 类型 (test_orchestrator 仍使用) |
| **P2** | `services/dl_services/` (11 files) | style classifier, VAD, DTW 仍在使用 |
| **P2** | `api/routes/` (Flask, ~500 行) | 与 FastAPI 端点重复, Flask /old 挂载仍活跃 |
| **P2** | `backend/domain/comparison/` (桩) | entities.py, services.py 未实现 |

### 功能未完成

| 优先级 | 项目 | 说明 |
|--------|------|------|
| **P1** | `enable_audiofeat=True` 接入评分 | 特征已提取, 待接入 scorer 增强 breath/technique 维度 |
| **P2** | PyArmor 代码保护 | ADR-8, 构建脚本就绪 |
| **P2** | electron-builder 完整打包 | 配置就绪, 未执行 |
| **P2** | timbral_models 集成 | Python 3.12 兼容性问题, 待上游修复 |

### 测试遗留

| 问题 | 数量 | 说明 |
|------|------|------|
| Rate-limit 中间件测试 | 2 | `VAS_DISABLE_RATE_LIMIT` 环境变量问题 |
| 已有 TDD 失败 | ~8 | v6.x FeatureFlags 默认值变更 |
| 集成测试失败 | ~9 | FastAPI TestClient 部分端点超时 |
| BDD 步骤未实现 | ~36 | Step definitions 缺失或 API 契约不匹配 |

---

## 六、快速参考

### 关键文件

| 文件 | 说明 |
|------|------|
| `backend/domain/audio/audio_utils.py` | 归一化 + 人声分段 (纯函数, 零依赖) |
| `backend/domain/audio/audiofeat_extractor.py` | v7.2 — 22 增强声学特征 (CPPS/GNE/Jitter/等) |
| `backend/shared/math_utils.py` | v7.2.1 — safe_float + safe_clamp (去重) |
| `backend/domain/audio/feature_types.py` | `AcousticFeatures` 冻结数据类 |
| `backend/domain/audio/feature_protocols.py` | 提取器 Protocol 接口 |
| `backend/application/assessment/ddd_feature_orchestrator.py` | 特征编排 (13 提取器, DddFeatureSet frozen) |
| `backend/application/assessment/scoring_orchestrator.py` | 评分编排 (calculate_ddd) |
| `backend/domain/assessment/feature_flags.py` | DimensionFlags (含 enable_audiofeat) |
| `services/feature_flags.py` | FeatureFlags (含 enable_audiofeat) |
| `api/business/audio_analysis.py` | analyze_and_score() — DDD 唯一路径 |

### 启动命令

```bash
# 开发模式
cd frontend && npm run dev          # Vite :5173
python backend/main.py              # FastAPI :8000

# 测试
pytest tests/unit/domain/ -q               # 领域评分测试 (88 tests)
pytest tests/unit/infrastructure/ -q        # DDD 基建测试 (106 tests)
pytest tests/unit/test_ddd_alignment.py     # DDD 对齐测试
pytest tests/unit/test_ddd_extraction_flag.py  # Flag 测试
python tests/tools/test_real_audio_comparison.py  # 真实音频验证
```
