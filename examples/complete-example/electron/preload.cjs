/**
 * Electron Preload 脚本
 *
 * 在渲染进程中暴露安全的 IPC API，用于与主进程通信。
 * 使用 contextBridge 确保安全性，避免直接暴露 Node.js API。
 */

const { contextBridge, ipcRenderer } = require('electron');

console.log('[Preload] Loading preload script...');

// 通过 contextBridge 暴露安全的 API 给渲染进程
contextBridge.exposeInMainWorld('electronAPI', {
  /**
   * 打开应用窗口
   * @param {Object} appData - 应用数据 {id, name, url, iconUrl?}
   * @returns {Promise<{success: boolean, error?: string}>}
   */
  openAppWindow: async (appData) => {
    console.log('[Preload] openAppWindow called:', appData);
    try {
      const result = await ipcRenderer.invoke('open-app-window', appData);
      return result;
    } catch (error) {
      console.error('[Preload] openAppWindow error:', error);
      return { success: false, error: error.message };
    }
  },

  /**
   * 关闭应用窗口
   * @param {string} appId - 应用ID
   * @returns {Promise<{success: boolean, error?: string}>}
   */
  closeAppWindow: async (appId) => {
    console.log('[Preload] closeAppWindow called:', appId);
    try {
      const result = await ipcRenderer.invoke('close-app-window', appId);
      return result;
    } catch (error) {
      console.error('[Preload] closeAppWindow error:', error);
      return { success: false, error: error.message };
    }
  },

  /**
   * 获取所有打开的应用窗口ID列表
   * @returns {Promise<{success: boolean, data?: string[], error?: string}>}
   */
  getOpenAppWindows: async () => {
    try {
      const result = await ipcRenderer.invoke('get-open-app-windows');
      return result;
    } catch (error) {
      console.error('[Preload] getOpenAppWindows error:', error);
      return { success: false, error: error.message };
    }
  },

  /**
   * 检查是否在 Electron 环境
   * @returns {Promise<{success: boolean, data?: boolean}>}
   */
  isElectron: async () => {
    try {
      const result = await ipcRenderer.invoke('is-electron');
      return result;
    } catch (error) {
      console.error('[Preload] isElectron error:', error);
      return { success: false, data: false };
    }
  },

  /**
   * 监听应用窗口关闭事件
   * @param {Function} callback - 回调函数，接收应用ID参数
   * @returns {Function} 取消监听的函数
   */
  onAppWindowClosed: (callback) => {
    const listener = (event, appId) => {
      console.log('[Preload] onAppWindowClosed event:', appId);
      callback(appId);
    };
    ipcRenderer.on('app-window-closed', listener);

    // 返回取消监听的函数
    return () => {
      ipcRenderer.removeListener('app-window-closed', listener);
    };
  },
});

console.log('[Preload] ✓ Electron API exposed to window.electronAPI');

// 在开发环境下，方便调试
if (process.env.NODE_ENV === 'development') {
  console.log('[Preload] Available APIs:', Object.keys(window.electronAPI || {}));
}
