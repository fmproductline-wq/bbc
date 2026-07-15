// Downloads and hash-verifies a file from UHRP, saving it to disk.
// No wallet is required — downloads are free reads.
//
// Usage: node download.mjs <uhrpURL> <outPath> [networkPreset]
import fs from 'node:fs'
import { StorageDownloader } from '@bsv/sdk'

async function main () {
  const [, , uhrpURL, outPath, networkPreset] = process.argv
  if (!uhrpURL || !outPath) {
    console.log(JSON.stringify({ ok: false, error: 'usage: download.mjs <uhrpURL> <outPath> [networkPreset]' }))
    process.exitCode = 1
    return
  }

  try {
    const downloader = new StorageDownloader({ networkPreset: networkPreset || 'mainnet' })
    const result = await downloader.download(uhrpURL)
    fs.writeFileSync(outPath, Buffer.from(result.data))
    console.log(JSON.stringify({
      ok: true,
      mimeType: result.mimeType,
      size: result.data.length,
      savedTo: outPath
    }))
  } catch (err) {
    console.log(JSON.stringify({ ok: false, error: err && err.message ? err.message : String(err) }))
    process.exitCode = 1
  }
}

main()
