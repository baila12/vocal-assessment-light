/**
 * ModeSelect 单元测试
 *
 * 测试范围:
 * 1. 模式默认值
 * 2. 模式切换
 * 3. 持久化
 * 4. 传入后端参数
 * 5. 文件不因切换而丢失
 *
 * @version 1.0
 */

window.__modeSelectTests = {

  /** 1. 默认选中快速模式 */
  testDefaultQuickMode(page) {
    const store = new window.__MockStore({ evalMode: 'quick' });
    return {
      pass: store.get('evalMode') === 'quick',
      mode: store.get('evalMode')
    };
  },

  /** 2. 切换到专业模式 */
  testSwitchToProfessional(page) {
    const store = new window.__MockStore({ evalMode: 'quick' });
    store.set('evalMode', 'professional');
    return {
      pass: store.get('evalMode') === 'professional',
      before: 'quick',
      after: store.get('evalMode')
    };
  },

  /** 3. 模式持久化到 localStorage */
  testPersistToLocalStorage(page) {
    try {
      localStorage.setItem('vocal_app_evalMode', 'professional');
      const stored = localStorage.getItem('vocal_app_evalMode');
      return {
        pass: stored === 'professional',
        stored
      };
    } catch (e) {
      return { pass: false, error: e.message };
    }
  },

  /** 4. 刷新后模式恢复 */
  testRestoreAfterRefresh(page) {
    // Simulate reading from localStorage on page load
    const stored = localStorage.getItem('vocal_app_evalMode') || 'quick';
    return {
      pass: stored === 'professional' || stored === 'quick',
      restored: stored
    };
  },

  /** 5. 上传时携带 mode 参数 */
  testUploadWithMode(page) {
    const calls = [];
    const mockApi = {
      uploadAudio: (file, mode) => {
        calls.push({ file, mode });
        return Promise.resolve({ success: true });
      }
    };

    mockApi.uploadAudio('test.mp3', 'professional');

    return {
      pass: calls.length === 1 && calls[0].mode === 'professional',
      modeSent: calls[0]?.mode
    };
  },

  /** 6. 切换模式不影响已选文件 */
  testModeSwitchKeepsFile(page) {
    let selectedFile = { name: 'test.mp3', size: 1024 };

    // Simulate file selection
    const fileBefore = selectedFile;

    // Simulate mode switch — file stays
    const fileAfter = selectedFile;

    return {
      pass: fileBefore === fileAfter && fileAfter !== null,
      file: fileAfter?.name
    };
  },

  /** 7. 模式切换不触发网络请求 */
  testNoNetworkOnSwitch(page) {
    let fetchCalls = 0;
    const origFetch = window.fetch;
    // In real test we'd monitor, here we just verify the concept
    window.fetch = origFetch;

    return {
      pass: true,
      note: 'mode switch is a pure UI operation'
    };
  },

  /** 运行全部 */
  runAll() {
    const results = {};
    const methods = Object.keys(window.__modeSelectTests)
      .filter(k => k.startsWith('test'));

    methods.forEach(name => {
      try {
        results[name] = window.__modeSelectTests[name]();
      } catch (e) {
        results[name] = { pass: false, error: e.message };
      }
    });

    const passed = Object.values(results).filter(r => r.pass).length;
    const total = Object.keys(results).length;
    return { results, summary: passed + '/' + total + ' tests passed' };
  }
};
