"""
Probability analyzer for prediction markets.

Methods:
  - Kelly criterion for optimal bet sizing
  - Bayesian probability estimation from multiple signals
  - Market efficiency scoring (compare market price vs our estimate)
  - Expected value calculator
  - Calibration helpers for Polymarket / Kalshi / Metaculus
"""
from __future__ import annotations
import math
from dataclasses import dataclass


# ── Core probability math ─────────────────────────────────────────────────────

def kelly_fraction(p: float, b: float, f_max: float = 0.25) -> float:
    """
    Kelly criterion: optimal fraction of bankroll to bet.

    Args:
        p:     estimated probability of winning (0–1)
        b:     net odds (e.g. b=1.0 means even money, b=4.0 means 4:1)
        f_max: cap fraction at this value (default 25% — quarter-Kelly is common)

    Returns:
        Fraction of bankroll to bet (0–f_max)
    """
    if p <= 0 or b <= 0:
        return 0.0
    f = (b * p - (1 - p)) / b
    return max(0.0, min(f_max, f))


def implied_probability(price: float, platform: str = "polymarket") -> float:
    """
    Convert market price to implied probability.

    Polymarket: price IS the probability (0–1).
    Kalshi:     price is in cents (1–99), divide by 100.
    """
    if platform == "kalshi":
        return price / 100.0
    return float(price)  # polymarket / metaculus already 0–1


def expected_value(p_est: float, p_market: float, payout_yes: float = 1.0) -> float:
    """
    EV of buying YES at market price p_market given our estimate p_est.

    EV = p_est * (payout_yes - p_market) - (1 - p_est) * p_market
    """
    win = p_est * (payout_yes - p_market)
    lose = (1 - p_est) * p_market
    return win - lose


def edge(p_est: float, p_market: float) -> float:
    """Probability edge = our estimate - market implied probability."""
    return p_est - p_market


# ── Bayesian signal combiner ──────────────────────────────────────────────────

def bayesian_update(prior: float, likelihoods: list[tuple[float, float]]) -> float:
    """
    Update a prior probability given a list of (likelihood_if_true, likelihood_if_false) pairs.

    Each pair represents a piece of evidence:
      - likelihood_if_true:  P(evidence | outcome = YES)
      - likelihood_if_false: P(evidence | outcome = NO)

    Example:
        prior = 0.5
        evidence = [
            (0.8, 0.3),  # strong signal for YES
            (0.6, 0.5),  # weak signal for YES
        ]
        result ≈ 0.73
    """
    p = prior
    for l_true, l_false in likelihoods:
        numerator = l_true * p
        denominator = l_true * p + l_false * (1 - p)
        if denominator == 0:
            continue
        p = numerator / denominator
    return round(p, 4)


def combine_signals(signals: list[float]) -> float:
    """
    Average multiple probability estimates (e.g. from different indicators).
    Clips to [0.01, 0.99].
    """
    if not signals:
        return 0.5
    avg = sum(signals) / len(signals)
    return max(0.01, min(0.99, avg))


# ── Market opportunity scorer ─────────────────────────────────────────────────

@dataclass
class BetOpportunity:
    platform: str
    market_id: str
    question: str
    side: str              # "YES" | "NO"
    market_price: float    # market implied probability
    our_estimate: float    # our probability estimate
    edge_pct: float        # edge in percent points
    kelly_pct: float       # optimal bet size as % of bankroll
    ev: float              # expected value per dollar risked
    verdict: str           # "STRONG BET" | "BET" | "MARGINAL" | "SKIP"
    rationale: str

    def to_telegram(self) -> str:
        emoji = {
            "STRONG BET": "🔥",
            "BET": "✅",
            "MARGINAL": "⚠️",
            "SKIP": "❌",
        }.get(self.verdict, "❓")
        return (
            f"{emoji} *{self.verdict}* — {self.platform}\n"
            f"_{self.question}_\n"
            f"Side: *{self.side}* @ `{self.market_price*100:.1f}¢`\n"
            f"Our estimate: `{self.our_estimate*100:.1f}%`\n"
            f"Edge: `{self.edge_pct:+.1f}pp` | EV: `{self.ev*100:.2f}¢/$`\n"
            f"Kelly bet: `{self.kelly_pct*100:.1f}% of bankroll`\n"
            f"_{self.rationale}_"
        )


def score_opportunity(
    platform: str,
    market_id: str,
    question: str,
    market_price_raw: float,   # as returned by the API (0–1 or cents)
    our_estimate: float,       # our probability 0–1
    side: str = "YES",
) -> BetOpportunity:
    """
    Score a prediction market bet opportunity.

    For YES bets: we bet when market_price < our_estimate.
    For NO  bets: we bet when (1-market_price) < (1-our_estimate)
                            = our_estimate < market_price.
    """
    p_market = implied_probability(market_price_raw, platform)
    p_est = our_estimate

    if side.upper() == "NO":
        # Flip to express as probability of the NO outcome
        p_market_side = 1 - p_market
        p_est_side = 1 - p_est
    else:
        p_market_side = p_market
        p_est_side = p_est

    # Net odds b: if we risk p_market_side, we gain (1 - p_market_side)
    b = (1 - p_market_side) / p_market_side if p_market_side > 0 else 0
    ev = expected_value(p_est_side, p_market_side)
    kel = kelly_fraction(p_est_side, b, f_max=0.20)
    edg = edge(p_est_side, p_market_side) * 100  # in percentage points

    if edg > 15 and kel > 0.05:
        verdict = "STRONG BET"
    elif edg > 8 and kel > 0.02:
        verdict = "BET"
    elif edg > 3:
        verdict = "MARGINAL"
    else:
        verdict = "SKIP"

    rationale = (
        f"Market implies {p_market_side*100:.1f}% for {side}, "
        f"we estimate {p_est_side*100:.1f}%. "
        f"{'Good edge.' if edg > 8 else 'Thin edge.' if edg > 3 else 'No edge — skip.'}"
    )

    return BetOpportunity(
        platform=platform,
        market_id=market_id,
        question=question,
        side=side.upper(),
        market_price=p_market_side,
        our_estimate=p_est_side,
        edge_pct=round(edg, 2),
        kelly_pct=round(kel, 4),
        ev=round(ev, 4),
        verdict=verdict,
        rationale=rationale,
    )


# ── Crypto-to-prediction-market bridge ───────────────────────────────────────

def estimate_crypto_market_prob(
    current_price: float,
    target_price: float,
    days_to_resolve: int,
    annualized_vol: float = 0.80,  # 80% annual vol is typical for BTC
) -> float:
    """
    Log-normal probability that price reaches target_price within days_to_resolve.

    Uses Black-Scholes-style log-normal model.
    Good for prediction markets like "Will BTC be above $100k by Dec 2025?"
    """
    if days_to_resolve <= 0 or current_price <= 0 or target_price <= 0:
        return 0.5

    t = days_to_resolve / 365.0
    sigma = annualized_vol
    mu = 0.0  # risk-neutral drift (simplified)

    # P(S_T > K) = N(d2) where S_T log-normally distributed
    d2 = (math.log(current_price / target_price) + (mu - 0.5 * sigma ** 2) * t) / (sigma * math.sqrt(t))

    # Standard normal CDF approximation
    return _norm_cdf(d2)


def _norm_cdf(x: float) -> float:
    """Standard normal CDF via math.erfc."""
    return 0.5 * math.erfc(-x / math.sqrt(2))
