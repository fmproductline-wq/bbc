const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  minimize: () => ipcRenderer.send('window-minimize'),
  maximize: () => ipcRenderer.send('window-maximize'),
  close: () => ipcRenderer.send('window-close'),

  getStore: (key) => ipcRenderer.invoke('get-store', key),
  setStore: (key, value) => ipcRenderer.invoke('set-store', key, value),

  getModelsPath: () => ipcRenderer.invoke('get-models-path'),
  openModelsFolder: () => ipcRenderer.invoke('open-models-folder'),
  getServerPort: () => ipcRenderer.invoke('get-server-port'),
  getVersion: () => ipcRenderer.invoke('get-version'),

  installOllama: (onLog) => {
    ipcRenderer.on('ollama-install-log', (_, line) => onLog(line));
    return ipcRenderer.invoke('install-ollama');
  },
  openExternal: (url) => ipcRenderer.invoke('open-external', url),
});
