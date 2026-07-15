// Looks up name/size/mimeType/expiry for one UHRP URL already on a host.
// Usage: node find.mjs <uhrpURL> [storageURL]
import { WalletClient, StorageUploader } from '@bsv/sdk'

async function main () {
  const [, , uhrpURL, storageURL] = process.argv
  if (!uhrpURL) {
    console.log(JSON.stringify({ ok: false, error: 'usage: find.mjs <uhrpURL> [storageURL]' }))
    process.exitCode = 1
    return
  }
  const originator = process.env.UHRP_WALLET_ORIGINATOR || 'localhost'

  try {
    const wallet = new WalletClient('auto', originator)
    const uploader = new StorageUploader(storageURL ? { storageURL, wallet } : { wallet })
    const data = await uploader.findFile(uhrpURL)
    console.log(JSON.stringify({ ok: true, data }))
  } catch (err) {
    console.log(JSON.stringify({ ok: false, error: err && err.message ? err.message : String(err) }))
    process.exitCode = 1
  }
}

main()
