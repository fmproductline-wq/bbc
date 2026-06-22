const { app, BrowserWindow, ipcMain, shell, Menu, Tray, nativeImage } = require('electron');
const path = require('path');
const { startLocalServer } = require('./server');
const { installOllama } = require('./ollama-installer');
const Store = require('electron-store');

const store = new Store();
const isDev = process.env.NODE_ENV === 'development';
let mainWindow = null;
let tray = null;
let serverPort = 3791;

async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 840,
    minHeight: 600,
    frame: false,
    titleBarStyle: 'hidden',
    backgroundColor: '#212121',
    icon: path.join(__dirname, '../../assets/icon.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      webSecurity: false,
    },
  });

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
  } else {
    mainWindow.loadFile(path.join(__dirname, '../../dist/index.html'));
  }

  mainWindow.on('closed', () => { mainWindow = null; });
}

function createTray() {
  const trayPath = path.join(__dirname, '../../assets/tray-icon.png');
  const icon = nativeImage.createFromPath(trayPath);
  tray = new Tray(icon.isEmpty() ? nativeImage.createEmpty() : icon);
  const menu = Menu.buildFromTemplate([
    { label: 'Open BestBrand AI', click: () => { mainWindow?.show(); mainWindow?.focus(); } },
    { type: 'separator' },
    { label: 'Quit', click: () => { app.isQuitting = true; app.quit(); } },
  ]);
  tray.setToolTip('BestBrand AI Agent');
  tray.setContextMenu(menu);
  tray.on('double-click', () => { mainWindow?.show(); mainWindow?.focus(); });
}

// ── IPC ──────────────────────────────────────────────────────
ipcMain.handle('get-store', (_, key) => store.get(key));
ipcMain.handle('set-store', (_, key, value) => store.set(key, value));

ipcMain.handle('get-models-path', () =>
  app.isPackaged
    ? path.join(process.resourcesPath, 'models')
    : path.join(__dirname, '../../models')
);

ipcMain.handle('open-models-folder', () => {
  const p = app.isPackaged
    ? path.join(process.resourcesPath, 'models')
    : path.join(__dirname, '../../models');
  shell.openPath(p);
});

ipcMain.handle('get-server-port', () => serverPort);
ipcMain.handle('get-version', () => app.getVersion());

// Auto-install Ollama (Linux only; Windows/Mac open browser)
ipcMain.handle('install-ollama', async (event) => {
  return installOllama((line) => {
    event.sender.send('ollama-install-log', line);
  });
});

ipcMain.on('window-minimize', () => mainWindow?.minimize());
ipcMain.on('window-maximize', () => {
  mainWindow?.isMaximized() ? mainWindow.unmaximize() : mainWindow?.maximize();
});
ipcMain.on('window-close', () => mainWindow?.close());

// ── App lifecycle ─────────────────────────────────────────────
app.whenReady().then(async () => {
  serverPort = await startLocalServer();
  await createWindow();
  createTray();
  app.on('activate', () => { if (!BrowserWindow.getAllWindows().length) createWindow(); });
});

app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
app.on('before-quit', () => { app.isQuitting = true; });
