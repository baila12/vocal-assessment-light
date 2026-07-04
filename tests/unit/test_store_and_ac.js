/**
 * Store + AnimationController 集成测试
 *
 * 使用真实 Store, AnimationController, 和 Presets 模块进行测试。
 * Mock 仅用于 GSAP（因为 GSAP 在测试环境无 DOM 渲染）。
 *
 * 运行方式: 通过 Playwright E2E 测试在浏览器中执行
 *   python tests/tools/run_js_unit_tests.py
 *
 * @version 2.0
 */

window.__storeAndACTests = {

  // ==========================================================================
  // Store 测试
  // ==========================================================================

  /** 1. Store 初始化具有默认状态 */
  testStoreInitialization() {
    const Store = window.__StoreClass;
    if (!Store) return { pass: false, reason: 'Store module not loaded' };

    const store = new Store();
    const state = store.getState();

    const checks = [
      state.route !== undefined,
      state.route.current === '#/',
      state.analysis !== undefined,
      state.analysis.mode === 'quick',
      state.analysis.status === 'idle',
      state.preferences !== undefined,
      state.preferences.evalMode === 'quick',
    ];

    return {
      pass: checks.every(Boolean),
      checks,
      detail: `${checks.filter(Boolean).length}/${checks.length} checks passed`
    };
  },

  /** 2. setState 合并更新 */
  testStoreSetState() {
    const Store = window.__StoreClass;
    if (!Store) return { pass: false, reason: 'Store module not loaded' };

    const store = new Store();

    // 更新嵌套路径
    store.setState({ mode: 'professional' }, 'analysis');
    const analysisState = store.getState('analysis');
    const check1 = analysisState.mode === 'professional';

    // 更新顶层
    store.setState({ selectedFile: { name: 'test.mp3', size: 1024 } });
    const fullState = store.getState();
    const check2 = fullState.selectedFile !== undefined;
    const check3 = fullState.selectedFile.name === 'test.mp3';

    return {
      pass: check1 && check2 && check3,
      check1, check2, check3,
      detail: `mode=${analysisState.mode}, file=${fullState.selectedFile?.name}`
    };
  },

  /** 3. subscribe 接收更新 */
  testStoreSubscribe() {
    const Store = window.__StoreClass;
    if (!Store) return { pass: false, reason: 'Store module not loaded' };

    const store = new Store();
    let receivedValue = null;

    const unsub = store.subscribe('analysis.mode', (val) => {
      receivedValue = val;
    });

    store.setState({ mode: 'professional' }, 'analysis');

    const check1 = receivedValue === 'professional';

    // 取消订阅后不应再收到更新
    unsub();
    store.setState({ mode: 'quick' }, 'analysis');
    const check2 = receivedValue === 'professional'; // 仍然是旧值

    return {
      pass: check1 && check2,
      received: receivedValue,
      detail: `received=${receivedValue}, unsubbed=${check2}`
    };
  },

  /** 4. Store 事件总线 on/emit */
  testStoreEvents() {
    const Store = window.__StoreClass;
    if (!Store) return { pass: false, reason: 'Store module not loaded' };

    const store = new Store();
    let eventData = null;

    store.on('test:event', (data) => {
      eventData = data;
    });

    store.emit('test:event', { value: 42 });

    return {
      pass: eventData !== null && eventData.value === 42,
      eventData,
      detail: `event received: ${JSON.stringify(eventData)}`
    };
  },

  /** 5. Store persist 写入 localStorage */
  testStorePersist() {
    const Store = window.__StoreClass;
    if (!Store) return { pass: false, reason: 'Store module not loaded' };

    const store = new Store();
    store.persist('preferences');
    store.setState({ evalMode: 'professional' }, 'preferences');

    const stored = localStorage.getItem('vocal_app_preferences');
    const parsed = stored ? JSON.parse(stored) : null;

    return {
      pass: parsed !== null && parsed.evalMode === 'professional',
      stored,
      detail: `localStorage has evalMode=${parsed?.evalMode}`
    };
  },

  // ==========================================================================
  // AnimationController 测试
  // ==========================================================================

  /** 6. AnimationController 初始化 (真实模块, mock GSAP) */
  testACInitialization() {
    const AnimationController = window.__AnimationControllerClass;
    const Store = window.__StoreClass;
    if (!AnimationController) return { pass: false, reason: 'AnimationController module not loaded' };

    const mockGSAP = _createMockGSAP();
    const ac = new AnimationController(mockGSAP, { detectReducedMotion: false });

    const checks = [
      ac.enabled === true,
      typeof ac.enter === 'function',
      typeof ac.leave === 'function',
      typeof ac.stagger === 'function',
      typeof ac.countUp === 'function',
      typeof ac.fillBar === 'function',
      typeof ac.setEnabled === 'function',
      typeof ac.killAll === 'function',
    ];

    return {
      pass: checks.every(Boolean),
      passed: checks.filter(Boolean).length,
      total: checks.length,
      detail: `${checks.filter(Boolean).length}/${checks.length} methods found`
    };
  },

  /** 7. enter() 使用真实预设 */
  testACEnterWithRealPreset() {
    const AnimationController = window.__AnimationControllerClass;
    if (!AnimationController) return { pass: false, reason: 'AnimationController module not loaded' };

    const mockGSAP = _createMockGSAP();
    const ac = new AnimationController(mockGSAP, { detectReducedMotion: false });

    const el = document.createElement('div');
    document.body.appendChild(el);

    ac.enter(el, { preset: 'page-enter' });

    const lastTween = mockGSAP._tweens[mockGSAP._tweens.length - 1];
    document.body.removeChild(el);

    return {
      pass: lastTween?.type === 'fromTo',
      tweenType: lastTween?.type,
      from: lastTween?.fromVars,
      to: lastTween?.toVars,
      detail: 'enter() should create gsap.fromTo with real preset'
    };
  },

  /** 8. setEnabled(false) 跳过动画 */
  testACDisabled() {
    const AnimationController = window.__AnimationControllerClass;
    if (!AnimationController) return { pass: false, reason: 'AnimationController module not loaded' };

    const mockGSAP = _createMockGSAP();
    const ac = new AnimationController(mockGSAP, { detectReducedMotion: false });
    ac.setEnabled(false);

    const el = document.createElement('div');
    const beforeCount = mockGSAP._tweens.length;
    ac.enter(el, { preset: 'page-enter' });
    const afterCount = mockGSAP._tweens.length;

    return {
      pass: afterCount === beforeCount,
      beforeCount, afterCount,
      detail: 'disabled AC should not create tweens'
    };
  },

  /** 9. stagger() 创建带 stagger 参数的动画 */
  testACStagger() {
    const AnimationController = window.__AnimationControllerClass;
    if (!AnimationController) return { pass: false, reason: 'AnimationController module not loaded' };

    const mockGSAP = _createMockGSAP();
    const ac = new AnimationController(mockGSAP, { detectReducedMotion: false });

    const elements = [
      document.createElement('div'),
      document.createElement('div'),
      document.createElement('div')
    ];
    elements.forEach(el => document.body.appendChild(el));

    ac.stagger(elements, { preset: 'slideUp', stagger: 0.1 });

    const lastTween = mockGSAP._tweens[mockGSAP._tweens.length - 1];
    elements.forEach(el => document.body.removeChild(el));

    return {
      pass: lastTween?.vars?.stagger !== undefined,
      staggerValue: lastTween?.vars?.stagger,
      detail: 'stagger() should set stagger param'
    };
  },

  /** 10. countUp() 使用 snap.textContent 进行数字动画 */
  testACCountUp() {
    const AnimationController = window.__AnimationControllerClass;
    if (!AnimationController) return { pass: false, reason: 'AnimationController module not loaded' };

    const mockGSAP = _createMockGSAP();
    const ac = new AnimationController(mockGSAP, { detectReducedMotion: false });

    const el = document.createElement('span');
    el.textContent = '0';
    document.body.appendChild(el);

    ac.countUp(el, 88.5, { duration: 1.2 });

    const lastTween = mockGSAP._tweens[mockGSAP._tweens.length - 1];
    document.body.removeChild(el);

    const hasSnap = lastTween?.vars?.snap?.textContent !== undefined;

    return {
      pass: hasSnap,
      snap: lastTween?.vars?.snap,
      detail: 'countUp() should use snap.textContent for number rolling'
    };
  },

  /** 11. fillBar() 使用 scaleX (compositor-only) */
  testACFillBar() {
    const AnimationController = window.__AnimationControllerClass;
    if (!AnimationController) return { pass: false, reason: 'AnimationController module not loaded' };

    const mockGSAP = _createMockGSAP();
    const ac = new AnimationController(mockGSAP, { detectReducedMotion: false });

    const el = document.createElement('div');
    document.body.appendChild(el);

    ac.fillBar(el, 75);

    const lastTween = mockGSAP._tweens[mockGSAP._tweens.length - 1];
    document.body.removeChild(el);

    return {
      pass: lastTween?.vars?.scaleX !== undefined,
      props: Object.keys(lastTween?.vars || {}),
      detail: 'fillBar() should use scaleX (compositor-friendly)'
    };
  },

  /** 12. 未知预设 — 优雅降级不崩溃 */
  testACUnknownPreset() {
    const AnimationController = window.__AnimationControllerClass;
    if (!AnimationController) return { pass: false, reason: 'AnimationController module not loaded' };

    const mockGSAP = _createMockGSAP();
    const ac = new AnimationController(mockGSAP, { detectReducedMotion: false });

    const el = document.createElement('div');
    let threw = false;
    try {
      ac.enter(el, { preset: 'non-existent-preset-xyz' });
    } catch (e) {
      threw = true;
    }

    return {
      pass: !threw,
      detail: 'unknown preset should fallback gracefully, not throw'
    };
  },

  /** 13. killAll() 杀死所有活跃动画 */
  testACKillAll() {
    const AnimationController = window.__AnimationControllerClass;
    if (!AnimationController) return { pass: false, reason: 'AnimationController module not loaded' };

    const mockGSAP = _createMockGSAP();
    const ac = new AnimationController(mockGSAP, { detectReducedMotion: false });

    let killedCount = 0;
    const origKill = mockGSAP.killTweensOf;
    mockGSAP.killTweensOf = () => { killedCount++; };

    ac.killAll();
    mockGSAP.killTweensOf = origKill;

    return {
      pass: killedCount >= 1,
      killedCount,
      detail: 'killAll() should call gsap.killTweensOf'
    };
  },

  // ==========================================================================
  // Presets 测试
  // ==========================================================================

  /** 14. 所有预设定义有效 */
  testPresetsValid() {
    const PRESETS = window.__presets;
    const hasPreset = window.__hasPreset;

    if (!PRESETS) return { pass: false, reason: 'Presets not loaded' };

    const required = [
      'page-enter', 'page-enter-down', 'page-enter-scale', 'page-leave',
      'slideUp', 'slideInRight', 'popIn', 'fadeIn-stagger',
      'toast-enter', 'toast-exit', 'fillBar'
    ];

    const missing = required.filter(name => !hasPreset(name));

    // 验证已知预设的结构
    const structuralErrors = [];
    for (const [name, preset] of Object.entries(PRESETS)) {
      if (preset.type === 'fromTo') {
        if (!preset.from) structuralErrors.push(`${name}: missing 'from'`);
        if (!preset.to) structuralErrors.push(`${name}: missing 'to'`);
      }
      if (preset.type === 'timeline') {
        if (!Array.isArray(preset.steps)) structuralErrors.push(`${name}: missing 'steps' array`);
      }
    }

    return {
      pass: missing.length === 0 && structuralErrors.length === 0,
      missing,
      structuralErrors,
      totalPresets: Object.keys(PRESETS).length,
      detail: `${Object.keys(PRESETS).length} presets, ${missing.length} missing, ${structuralErrors.length} structural errors`
    };
  },

  // ==========================================================================
  // 模式选择集成测试
  // ==========================================================================

  /** 15. 模式切换通过 Store 工作 */
  testModeSwitchViaStore() {
    const Store = window.__StoreClass;
    if (!Store) return { pass: false, reason: 'Store module not loaded' };

    const store = new Store();
    store.persist('preferences');

    // 默认 quick
    const check1 = store.getState('preferences').evalMode === 'quick';

    // 切换到 professional
    store.setState({ evalMode: 'professional' }, 'preferences');
    const check2 = store.getState('preferences').evalMode === 'professional';

    // localStorage 应同步
    const stored = localStorage.getItem('vocal_app_preferences');
    const parsed = stored ? JSON.parse(stored) : {};
    const check3 = parsed.evalMode === 'professional';

    return {
      pass: check1 && check2 && check3,
      check1, check2, check3,
      detail: `default=${check1}, switch=${check2}, persist=${check3}`
    };
  },

  /** 16. 切换模式不影响已选文件状态 */
  testModeSwitchPreservesFile() {
    const Store = window.__StoreClass;
    if (!Store) return { pass: false, reason: 'Store module not loaded' };

    const store = new Store();

    // 选择文件
    store.setState({
      file: { name: 'test.mp3', size: 1024 },
      name: 'test.mp3',
      duration: 120,
      url: 'blob:test',
      format: 'mp3'
    }, 'audio');

    // 切换模式
    store.setState({ mode: 'professional' }, 'analysis');

    // 文件应该还在
    const audio = store.getState('audio');
    const check1 = audio.file !== null;
    const check2 = audio.name === 'test.mp3';

    return {
      pass: check1 && check2,
      file: audio.file?.name,
      mode: store.getState('analysis').mode,
      detail: `file=${audio.name}, mode=${store.getState('analysis').mode}`
    };
  },

  // ==========================================================================
  // 运行全部
  // ==========================================================================

  runAll() {
    const results = {};
    const testKeys = Object.keys(window.__storeAndACTests).filter(k => k.startsWith('test'));

    testKeys.forEach(name => {
      try {
        results[name] = window.__storeAndACTests[name]();
      } catch (e) {
        results[name] = { pass: false, error: String(e.message || e), stack: String(e.stack || '') };
      }
    });

    const passed = Object.values(results).filter(r => r && r.pass).length;
    const total = testKeys.length;

    return { results, summary: `${passed}/${total} tests passed`, passed, total };
  }
};

// ============================================================================
// Mock GSAP (唯一保留的 mock — GSAP 在无渲染环境无法工作)
// ============================================================================
function _createMockGSAP() {
  const tweens = [];
  const mockTween = () => ({
    kill: () => {}, pause: () => {}, play: () => {},
    then: () => Promise.resolve()
  });

  return {
    to: (target, vars) => { tweens.push({ type: 'to', target, vars }); return mockTween(); },
    from: (target, vars) => { tweens.push({ type: 'from', target, vars }); return mockTween(); },
    fromTo: (target, fromVars, toVars) => {
      tweens.push({ type: 'fromTo', target, fromVars, toVars, vars: toVars });
      return mockTween();
    },
    set: (target, vars) => { tweens.push({ type: 'set', target, vars }); return mockTween(); },
    timeline: () => ({
      to: function() { return this; }, from: function() { return this; },
      fromTo: function() { return this; }, set: function() { return this; },
      add: function() { return this; }, kill: () => {}, clear: () => {}
    }),
    killTweensOf: () => {},
    config: () => {}, defaults: () => {}, registerPlugin: () => {},
    _tweens: tweens
  };
}
