// Resolves a UHRP URL to the direct HTTPS URL(s) currently hosting it.
// No wallet is required — resolution is a free overlay-network lookup.
//
// Usage: node resolve.mjs <uhrpURL> [networkPreset]
import { StorageDownloader } from '@bsv/sdk'

async function main () {
  const [, , uhrpURL, networkPreset] = process.argv
  if (!uhrpURL) {
    console.log(JSON.stringify({ ok: false, error: 'usage: resolve.mjs <uhrpURL> [networkPreset]' }))
    process.exitCode = 1
    return
  }

  try {
    const downloader = new StorageDownloader({ networkPreset: networkPreset || 'mainnet' })
    const urls = await downloader.resolve(uhrpURL)
    console.log(JSON.stringify({ ok: true, urls }))
  } catch (err) {
    console.log(JSON.stringify({ ok: false, error: err && err.message ? err.message : String(err) }))
    process.exitCode = 1
  }
}

main()
