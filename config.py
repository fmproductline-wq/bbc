import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Wallet
    WALLET_PRIVATE_KEY: str = os.getenv("WALLET_PRIVATE_KEY", "")
    WALLET_ADDRESS: str = os.getenv("WALLET_ADDRESS", "")

    # RPC
    ETH_RPC_URL: str = os.getenv("ETH_RPC_URL", "https://eth.llamarpc.com")
    POLYGON_RPC_URL: str = os.getenv("POLYGON_RPC_URL", "https://polygon.llamarpc.com")
    BSC_RPC_URL: str = os.getenv("BSC_RPC_URL", "https://bsc-dataseed.binance.org/")
    DEFAULT_CHAIN: str = os.getenv("DEFAULT_CHAIN", "polygon")

    # 1inch
    ONEINCH_API_KEY: str = os.getenv("ONEINCH_API_KEY", "")

    # Platform fee — 0.02% of every trade notional, sent to this wallet
    FEE_WALLET_ADDRESS: str = os.getenv("FEE_WALLET_ADDRESS", "")
    FEE_BPS: float = 2.0   # 2 basis points = 0.02% — do not change

    # TradingView
    TRADINGVIEW_WEBHOOK_SECRET: str = os.getenv("TRADINGVIEW_WEBHOOK_SECRET", "")

    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_ALLOWED_USER_ID: int = int(os.getenv("TELEGRAM_ALLOWED_USER_ID", "0"))

    # Polymarket
    POLYMARKET_API_KEY: str = os.getenv("POLYMARKET_API_KEY", "")
    POLYMARKET_API_SECRET: str = os.getenv("POLYMARKET_API_SECRET", "")
    POLYMARKET_API_PASSPHRASE: str = os.getenv("POLYMARKET_API_PASSPHRASE", "")

    # Kalshi
    KALSHI_EMAIL: str = os.getenv("KALSHI_EMAIL", "")
    KALSHI_PASSWORD: str = os.getenv("KALSHI_PASSWORD", "")
    KALSHI_API_KEY: str = os.getenv("KALSHI_API_KEY", "")
    KALSHI_BASE_URL: str = os.getenv("KALSHI_BASE_URL", "https://trading-api.kalshi.com/trade-api/v2")

    # Metaculus
    METACULUS_TOKEN: str = os.getenv("METACULUS_TOKEN", "")

    # Stripe payments
    STRIPE_SECRET_KEY: str       = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_PUBLISHABLE_KEY: str  = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    STRIPE_WEBHOOK_SECRET: str   = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    STRIPE_PRICE_ID: str         = os.getenv("STRIPE_PRICE_ID", "")   # one-time price ID
    APP_BASE_URL: str            = os.getenv("APP_BASE_URL", "https://bestbrand.ca")

    # Risk
    MAX_TRADE_PCT: float = float(os.getenv("MAX_TRADE_PCT", "5"))
    MAX_BET_PCT: float = float(os.getenv("MAX_BET_PCT", "2"))
    SLIPPAGE_PCT: float = float(os.getenv("SLIPPAGE_PCT", "1"))
    STOP_LOSS_PCT: float = float(os.getenv("STOP_LOSS_PCT", "3"))
    # Risk-based position sizing: % of account to risk per trade (used with ATR stop distance)
    RISK_PCT_PER_TRADE: float = float(os.getenv("RISK_PCT_PER_TRADE", "1.0"))
    # Multi-timeframe: require 4h to agree with 1h before firing signal
    MTF_CONFIRMATION: bool = os.getenv("MTF_CONFIRMATION", "true").lower() == "true"
    # Trailing stop: move SL to breakeven after TP1 hit
    TRAILING_STOP: bool = os.getenv("TRAILING_STOP", "true").lower() == "true"

    CHAIN_IDS = {
        "ethereum": 1,
        "polygon": 137,
        "bsc": 56,
    }

    RPC_URLS = {
        "ethereum": ETH_RPC_URL,
        "polygon": POLYGON_RPC_URL,
        "bsc": BSC_RPC_URL,
    }

    @property
    def chain_id(self) -> int:
        return self.CHAIN_IDS.get(self.DEFAULT_CHAIN, 137)

    @property
    def rpc_url(self) -> str:
        return {
            "ethereum": self.ETH_RPC_URL,
            "polygon": self.POLYGON_RPC_URL,
            "bsc": self.BSC_RPC_URL,
        }.get(self.DEFAULT_CHAIN, self.POLYGON_RPC_URL)


cfg = Config()
