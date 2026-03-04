const esbuild = require('esbuild')
const path = require('path')

esbuild.build({
  entryPoints: [path.join(__dirname, 'src', 'renderer.js')],
  bundle: true,
  minify: true,
  sourcemap: false,
  platform: 'browser',
  target: ['es2017'],
  outfile: path.join(__dirname, 'build', 'renderer.js'),
}).catch(() => process.exit(1))
