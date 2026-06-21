"""Web3 wallet connection using Rabby wallet private key."""
from web3 import Web3
from eth_account import Account
from loguru import logger
from config import cfg


def get_web3(chain: str | None = None) -> Web3:
    rpc = {
        "ethereum": cfg.ETH_RPC_URL,
        "polygon": cfg.POLYGON_RPC_URL,
        "bsc": cfg.BSC_RPC_URL,
    }.get(chain or cfg.DEFAULT_CHAIN, cfg.rpc_url)
    w3 = Web3(Web3.HTTPProvider(rpc))
    return w3


def get_account() -> Account:
    return Account.from_key(cfg.WALLET_PRIVATE_KEY)


def get_balance_native(chain: str | None = None) -> float:
    """Return native token balance (ETH/MATIC/BNB) in human-readable units."""
    w3 = get_web3(chain)
    bal_wei = w3.eth.get_balance(cfg.WALLET_ADDRESS)
    return float(w3.from_wei(bal_wei, "ether"))


ERC20_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}],
     "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals",
     "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "symbol",
     "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_spender", "type": "address"},
                                    {"name": "_value", "type": "uint256"}],
     "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
]


def get_token_balance(token_address: str, chain: str | None = None) -> tuple[float, str]:
    """Return (balance, symbol) for an ERC-20 token."""
    w3 = get_web3(chain)
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(token_address),
        abi=ERC20_ABI,
    )
    decimals = contract.functions.decimals().call()
    symbol = contract.functions.symbol().call()
    raw = contract.functions.balanceOf(cfg.WALLET_ADDRESS).call()
    return raw / (10 ** decimals), symbol


def approve_token(token_address: str, spender: str, amount_wei: int, chain: str | None = None) -> str:
    """Approve a spender (e.g. 1inch router) to spend tokens. Returns tx hash."""
    w3 = get_web3(chain)
    account = get_account()
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(token_address),
        abi=ERC20_ABI,
    )
    nonce = w3.eth.get_transaction_count(account.address)
    tx = contract.functions.approve(
        Web3.to_checksum_address(spender), amount_wei
    ).build_transaction({
        "from": account.address,
        "nonce": nonce,
        "gas": 100_000,
        "gasPrice": w3.eth.gas_price,
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    logger.info(f"Approval tx: {tx_hash.hex()}")
    w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    return tx_hash.hex()
