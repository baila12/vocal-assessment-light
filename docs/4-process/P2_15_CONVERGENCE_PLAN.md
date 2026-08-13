# P2-15 Legacy 收敛进 DDD — 详细实施计划

> **创建**: 2026-08-13 | **依据**: [DEEP_REVIEW_v7.14.md](../3-quality/DEEP_REVIEW_v7.14.md) A1 (评分逻辑双轨) + P2-15 (legacy 收敛)
> **目标**: 将 `api/business/audio_analysis.py` + `services/*` 中的重复编排逻辑 (建议/音色/逐句) 收敛进 DDD application 层，
> 消除"评分逻辑双轨"，使评分路径唯一、模块化、低耦合。
> **方法**: 绞杀者模式 (strangler-fig) — 每阶段独立可测 GREEN，绝不一次性大爆炸重写。

---

## 0. 前置约束（所有阶段必须遵守）

| 约束 | 来源 | 违反后果 |
|------|------|---------|
| `api.business.analyze_and_score` 入口名必须保留 | 4 测试文件 + 1 BDD 步骤文件字符串 monkeypatch (`monkeypatch.setattr('api.business.analyze_and_score', ...)`) | 所有 monkeypatch 静默失效，测试假绿 |
| import 时单例必须保留构建 | `tests/unit/test_ddd_extraction_flag.py::test_ddd_extractor_initialization_in_audio_analysis` 断言 `_ddd_feature_extractor` import 后非 None | 测试失败 |
| 真实音频回归 28 例必须全绿 | `test_real_audio_regression.py` BASELINE_V7_14 (total ±6, pitch/art/muscle ±8, rhythm/breath/tech ±10) | 任何评分行为漂移立即失败 |
| `_ddd_feature_extractor = DddFeatureExtractionOrchestrator(flags=DimensionFlags(enable_audiofeat=True))` 不动 | 评分路径输入契约 | 评分漂移 |
| 每阶段独立提交 + 全量回归 | 项目 TDD/BDD 纪律 | 无法定位回归 |

**测试安全网（每阶段必须保持 GREEN）**:
- `tests/integration/test_real_audio_regression.py` (28, ~27min) — 评分数值契约
- `tests/unit/test_ddd_extraction_flag.py` (23) — DDD flag 接线
- `tests/unit/test_audio_service_mixed_detection.py` + `test_audio_service_analyze_error.py` (5) — audio_service 契约
- `tests/integration/test_song_match_api.py` + `test_compare_pitch_api.py` (monkeypatch) — facade 契约
- BDD: upload.feature / differentiation.feature / history.feature

---

## Phase 0 — 稳定化 + 删除纯死代码（风险：🟢 零）

**目标**: 删除无行为影响的死代码，建立基线。

### 0.1 删除 `services/audio_service.py` 4 个从不读取字段
- **代码**: L86-89 `_pitch_stability`/`_tonal_clarity`/`_voice_clarity`/`_vibrato_count` + 对应写入点 L187/L190/L196/L199
- **证据**: 全库 grep 确认无读取点 (含 `test_real_audio_regression` 数字断言不读这些字段)
- **同时删除**: `_analyze_tonal_clarity` (L470-483) 死方法（`_analyze_tonal_clarity_fast` L485 是活路径，保留）
- **测试**: 无新增；运行现有 audio_service 契约测试 (mixed_detection + analyze_error) 确认 GREEN

### 0.2 修复 stale 测试脚本 `tests/tools/test_real_audio_comparison.py`
- **问题**: L8 引用已删符号 `_ddd_feature_extractor_available` → import 即失败
- **修复**: 更新导入为当前存在的符号 (`_ddd_feature_extractor`/`ddd_orchestrator`) 或修正断言目标
- **测试**: 脚本可手动运行 (非 pytest collected)

### 0.3 删除死 `calculate()` 路径 + `FeatureAdapterRegistry`
- **代码**: `scoring_orchestrator.py` L95-201 `calculate()` + `feature_adapters.py`
- **证据**: `calculate()` 全库仅被 `feature_adapters.py` 自身引用；live 路径全部走 `calculate_ddd()`
- **注意**: `tests/unit/test_ddd_alignment.py:153` 引用了 `FeatureAdapterRegistry` — 需先更新该测试
- **风险**: `calculate()` 内的 `_make_diagnosis` 逻辑 (L464-479) 是 Phase 3 的移植源，**删除前先抄录保留**

### 0.4 验证
- `pytest tests/unit/ tests/unit/interfaces/ws/` + mixed_detection + analyze_error 全 GREEN
- 测试计数: 后端 766 → 约 764（若 test_ddd_alignment 的 adapter 测试删除）

---

## Phase 0b — 修复历史双写 bug（风险：🟢 低，本次实测确认的真实 bug）

**目标**: 每次上传只写 1 条完整历史记录。

### 背景（实测证实）
- `audio_analysis.py:41` import 时 `HistoryEventSubscriber(...).subscribe_to(_event_bus)` → 每次评分经 EventBus 写"最小记录"（无 analysis_id/filename/filepath，`level` 中文乱码）
- `assessment.py:212/301` `_save_history` → 写"完整记录"
- `save()` 无去重 → **实测 web_history.json: 50 条中 32 条是垃圾最小记录，挤占 max_records=50 槽位，淘汰完整记录**

### 方案选择
| 方案 | 做法 | 风险 |
|------|------|------|
| **A (推荐)** | 删除 `audio_analysis.py:35-41` 的 EventBus 订阅（历史由路由 `_save_history` 单一负责）。`ScoringOrchestrator(event_bus=None)` 不再传 event_bus | 低 — 路由已完整保存 |
| B | 保留订阅但改为"只写完整记录" | 中 — 需与路由去重，复杂 |

### 测试（RED 先行）
- 新增 `tests/integration/test_history_single_write.py`:
  - `test_upload_writes_exactly_one_history_record` — 上传 → 断言 history 文件仅 +1 条
  - `test_history_record_has_analysis_id_and_filename` — 记录含完整字段
- **验证**: RED（现为 2 条）→ GREEN（方案 A 后 1 条）

### 附加修复
- 清理 `web_history.json` 中 32 条垃圾记录（保留 18 条完整记录）— 需用户授权，因是数据变更

---

## Phase 1 — 建议生成器迁入 DDD（风险：🟢 低，纯移植）

**目标**: `AdviceService.generate` → DDD application 层 `AdviceGenerator`，消除"建议 100% legacy"。

### 新建 `backend/application/assessment/advice_generator.py`
```python
@dataclass(frozen=True)
class AdviceResult:
    advice: List[str]
    strongest_dimension: str
    weakest_dimension: str

class AdviceGenerator:
    """DDD 建议生成器 — 纯函数, 无状态, 消费 calculate_ddd dict"""
    DIMENSION_NAMES = {...}   # 从 AdviceService 迁移
    _TIPS = {...}             # 迁移
    _PRAISE = {...}           # 迁移
    def generate(self, scores: dict) -> AdviceResult: ...
```
- **迁移内容**: `services/advice_service.py` 全部逻辑 (L71-150) 原样移植
- **测试 (RED 先行)**: 新增 `tests/unit/application/test_advice_generator.py`:
  - 最弱维度 <75 → 含改进建议
  - 最强维度 >=90 → 含表扬
  - 总体评价分档 (>=90/>=85/>=80/>=70/>=60/<60)
  - 六维排序正确 (strongest/weakest)
- **接线**: `audio_analysis.py:122` 调 `AdviceGenerator().generate(score_result)` 替代 `advice_service.generate`
- **清理**: 删除 `services/advice_service.py`；`services/__init__.py` 的导出同步
- **验证**: 新增 ~8 单测 + 回归 28 例（数字断言，不受影响）全 GREEN

---

## Phase 2 — DDD 输出完整音色 dict（风险：🟠 中，pro 模式）

**目标**: 消除"音色计算两遍"。

### 现状
- DDD `TimbreAdjuster.calculate` 已算出 `brightness_score/warmth_score/nasality_score/confidence`（含 8 维 audiofeat 剖面）
- 但 `calculate_ddd` L297 只输出 `ta.adjustment` → 完整音色被丢弃
- legacy `TimbreService.analyze` 用**不同公式**重算 brightness/HNR/vibrato (pro 模式)

### 实施
1. **扩展 `calculate_ddd` 输出**: 增加 `result["timbre_detail"]` = {brightness, warmth, nasality, breathiness, hnr, vibrato_rate, vibrato_extent, vibrato_count, style}（从 `ta` + features 组装）
2. **新建音色应用服务** 或直接在 audio_analysis 组装 — 保持简单
3. **替换**: `audio_analysis.py:138` `timbre_service.analyze` → 从 DDD 产物组装 `_build_timbre_dict`
4. **测试 (RED 先行)**:
   - `test_timbre_dict_in_calculate_ddd.py`: `calculate_ddd(timbre=...)` 输出含 brightness/warmth/nasality 键且与 `ta.brightness_score` 一致
   - **等价性测试**: 同一 f0/audio 输入下，legacy TimbreService vs DDD timbre 输出对比（或断言 DDD 输出非空且在合理范围）
5. **清理**: 删除 `services/timbre_service.py`

### 风险缓解
- 前端消费的 `timbre` 字段结构 (`_build_timbre_dict` 契约) 保持不变 — 只换数据来源
- pro 模式集成测试需一条（断言 phrase/timbre 结构），但真实音频 28 例只测数字，注意 pro 路径回归

---

## Phase 3 — 在线路径补全逐维诊断（风险：🟢 低）

**目标**: 修复"诊断 block 恒空"缺陷（DEEP_REVIEW 未列但映射发现）。

### 现状
- `calculate()` (死路径) L177-181 调 `_make_diagnosis` 输出 `pitch_diagnosis/rhythm_diagnosis/breath_diagnosis/technique_diagnosis/artistry_diagnosis`
- `calculate_ddd()` (活路径) **完全省略**这些键 → 前端诊断 block 恒空
- `audio_analysis.py:292-372` 三个 `_build_*_diagnosis` 防御性分支白写

### 实施
1. **`calculate_ddd` 增加 5 个 `*_diagnosis` 键**（移植 `_make_diagnosis` 调用，对每个 score_obj）
2. **删除** `audio_analysis.py` `_build_diagnosis_dict`/`_build_breath_diagnosis`/`_build_technique_diagnosis` 的 isinstance 防御分支（改为直读 DDD dict）
3. **测试 (RED 先行)**: `test_diagnosis_in_calculate_ddd.py` — 断言 5 个诊断键存在、含 score/level/issues/suggestions 结构、mae_cents/deviation_ratio 额外字段

### 风险缓解
- 纯增加输出字段，不动评分公式 → 28 例回归数字断言不受影响

---

## Phase 4 — 逐句评分迁入 DDD（风险：🔴 高，pro 模式，未测试充分）

**目标**: 消除"逐句评分 100% legacy"。

### 现状
- `PhraseService.analyze_phrases` (630 行) — 乐句分割 + 每句 pitch/rhythm/breath/emotion/volume 评分 (pro 模式)
- DDD 无等价物（仅 ArtistryScore.phrase_expression 标量）
- pro 模式是 ~300s Demucs 路径，回归套件几乎不测 → **高风险**

### 实施（可选推迟）
1. 新建 `backend/application/assessment/phrase_scorer.py` — 镜像 PhraseService 分割 + 评分逻辑
2. 替换 `audio_analysis.py:147`
3. **测试**: phrase_scorer 单元 + 1 条 pro 集成断言 phrase_result 结构
4. 清理 `services/phrase_service.py`

### 风险缓解
- **强烈建议推迟至独立会话**（用户可决定）
- 或先加 pro 模式集成测试（现状空白）建立基线，再迁移

---

## Phase 5 — 折叠 facade（风险：🟠 中）

**目标**: `audio_analysis.py` 瘦身为薄响应整形适配器。

### 5.1 删除死 `analyze_emotion` 启发式 (L429-467)
- 证据: L276 `result['scores']['emotion'] = artistry_score` 覆盖其输出；仅 `basic_info.emotion_info` 存活
- 替换为从 `score_result`/features 组装 emotion_info 或直接删除

### 5.2 对齐 `_ddd_feature_extractor` 硬编码 `enable_audiofeat=True`
- 与运行时 `FeatureFlags` 对齐（flag 桥接已在 v7.7 就绪）

### 5.3 移除无用 `reference_path` 参数 (L53)

### 5.4 测试: facade 收缩后 `api.business.analyze_and_score` 导出保持 + 全量回归 + BDD

---

## 测试数量预估

| 阶段 | 新增测试 | 删除/变更测试 | 后端 collected 变化 |
|------|:-------:|:------------:|:------------------:|
| Phase 0 | 0 | test_ddd_alignment (adapter) 约 -2 | 766 → ~764 |
| Phase 0b | +2 (history single write) | 0 | ~766 |
| Phase 1 | +8 (advice_generator) | 0 | ~774 |
| Phase 2 | +3 (timbre dict + equivalence) | 0 | ~777 |
| Phase 3 | +2 (diagnosis) | 0 | ~779 |
| Phase 4 | +5 (phrase scorer + pro integration) | 0 | ~784 |
| Phase 5 | +1 (no-double-history) | 0 | ~785 |
| **合计** | **~+21** | **~-2** | **~785** |

---

## 提交策略

每个 Phase 一个独立 commit（conventional commits，如 `refactor: v7.16 P2-15 Phase 1 — AdviceGenerator 迁入 DDD`），
提交前跑对应测试 + 全量快速回归。Phase 4 单独决策是否纳入本会话。

## 版本决策

本轮收敛涉及评分管线结构（非评分公式），建议版本号 **v7.15 → v7.16**（结构重构，数值不变）。
真实音频回归 28 例是"评分数值不变"的权威验证。
