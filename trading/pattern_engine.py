"""
Best Brand Co. — Signal Pattern Engine

Learns entry/exit timing from HOTT/LOTT + Xtreme Trend historical signals.

For any coin/timeframe it:
  1. Fetches N candles of history
  2. Runs HOTT/LOTT and Xtreme Trend on them
  3. Finds every signal that fired and measures the outcome
     (did price go up or down over the next 1/3/5/10 candles?)
  4. Builds a pattern stat table — win rate, avg gain, avg loss, R:R per setup
  5. Scores the CURRENT signal against those historical stats
  6. Returns a verdict: ENTER / WAIT / EXIT with confidence %

Signal combinations tracked
────────────────────────────
  BOTH_BUY   — HOTT trend=+1 AND xt_signal=+1   (strongest long)
  HL_BUY     — HOTT trend=+1, xt flat             (trend confirmed, no XT)
  XT_BUY     — xt_signal=+1, HOTT flat            (XT fired, trend not yet)
  BOTH_SELL  — HOTT trend=-1 AND xt_signal=-1    (strongest short)
  HL_SELL    — HOTT trend=-1, xt flat
  XT_SELL    — xt_signal=-1, HOTT flat
  CONFLICT   — indicators disagree
  FLAT       — both flat / neutral
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import pandas as pd
import numpy as np
from loguru import logger


# ── Signal label helpers ───────────────────────────────────────────────────────

def _label(hl: int, xt: int) -> str:
    if hl == 1 and xt == 1:  return "BOTH_BUY"
    if hl == -1 and xt == -1: return "BOTH_SELL"
    if hl == 1 and xt == 0:  return "HL_BUY"
    if hl == -1 and xt == 0: return "HL_SELL"
    if xt == 1 and hl == 0:  return "XT_BUY"
    if xt == -1 and hl == 0: return "XT_SELL"
    if hl != 0 and xt != 0 and hl != xt: return "CONFLICT"
    return "FLAT"


BUY_LABELS  = {"BOTH_BUY", "HL_BUY", "XT_BUY"}
SELL_LABELS = {"BOTH_SELL", "HL_SELL", "XT_SELL"}


# ── Outcome dataclass ──────────────────────────────────────────────────────────

@dataclass
class PatternStats:
    label: str
    count: int                = 0
    wins: int                 = 0
    losses: int               = 0
    total_gain_pct: float     = 0.0   # sum of winning trade %
    total_loss_pct: float     = 0.0   # sum of losing trade % (positive number)
    avg_bars_to_peak: float   = 0.0

    @property
    def win_rate(self) -> float:
        return self.wins / self.count if self.count else 0.0

    @property
    def avg_win(self) -> float:
        return self.total_gain_pct / self.wins if self.wins else 0.0

    @property
    def avg_loss(self) -> float:
        return self.total_loss_pct / self.losses if self.losses else 0.0

    @property
    def expectancy(self) -> float:
        """Expected % gain per trade."""
        return (self.win_rate * self.avg_win) - ((1 - self.win_rate) * self.avg_loss)

    @property
    def rr(self) -> float:
        return self.avg_win / self.avg_loss if self.avg_loss > 0 else 0.0

    def summary(self) -> str:
        if self.count == 0:
            return f"{self.label}: no history"
        return (
            f"{self.label}: {self.count} signals | "
            f"Win {self.win_rate*100:.0f}% | "
            f"Avg +{self.avg_win:.2f}% / -{self.avg_loss:.2f}% | "
            f"R:R {self.rr:.1f} | EV {self.expectancy:+.2f}%"
        )


# ── Verdict dataclass ──────────────────────────────────────────────────────────

@dataclass
class SignalVerdict:
    action: str           # "LONG" | "SHORT" | "CLOSE" | "WAIT"
    confidence: float     # 0–100
    label: str            # signal combo name
    win_rate: float
    expectancy: float
    rr: float
    sample_size: int
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    reasoning: str

    def to_text(self) -> str:
        bar = "█" * int(self.confidence / 10) + "░" * (10 - int(self.confidence / 10))
        return (
            f"{'📈' if self.action=='LONG' else '📉' if self.action=='SHORT' else '⏸'} "
            f"*{self.action}*  [{bar}] {self.confidence:.0f}%\n"
            f"Setup:      `{self.label}`\n"
            f"Win rate:   `{self.win_rate*100:.0f}%` ({self.sample_size} past signals)\n"
            f"Expectancy: `{self.expectancy:+.2f}%` per trade\n"
            f"R:R:        `1:{self.rr:.1f}`\n"
            f"Entry:      `${self.entry_price:,.4f}`\n"
            f"Stop:       `${self.stop_loss:,.4f}`\n"
            f"TP1:        `${self.take_profit_1:,.4f}`\n"
            f"TP2:        `${self.take_profit_2:,.4f}`\n"
            f"_{self.reasoning}_"
        )


# ── Core engine ───────────────────────────────────────────────────────────────

MIN_SAMPLES  = 5     # need at least this many past signals to act
LOOK_FORWARD = 10    # candles ahead to measure outcome
WIN_THRESHOLD = 0.3  # price must move 0.3% in signal direction to count as win
MIN_WIN_RATE  = 0.52 # below this → WAIT
MIN_EV        = 0.1  # minimum positive expectancy % to take a trade


def backtest_signals(df: pd.DataFrame) -> dict[str, PatternStats]:
    """
    Run HOTT/LOTT + Xtreme Trend on df and measure outcomes.
    Returns a dict of PatternStats keyed by label.
    """
    from analysis.market_analyzer import hott_lott, xtreme_trend

    df = hott_lott(df.copy())
    df = xtreme_trend(df)

    stats: dict[str, PatternStats] = {}

    # Walk each candle (leave LOOK_FORWARD candles at the end for outcome measurement)
    for i in range(1, len(df) - LOOK_FORWARD):
        prev_hl  = int(df["hott_lott_trend"].iloc[i - 1])
        curr_hl  = int(df["hott_lott_trend"].iloc[i])
        prev_xt  = int(df["xt_signal"].iloc[i - 1])
        curr_xt  = int(df["xt_signal"].iloc[i])

        # Only record the FIRST candle of a new signal (state change)
        hl_new = curr_hl != prev_hl
        xt_new = curr_xt != prev_xt
        if not (hl_new or xt_new):
            continue

        label = _label(curr_hl, curr_xt)
        if label in ("FLAT", "CONFLICT"):
            continue

        entry = float(df["close"].iloc[i])
        future = df["close"].iloc[i + 1 : i + 1 + LOOK_FORWARD]
        peak   = float(future.max())
        trough = float(future.min())

        is_buy  = label in BUY_LABELS
        is_sell = label in SELL_LABELS

        if is_buy:
            gain_pct = (peak   - entry) / entry * 100
            loss_pct = (entry  - trough) / entry * 100
            win = gain_pct >= WIN_THRESHOLD
        else:
            gain_pct = (entry  - trough) / entry * 100
            loss_pct = (peak   - entry)  / entry * 100
            win = gain_pct >= WIN_THRESHOLD

        # Find bars to peak/trough
        if is_buy:
            peak_bar = int(future.values.argmax()) + 1
        else:
            peak_bar = int(future.values.argmin()) + 1

        if label not in stats:
            stats[label] = PatternStats(label=label)
        s = stats[label]
        s.count += 1
        if win:
            s.wins += 1
            s.total_gain_pct += gain_pct
        else:
            s.losses += 1
            s.total_loss_pct += loss_pct
        s.avg_bars_to_peak = (s.avg_bars_to_peak * (s.count - 1) + peak_bar) / s.count

    return stats


def evaluate_current(df: pd.DataFrame, atr_multiplier_sl: float = 1.5,
                     atr_multiplier_tp: float = 3.0) -> SignalVerdict:
    """
    Given a DataFrame (with HOTT/LOTT + Xtreme Trend already computed,
    or we compute them here), evaluate the current bar's signal against
    historical pattern stats and return a verdict with entry/exit levels.
    """
    from analysis.market_analyzer import hott_lott, xtreme_trend, atr as calc_atr

    # Always recompute on the full history for accurate stats
    df = hott_lott(df.copy())
    df = xtreme_trend(df)

    stats = backtest_signals(df)

    # Current signal
    last  = df.iloc[-1]
    prev  = df.iloc[-2]
    curr_hl = int(last["hott_lott_trend"])
    curr_xt = int(last["xt_signal"])
    label   = _label(curr_hl, curr_xt)

    entry   = float(last["close"])
    atr_val = float(calc_atr(df).iloc[-1])

    # Default neutral levels
    sl  = entry - atr_val * atr_multiplier_sl
    tp1 = entry + atr_val * atr_multiplier_tp
    tp2 = entry + atr_val * atr_multiplier_tp * 1.8

    s = stats.get(label)

    # ── FLAT or CONFLICT → always WAIT ────────────────────────────────────────
    if label in ("FLAT", "CONFLICT"):
        return SignalVerdict(
            action="WAIT", confidence=0, label=label,
            win_rate=0, expectancy=0, rr=0, sample_size=0,
            entry_price=entry, stop_loss=sl, take_profit_1=tp1, take_profit_2=tp2,
            reasoning="Indicators conflict or flat — no edge. Stay out.",
        )

    # ── Not enough history → WAIT ──────────────────────────────────────────────
    if s is None or s.count < MIN_SAMPLES:
        return SignalVerdict(
            action="WAIT", confidence=10, label=label,
            win_rate=0, expectancy=0, rr=0,
            sample_size=s.count if s else 0,
            entry_price=entry, stop_loss=sl, take_profit_1=tp1, take_profit_2=tp2,
            reasoning=f"Only {s.count if s else 0} past signals for {label} — need {MIN_SAMPLES} minimum.",
        )

    # ── Stats below threshold → WAIT ──────────────────────────────────────────
    if s.win_rate < MIN_WIN_RATE or s.expectancy < MIN_EV:
        return SignalVerdict(
            action="WAIT", confidence=20, label=label,
            win_rate=s.win_rate, expectancy=s.expectancy, rr=s.rr,
            sample_size=s.count,
            entry_price=entry, stop_loss=sl, take_profit_1=tp1, take_profit_2=tp2,
            reasoning=(
                f"{label} has {s.win_rate*100:.0f}% win rate and {s.expectancy:+.2f}% EV "
                f"across {s.count} signals — below threshold. Waiting for better setup."
            ),
        )

    # ── Signal has edge — determine direction ──────────────────────────────────
    is_buy = label in BUY_LABELS

    # ATR-based levels
    if is_buy:
        sl  = entry - atr_val * atr_multiplier_sl
        tp1 = entry + atr_val * atr_multiplier_tp
        tp2 = entry + atr_val * atr_multiplier_tp * 1.8
        action = "LONG"
    else:
        sl  = entry + atr_val * atr_multiplier_sl
        tp1 = entry - atr_val * atr_multiplier_tp
        tp2 = entry - atr_val * atr_multiplier_tp * 1.8
        action = "SHORT"

    # Confidence: blend win rate + EV + sample size (capped at 95)
    sample_weight = min(s.count / 30, 1.0)        # more samples = more confidence
    raw = (s.win_rate * 60) + (min(s.expectancy, 3.0) / 3.0 * 25) + (sample_weight * 15)
    confidence = min(round(raw, 1), 95.0)

    # Label strength description
    strength = {
        "BOTH_BUY":  "HOTT + Xtreme Trend both bullish — strongest long setup",
        "BOTH_SELL": "HOTT + Xtreme Trend both bearish — strongest short setup",
        "HL_BUY":    "HOTT trend confirmed bullish; Xtreme Trend not yet triggered",
        "HL_SELL":   "HOTT trend confirmed bearish; Xtreme Trend not yet triggered",
        "XT_BUY":    "Xtreme Trend fired bullish; HOTT trend band not yet broken",
        "XT_SELL":   "Xtreme Trend fired bearish; HOTT trend band not yet broken",
    }.get(label, label)

    reasoning = (
        f"{strength}. "
        f"Pattern has fired {s.count}× — won {s.wins}/{s.count} ({s.win_rate*100:.0f}%). "
        f"Avg gain {s.avg_win:.2f}% vs avg loss {s.avg_loss:.2f}% "
        f"(R:R {s.rr:.1f}). EV {s.expectancy:+.2f}% per trade."
    )

    return SignalVerdict(
        action=action, confidence=confidence, label=label,
        win_rate=s.win_rate, expectancy=s.expectancy, rr=s.rr,
        sample_size=s.count,
        entry_price=entry,
        stop_loss=round(sl, 6),
        take_profit_1=round(tp1, 6),
        take_profit_2=round(tp2, 6),
        reasoning=reasoning,
    )


def full_report(coin: str, timeframe: str = "1h", limit: int = 300) -> tuple[SignalVerdict, dict[str, PatternStats]]:
    """
    Fetch candles, run the pattern engine, return (verdict, all_stats).
    limit should be large (300+) to get meaningful backtest stats.
    """
    from analysis.data_fetcher import fetch_candles
    df = fetch_candles(coin, timeframe, limit)
    if df.empty or len(df) < 50:
        raise ValueError(f"Not enough data for {coin} {timeframe}")
    stats   = backtest_signals(df)
    verdict = evaluate_current(df)
    return verdict, stats
