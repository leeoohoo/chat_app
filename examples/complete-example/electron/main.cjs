const { app, BrowserWindow, session } = require('electron');
const net = require('net');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

let mainWindow;
let backendProcess = null;
let selectedBackendPort = null;

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
        : parseInt(process.env.BACKEND_PORT || (isDev ? '3001' : '8000'), 10);
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

    // 根据平台与架构构建 Nuitka 目录名
    const platform = process.platform; // 'darwin' | 'win32' | 'linux'
    const arch = process.arch; // 'arm64' | 'x64' | ...
    const nuitkaDirName = `chat_app_server_nuitka_${platform}_${arch}`;
    const targetBinaryPath = path.join(
        repoRoot,
        'server',
        'chat_app_server',
        'dist',
        nuitkaDirName,
        binaryName
    );

    console.log('[Electron] Resolving backend binary (Nuitka):', targetBinaryPath);

    if (fs.existsSync(targetBinaryPath)) {
        try {
            const stats = fs.statSync(targetBinaryPath);
            console.log(`[Electron] ✓ Found binary: ${targetBinaryPath}`);
            console.log(`[Electron]   Size: ${stats.size} bytes`);

            if (!isWin && !(stats.mode & parseInt('111', 8))) {
                console.log(`[Electron]   Setting executable permissions...`);
                fs.chmodSync(targetBinaryPath, 0o755);
            }

            return {
                path: targetBinaryPath,
                workingDir: path.dirname(targetBinaryPath),
                size: stats.size,
            };
        } catch (err) {
            console.warn(`[Electron] Error checking binary ${targetBinaryPath}: ${err.message}`);
        }
    } else {
        console.error('[Electron] ❌ Backend binary not found at:', targetBinaryPath);
        console.error('[Electron] Platform/Arch:', { platform, arch });
        console.error('[Electron] Hint: Ensure Nuitka build output exists at directory:', nuitkaDirName);
        console.error('[Electron] Or set BACKEND_BIN_PATH to the absolute path of the binary');
    }

    return null;
}

async function ensureBackendStarted() {
    const { host } = getBackendHostPort();

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

    console.log(`[Electron] Launching binary: ${binaryInfo.path}`);
    console.log(`[Electron] Working directory: ${binaryInfo.workingDir}`);

    try {
        backendProcess = spawn(binaryInfo.path, [], {
            cwd: binaryInfo.workingDir,
            env: {
                ...process.env,
                PORT: String(port),
                // 确保二进制文件有正确的环境
                PYTHONUNBUFFERED: '1',
            },
            stdio: ['ignore', 'pipe', 'pipe'],
        });

        console.log(`[Electron] ✓ Binary process started with PID: ${backendProcess.pid}`);

        // 监听输出
        backendProcess.stdout.on('data', (data) => {
            process.stdout.write(`[Backend] ${data}`);
        });

        backendProcess.stderr.on('data', (data) => {
            process.stderr.write(`[Backend] ${data}`);
        });

        backendProcess.on('error', (err) => {
            console.error('[Electron] Binary process error:', err);
            throw err;
        });

        backendProcess.on('exit', (code, signal) => {
            console.log(`[Electron] Binary process exited: code=${code} signal=${signal}`);
            backendProcess = null;
        });

        return true;

    } catch (err) {
        console.error('[Electron] Failed to start binary process:', err);
        throw err;
    }
}

async function waitForBackendReady(maxRetries = 50, intervalMs = 300) {
    const { host, port } = getBackendHostPort();

    console.log(`[Electron] Waiting for backend at http://${host}:${port}...`);

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
        candidates.push(isDev ? 3001 : 8000);
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
            const freePort = typeof addr === 'object' && addr ? addr.port : (isDev ? 3001 : 8000);
            server.close(() => resolve(freePort));
        });
        server.on('error', () => resolve(isDev ? 3001 : 8000));
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
            } else if (isLocal && (u.port === '3001' || u.port === '8000') && u.pathname.startsWith('/api')) {
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

app.disableHardwareAcceleration();

app.whenReady().then(async () => {
    console.log('[Electron] App ready, starting binary backend...');

    try {
        await ensureBackendStarted();
        const ready = await waitForBackendReady();

        if (!ready) {
            console.error('[Electron] ❌ Backend failed to start');
            // 显示错误对话框
            const { dialog } = require('electron');
            await dialog.showErrorBox(
                'Backend Error',
                'Failed to start the backend server. Please check the console for details.'
            );
            app.quit();
            return;
        }

        console.log('[Electron] ✓ Backend ready, creating window...');
        setupApiRewrite();
        createWindow();

    } catch (error) {
        console.error('[Electron] Startup error:', error);
        const { dialog } = require('electron');
        await dialog.showErrorBox(
            'Startup Error',
            `Failed to start application: ${error.message}`
        );
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
    terminateBackendProcess();
    app.quit();
});

app.on('will-quit', () => {
    terminateBackendProcess();
});