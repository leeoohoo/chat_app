const path = require('path');
const fs = require('fs');
const { spawnSync } = require('child_process');

module.exports = async function afterPack(context) {
  try {
    const platform = context.electronPlatformName; // 'darwin' | 'win32' | 'linux'
    const appName = context.packager.appInfo.productFilename;

    let resourcesDir;
    if (platform === 'darwin') {
      resourcesDir = path.join(context.appOutDir, `${appName}.app`, 'Contents', 'Resources');
    } else {
      resourcesDir = path.join(context.appOutDir, 'resources');
    }

    const serverDir = path.join(resourcesDir, 'server', 'chat_app_node_server');
    if (!fs.existsSync(serverDir)) {
      console.warn('[afterPack] Server directory not found:', serverDir);
      return;
    }

    let electronVersion = (context.packager.info && context.packager.info.electronVersion) || null;
    try {
      if (!electronVersion) {
        const pkg = require(path.join(context.packager.projectDir, 'node_modules', 'electron', 'package.json'));
        electronVersion = pkg.version;
      }
    } catch (_) {}

    console.log('[afterPack] Rebuilding native module better-sqlite3 for Electron', electronVersion || 'unknown');
    const npmCmd = process.platform === 'win32' ? 'npm.cmd' : 'npm';
    const args = ['rebuild', 'better-sqlite3'];
    if (electronVersion) {
      args.push('--runtime=electron', `--target=${electronVersion}`);
    } else {
      args.push('--runtime=electron');
    }
    const result = spawnSync(npmCmd, args, { cwd: serverDir, stdio: 'inherit' });
    if (result.status !== 0) {
      console.warn('[afterPack] npm rebuild returned non-zero exit code:', result.status);
    } else {
      console.log('[afterPack] ✓ Rebuild completed');
    }
  } catch (err) {
    console.warn('[afterPack] Failed to rebuild native modules:', err && err.message);
  }
};