const { app, BrowserWindow } = require('electron');
const net = require('net');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

let mainWindow;
let backendProcess = null;

function getBackendHostPort() {
    const host = '127.0.0.1';
    const isDev = !!process.env.VITE_DEV_SERVER_URL;
    const port = parseInt(process.env.BACKEND_PORT || (isDev ? '3001' : '8000'), 10);
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

    // 按优先级查找二进制文件
    const binaryPaths = [
        // 1. 服务器 dist 目录（PyInstaller 输出）
        path.join(repoRoot, 'server', 'chat_app_server', 'dist', 'chat_app_server_darwin_arm64', binaryName),
        path.join(repoRoot, 'server', 'chat_app_server', 'dist', binaryName),

        // 2. Electron 应用的 resources 目录（打包后）
        path.join(process.resourcesPath || path.join(__dirname, '..'), 'bin', binaryName),

        // 3. 应用目录下的 bin 目录
        path.join(__dirname, '..', 'bin', binaryName),
    ];

    console.log('[Electron] Searching for binary executable...');
    console.log(`[Electron] Target binary: ${binaryName}`);

    for (const binaryPath of binaryPaths) {
        console.log(`[Electron] Checking: ${binaryPath}`);

        if (fs.existsSync(binaryPath)) {
            try {
                const stats = fs.statSync(binaryPath);
                console.log(`[Electron] ✓ Found binary: ${binaryPath}`);
                console.log(`[Electron]   Size: ${stats.size} bytes`);

                // 确保可执行权限
                if (!isWin && !(stats.mode & parseInt('111', 8))) {
                    console.log(`[Electron]   Setting executable permissions...`);
                    fs.chmodSync(binaryPath, 0o755);
                }

                return {
                    path: binaryPath,
                    workingDir: path.dirname(binaryPath),
                    size: stats.size
                };
            } catch (err) {
                console.warn(`[Electron] Error checking binary ${binaryPath}: ${err.message}`);
            }
        }
    }

    return null;
}

async function ensureBackendStarted() {
    const { host, port } = getBackendHostPort();

    // 检查是否已经在运行
    const isUp = await checkPort(host, port);
    if (isUp) {
        console.log(`[Electron] Backend already running at http://${host}:${port}`);
        return true;
    }

    console.log('[Electron] Starting backend server on port', port);

    // 查找二进制文件
    const binaryInfo = findBinaryExecutable();

    if (!binaryInfo) {
        console.error('[Electron] ❌ Binary executable not found!');
        console.error('[Electron] Please ensure the server binary is built and available.');
        console.error('[Electron] Expected locations:');
        console.error('[Electron]   - server/chat_app_server/dist/chat_app_server_darwin_arm64/');
        console.error('[Electron]   - server/chat_app_server/dist/');
        console.error('[Electron]   - app/bin/');
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
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('will-quit', () => {
    if (backendProcess && !backendProcess.killed) {
        console.log('[Electron] Terminating backend process...');
        try {
            backendProcess.kill('SIGTERM');
            // 给进程一些时间优雅退出
            setTimeout(() => {
                if (backendProcess && !backendProcess.killed) {
                    backendProcess.kill('SIGKILL');
                }
            }, 3000);
        } catch (err) {
            console.warn('[Electron] Error terminating backend:', err.message);
        }
    }
});