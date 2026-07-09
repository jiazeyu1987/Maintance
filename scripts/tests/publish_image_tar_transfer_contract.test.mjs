import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'

const root = path.resolve(import.meta.dirname, '../..')
const script = fs.readFileSync(path.join(root, 'ops/deploy/publish-int-ruoyi.ps1'), 'utf8')

test('publish script uploads release image tar through chunked transfer with remote byte verification', () => {
  assert.match(script, /function\s+Copy-LargeFileToServerInChunks/)
  assert.match(script, /chunk-\{0:D6\}\.part/)
  assert.match(script, /\$chunkIndex\+\+/)
  assert.match(script, /Get-RemoteFileSize/)
  assert.match(script, /\$sizeResult\s*=\s*Invoke-ProcessCapture/)
  assert.match(script, /\$sizeResult\.StdOut/)
  assert.doesNotMatch(script, /\$sizeText\.Trim\(\)/)
  assert.match(script, /Assert-RemoteFileSize/)
  assert.match(script, /Copy-LargeFileToServerInChunks\s+-LocalPath\s+\$imageTar\s+-RemotePath\s+\$remoteImageTar/)
  assert.doesNotMatch(script, /Copy-ToServer\s+-LocalPath\s+\$imageTar\s+-RemotePath\s+\$remoteImageTar/)
})
