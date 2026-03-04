const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('api', {
  send: (channel, payload) => {
    ipcRenderer.send(channel, payload)
  },
  on: (channel, listener) => {
    ipcRenderer.on(channel, (event, ...args) => listener(...args))
  },
  invoke: (channel, ...args) => ipcRenderer.invoke(channel, ...args),
})

// Convenience helpers for common window controls
contextBridge.exposeInMainWorld('windowControls', {
  moveWindowDelta: (dx, dy) => ipcRenderer.send('move-window-delta', { dx, dy }),
  setIgnoreMouse: (ignore) => ipcRenderer.send('set-ignore-mouse', ignore),
  moveWindow: (pos) => ipcRenderer.send('move-window', pos),
})
