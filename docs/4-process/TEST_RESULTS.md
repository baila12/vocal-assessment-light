# 测试结果记录

> 每次测试运行后更新。格式: 日期 | 提交 | 测试统计 | 真音频回归

---

## 运行命令

```bash
# 全量测试 (跳过 E2E, 需要启动服务)
pytest tests/unit/ tests/integration/ tests/tdd/ -v --tb=short --durations=10

# 仅单元测试 (快速, < 2min)
pytest tests/unit/ -q --tb=short

# TDD 测试 (含真音频, ~5-10min)
pytest tests/tdd/ -v --tb=short

# E2E 测试 (需要先启动 Flask 服务)
python web_app.py &
pytest tests/e2e/ -v --tb=short
```

---

## 测试模块一览

| 目录 | 文件 | 类型 | 测试数 | 速度 |
|------|------|------|--------|------|
| `tests/unit/` | `test_scorers.py` | 评分器单元 | ~30 | < 10s |
| | `test_features.py` | 特征提取器 | ~20 | < 20s |
| | `test_comparison_dtw.py` | DTW 对比 | ~10 | < 10s |
| | `test_spa_routes.py` | 路由测试 | ~5 | < 5s |
| | 其他 | 配置/工具 | ~56 | < 10s |
| `tests/integration/` | `test_api_endpoints.py` | API 集成 | ~48 | < 60s |
| `tests/tdd/` | `test_acoustic_algorithms.py` | Feature Flag + HNR/CPP/Voicing/CREPE | 12 | < 10s |
| | `test_mixed_audio.py` | 混合音频 + 混响补偿 | 11 | < 120s |
| | `test_scoring_v6_1.py` | 评分区分度验证 | 9 | < 60s* |
| | `test_future_features.py` | RED 阶段 (xfail) | 5 | < 5s |
| `tests/e2e/` | `test_e2e_v3.py` 等 | E2E 浏览器测试 | ~72 | 需要服务 |
| `tests/bdd/` | BDD scenarios | BDD API 测试 | ~120 | < 120s |

> *: 含真音频的测试受益于会话级缓存 (conftest.py fixture)

---

## 测试结果记录

### 2026-07-06 | `feat/v5.18-gsap-animation-redesign` | v6.1

**提交**: `6d89ac8` (perf) + `79281e0` (refactor) + `793beaf` (docs) + `81b6582` (Artistry) + `2c4904f` (Scoring)

| 套件 | 通过 | 失败 | 跳过 | xfail | 耗时 |
|------|------|------|------|-------|------|
| unit | 121 | 0 | 0 | 0 | 82s |
| tdd/test_acoustic_algorithms | 12 | 0 | 0 | 0 | ~15s |
| tdd/test_mixed_audio | 11 | 0 | 1* | 0 | ~120s |
| tdd/test_scoring_v6_1 | 9 | 0 | 0 | 1 | ~40s |
| tdd/test_future_features | 5 | 0 | 0 | 5 (RED) | < 5s |
| **合计** | **158** | **0** | **1** | **6** | **~260s** |

> *: `test_detect_light_accompaniment_ballad` 已知局限 skip (HPSS > 0.88)

**真音频回归 (Quick 模式, v6.1 新评分基线)**:

| 音频 | 总分 | 音准 | 节奏 | 气息 | 技术 | 艺术 | 音量 |
|------|------|------|------|------|------|------|------|
| ⏳ 待更新 (需 GPU 或夜间运行) | | | | | | | |

**已知问题**:
- 真音频回归基线需重新校准 (v6.1 Artistry 公式变更)
- librosa HPSS 首次调用 8s 开销 (Windows), 后续调用正常
- E2E 测试需启动 Flask 服务, 不在 CI 中自动运行
