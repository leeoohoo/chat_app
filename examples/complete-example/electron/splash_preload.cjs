const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('splashAPI', {
  onStatus: (handler) => {
    if (typeof handler === 'function') {
      ipcRenderer.on('splash:status', (_event, payload) => {
        try { handler(payload || {}); } catch (_) {}
      });
    }
  },
  proceed: () => {
    try { ipcRenderer.send('splash:proceed'); } catch (_) {}
  },
  onFadeout: (handler) => {
    if (typeof handler === 'function') {
      ipcRenderer.on('splash:fadeout', () => {
        try { handler(); } catch (_) {}
      });
    }
  }
});