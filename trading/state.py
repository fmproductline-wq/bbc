"""Shared in-memory state for the bot."""
from dataclasses import dataclass, field
from typing import Optional
import time


@dataclass
class Position:
    token_in: str
    token_out: str
    amount_in: float
    amount_out: float
    entry_price: float
    stop_loss: float
    chain: str
    tx_hash: str
    opened_at: float = field(default_factory=time.time)
    closed: bool = False
    close_tx: Optional[str] = None
    pnl: Optional[float] = None
    take_profit_1: Optional[float] = None
    take_profit_2: Optional[float] = None
    size: float = 0.0
    trade_history_id: Optional[int] = None   # FK into trade_history DB


class BotState:
    def __init__(self):
        self.running: bool = False
        self.auto_trade: bool = False
        self.auto_bet: bool = False
        self.positions: list[Position] = []
        self.signal_log: list[dict] = []
        self.bet_log: list[dict] = []

    def log_signal(self, signal: dict):
        self.signal_log.insert(0, signal)
        if len(self.signal_log) > 100:
            self.signal_log.pop()

    def log_bet(self, bet: dict):
        self.bet_log.insert(0, bet)
        if len(self.bet_log) > 100:
            self.bet_log.pop()

    def open_positions(self) -> list[Position]:
        return [p for p in self.positions if not p.closed]


state = BotState()
