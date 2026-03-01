const { app, BrowserWindow, ipcMain, screen } = require('electron')
const path = require('path')

let win

function createWindow() {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize

  win = new BrowserWindow({
    width: 200,
    height: 200,
    x: width - 220,
    y: height - 220,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    hasShadow: false,
    skipTaskbar: false,
    resizable: false,
    backgroundColor: '#00000000',
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    }
  })

  win.loadFile(path.join(__dirname, 'index.html'))
}

app.whenReady().then(createWindow)

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

// Allow renderer to move the window (for dragging)
ipcMain.on('move-window', (event, { x, y }) => {
  if (win) win.setPosition(Math.round(x), Math.round(y))
})

ipcMain.on('set-ignore-mouse', (event, ignore) => {
  if (win) win.setIgnoreMouseEvents(ignore, { forward: true })
})

ipcMain.on('move-window-delta', (event, { dx, dy }) => {
  if (win) {
    const [x, y] = win.getPosition()
    win.setPosition(x + dx, y + dy)
  }
})