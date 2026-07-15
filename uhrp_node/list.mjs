// Lists every file this wallet's identity has hosted on the storage provider.
// This is what backs the "Files" / "Manage Your Files" view in UHRP storage
// UIs. Requires the same wallet used for uploading (authenticated route).
//
// Usage: node list.mjs [storageURL]
import { WalletClient, StorageUploader } from '@bsv/sdk'

async function main () {
  const [, , storageURL] = process.argv
  const originator = process.env.UHRP_WALLET_ORIGINATOR || 'localhost'

  try {
    const wallet = new WalletClient('auto', originator)
    const uploader = new StorageUploader(storageURL ? { storageURL, wallet } : { wallet })
    const uploads = await uploader.listUploads()
    console.log(JSON.stringify({ ok: true, uploads }))
  } catch (err) {
    console.log(JSON.stringify({ ok: false, error: err && err.message ? err.message : String(err) }))
    process.exitCode = 1
  }
}

main()
