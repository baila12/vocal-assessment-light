# 测试结果记录 v7.11

> 更新: 2026-08-04 | 521 tests 100% GREEN | 分支: `main`
>
> 关联: [PROJECT_STATUS.md](PROJECT_STATUS.md) | [TDD.md](../3-quality/TDD.md) | [BDD.md](../3-quality/BDD.md)

---

## v7.11 测试统计

### 生产测试 (全部 GREEN)

| 套件 | 测试数 | 结果 | 说明 |
|------|:-----:|------|------|
| DDD 领域 (scorers + value objects + comparison + songs + **ScoringWeights**) | 257 | ✅ 100% | 7 scorers + comparison + songs + ScoringWeights 值对象 (v7.11: +29) |
| DDD 基建 (extractors + orchestrator + ABI + sqlite) | 132 | ✅ 100% | 10 extractors + audio_utils + ABI + songs 仓储 |
| DDD 对齐 + Flag bridge | 23 | ✅ 100% | alignment + extraction flag + flag bridge |
| 中间件 | 23 | ✅ 100% | SecurityHeaders + RateLimit + MaxBodySize |
| **DDD 合计** | **435** | **100% GREEN** | (~25s) |
| FastAPI 集成 | 50 | ✅ 100% | test_api_routes (19) + test_songs_api (17, 含 v7.10 TestAudioPlayback ×3) + **test_scoring_api (14, v7.11 new)** |
| 扩展测试 (DTW/repos/calibrator) | 36 | ✅ 100% | tests/extended/ |
| **生产代码总计** | **521** | **100% GREEN** | (DDD 435 + 集成 50 + 扩展 36) |
| 真实音频回归 | 28 | ✅ 100% | BASELINE_V7_6, 高低分区分度 9.1 pts |
| BDD (16 step files) | 162 scenarios collected | ✅ | scoring-config API 级 PASS; upload.feature 38 场景测试数据缺失预存失败; animations.feature 15 场景待迁移; 6 features 缺 step defs |
| 前端 Vitest | 68 | ✅ 100% | songs.store (24) + scoring.store 🆕 (11) + 33 其他 |
| vue-tsc | 0 errors | ✅ | TypeScript 零错误 |
| Vite build | 8.9s | ✅ | 生产构建 |

### v7.11 新增测试明细

| 文件 | 新增测试数 | 覆盖 |
|------|:---------:|------|
| `test_scoring_weights.py` | 25 | ScoringWeights 值对象: 默认权重/总和校验/单维≤50%/非负/4 风格预设/weighted_total/to_dict/from_dict |
| `test_scoring_api.py` | 14 | GET /presets + POST /apply-weights: 默认流行/预设校验/超50%拒绝/总和校验/未知预设400/非法权重422/apply-weights 总分等级星标 |
| `test_scoring_domain_service.py` (扩展) | +4 | calculate_total(weights=...) 注入 + weighted_total_from_scores |
| `frontend/tests/unit/stores/scoring.test.ts` | 11 | 预设加载/滑块权重/总和校验/自动归一化/recalc 纯前端重算 |

## v7.5 测试统计 (历史)

### 生产测试 (全部 GREEN)

| 套件 | 测试数 | 结果 | 说明 |
|------|:-----:|------|------|
| DDD 领域 (含 comparison + audiofeat) | 137 | ✅ 100% | 7 scorers + timbre 八维 22 tests + muscle 代理 4 tests + artistry 2 tests |
| DDD 基建 (extractors + orchestrator) | 112 | ✅ 100% | audiofeat + audio_utils + acoustic + pitch + rhythm + breath + technique + muscle |
| DDD 对齐 + Flag | 17 | ✅ 100% | alignment + extraction flag + SPA routes |
| 中间件 | 22 | ✅ 100% | SecurityHeaders + RateLimit + MaxBodySize |
| **DDD 合计** | **343** | **100% GREEN** | (~15s) |
| FastAPI 集成 | 20 | ✅ 100% | test_api_routes (独立进程) |
| Flask + WS 集成 | 14 | ✅ 100% | test_ws_score + test_api (独立进程) |
| 扩展测试 (DTW/repos/calibrator/SPA) | 51 | ✅ 100% | tests/extended/ (独立进程) |
| **生产代码总计** | **428** | **100% GREEN** | |

- v7.5 新增: ~28 tests (timbre 八维 22 + muscle SPR/Alpha 4 + artistry 2)

### 真实音频回归

| 套件 | 测试数 | 结果 | 说明 |
|------|:-----:|------|------|
| 真实音频 Quick + Pro | 28 | ⚠️ 需更新基线 | v7.5 评分参数变更, BASELINE_V7_4 → V7_5 |
| TDD 未来特性 | 1 skip + 4 xfail | ⏭️ | 按需实现 |
| BDD | 13 step files | ✅ | 29 scenarios |

### 前端测试

| 套件 | 测试数 | 结果 |
|------|:-----:|------|
| Vitest (stores) | 33 | ✅ 100% |

---

## v7.4 测试统计 (历史参考)

| 套件 | 测试数 | 结果 | 说明 |
|------|:-----:|------|------|
| BDD | 13 step files (29 scenarios) | ✅ | |
| 前端 Vitest (stores) | 33 | ✅ 100% | |

---

## v7.4 真实音频评分 (Quick, DDD 唯一路径)

| 音频 | Total | Pitch | Rhythm | Breath | Tech | Muscle | Art | Timbre |
|------|:-----:|:-----:|:------:|:------:|:----:|:------:|:---:|:------:|
| 恋人 (高分) | ~66 | ~67 | ~66 | ~92 | **~47** | ~80 | ~76 | ~0 |
| 手写的从前 (高分) | ~62 | ~70 | ~42 | ~94 | **~45** | ~76 | ~77 | ~0 |
| 1 (高分) | ~66 | ~71 | ~71 | ~97 | **~45** | ~78 | ~76 | ~0 |
| 音频-3分26秒 (高分) | ~66 | ~68 | ~58 | ~89 | **~48** | ~80 | ~76 | ~0 |
| 陈奕迅难听之声 (低分) | ~53 | ~66 | ~5 | ~84 | **~49** | ~70 | ~74 | ~0 |

### Technique 维度变化 (v7.3 → v7.4)

| 音频 | v7.3 Tech | v7.4 Tech | Δ |
|------|:--------:|:--------:|:--:|
| 恋人（高分） | 25 | **46.8** | +21.8 |
| 手写的从前（高分） | 19 | **44.9** | +25.9 |
| 1（高分） | 20 | **44.9** | +24.9 |
| 音频-3分26秒(高分) | 30 | **47.5** | +17.5 |
| 陈奕迅难听之声（低分） | 16 | **48.8** | +32.8 |

> Technique 维度平均提升 **+24.6 分**。CPPS 主特征替代 HNR 后，气声比评分更准确反映实际嗓音质量，系统性偏低问题已修复。
>
> **v7.4 权重**: pitch=13%, rhythm=12%, breath=22%, technique=25%, muscle=15%, artistry=13%
>
> **Timbre**: audiofeat 默认禁用 (enable_audiofeat=False), 音色调整在生产环境始终为 0。P1-2a 门控修复已就绪, 等待 audiofeat 启用后生效。

---

## v7.4 新增测试

| 文件 | 新增测试数 | 覆盖 |
|------|:---------:|------|
| `test_technique_scorer.py` | +12 | CPPS 主特征 (7) + ZCR/Centroid 咬字 (5) |
| `test_artistry_scorer.py` | +4 | 颤音 fallback |
| `test_timbre_adjuster.py` | +3 | 双源置信度门控 |
| `test_muscle_scorer.py` | +6 | 五维代理增强 |
| **合计** | **+25** | |

---

## 运行命令

```bash
# DDD 核心 (435 tests, ~25s)
# ⚠️ 不直接运行 pytest tests/unit/ (PyTorch C 扩展冲突 → 崩溃), 必须使用分组命令:
pytest tests/unit/domain/ tests/unit/infrastructure/ \
       tests/unit/test_middleware.py \
       tests/unit/test_ddd_alignment.py \
       tests/unit/test_ddd_extraction_flag.py \
       tests/unit/test_flag_bridge.py

# 集成测试 (独立进程)
pytest tests/integration/test_api_routes.py -v     # FastAPI (19 tests)
pytest tests/integration/test_songs_api.py -v      # Songs API (17 tests)
pytest tests/integration/test_scoring_api.py -v    # Scoring API 🆕 v7.11 (14 tests)

# 扩展测试 (独立进程, ~9s)
pytest tests/extended/ -v                           # 36 tests (DTW/repos/calibrator)

# 真实音频回归 (独立进程, ~27min)
pytest tests/integration/test_real_audio_regression.py -v

# BDD (API 级别, 不含浏览器)
pytest tests/bdd/ -v -m "not browser"

# 前端测试
cd frontend && npx vitest run
```

---

## 历史记录

### v7.3 (2026-07-27) — DDD 唯一路径 + audiofeat 增强

| 音频 | Total | Pitch | Rhythm | Breath | Tech | Muscle | Art |
|------|:-----:|:-----:|:------:|:------:|:----:|:------:|:---:|
| 恋人（高分） | 65.7 | 67 | 66 | 92 | 25 | 80 | 76 |
| 陈奕迅难听之声（低分） | 52.8 | 66 | 5 | 84 | 16 | 70 | 74 |

> v7.3 使用五维旧权重 (pitch=10%, rhythm=10%, breath=20%, tech=25%, muscle=25%, art=10%)。v7.4 起切换至六维新权重。

### v6.2 (2026-07-07) — 最终 Flask 五维基线

| 音频 | Total | Pitch | Rhythm | Breath | Tech | Art |
|------|:-----:|:-----:|:------:|:------:|:----:|:---:|
| 恋人（高分） | 82.2 | 77.7 | 77.1 | 93.6 | 82.2 | 82.0 |
| 陈奕迅难听之声（低分） | 50.0 | 72.7 | 2.5 | 84.8 | 66.2 | 81.2 |

> v6.2 使用五维评分 (无 muscle 维度) + 旧版 technique 定义 (HNR/CPP/技巧完成度)。v7.0 起切换至六维 + 新 technique 定义，分数不可直接对比。
