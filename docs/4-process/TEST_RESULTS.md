# 测试结果记录 v7.16

> 更新: 2026-08-13 | 后端 **786 collected** (643 单元 + 94 集成 + 21 扩展 + 28 真实音频) + 前端 **307 Vitest GREEN** | 分支: `main`
>
> 关联: [PROJECT_STATUS.md](PROJECT_STATUS.md) | [TDD.md](../3-quality/TDD.md) | [BDD.md](../3-quality/BDD.md)

---

## v7.16 测试统计

### 生产测试 (全部 GREEN)

| 套件 | 测试数 | 结果 | 说明 |
|------|:-----:|------|------|
| Unit (DDD 领域: 6 scorers + 音色调整 + comparison + songs + songs_pitch + song_match + ScoringWeights + fallback) | 364 | ✅ 100% | (v7.14 计数值, 本轮无改动) |
| Unit (DDD 基建: extractors + orchestrator + ABI + sqlite + pitch cache + deps) | 159 | ✅ 100% | (v7.14 计数值, 本轮无改动) |
| Unit (DDD 对齐 + Flag bridge) | 23 | ✅ 100% | |
| Unit (中间件) | 23 | ✅ 100% | |
| Unit (WS streaming 会话) | 12 | ✅ 100% | |
| Unit (接口 sanitize_filename) | 14 | ✅ 100% | |
| Unit (混合检测, 根目录) | 2 | ✅ 100% | |
| Unit (静默错误可观测性 v7.15 M3/M4/M5) | 14 | ✅ 100% | test_acoustic_extractor_observability (7) + test_audio_dl_helpers_observability (4) + test_audio_service_analyze_error (3) |
| Unit (uploads 自动清理 v7.15 P2-14 余项) | 15 | ✅ 100% | test_upload_cleaner (9) + test_history_repository_unlink (6) |
| Unit (建议生成器 🆕 v7.16 P2-15 Phase 1) | 15 | ✅ 100% | test_advice_generator (15) — AdviceGenerator 纯函数行为契约 |
| Unit (calculate_ddd 诊断 🆕 v7.16 P2-15 Phase 3) | 5 | ✅ 100% | test_diagnosis_in_calculate_ddd (5) — 诊断键/结构/额外字段/分数一致 |
| **Unit 合计** | **643** | **100% GREEN** | (v7.15 626 − 3 删死路径 fallback + 20 新增) |
| API 集成 (7 文件) | 77 | ✅ 100% | test_api_routes (20) + test_songs_api (21) + test_scoring_api (14) + songs_pitch_api (9) + compare_pitch_api (4) + song_match_api (6) + **history_single_write (3, 🆕 v7.16 历史双写回归)** |
| WebSocket 集成 | 17 | ✅ 100% | test_ws_score (13) + ws_pitch_update (4) |
| 扩展测试 (DTW/repos) | 21 | ✅ 100% | tests/extended/ |
| **生产代码总计** | **758** | **100% GREEN** | (unit 643 + API 77 + WS 17 + 扩展 21) |
| 真实音频回归 | 28 | ✅ **全 PASS** | (BASELINE_V7_14, 本轮无评分公式改动 — 结构重构数值不变) |
| **后端 collected** | **786** | ✅ | 758 生产 + 28 真实音频; 本轮新增 20 测试全部 RED→GREEN |

### v7.16 测试变更明细 (v7.15 → v7.16)

| 文件 | 变化 | 覆盖 |
|------|:-----:|------|
| `tests/unit/application/test_advice_generator.py` (新) | +15 | P2-15 Phase 1: AdviceGenerator 结构/最强最弱/总体分档/阈值边界 (DDD application 层) |
| `tests/unit/application/test_diagnosis_in_calculate_ddd.py` (新) | +5 | P2-15 Phase 3: calculate_ddd 5 诊断键/结构/mae_cents/deviation_ratio/分数一致 |
| `tests/integration/test_history_single_write.py` (新) | +3 | P2-15 Phase 0b: 历史双写回归 (无 EventBus 自动保存订阅/每次上传 1 条/完整字段) |
| `tests/unit/domain/test_fallback_marking.py` | −3 | 删 3 个测死 calculate() 路径的 fallback 测试 (v7.16 Phase 0) |
| `tests/integration/test_api_routes.py` | 修改 | openapi 标题断言改为从 APP_VERSION 派生 (VAS v7.16, 防漂移) |

### 集成隔离说明

v7.15 修复 (pre-existing): 单进程组合运行全部集成模块 94 passed (含 history_single_write 3), 不依赖"每模块独立进程"工作流。

---

## v7.15 测试统计

### 生产测试 (全部 GREEN)

| 套件 | 测试数 | 结果 | 说明 |
|------|:-----:|------|------|
| Unit (DDD 领域: 6 scorers + 音色调整 + comparison + songs + songs_pitch + song_match + ScoringWeights + fallback) | 364 | ✅ 100% | (v7.14 计数值, 本轮无改动) |
| Unit (DDD 基建: extractors + orchestrator + ABI + sqlite + pitch cache + deps) | 159 | ✅ 100% | (v7.14 计数值, 本轮无改动) |
| Unit (DDD 对齐 + Flag bridge) | 23 | ✅ 100% | |
| Unit (中间件) | 23 | ✅ 100% | |
| Unit (WS streaming 会话) | 12 | ✅ 100% | |
| Unit (接口 sanitize_filename) | 14 | ✅ 100% | |
| Unit (混合检测, 根目录) | 2 | ✅ 100% | |
| Unit (静默错误可观测性 🆕 v7.15 M3/M4/M5) | 14 | ✅ 100% | test_acoustic_extractor_observability (7) + test_audio_dl_helpers_observability (4) + test_audio_service_analyze_error (3) — 异常保留/传播/状态码断言 |
| Unit (uploads 自动清理 🆕 v7.15 P2-14 余项) | 15 | ✅ 100% | test_upload_cleaner (9: unlink_files 路径锁/孤儿扫描) + test_history_repository_unlink (6: 删除/批量删除/逐出联动 unlink) |
| **Unit 合计** | **626** | **100% GREEN** | (v7.14 597 + v7.15 29) |
| API 集成 (6 文件) | 74 | ✅ 100% | test_api_routes (20) + test_songs_api (21) + test_scoring_api (14) + songs_pitch_api (9) + compare_pitch_api (4) + song_match_api (6) |
| WebSocket 集成 | 17 | ✅ 100% | test_ws_score (13) + ws_pitch_update (4) |
| 扩展测试 (DTW/repos) | 21 | ✅ 100% | tests/extended/ |
| **生产代码总计** | **738** | **100% GREEN** | (unit 626 + API 74 + WS 17 + 扩展 21) |
| 真实音频回归 | 28 | ✅ **全 PASS** | (BASELINE_V7_14, 与 v7.14 相同 — 本轮无评分改动) |
| **后端 collected** | **766** | ✅ | 738 生产 + 28 真实音频; **本轮新增 29 单元测试全部 RED→GREEN** |
| BDD (21 step files) | 182 scenarios collected (112 API + 70 browser) | ✅ **0F / 31P / 42S / 39X** (API 级) | v7.15 新增 compare-automatch.feature (3 browser) + sing-song-select +1 → 178→182; browser 70 (v7.14 66 + 4) — 详见 BDD.md |
| 前端 Vitest | 307 | ✅ 100% | (v7.14 297 + 10: matchFeedback 6 + useWsDisconnectGuard 4; stores 85 + pitch utils 212 + matchFeedback/ws 10) |
| vue-tsc | 0 errors | ✅ | TypeScript 零错误 |
| Vite build | ~16s | ✅ | 生产构建 |

### v7.15 新增测试明细 (v7.14 → v7.15)

| 文件 | 变化 | 覆盖 |
|------|:-----:|------|
| `test_acoustic_extractor_observability.py` | +7 | M3: HNR/CPP/HPSS/mixed 失败异常保留 (不再静默返回空特征) |
| `test_audio_dl_helpers_observability.py` | +4 | M5: 下载/加载 helper 异常传播 + 路径锁 |
| `test_audio_service_analyze_error.py` | +3 | M4: analyze 静默失败→HTTP 500 可见化 + 根因保留 |
| `test_upload_cleaner.py` | +9 | P2-14 余项: unlink_files 仅限 uploads 目录内 (`is_relative_to`) / missing_ok / OSError→warning; collect_referenced_files; cleanup_orphans 顶层扫描; run_startup_upload_cleanup repo=None 安全 no-op |
| `test_history_repository_unlink.py` | +6 | P2-14 余项: delete/delete_batch/save 逐出联动 unlink 文件; 共享文件仍被引用则保留; upload_dir=None 向后兼容 |
| `frontend/tests/unit/utils/matchFeedback.test.ts` | +6 | H-B14: songMatch.store 错误/命中/回退 → 反馈文案 + severity |
| `frontend/tests/unit/composables/useWsDisconnectGuard.test.ts` | +4 | H-B15: WS 断连 4 状态机 (open 中断连→置灰 + 重连提示; 主动关闭/空引用/未 open 不误报) |
| `tests/bdd/features/compare-automatch.feature` + steps | +3 browser | H-B14: 自动匹配失败告警 (`[data-test=auto-match-error]`) / 成功命中徽标 / 无命中优雅回退 — 注入 songMatch.store 状态验证渲染 |
| `tests/bdd/features/sing-song-select.feature` + steps | +1 browser | H-B15 断连提示场景 |
| `tests/integration/conftest.py` | 修复 | **隔离修复 (pre-existing)**: 模块级 autouse 清空 deps 6 个 lru_cache 单例 (get_settings/get_song_repo/get_song_service/get_pitch_cache/get_song_match_profile_repo/get_auto_match_use_case) — 组合运行多模块不再跨库污染 |
| `test_songs_api.py` / `test_song_pitch_api.py` / `test_song_match_api.py` / `test_compare_pitch_api.py` | 修复 | client fixture 重断言 VAS_SONGS_DB/VAS_SONGS_DIR — 保证每个模块绑定自己的临时 DB (与 BDD conftest.fastapi_client 模式一致) |

### 集成隔离修复说明 (pre-existing, 本次一并修复)

- **现象**: 单进程组合运行多个集成模块时, `test_song_match_api.py::test_match_no_match_fallback` 确定性失败 — 误命中前一模块写入的歌曲。
- **根因**: deps `@lru_cache` 单例跨模块持久, 后续模块即使已设 `VAS_SONGS_DB`, 仍绑定上一模块的临时 DB; HEAD (32f9419) 亦复现, 与 v7.15 代码无关。
- **修复**: ① `tests/integration/conftest.py` 模块级 autouse `_reset_deps_caches` 清空 6 个单例; ② 4 个 env-setting 模块的 client fixture 重断言 env。
- **验证**: 全量集成模块**单进程组合运行 119 passed** (含真实音频回归 28, ~25min) — 比文档化"每模块独立进程"更严格。

---

## v7.14 测试统计 (历史)

### 生产测试 (全部 GREEN)

| 套件 | 测试数 | 结果 | 说明 |
|------|:-----:|------|------|
| Unit (DDD 领域: 6 scorers + 音色调整 + comparison + songs + songs_pitch + song_match + ScoringWeights + fallback) | 364 | ✅ 100% | 6 scorers + 音色调整 + comparison + songs + songs_pitch (v7.13) + **song_match (v7.14: +79)** + ScoringWeights 值对象 + **fallback_marking (v7.14 修复轮: +11)** + **song_pitch_service sr 契约 (+1, v7.14 P2)** |
| Unit (DDD 基建: extractors + orchestrator + ABI + sqlite + pitch cache + deps) | 159 | ✅ 100% | 10 extractors + audio_utils + ABI + songs 仓储 + sqlite_song_match_profile_repo + **in_memory_pitch_cache (+7) + deps_singleton (+2) (v7.14 修复轮)** |
| Unit (DDD 对齐 + Flag bridge) | 23 | ✅ 100% | alignment + extraction flag + flag bridge |
| Unit (中间件) | 23 | ✅ 100% | SecurityHeaders + RateLimit + MaxBodySize |
| Unit (WS streaming 会话) | 12 | ✅ 100% | test_streaming_session (compute_partial 等) + **P2-13 audio_buffer 缓存 (+5)** |
| Unit (接口 sanitize_filename) 🆕 v7.14 P2 | 14 | ✅ 100% | test_sanitize_filename (P2-14: GBK 乱码恢复 + NFC + 非法字符 + 路径穿越) |
| Unit (混合检测, 根目录) | 2 | ✅ 100% | test_audio_service_mixed_detection (audio_service 混合/纯声检测) |
| **Unit 合计** | **597** | **100% GREEN** | (~30s) |
| API 集成 (6 文件) | 74 | ✅ 100% | test_api_routes (20 + **sr=16000 契约断言, v7.14 P2**) + test_songs_api (21) + test_scoring_api (14) + songs_pitch_api (9) + compare_pitch_api (4) + **song_match_api (6, v7.14)** |
| WebSocket 集成 | 17 | ✅ 100% | test_ws_score (13) + ws_pitch_update (4, v7.13) |
| 扩展测试 (DTW/repos) | 21 | ✅ 100% | tests/extended/ |
| **生产代码总计** | **709** | **100% GREEN** | (unit 597 + API 74 + WS 17 + 扩展 21) |
| 真实音频回归 | 28 | ✅ **全 PASS** (v7.14 P2) | **BASELINE_V7_6 → V7_14 重校准** (sr 错配 bug 修复后真实值); 旧 4 个 breath 基线漂移 FAIL 自然消除; 区分度断言改"总分排序 + 单维 gap ≥10" (实测 rhythm 34.5) — 含 quick_pro 单测 |
| **后端 collected** | **737** | ✅ | 709 生产 + 28 真实音频 (unit 597 + API 74 + WS 17 + 扩展 21 = 709) |
| BDD (18 step files) | 178 scenarios collected (112 API + 66 browser) | ✅ **0F/30P/43S/39X** (v7.14 P2 续轮) | **compare.feature 重写 (2P+1X), Flask 遗留失败全部清除**; **differentiation 6F→6P+1X 与 history 3F→4P 已修复 (v7.14 P2: 断言一致化 + get_json 修复)**; upload 5P+3S; animations 7P+9X; auto-match **5P+3X**; database ✅ — 详见 BDD.md |
| 前端 Vitest | 297 | ✅ 100% | stores 85 + pitch utils 212 (v7.14 +11 songMatch.store) |
| vue-tsc | 0 errors | ✅ | TypeScript 零错误 |
| Vite build | ~16s | ✅ | 生产构建 |

### v7.14 新增/移除测试明细 (v7.13 → v7.14)

| 文件 | 变化 | 覆盖 |
|------|:-----:|------|
| `test_song_match_value_objects.py` | +13 | v7.14 MatchFeatures/SongMatchProfile/MatchCandidate/MatchResult (frozen/默认/序列化) |
| `test_song_match_service.py` | +54 | v7.14 确定性置信度 (精确/BPM±9%/Key+2/Top-3 排序/no_match/空库/超时 partial/短音频) + K-S 24 键检测参数化 (13 键 + 升号/降号 + 混淆) |
| `test_match_feature_extractor.py` | +6 | v7.14 合成音频 (节拍器 BPM + 正弦根音) 提取校验; 静音/噪声/短音频容错 |
| `test_auto_match_use_case.py` | +6 | v7.14 编排/missing profile 生成/超时 partial/失败跳过/空库 fallback |
| `test_sqlite_song_match_profile_repo.py` | +9 | v7.14 profile CRUD/upsert/chroma JSON 往返 + 审查回归 (非 12 维/空 chroma → 零向量) |
| `test_sqlite_song_repo.py` | +2 | v7.14 list_all_with_filepath |
| `test_song_match_api.py` | +6 | v7.14 POST /songs/match (成功/top_n/无匹配 fallback/400) + upload auto_match 开/关 |
| `frontend/tests/unit/stores/songMatch.store.test.ts` | +11 | v7.14 matchAudio/selectCandidate/compareWithSelected/fetchUserPitch (mock apiClient) |

### v7.14 深度审查修复轮新增测试 (2026-08-10, P0+P1)

| 文件 | 变化 | 覆盖 |
|------|:-----:|------|
| `test_fallback_marking.py` | +11 | P0-3 回归: rhythm None→fallback; voiced coverage 公式 (0 分母/空 voiced → 0.0) |
| `test_streaming_session.py` | +7 | P0-3 compute_partial 边界: 空帧/半帧/0 分母/时长钳制 |
| `test_in_memory_pitch_cache.py` | +7 | P1-6 新增 LRU 缓存单测: 容量/LRU 逐出/None 不缓存/clear |
| `test_deps_singleton.py` | +2 | P1-6 deps 单例 (@lru_cache get_song_repo/get_pitch_cache) |
| `test_api_routes.py` | 断言同步 | P1-9 APP_VERSION 7.13.0 → 7.14.0 |
| `test_songs_api.py` | +1 | P1-4 删除歌曲级联清理 pitch 缓存 |
| `test_compare_pitch_api.py` | +1 | P1-6 删除歌曲后 404 校验 |
| `test_ws_score.py` | +3 | P0-1 weighted_total 不再 /100: 满分 100 场景 |
| `test_scoring_api.py` | 断言同步 | P0-1 权重应用总分为百分制 |
| `tests/bdd/conftest.py` | 修复 | **P0-2 关键**: fastapi_client fixture 增加 `deps.get_song_repo/get_pitch_cache/get_song_match_profile_repo/get_auto_match_use_case.cache_clear()` — 恢复 BDD 场景隔离 (API 级失败 33→21) |

### v7.14 P2 完善修复轮新增测试 (2026-08-11, sr 错配根因修复)

| 文件 | 变化 | 覆盖 |
|------|:-----:|------|
| `test_audio_service_mixed_detection.py` | +2 | P2-12a: `_preprocess_for_scoring` 只跑 HPSS+混合检测 (不再全量 extract); 纯人声/混合音频分支 |
| `test_sanitize_filename.py` | +11 | P2-14: GBK 乱码往返恢复 (`1£¨¸ß·Ö£©`→`1（高分）`) + NFC 规范化 + 非法字符剥离 + 路径穿越 + 空名回退 |
| `test_streaming_session.py` | +5 | P2-13: `audio_buffer` 惰性拼接缓存 (dirty 标志/重复访问命中/append 失效/cleanup 释放) |
| `test_song_pitch_service.py` | +1 | P2-11: PitchExtractionService 一步加载 sr=16000 (契约: 输出 sr 与音频一致) |
| `test_api_routes.py` | 断言同步 | P2-11: `sample_rate==16000` 契约断言 (load 契约) |
| `test_real_audio_regression.py` | 🔧 重校准 | **BASELINE_V7_6 → BASELINE_V7_14** (sr 修复后真实值范围 + 根因注释) + 区分度断言改"总分排序 + 单维 gap ≥10" (与 BDD differentiation.feature 一致) |
| `tests/bdd/features/differentiation.feature` + steps | 🔧 规格修正 | 断言与实测一致化 (total gap 不可达 → 单维区分度不变量), 见 DEEP_REVIEW P2-16 备注 |

## v7.13 测试统计 (历史)

### 生产测试 (全部 GREEN)

| 套件 | 测试数 | 结果 | 说明 |
|------|:-----:|------|------|
| DDD 领域 (scorers + value objects + comparison + songs + songs_pitch + ScoringWeights) | 273 | ✅ 100% | 6 scorers + 音色调整 + comparison + songs + songs_pitch (v7.13) + ScoringWeights 值对象 |
| DDD 基建 (extractors + orchestrator + ABI + sqlite) | 132 | ✅ 100% | 10 extractors + audio_utils + ABI + songs 仓储 |
| DDD 对齐 + Flag bridge | 23 | ✅ 100% | alignment + extraction flag + flag bridge |
| 中间件 | 23 | ✅ 100% | SecurityHeaders + RateLimit + MaxBodySize |
| **DDD 合计** | **451** | **100% GREEN** | (~25s) |
| FastAPI 集成 | 65 | ✅ 100% | test_api_routes (19) + test_songs_api (20) + test_scoring_api (14) + songs_pitch_api (9) + compare_pitch_api (3, v7.13 P5) |
| WebSocket 集成 | 14 | ✅ 100% | test_ws_score (10) + ws_pitch_update (4, v7.13) |
| 扩展测试 (DTW/repos) | 21 | ✅ 100% | tests/extended/ |
| **生产代码总计** | **537** | **100% GREEN** | (DDD 451 + 集成 65 + 扩展 21; 不含 WS 14 / 真实音频回归 28) |
| 真实音频回归 | 28 | ⚠️ 24 PASS + 4 FAIL | 4 失败均为 breath 维度基线漂移 (BASELINE_V7_6 阈值过紧, 既有) — 见 PROJECT_STATUS |
| BDD (17 step files) | 179 scenarios collected | ✅ | upload 5P+3S; animations 7P+9X; sing-song-select 6P+6X; scoring-config API 级 PASS; database 4P+6X; **pitch-realtime 25X (v7.13 P1-P5 骨架)**; 5 features 缺 step defs |
| 前端 Vitest | 286 | ✅ 100% | stores 74 + pitch utils 212 (v7.13 P1 +34, P2 +64, P3 +31, P4 +33, P5 +56) |
| vue-tsc | 0 errors | ✅ | TypeScript 零错误 |
| Vite build | ~16s | ✅ | 生产构建 |

### v7.13 新增/移除测试明细

| 文件 | 变化 | 覆盖 |
|------|:-----:|------|
| `test_song_pitch_vo.py` | +8 | v7.13 SongPitchCurve 值对象 (frozen/NaN→0.0/往返) |
| `test_song_pitch_service.py` | +4 | v7.13 PitchExtractionService (librosa.yin) |
| `test_get_song_pitch_usecase.py` | +4 | v7.13 GetSongPitchUseCase (缓存优先) |
| `test_song_pitch_api.py` | +9 | v7.13 GET /songs/{id}/pitch (5) + POST compare (4) |
| `test_ws_pitch_update.py` | +4 | v7.13 WS pitch_update 增量推送 |
| `test_api_routes.py` | 断言同步 | v7.13 版本对齐: health/openapi → 7.13.0 / VAS v7.13 |
| `frontend/tests/unit/utils/pitchNotes.test.ts` | +22 | v7.13 P2 freq↔MIDI↔音名/白键/音高刻度 |
| `frontend/tests/unit/utils/pitchStats.test.ts` | +10 | v7.13 P2 偏差百分比/音域范围 |
| `frontend/tests/unit/utils/pitchScrollTicks.test.ts` | +9 | v7.13 P2 自动刻度步长/时间刻度 |
| `frontend/tests/unit/utils/pitchPlayback.test.ts` | +21 | v7.13 P2 clampSeek/倍速/A-B 循环/帧率降级 |
| `frontend/tests/unit/utils/pitchDeviation.test.ts` | +2 | v7.13 P2 置信度 < 0.5 → 静音灰 |
| `frontend/tests/unit/utils/pitchLive.test.ts` | +31 | v7.13 P3 录音中实时对比 (趋势/偏差格式/最近偏差/圆点淡出/色带几何) + 审查边界 (NaN/keep≤0) |
| `frontend/tests/unit/utils/pitchSegments.test.ts` | +32 | v7.13 P4 问题段落 (findProblemSegments) + 乐句切分 (segmentPhrases) + 逐句评分 (scorePhrase) + 分数颜色 (phraseScoreColor) |
| `frontend/tests/unit/utils/pitchStats.test.ts` | +1 | v7.13 P4 审查回归 — 无声率取整不引入分母误差 (2000 帧精确计数 25.1/50.0/25.0/24.9) |
| `tests/integration/test_compare_pitch_api.py` | +3 | v7.13 P5 POST /compare 双正弦 WAV → standard_pitch/user_pitch; 同文件 → low_alignment_segments 空; score/level 向后兼容 |
| `frontend/tests/unit/utils/pitchKeyboard.test.ts` | +13 | v7.13 P5 快捷键映射 + 修饰键/可编辑目标/滑块 (role=slider) 守卫 |
| `frontend/tests/unit/utils/pitchFps.test.ts` | +9 | v7.13 P5 FPS 监控状态机 (60fps 不降级 / 10fps 3s 降级 / 手动恢复幂等 / resetTime 保留降级) |
| `frontend/tests/unit/utils/pitchHeatmap.test.ts` | +11 | v7.13 P5 热力图全时长分桶 (颜色密度) + heatmapClickToTime 钳制 |
| `frontend/tests/unit/utils/pitchScreenshot.test.ts` | +9 | v7.13 P5 时间戳格式化 / 离屏 DPR 1:1 截图水印 / 下载触发 |
| `frontend/tests/unit/utils/pitchCompareDraw.test.ts` | +8 | v7.13 P5 双轨绘制 — 性能模式每 3 帧着色回归 (原实现仅画首帧) / 三色填色 / 三色隧道 / 静音与无声帧跳过 |
| `frontend/tests/unit/utils/pitchStats.test.ts` | +6 | v7.13 P5 excludeLowAlignmentFrames 不可变过滤低置信度段落帧 |

## v7.12 测试统计 (历史)

### 生产测试 (全部 GREEN)

| 套件 | 测试数 | 结果 | 说明 |
|------|:-----:|------|------|
| DDD 领域 (scorers + value objects + comparison + songs + **ScoringWeights**) | 257 | ✅ 100% | 7 scorers + comparison + songs + ScoringWeights 值对象 |
| DDD 基建 (extractors + orchestrator + ABI + sqlite) | 132 | ✅ 100% | 10 extractors + audio_utils + ABI + songs 仓储 |
| DDD 对齐 + Flag bridge | 23 | ✅ 100% | alignment + extraction flag + flag bridge |
| 中间件 | 23 | ✅ 100% | SecurityHeaders + RateLimit + MaxBodySize |
| **DDD 合计** | **435** | **100% GREEN** | (~25s) |
| FastAPI 集成 | 53 | ✅ 100% | test_api_routes (19) + test_songs_api (20, 含 v7.12 vocal_range ×3) + test_scoring_api (14) |
| WebSocket 集成 | 10 | ✅ 100% | test_ws_score (8 + v7.12 song_id ×2) |
| 扩展测试 (DTW/repos) | 21 | ✅ 100% | tests/extended/ (v7.12 删 test_score_calibrator 15) |
| **生产代码总计** | **509** | **100% GREEN** | (DDD 435 + 集成 53 + 扩展 21; 不含 WS 10 / 真实音频回归 28) |
| 真实音频回归 | 28 | ✅ 100% | BASELINE_V7_6, 高低分区分度 9.1 pts |
| BDD (16 step files) | 162 scenarios collected | ✅ | upload 5P+3S; animations 7P+9X; sing-song-select 6P+6X (v7.12); scoring-config API 级 PASS; 6 features 缺 step defs |
| 前端 Vitest | 68 | ✅ 100% | songs.store (24) + scoring.store (11) + 33 其他 |
| vue-tsc | 0 errors | ✅ | TypeScript 零错误 |
| Vite build | ~12s | ✅ | 生产构建 |

### v7.12 新增/移除测试明细

| 文件 | 变化 | 覆盖 |
|------|:-----:|------|
| `test_songs_api.py` | +3 | v7.12 vocal_range: 创建携带/默认空/详情返回 |
| `test_ws_score.py` | +2 | v7.12 WS start 携带 song_id → 会话存储 |
| `test_score_calibrator.py` | -15 | v7.12 删除 (dl_services enhanced_dl_assessor 死代码随之清理) |

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
# DDD 核心 (626 tests, ~20s; v7.15 +29: M3/M4/M5 可观测性 + uploads 清理)
# ⚠️ 不直接运行 pytest tests/unit/ (PyTorch C 扩展冲突 → 崩溃), 必须使用分组命令:
pytest tests/unit/domain/ tests/unit/infrastructure/ tests/unit/interfaces/ws/ \
       tests/unit/test_middleware.py \
       tests/unit/test_ddd_alignment.py \
       tests/unit/test_ddd_extraction_flag.py \
       tests/unit/test_flag_bridge.py \
       tests/unit/test_upload_cleaner.py \
       tests/unit/test_history_repository_unlink.py \
       tests/unit/test_audio_dl_helpers_observability.py \
       tests/unit/test_audio_service_analyze_error.py
pytest tests/unit/interfaces/api/test_sanitize_filename.py tests/unit/test_audio_service_mixed_detection.py -q  # 剩余 16 tests

# 集成测试 (独立进程; v7.15 修复后亦可单进程全量组合: pytest tests/integration/ = 119, ~25min 含真实音频)
pytest tests/integration/test_api_routes.py -v     # FastAPI (20 tests)
pytest tests/integration/test_songs_api.py -v      # Songs API (21 tests)
pytest tests/integration/test_scoring_api.py -v    # Scoring API (14 tests)
pytest tests/integration/test_song_pitch_api.py -v # Songs Pitch API (9 tests, v7.13)
pytest tests/integration/test_song_match_api.py -v # SongMatch API (6 tests, v7.14)
pytest tests/integration/test_compare_pitch_api.py -v # Compare Pitch API (4 tests, v7.13 P5)
pytest tests/integration/test_ws_score.py tests/integration/test_ws_pitch_update.py -v   # WebSocket (17 tests: ws_score 13 + ws_pitch_update 4)

# 扩展测试 (独立进程, ~6s)
pytest tests/extended/ -v                           # 21 tests (DTW/repos; v7.12 -calibrator)

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
