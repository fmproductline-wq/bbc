"""
Best Brand Co. — Personal Trade History Database  (#3)

Every executed trade is stored in ~/.bestbrand/trades.db (SQLite).
Trades are linked to which signal combo fired them (BOTH_BUY etc.)
so the pattern engine can learn from YOUR actual results, not just
historical price action.

Schema
──────
  trades:
    id           INTEGER PK
    ticker       TEXT
    timeframe    TEXT
    signal_label TEXT      (BOTH_BUY, HL_SELL, ...)
    action       TEXT      (LONG / SHORT)
    entry_price  REAL
    exit_price   REAL      (NULL while open)
    size         REAL
    stop_loss    REAL
    take_profit1 REAL
    take_profit2 REAL
    confidence   REAL
    opened_at    REAL      (unix ts)
    closed_at    REAL      (NULL while open)
    pnl_usd      REAL      (NULL while open)
    pnl_pct      REAL      (NULL while open)
    outcome      TEXT      (NULL | 'win' | 'loss' | 'breakeven')
    notes        TEXT
"""
from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional
from loguru import logger

_BBC_DIR   = Path.home() / ".bestbrand"
_DB_PATH   = _BBC_DIR / "trades.db"

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS trades (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker       TEXT    NOT NULL,
    timeframe    TEXT    NOT NULL DEFAULT '1h',
    signal_label TEXT    NOT NULL DEFAULT '',
    action       TEXT    NOT NULL,
    entry_price  REAL    NOT NULL,
    exit_price   REAL,
    size         REAL    NOT NULL DEFAULT 0,
    stop_loss    REAL,
    take_profit1 REAL,
    take_profit2 REAL,
    confidence   REAL    DEFAULT 0,
    opened_at    REAL    NOT NULL,
    closed_at    REAL,
    pnl_usd      REAL,
    pnl_pct      REAL,
    outcome      TEXT,
    notes        TEXT
);
"""


@contextmanager
def _db():
    _BBC_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(_CREATE_SQL)
        conn.commit()
        yield conn
    finally:
        conn.close()


def record_open(
    ticker: str,
    action: str,
    entry_price: float,
    size: float,
    stop_loss: float,
    take_profit1: float,
    take_profit2: float,
    signal_label: str = "",
    timeframe: str = "1h",
    confidence: float = 0.0,
    notes: str = "",
) -> int:
    """Record a new open trade. Returns the new trade id."""
    with _db() as conn:
        cur = conn.execute(
            """INSERT INTO trades
               (ticker, timeframe, signal_label, action, entry_price, size,
                stop_loss, take_profit1, take_profit2, confidence, opened_at, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (ticker, timeframe, signal_label, action, entry_price, size,
             stop_loss, take_profit1, take_profit2, confidence, time.time(), notes),
        )
        conn.commit()
        trade_id = cur.lastrowid
        logger.info(f"Trade history: opened #{trade_id} {action} {ticker} @ {entry_price}")
        return trade_id


def record_close(
    trade_id: int,
    exit_price: float,
    pnl_usd: Optional[float] = None,
    notes: str = "",
) -> None:
    """Mark a trade as closed and record its outcome."""
    with _db() as conn:
        row = conn.execute("SELECT * FROM trades WHERE id=?", (trade_id,)).fetchone()
        if not row:
            logger.warning(f"Trade #{trade_id} not found in history")
            return

        entry = row["entry_price"]
        action = row["action"]
        size   = row["size"]

        if pnl_usd is None:
            if action == "LONG":
                pnl_usd = (exit_price - entry) * size
            else:
                pnl_usd = (entry - exit_price) * size

        pnl_pct = ((exit_price - entry) / entry * 100) if action == "LONG" \
                  else ((entry - exit_price) / entry * 100)

        if pnl_pct > 0.1:
            outcome = "win"
        elif pnl_pct < -0.1:
            outcome = "loss"
        else:
            outcome = "breakeven"

        conn.execute(
            """UPDATE trades SET exit_price=?, closed_at=?, pnl_usd=?, pnl_pct=?,
               outcome=?, notes=COALESCE(notes||' '||?, notes) WHERE id=?""",
            (exit_price, time.time(), pnl_usd, pnl_pct, outcome, notes, trade_id),
        )
        conn.commit()
        logger.info(f"Trade history: closed #{trade_id} {outcome} PnL={pnl_pct:+.2f}%")


def get_open_trades() -> list[dict]:
    with _db() as conn:
        rows = conn.execute(
            "SELECT * FROM trades WHERE closed_at IS NULL ORDER BY opened_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_closed_trades(limit: int = 200) -> list[dict]:
    with _db() as conn:
        rows = conn.execute(
            "SELECT * FROM trades WHERE closed_at IS NOT NULL ORDER BY closed_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_all_trades(limit: int = 500) -> list[dict]:
    with _db() as conn:
        rows = conn.execute(
            "SELECT * FROM trades ORDER BY opened_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_personal_stats_by_label() -> dict[str, dict]:
    """
    Return win/loss stats grouped by signal_label for use in the pattern engine.
    Only counts closed trades.
    """
    with _db() as conn:
        rows = conn.execute(
            """SELECT signal_label,
                      COUNT(*) as total,
                      SUM(CASE WHEN outcome='win' THEN 1 ELSE 0 END) as wins,
                      SUM(CASE WHEN outcome='loss' THEN 1 ELSE 0 END) as losses,
                      AVG(CASE WHEN outcome='win' THEN pnl_pct ELSE NULL END) as avg_win,
                      AVG(CASE WHEN outcome='loss' THEN pnl_pct ELSE NULL END) as avg_loss,
                      AVG(pnl_pct) as avg_pnl
               FROM trades
               WHERE closed_at IS NOT NULL AND signal_label != ''
               GROUP BY signal_label""",
        ).fetchall()
    return {r["signal_label"]: dict(r) for r in rows}


def get_summary() -> dict:
    """Return overall performance summary."""
    with _db() as conn:
        row = conn.execute(
            """SELECT
                 COUNT(*) as total_trades,
                 SUM(CASE WHEN closed_at IS NOT NULL THEN 1 ELSE 0 END) as closed,
                 SUM(CASE WHEN outcome='win' THEN 1 ELSE 0 END) as wins,
                 SUM(CASE WHEN outcome='loss' THEN 1 ELSE 0 END) as losses,
                 SUM(COALESCE(pnl_usd,0)) as total_pnl_usd,
                 AVG(CASE WHEN pnl_pct IS NOT NULL THEN pnl_pct END) as avg_pnl_pct,
                 MAX(pnl_pct) as best_trade_pct,
                 MIN(pnl_pct) as worst_trade_pct
               FROM trades"""
        ).fetchone()
    return dict(row) if row else {}


def get_equity_curve() -> list[dict]:
    """Return closed trades in time order with cumulative PnL for equity curve chart."""
    with _db() as conn:
        rows = conn.execute(
            """SELECT closed_at, pnl_usd, ticker, action, outcome
               FROM trades WHERE closed_at IS NOT NULL
               ORDER BY closed_at ASC"""
        ).fetchall()

    curve = []
    cum = 0.0
    for r in rows:
        cum += r["pnl_usd"] or 0
        curve.append({
            "ts":       r["closed_at"],
            "pnl_usd":  r["pnl_usd"],
            "cumulative": cum,
            "ticker":  r["ticker"],
            "action":  r["action"],
            "outcome": r["outcome"],
        })
    return curve
