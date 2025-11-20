const { app, BrowserWindow, session, ipcMain } = require('electron');
const net = require('net');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

let mainWindow;
let backendProcess = null;
let selectedBackendPort = null;
let splashWindow = null;
// 应用窗口管理：Map<应用ID, BrowserWindow>
const appWindows = new Map();

function terminateBackendProcess() {
    if (backendProcess && !backendProcess.killed) {
        console.log('[Electron] Terminating backend process...');
        try {
            backendProcess.kill('SIGTERM');
            setTimeout(() => {
                if (backendProcess && !backendProcess.killed) {
                    console.log('[Electron] Forcing backend process kill...');
                    backendProcess.kill('SIGKILL');
                }
            }, 3000);
        } catch (err) {
            console.warn('[Electron] Error terminating backend:', err.message);
        }
    }
}

function getBackendHostPort() {
    const host = '127.0.0.1';
    const isDev = !!process.env.VITE_DEV_SERVER_URL;
    const port = selectedBackendPort != null
        ? selectedBackendPort
        : parseInt(process.env.BACKEND_PORT || '3001', 10);
    return { host, port, isDev };
}

function checkPort(host, port, timeoutMs = 800) {
    return new Promise((resolve) => {
        const socket = new net.Socket();
        const onError = () => {
            socket.destroy();
            resolve(false);
        };
        socket.setTimeout(timeoutMs);
        socket.once('error', onError);
        socket.once('timeout', onError);
        socket.connect(port, host, () => {
            socket.end();
            resolve(true);
        });
    });
}

function findBinaryExecutable() {
    const isWin = process.platform === 'win32';
    const binaryName = isWin ? 'chat_app_server.exe' : 'chat_app_server';

    const repoRoot = path.join(__dirname, '..', '..', '..');

    // 支持环境变量覆盖（绝对路径或相对 repoRoot 的路径）
    const envOverride = process.env.BACKEND_BIN_PATH;
    if (envOverride) {
        const overridePath = path.isAbsolute(envOverride)
            ? envOverride
            : path.join(repoRoot, envOverride);
        console.log('[Electron] Using BACKEND_BIN_PATH override:', overridePath);
        if (fs.existsSync(overridePath)) {
            try {
                const stats = fs.statSync(overridePath);
                if (!isWin && !(stats.mode & parseInt('111', 8))) {
                    fs.chmodSync(overridePath, 0o755);
                }
                return {
                    path: overridePath,
                    workingDir: path.dirname(overridePath),
                    size: stats.size,
                };
            } catch (err) {
                console.warn(`[Electron] Error checking override path ${overridePath}: ${err.message}`);
            }
        } else {
            console.warn('[Electron] BACKEND_BIN_PATH not found:', overridePath);
        }
    }

    // 优先查找打包的 Node 后端脚本
    const isDev = !!process.env.VITE_DEV_SERVER_URL;
    const resRoot = isDev ? repoRoot : (process.resourcesPath || repoRoot);
    const packagedNodeDir = path.join(resRoot, 'server', 'chat_app_node_server');
    const packagedNodeEntry = path.join(packagedNodeDir, 'src', 'main.js');
    console.log('[Electron] Resolving backend node script:', packagedNodeEntry);
    if (fs.existsSync(packagedNodeEntry)) {
        try {
            const stats = fs.statSync(packagedNodeEntry);
            return {
                path: packagedNodeEntry,
                workingDir: packagedNodeDir,
                size: stats.size,
                isNodeScript: true,
            };
        } catch (err) {}
    }

    // 兼容原有二进制后端（Python），仅当存在时使用
    const packagedDir = path.join(repoRoot, 'server', 'chat_app_server', 'dist', 'chat_app_server');
    const packagedBinaryPath = path.join(packagedDir, binaryName);
    if (fs.existsSync(packagedBinaryPath)) {
        try {
            const stats = fs.statSync(packagedBinaryPath);
            if (!isWin && !(stats.mode & parseInt('111', 8))) {
                fs.chmodSync(packagedBinaryPath, 0o755);
            }
            return {
                path: packagedBinaryPath,
                workingDir: packagedDir,
                size: stats.size,
            };
        } catch (err) {}
    }

    return null;
}

async function ensureBackendStarted() {
    const { host, isDev } = getBackendHostPort();

    if (isDev) {
        const devPort = parseInt(process.env.BACKEND_PORT || '3001', 10);
        selectedBackendPort = devPort;

        const alreadyUp = await checkPort(host, devPort);
        if (alreadyUp) {
            return true;
        }

        const binaryInfo = findBinaryExecutable();
        if (binaryInfo && binaryInfo.isNodeScript) {
            try {
                backendProcess = spawn('node', [binaryInfo.path], {
                    cwd: binaryInfo.workingDir,
                    env: {
                        ...process.env,
                        PORT: String(devPort),
                    },
                    stdio: ['ignore', 'pipe', 'pipe'],
                });

                backendProcess.stdout.on('data', (data) => {
                    process.stdout.write(`[Backend] ${data}`);
                });
                backendProcess.stderr.on('data', (data) => {
                    process.stderr.write(`[Backend] ${data}`);
                });

                backendProcess.on('error', (err) => {
                    console.error('[Electron] Backend process error:', err);
                });

                backendProcess.on('exit', (code, signal) => {
                    console.log(`[Electron] Backend process exited: code=${code} signal=${signal}`);
                    backendProcess = null;
                });

            } catch (err) {
                console.error('[Electron] Failed to start dev backend process:', err);
            }
        }

        return true;
    }

    // 选择可用端口
    const port = await findAvailablePort(host);
    selectedBackendPort = port;
    console.log('[Electron] Starting backend server on selected port', port);

    // 查找二进制文件
    const binaryInfo = findBinaryExecutable();

    if (!binaryInfo) {
        console.error('[Electron] ❌ Binary executable not found!');
        console.error('[Electron] Please ensure the server binary is built and available.');
        const platform = process.platform;
        const arch = process.arch;
        const expectedDir = `chat_app_server_nuitka_${platform}_${arch}`;
        console.error('[Electron] Expected location:');
        console.error('[Electron]   - server/chat_app_server/dist/' + expectedDir + '/');
        console.error('[Electron] Or set BACKEND_BIN_PATH to point directly to the binary');
        throw new Error('Binary executable not found');
    }

    console.log(`[Electron] Launching backend: ${binaryInfo.path}`);
    console.log(`[Electron] Working directory: ${binaryInfo.workingDir}`);

    try {
        if (binaryInfo.isNodeScript) {
            const { isDev } = getBackendHostPort();
            if (isDev) {
                backendProcess = spawn('node', [binaryInfo.path], {
                    cwd: binaryInfo.workingDir,
                    env: {
                        ...process.env,
                        PORT: String(port),
                    },
                    stdio: ['ignore', 'pipe', 'pipe'],
                });
            } else {
            backendProcess = spawn(process.execPath, [binaryInfo.path], {
                cwd: binaryInfo.workingDir,
                env: {
                    ...process.env,
                    PORT: String(port),
                    ELECTRON_RUN_AS_NODE: '1',
                },
                stdio: ['ignore', 'pipe', 'pipe'],
            });
            }
        } else {
            backendProcess = spawn(binaryInfo.path, [], {
                cwd: binaryInfo.workingDir,
                env: {
                    ...process.env,
                    PORT: String(port),
                    PYTHONUNBUFFERED: '1',
                },
                stdio: ['ignore', 'pipe', 'pipe'],
            });
        }

        console.log(`[Electron] ✓ Backend process started with PID: ${backendProcess.pid}`);

        // 监听输出
        backendProcess.stdout.on('data', (data) => {
            process.stdout.write(`[Backend] ${data}`);
        });

        backendProcess.stderr.on('data', (data) => {
            process.stderr.write(`[Backend] ${data}`);
        });

        backendProcess.on('error', (err) => {
            console.error('[Electron] Backend process error:', err);
            throw err;
        });

        backendProcess.on('exit', (code, signal) => {
            console.log(`[Electron] Backend process exited: code=${code} signal=${signal}`);
            backendProcess = null;
        });

        return true;

    } catch (err) {
        console.error('[Electron] Failed to start backend process:', err);
        throw err;
    }
}

async function waitForBackendReady(maxRetries = 200, intervalMs = 300) {
    const { host, port } = getBackendHostPort();
    // 支持通过环境变量覆盖等待时长（毫秒）
    const overrideMsRaw = process.env.BACKEND_WAIT_MS || process.env.BACKEND_WAIT_TIMEOUT_MS;
    if (overrideMsRaw) {
        const overrideMs = parseInt(overrideMsRaw, 10);
        if (!Number.isNaN(overrideMs) && overrideMs > 0) {
            maxRetries = Math.ceil(overrideMs / intervalMs);
        }
    }
    const totalMs = maxRetries * intervalMs;
    console.log(`[Electron] Waiting for backend at http://${host}:${port} (timeout ~${totalMs}ms)...`);

    for (let i = 0; i < maxRetries; i++) {
        const ok = await checkPort(host, port);
        if (ok) {
            console.log(`[Electron] ✓ Backend is ready at http://${host}:${port}`);
            return true;
        }

        if (i === 0) {
            console.log('[Electron] Backend starting...');
        } else if (i % 10 === 0) {
            console.log(`[Electron] Still waiting... (${i}/${maxRetries})`);
        }

        await new Promise((r) => setTimeout(r, intervalMs));
    }

    console.error(`[Electron] ❌ Backend did not start within ${maxRetries * intervalMs}ms`);
    return false;
}

function findAvailablePort(host, preferred = []) {
    return new Promise(async (resolve) => {
        const candidates = [];
        if (process.env.BACKEND_PORT) {
            const p = parseInt(process.env.BACKEND_PORT, 10);
            if (!Number.isNaN(p)) candidates.push(p);
        }
        const { isDev } = getBackendHostPort();
        candidates.push(3001);
        candidates.push(...preferred);

        for (const p of candidates) {
            // true => port occupied; we want free
            const inUse = await checkPort(host, p);
            if (!inUse) {
                return resolve(p);
            }
        }

        const server = net.createServer();
        server.listen(0, host, () => {
            const addr = server.address();
            const freePort = typeof addr === 'object' && addr ? addr.port : 3001;
            server.close(() => resolve(freePort));
        });
        server.on('error', () => resolve(3001));
    });
}

function setupApiRewrite() {
    const { host, port } = getBackendHostPort();
    const targetBase = `http://${host}:${port}`;
    const filter = { urls: ['*://*/*'] };

    session.defaultSession.webRequest.onBeforeRequest(filter, (details, callback) => {
        const url = details.url || '';
        let redirectURL = null;
        try {
            const u = new URL(url);
            const isLocal = (u.hostname === 'localhost' || u.hostname === '127.0.0.1');
            const isApiPath = u.pathname.startsWith('/api');

            if (isApiPath) {
                // 重写任何 /api 前缀请求到当前后端端口
                redirectURL = `${targetBase}${u.pathname}${u.search}`;
            } else if (isLocal && (u.port === '3001') && u.pathname.startsWith('/api')) {
                redirectURL = `${targetBase}${u.pathname}${u.search}`;
            }
        } catch (_) {}

        if (redirectURL && redirectURL !== url) {
            callback({ redirectURL });
        } else {
            callback({});
        }
    });
}

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        minWidth: 960,
        minHeight: 600,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            webSecurity: false,
            // 允许在渲染进程使用 <webview> 标签，以替代 iframe 进行页面嵌入
            webviewTag: true,
            // 让 window.open 在 Electron 中创建原生 BrowserWindow（更符合预期）
            nativeWindowOpen: true,
            // 添加 preload 脚本以暴露安全的 IPC API
            preload: path.join(__dirname, 'preload.cjs'),
        },
        title: 'AI Chat Example',
    });

    const devServerUrl = process.env.VITE_DEV_SERVER_URL;
    console.log('[Electron] VITE_DEV_SERVER_URL =', devServerUrl);

    if (devServerUrl) {
        mainWindow.loadURL(devServerUrl + `?ts=${Date.now()}`);
        mainWindow.webContents.openDevTools({ mode: 'detach' });
    } else {
        const indexPath = path.join(__dirname, '..', 'dist', 'index.html');
        mainWindow.loadFile(indexPath);
    }

    mainWindow.webContents.on('did-finish-load', () => {
        console.log('[Electron] Page loaded:', mainWindow.webContents.getURL());
    });

    mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription, validatedURL, isMainFrame) => {
        console.error('[Electron] did-fail-load', { errorCode, errorDescription, validatedURL, isMainFrame });
        if (isMainFrame && devServerUrl) {
            const indexPath = path.join(__dirname, '..', 'dist', 'index.html');
            console.log('[Electron] Falling back to local file:', indexPath);
            mainWindow.loadFile(indexPath);
        }
    });

    // 在窗口关闭时终止后端进程
    mainWindow.on('close', () => {
        console.log('[Electron] Window closing. Shutting down backend...');
        terminateBackendProcess();
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

function createSplashWindow() {
    try {
        const splashPath = path.join(__dirname, 'splash.html');
        console.log('[Electron] Creating splash window. Path =', splashPath);
        splashWindow = new BrowserWindow({
            width: 420,
            height: 300,
            frame: false,
            transparent: true,
            backgroundColor: '#00000000',
            resizable: false,
            alwaysOnTop: true,
            skipTaskbar: true,
            show: false,
            useContentSize: true,
        });
        splashWindow.setAlwaysOnTop(true, 'screen-saver');
        splashWindow.center();
        splashWindow.loadFile(splashPath);
        splashWindow.once('ready-to-show', () => {
            try {
                console.log('[Electron] Splash window ready-to-show');
                splashWindow.show();
            } catch (e) {
                console.warn('[Electron] Failed to show splash window:', e.message);
            }
        });
        splashWindow.webContents.on('did-finish-load', () => {
            console.log('[Electron] Splash window content loaded');
        });
        splashWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
            console.warn('[Electron] Splash did-fail-load', { errorCode, errorDescription });
        });
        splashWindow.on('closed', () => {
            splashWindow = null;
        });
    } catch (err) {
        console.warn('[Electron] Failed to create splash window:', err.message);
    }
}

app.disableHardwareAcceleration();

app.whenReady().then(async () => {
    console.log('[Electron] App ready, starting binary backend...');

    // 注册 IPC 处理器
    setupIpcHandlers();

    // 显示启动过场动画
    createSplashWindow();

    try {
        await ensureBackendStarted();
        const ready = await waitForBackendReady(); // 默认约60秒，可用 BACKEND_WAIT_MS 覆盖

        if (!ready) {
            console.error('[Electron] ❌ Backend failed to start');
            // 显示错误对话框
            const { dialog } = require('electron');
            await dialog.showErrorBox(
                'Backend Error',
                'Failed to start the backend server. Please check the console for details.'
            );
            if (splashWindow) {
                try { splashWindow.close(); } catch (_) {}
                splashWindow = null;
            }
            app.quit();
            return;
        }

        console.log('[Electron] ✓ Backend ready, creating window...');
        // 在开发模式下，Vite 已经对 /api 做了代理，避免 Electron 级别再做一次重写导致跨域/重定向问题
        if (!process.env.VITE_DEV_SERVER_URL) {
            setupApiRewrite();
        } else {
            console.log('[Electron] Dev mode detected, skip setupApiRewrite() (use Vite proxy)');
        }
        if (splashWindow) {
            try { splashWindow.close(); } catch (_) {}
            splashWindow = null;
        }
        createWindow();

    } catch (error) {
        console.error('[Electron] Startup error:', error);
        const { dialog } = require('electron');
        await dialog.showErrorBox(
            'Startup Error',
            `Failed to start application: ${error.message}`
        );
        if (splashWindow) {
            try { splashWindow.close(); } catch (_) {}
            splashWindow = null;
        }
        app.quit();
    }

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('window-all-closed', () => {
    // 关闭所有窗口后，退出应用（包括 macOS），并确保终止后端进程
    if (splashWindow) {
        try { splashWindow.close(); } catch (_) {}
        splashWindow = null;
    }
    terminateBackendProcess();
    app.quit();
});

app.on('will-quit', () => {
    if (splashWindow) {
        try { splashWindow.close(); } catch (_) {}
        splashWindow = null;
    }
    terminateBackendProcess();
});

// ==================== 应用窗口管理 ====================

/**
 * 创建或聚焦应用窗口
 * @param {Object} appData - 应用数据 {id, name, url, iconUrl?}
 */
function createOrFocusAppWindow(appData) {
    const { id, name, url, iconUrl } = appData;

    console.log('[Electron] createOrFocusAppWindow:', { id, name, url });

    // 如果窗口已存在且未关闭，则聚焦
    if (appWindows.has(id)) {
        const existingWindow = appWindows.get(id);
        if (existingWindow && !existingWindow.isDestroyed()) {
            console.log('[Electron] Window exists, focusing...');
            existingWindow.focus();
            return;
        } else {
            // 窗口已销毁，从 Map 中移除
            appWindows.delete(id);
        }
    }

    // 创建新窗口
    const appWindow = new BrowserWindow({
        width: 1000,
        height: 700,
        title: name || 'Application',
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            // 在开发环境下放宽安全策略以避免部分站点在新窗口中加载资源失败
            webSecurity: !process.env.VITE_DEV_SERVER_URL,
            allowRunningInsecureContent: !!process.env.VITE_DEV_SERVER_URL,
        },
        icon: iconUrl, // 可选：设置窗口图标
    });

    console.log('[Electron] Creating new window for:', name);

    // 加载应用 URL
    if (url) {
        appWindow.loadURL(url).catch(err => {
            console.error('[Electron] Failed to load URL:', url, err);
        });
    }

    // 窗口关闭时从 Map 中移除
    appWindow.on('closed', () => {
        console.log('[Electron] App window closed:', name);
        appWindows.delete(id);

        // 通知渲染进程窗口已关闭
        if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send('app-window-closed', id);
        }
    });

    // 保存窗口引用
    appWindows.set(id, appWindow);
}

/**
 * 关闭指定应用窗口
 * @param {string} appId - 应用ID
 */
function closeAppWindow(appId) {
    console.log('[Electron] closeAppWindow:', appId);

    if (appWindows.has(appId)) {
        const appWindow = appWindows.get(appId);
        if (appWindow && !appWindow.isDestroyed()) {
            appWindow.close();
        }
        appWindows.delete(appId);
    }
}

/**
 * 获取所有打开的应用窗口ID列表
 * @returns {string[]} 应用ID数组
 */
function getOpenAppWindowIds() {
    const openIds = [];
    for (const [id, window] of appWindows.entries()) {
        if (window && !window.isDestroyed()) {
            openIds.push(id);
        }
    }
    return openIds;
}

// ==================== IPC 通信处理 ====================

/**
 * 设置 IPC 监听器
 */
function setupIpcHandlers() {
    // 打开应用窗口
    ipcMain.handle('open-app-window', async (event, appData) => {
        try {
            createOrFocusAppWindow(appData);
            return { success: true };
        } catch (error) {
            console.error('[Electron] Error opening app window:', error);
            return { success: false, error: error.message };
        }
    });

    // 关闭应用窗口
    ipcMain.handle('close-app-window', async (event, appId) => {
        try {
            closeAppWindow(appId);
            return { success: true };
        } catch (error) {
            console.error('[Electron] Error closing app window:', error);
            return { success: false, error: error.message };
        }
    });

    // 获取打开的应用窗口列表
    ipcMain.handle('get-open-app-windows', async () => {
        try {
            const openIds = getOpenAppWindowIds();
            return { success: true, data: openIds };
        } catch (error) {
            console.error('[Electron] Error getting open app windows:', error);
            return { success: false, error: error.message };
        }
    });

    // 检查是否在 Electron 环境
    ipcMain.handle('is-electron', async () => {
        return { success: true, data: true };
    });

    console.log('[Electron] IPC handlers registered');
}
