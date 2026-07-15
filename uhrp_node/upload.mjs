// Publishes a local file to UHRP storage and prints the result as one JSON line.
//
// Usage: node upload.mjs <filePath> <retentionMinutes> [storageURL]
//
// Requires a running, funded BRC-100 wallet (e.g. Metanet Client) reachable
// over the default WalletClient substrate — StorageUploader pays the storage
// host's invoice through that wallet before the file is accepted.
//
// WalletClient's HTTP substrates (what Metanet Client and most desktop BRC-100
// wallets expose locally) REQUIRE an `originator` — a domain-like string
// identifying this app — when connecting from Node.js; without one the
// substrate throws immediately instead of falling through. Set it via the
// UHRP_WALLET_ORIGINATOR env var (see config.py); it's what shows up in the
// wallet's permission prompt.
import fs from 'node:fs'
import crypto from 'node:crypto'
import { WalletClient, StorageUploader } from '@bsv/sdk'
import { mimeForPath } from './mime.mjs'

async function main () {
  const [, , filePath, retentionMinutesArg, storageURL] = process.argv
  if (!filePath) {
    console.log(JSON.stringify({ ok: false, error: 'usage: upload.mjs <filePath> <retentionMinutes> [storageURL]' }))
    process.exitCode = 1
    return
  }
  const retentionPeriod = parseInt(retentionMinutesArg, 10)
  if (!Number.isInteger(retentionPeriod) || retentionPeriod < 1) {
    console.log(JSON.stringify({ ok: false, error: 'retentionMinutes must be a positive integer' }))
    process.exitCode = 1
    return
  }

  const originator = process.env.UHRP_WALLET_ORIGINATOR || 'localhost'

  try {
    const data = fs.readFileSync(filePath)
    const bytes = new Uint8Array(data)
    const sha256 = crypto.createHash('sha256').update(data).digest('hex')
    const mimeType = mimeForPath(filePath)

    const wallet = new WalletClient('auto', originator)
    const uploader = new StorageUploader(storageURL ? { storageURL, wallet } : { wallet })

    const result = await uploader.publishFile({
      file: { data: bytes, type: mimeType },
      retentionPeriod
    })

    console.log(JSON.stringify({
      ok: true,
      published: result.published,
      uhrpURL: result.uhrpURL,
      hostedBy: result.hostedBy,
      sha256,
      mimeType,
      size: bytes.length
    }))
  } catch (err) {
    console.log(JSON.stringify({ ok: false, error: err && err.message ? err.message : String(err) }))
    process.exitCode = 1
  }
}

main()
