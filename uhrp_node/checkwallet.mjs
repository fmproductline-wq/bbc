// Verifies a BRC-100 wallet (e.g. Metanet Client) is reachable before an
// upload tries to pay it. No file is touched and nothing is spent.
//
// Usage: node checkwallet.mjs
import { WalletClient } from '@bsv/sdk'

async function main () {
  const originator = process.env.UHRP_WALLET_ORIGINATOR || 'localhost'
  try {
    const wallet = new WalletClient('auto', originator)
    await wallet.connectToSubstrate()
    const { version } = await wallet.getVersion({})

    let identityKey = null
    try {
      const pk = await wallet.getPublicKey({ identityKey: true })
      identityKey = pk.publicKey
    } catch {
      // Some wallets require an explicit permission grant for this call;
      // connectivity itself is still confirmed by getVersion above.
    }

    console.log(JSON.stringify({ ok: true, version, identityKey, originator }))
  } catch (err) {
    console.log(JSON.stringify({ ok: false, error: err && err.message ? err.message : String(err), originator }))
    process.exitCode = 1
  }
}

main()
