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

async function ensureBackendStarted() {
  const { host, port, isDev } = getBackendHostPort();
  const isUp = await checkPort(host, port);
  if (isUp) {
    console.log(`[Electron] Backend already running at http://${host}:${port}`);
    return;
  }
  console.log('[Electron] Starting backend server on port', port);
  // Prefer Python dev script during development; use bundled binary in production
  const isWin = process.platform === 'win32';
  const binaryName = isWin ? 'chat_app_server.exe' : 'chat_app_server';
  const devBinaryPath = path.join(__dirname, '..', 'bin', binaryName);
  const prodBinaryPath = path.join(process.resourcesPath || path.join(__dirname, '..'), 'bin', binaryName);
  const repoRoot = path.join(__dirname, '..', '..', '..');
  const serverDistDarwinArm64 = path.join(repoRoot, 'server', 'chat_app_server', 'dist', 'chat_app_server_darwin_arm64', binaryName);

  let usedPath = null;
  let cwd = path.join(__dirname, '..');
  // Try server dist binary first (user-confirmed working), then app resources, then example bin.
  if (fs.existsSync(serverDistDarwinArm64)) {
    usedPath = serverDistDarwinArm64;
  } else if (fs.existsSync(prodBinaryPath)) {
    usedPath = prodBinaryPath;
  } else if (fs.existsSync(devBinaryPath)) {
    usedPath = devBinaryPath;
  }
  // In packaged app, __dirname points inside app.asar; ensure cwd is a real directory
  if (usedPath) {
    try {
      cwd = path.dirname(usedPath);
    } catch (_) {
      cwd = process.resourcesPath || path.join(__dirname, '..');
    }
  }

  if (usedPath) {
    console.log('[Electron] Launching bundled server binary:', usedPath);
    backendProcess = spawn(usedPath, [], {
      cwd,
      env: {
        ...process.env,
        PORT: String(port),
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    });
  } else {
    // Use Python dev server when in development, or if binary missing
    startPythonBackend(port);
  }
  backendProcess.stdout.on('data', (data) => {
    process.stdout.write(`[Backend] ${data}`);
  });
  backendProcess.stderr.on('data', (data) => {
    process.stderr.write(`[Backend] ${data}`);
  });
  backendProcess.on('error', (err) => {
    console.error('[Electron] Failed to start backend process:', err);
  });
  backendProcess.on('exit', (code, signal) => {
    console.log(`[Electron] Backend process exited: code=${code} signal=${signal}`);
    backendProcess = null;
  });
}

function startPythonBackend(port) {
  const repoRoot = path.join(__dirname, '..', '..', '..');
  const scriptPath = path.join(repoRoot, 'server', 'chat_app_server', 'scripts', 'start.py');
  console.log('[Electron] Using Python dev server:', scriptPath);
  const venvPython = path.join(repoRoot, '.venv', 'bin', 'python');
  const pythonCmd = fs.existsSync(venvPython) ? venvPython : 'python3';
  backendProcess = spawn(pythonCmd, [scriptPath], {
    cwd: repoRoot,
    env: {
      ...process.env,
      PORT: String(port),
      PYTHONUNBUFFERED: '1',
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
}

async function waitForBackendReady(maxRetries = 50, intervalMs = 300) {
  const { host, port } = getBackendHostPort();
  for (let i = 0; i < maxRetries; i++) {
    const ok = await checkPort(host, port);
    if (ok) {
      console.log(`[Electron] Backend is ready at http://${host}:${port}`);
      return true;
    }
    if (i === 0) {
      console.log('[Electron] Waiting for backend to be ready...');
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  console.error(`[Electron] Backend did not become ready within ${maxRetries * intervalMs}ms`);
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
      // Relax security for dev server to avoid blank due to blocked resources
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

  // Debug load lifecycle
  mainWindow.webContents.on('did-finish-load', () => {
    console.log('[Electron] Page loaded:', mainWindow.webContents.getURL());
  });
  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription, validatedURL, isMainFrame) => {
    console.error('[Electron] did-fail-load', { errorCode, errorDescription, validatedURL, isMainFrame });
    // If dev server is unavailable, fallback to local dist build
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

// Try disabling hardware acceleration to avoid potential blank screen issues
app.disableHardwareAcceleration();

app.whenReady().then(async () => {
  // Ensure backend is started, prefer binary; if not ready, fall back to Python
  try {
    await ensureBackendStarted();
  } catch (e) {
    console.error('[Electron] ensureBackendStarted error:', e);
  }
  let ready = await waitForBackendReady();
  if (!ready) {
    console.warn('[Electron] Backend not ready after binary launch. Trying Python fallback...');
    try {
      const { port } = getBackendHostPort();
      startPythonBackend(port);
      ready = await waitForBackendReady();
    } catch (e) {
      console.error('[Electron] Python fallback failed:', e);
    }
  }
  createWindow();

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
    try {
      backendProcess.kill();
    } catch (_) {}
  }
});