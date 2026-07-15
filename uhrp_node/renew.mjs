// Extends the hosting commitment for a UHRP file. Pays an additional fee
// through the wallet, same as the "Renew" action in UHRP storage UIs.
// Usage: node renew.mjs <uhrpURL> <additionalMinutes> [storageURL]
import { WalletClient, StorageUploader } from '@bsv/sdk'

async function main () {
  const [, , uhrpURL, additionalMinutesArg, storageURL] = process.argv
  const additionalMinutes = parseInt(additionalMinutesArg, 10)
  if (!uhrpURL || !Number.isInteger(additionalMinutes) || additionalMinutes < 1) {
    console.log(JSON.stringify({ ok: false, error: 'usage: renew.mjs <uhrpURL> <additionalMinutes> [storageURL]' }))
    process.exitCode = 1
    return
  }
  const originator = process.env.UHRP_WALLET_ORIGINATOR || 'localhost'

  try {
    const wallet = new WalletClient('auto', originator)
    const uploader = new StorageUploader(storageURL ? { storageURL, wallet } : { wallet })
    const result = await uploader.renewFile(uhrpURL, additionalMinutes)
    console.log(JSON.stringify({ ok: true, ...result }))
  } catch (err) {
    console.log(JSON.stringify({ ok: false, error: err && err.message ? err.message : String(err) }))
    process.exitCode = 1
  }
}

main()
