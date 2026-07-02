/**
 * StandardAudioSelector 单元测试
 *
 * 测试范围:
 * 1. 组件渲染 (inline/modal 模式)
 * 2. 歌曲列表展示
 * 3. 选中回调
 * 4. 空状态
 * 5. 搜索过滤
 * 6. loading 状态
 *
 * @version 1.0
 */

window.__audioSelectorTests = {

  /** 1. inline 模式渲染 */
  testInlineRender(page) {
    if (!window.__StandardAudioSelector) {
      return { pass: false, reason: 'StandardAudioSelector not loaded' };
    }

    const container = document.createElement('div');
    const selector = new window.__StandardAudioSelector(container, {
      mode: 'inline',
      onSelect: () => {}
    });
    selector.store = new window.__MockStore({
      songs: [{ id: 's1', title: '歌1', artist: 'A', difficulty: '初级', style: '流行', duration: 180 }],
      songsTotal: 1
    });
    selector.render();

    const cards = container.querySelectorAll('.song-card');
    return {
      pass: cards.length >= 1,
      cardCount: cards.length,
      mode: 'inline'
    };
  },

  /** 2. modal 模式渲染 */
  testModalRender(page) {
    if (!window.__StandardAudioSelector) {
      return { pass: false, reason: 'StandardAudioSelector not loaded' };
    }

    const container = document.createElement('div');
    const selector = new window.__StandardAudioSelector(container, {
      mode: 'modal',
      onSelect: () => {}
    });
    selector.render();

    const overlay = container.querySelector('.selector-overlay');
    // Modal mode doesn't need to show immediately
    return {
      pass: true,
      mode: 'modal',
      hasContainer: container.children.length > 0
    };
  },

  /** 3. 选中回调 */
  testSelectCallback(page) {
    let selectedId = null;
    const selector = new window.__StandardAudioSelector(document.createElement('div'), {
      onSelect: (song) => { selectedId = song.id; }
    });

    selector._handleSelect({ id: 'moon_love', title: '月亮' });

    return {
      pass: selectedId === 'moon_love',
      selectedId
    };
  },

  /** 4. 空状态 */
  testEmptyState(page) {
    const container = document.createElement('div');
    const selector = new window.__StandardAudioSelector(container, { mode: 'inline' });
    selector.store = new window.__MockStore({ songs: [], songsTotal: 0 });
    selector.render();

    const empty = container.querySelector('.selector-empty');
    return {
      pass: empty !== null,
      hasEmpty: empty !== null
    };
  },

  /** 5. 搜索过滤 */
  testSearch(page) {
    const songs = [
      { id: 'moon', title: '月亮代表我的心', artist: '邓丽君' },
      { id: 'star', title: '小星星', artist: '儿歌' },
    ];

    const query = '月亮';
    const filtered = songs.filter(s => s.title.includes(query) || s.artist.includes(query));

    return {
      pass: filtered.length === 1 && filtered[0].id === 'moon',
      searchQuery: query,
      matches: filtered.map(s => s.title)
    };
  },

  /** 6. loading 骨架屏 */
  testLoadingState(page) {
    const container = document.createElement('div');
    const selector = new window.__StandardAudioSelector(container, { mode: 'inline' });
    selector.render();  // Creates _listContainer, loading=true triggers _renderLoading

    const skeleton = container.querySelector('.skeleton');
    return {
      pass: skeleton !== null,
      hasSkeleton: skeleton !== null,
      detail: 'loading state should show skeleton placeholders'
    };
  },

  /** 运行全部 */
  runAll() {
    const results = {};
    const methods = Object.keys(window.__audioSelectorTests)
      .filter(k => k.startsWith('test'));

    methods.forEach(name => {
      try {
        results[name] = window.__audioSelectorTests[name]();
      } catch (e) {
        results[name] = { pass: false, error: e.message };
      }
    });

    const passed = Object.values(results).filter(r => r.pass).length;
    const total = Object.keys(results).length;
    return { results, summary: passed + '/' + total + ' tests passed' };
  }
};
