/**
 * MockStore — 用于 JS 单元测试的模拟 Store
 * 不需要依赖完整的 Store 实现
 */
window.__MockStore = class MockStore {
  constructor(data = {}) {
    this._data = { ...data };
    this._listeners = {};
  }

  get(key) {
    return this._data[key];
  }

  set(key, value) {
    this._data[key] = value;
    if (this._listeners[key]) {
      this._listeners[key].forEach(fn => fn(value));
    }
  }

  subscribe(key, fn) {
    if (!this._listeners[key]) this._listeners[key] = [];
    this._listeners[key].push(fn);
    return () => {
      this._listeners[key] = this._listeners[key].filter(f => f !== fn);
    };
  }

  getState(name) {
    return this._data;
  }

  setState(data, name) {
    Object.assign(this._data, data);
  }
};
