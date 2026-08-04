# 测试结果记录 v7.10

> 更新: 2026-08-04 | 478 tests 100% GREEN | 分支: `main`
>
> 关联: [PROJECT_STATUS.md](PROJECT_STATUS.md) | [TDD.md](../3-quality/TDD.md) | [BDD.md](../3-quality/BDD.md)

---

## v7.10 测试统计

| 套件 | 测试数 | 结果 | 说明 |
|------|:-----:|------|------|
| DDD 领域 (scorers + value objects + comparison + songs) | 154 | ✅ 100% | 7 scorers + comparison + songs 领域 (v7.9: +27) |
| DDD 基建 (extractors + orchestrator + ABI + sqlite) | 149 | ✅ 100% | 10 extractors + audio_utils + ABI + songs 仓储 (v7.9: +13) |
| DDD 对齐 + Flag bridge + GNE | 22 | ✅ 100% | alignment + extraction flag + flag bridge + GNE |
| 中间件 | 22 | ✅ 100% | SecurityHeaders + RateLimit + MaxBodySize |
| **DDD 合计** | **406** | **100% GREEN** | (~16s) |
| FastAPI 集成 | 36 | ✅ 100% | test_api_routes (19) + test_songs_api (17, v7.10: +TestAudioPlayback 3) |
| 扩展测试 (DTW/repos/calibrator) | 36 | ✅ 100% | tests/extended/ |
| **生产代码总计** | **478** | **100% GREEN** | |
| 真实音频回归 | 28 | ✅ 100% | BASELINE_V7_6 |
| BDD (16 step files) | 162 scenarios collected | ✅ | v7.9: +1 step file (database) |
| 前端 Vitest | 57 | ✅ 100% | stores |
| vue-tsc | 0 errors | ✅ | TypeScript 零错误 |
| Vite build | 8.5s | ✅ | 生产构建 |

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
# DDD 核心 (406 tests, ~16s)
pytest tests/unit/domain/ tests/unit/infrastructure/ \
       tests/unit/test_middleware.py \
       tests/unit/test_ddd_alignment.py \
       tests/unit/test_ddd_extraction_flag.py \
       tests/unit/test_flag_bridge.py

# 集成测试 (独立进程)
pytest tests/integration/test_api_routes.py -v     # FastAPI (19 tests)
pytest tests/integration/test_songs_api.py -v      # Songs API (17 tests, v7.10)

# 扩展测试 (独立进程, ~5s)
pytest tests/extended/ -v                           # 34 tests (DTW/repos/calibrator)

# 真实音频回归 (独立进程, ~27min)
pytest tests/integration/test_real_audio_regression.py -v

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
