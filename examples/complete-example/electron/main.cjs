const { app, BrowserWindow } = require('electron');
const net = require('net');
const { spawn } = require('child_process');
const path = require('path');

let mainWindow;
let backendProcess = null;

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
  const host = '127.0.0.1';
  const port = parseInt(process.env.BACKEND_PORT || '8000', 10);
  const isUp = await checkPort(host, port);
  if (isUp) {
    console.log(`[Electron] Backend already running at http://${host}:${port}`);
    return;
  }
  console.log('[Electron] Starting backend server on port', port);
  // Spawn Python backend (development fallback). For distribution, bundle server binary.
  const cwd = path.join(__dirname, '..', '..');
  const scriptPath = path.join(cwd, 'server', 'chat_app_server', 'scripts', 'start.py');
  backendProcess = spawn('python', [scriptPath], {
    cwd,
    env: {
      ...process.env,
      PORT: String(port),
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  backendProcess.stdout.on('data', (data) => {
    process.stdout.write(`[Backend] ${data}`);
  });
  backendProcess.stderr.on('data', (data) => {
    process.stderr.write(`[Backend] ${data}`);
  });
  backendProcess.on('exit', (code, signal) => {
    console.log(`[Electron] Backend process exited: code=${code} signal=${signal}`);
    backendProcess = null;
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

app.whenReady().then(() => {
  // Ensure backend is up in production runs
  ensureBackendStarted().catch((e) => console.error('[Electron] ensureBackendStarted error:', e));
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