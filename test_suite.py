"""
Best Brand Co. — Full Functional Test Suite
Tests every core module with real logic, no mocking.
"""
import sys, os, time, tempfile, shutil
sys.path.insert(0, "/home/user/bbc")
os.environ.setdefault("WALLET_PRIVATE_KEY", "0x" + "a" * 64)
os.environ.setdefault("WALLET_ADDRESS", "0x35FC6d6d715Fe6B699783030BF3AdF2d75c6645a")

PASS = "✅"
FAIL = "❌"
WARN = "⚠️ "
results = []

def test(name, fn):
    try:
        msg = fn()
        results.append((PASS, name, msg or ""))
        print(f"{PASS} {name}{' — '+msg if msg else ''}")
    except Exception as e:
        results.append((FAIL, name, str(e)))
        print(f"{FAIL} {name} — {e}")

print("\n" + "="*60)
print("  BEST BRAND CO. — FUNCTIONAL TEST SUITE")
print("="*60 + "\n")

# ── 1. Config loads ────────────────────────────────────────────
def t_config():
    from config import cfg
    assert cfg.RISK_PCT_PER_TRADE == 1.0
    assert cfg.MTF_CONFIRMATION == True
    assert cfg.TRAILING_STOP == True
    assert cfg.FEE_BPS == 2.0
    return f"RISK_PCT={cfg.RISK_PCT_PER_TRADE}% MTF={cfg.MTF_CONFIRMATION}"
test("Config loads with all new fields", t_config)

# ── 2. Key vault — encrypt / decrypt / wrong password ──────────
def t_keyvault():
    from security.key_vault import save_key, load_key, InvalidPassword, delete_vault
    import tempfile, os
    # Use a temp file so we don't touch real vault
    from security import key_vault as kv
    orig = kv._VAULT_FILE
    tmp = tempfile.mktemp(suffix=".enc")
    kv._VAULT_FILE = __import__("pathlib").Path(tmp)
    try:
        fake_key = "0x" + "ab12cd34ef56" * 5 + "ab12"   # 64 hex chars
        save_key(fake_key, "TestPass123!")
        recovered = load_key("TestPass123!")
        assert recovered == fake_key, f"Key mismatch: {recovered}"
        # Wrong password must raise
        try:
            load_key("WrongPassword!")
            raise AssertionError("Should have raised InvalidPassword")
        except InvalidPassword:
            pass
    finally:
        kv._VAULT_FILE = orig
        if os.path.exists(tmp):
            os.unlink(tmp)
    return "encrypt→decrypt→wrong-pw all correct"
test("Key vault: AES-256 encrypt/decrypt/wrong-pw", t_keyvault)

# ── 3. Secret vault — all secrets roundtrip ───────────────────
def t_secretvault():
    from security.secret_vault import save_secrets, load_secrets, InvalidSecretPassword
    import tempfile, os
    from security import secret_vault as sv
    orig = sv._SECRETS_FILE
    tmp = tempfile.mktemp(suffix=".enc")
    sv._SECRETS_FILE = __import__("pathlib").Path(tmp)
    try:
        secrets = {
            "TELEGRAM_BOT_TOKEN": "bot123:ABC",
            "STRIPE_SECRET_KEY": "sk_test_xyz",
            "POLYMARKET_API_KEY": "poly_key_abc",
        }
        save_secrets(secrets, "VaultPass456!")
        recovered = load_secrets("VaultPass456!")
        assert recovered == secrets
        try:
            load_secrets("WrongPass!")
            raise AssertionError("Should have raised")
        except InvalidSecretPassword:
            pass
    finally:
        sv._SECRETS_FILE = orig
        if os.path.exists(tmp):
            os.unlink(tmp)
    return f"{len(secrets)} secrets encrypted and recovered"
test("Secret vault: multi-key encrypt/decrypt/wrong-pw", t_secretvault)

# ── 4. Trade history DB — write/read/close ────────────────────
def t_tradehistory():
    import tempfile, os
    from trading import trade_history as th
    orig = th._DB_PATH
    tmp = tempfile.mktemp(suffix=".db")
    th._DB_PATH = __import__("pathlib").Path(tmp)
    try:
        tid = th.record_open(
            ticker="BTC", action="LONG",
            entry_price=105000.0, size=0.001,
            stop_loss=103000.0, take_profit1=109000.0,
            take_profit2=112000.0, signal_label="BOTH_BUY",
            timeframe="1h", confidence=72.5,
        )
        assert isinstance(tid, int) and tid > 0
        open_trades = th.get_open_trades()
        assert len(open_trades) == 1
        assert open_trades[0]["ticker"] == "BTC"

        th.record_close(tid, exit_price=108500.0)
        closed = th.get_closed_trades()
        assert len(closed) == 1
        assert closed[0]["outcome"] == "win"
        assert closed[0]["pnl_pct"] > 0

        summary = th.get_summary()
        assert summary["total_trades"] == 1
        assert summary["wins"] == 1

        by_label = th.get_personal_stats_by_label()
        assert "BOTH_BUY" in by_label
        assert by_label["BOTH_BUY"]["wins"] == 1

        curve = th.get_equity_curve()
        assert len(curve) == 1
        assert curve[0]["cumulative"] > 0
    finally:
        th._DB_PATH = orig
        if os.path.exists(tmp):
            os.unlink(tmp)
    return "open→close→win recorded, equity curve correct"
test("Trade history DB: open/close/win/equity curve", t_tradehistory)

# ── 5. Pattern engine — with synthetic OHLCV data ─────────────
def t_pattern_engine():
    import pandas as pd
    import numpy as np
    from trading.pattern_engine import backtest_signals, evaluate_current, BUY_LABELS, SELL_LABELS

    # Generate 300 bars of synthetic price data (random walk)
    np.random.seed(42)
    n = 300
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    close = np.maximum(close, 1)
    df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n, freq="1h"),
        "open":   close * (1 - np.random.rand(n) * 0.002),
        "high":   close * (1 + np.random.rand(n) * 0.004),
        "low":    close * (1 - np.random.rand(n) * 0.004),
        "close":  close,
        "volume": np.random.rand(n) * 1000 + 100,
    })

    stats = backtest_signals(df)
    assert isinstance(stats, dict)
    # Should have found at least some signal combinations
    assert len(stats) > 0, "No signals found in 300 bars of data"
    total_signals = sum(s.count for s in stats.values())
    assert total_signals > 5, f"Too few signals: {total_signals}"

    verdict = evaluate_current(df)
    assert verdict.action in ("LONG", "SHORT", "WAIT")
    assert 0 <= verdict.confidence <= 100
    assert verdict.entry_price > 0
    assert isinstance(verdict.reasoning, str) and len(verdict.reasoning) > 10

    return (f"{len(stats)} combos found, {total_signals} signals, "
            f"current={verdict.action} conf={verdict.confidence:.0f}%")
test("Pattern engine: backtest + evaluate on 300 synthetic bars", t_pattern_engine)

# ── 6. Trade restrictions ─────────────────────────────────────
def t_restrictions():
    from trading.restrictions import guard, FundRestrictionError, ALLOWED_BET_PLATFORMS
    assert "polymarket" in ALLOWED_BET_PLATFORMS
    assert "kalshi" in ALLOWED_BET_PLATFORMS
    assert "predictit" not in ALLOWED_BET_PLATFORMS
    assert len(ALLOWED_BET_PLATFORMS) == 2, f"Expected 2 platforms, got {ALLOWED_BET_PLATFORMS}"
    try:
        guard.check("transfer")
        raise AssertionError("Should have blocked transfer")
    except FundRestrictionError:
        pass
    return f"Platforms={ALLOWED_BET_PLATFORMS}, transfers blocked"
test("Restrictions: only Poly+Kalshi, transfers blocked", t_restrictions)

# ── 7. Fee calculation ────────────────────────────────────────
def t_fees():
    from trading.fees import calculate_fee, FEE_BPS, FEE_RATE
    assert FEE_BPS == 5.0, f"Expected 5.0 bps got {FEE_BPS}"
    fee = calculate_fee(10000.0)
    assert abs(fee - 5.0) < 0.001, f"Expected $5.00 got ${fee}"
    fee2 = calculate_fee(50000.0)
    assert abs(fee2 - 25.0) < 0.001
    return f"0.05% of $10k = ${fee:.4f} ✓"
test("Fee engine: 0.05% rate correct", t_fees)

# ── 8. Health monitor instantiation ──────────────────────────
def t_health():
    from trading.health_monitor import health_monitor, HealthMonitor
    assert isinstance(health_monitor, HealthMonitor)
    assert not health_monitor._is_down
    assert health_monitor._running == False
    status = health_monitor.status()
    assert "Health Monitor" in status
    return "singleton OK, status string OK"
test("Health monitor: instantiation + status string", t_health)

# ── 9. Trailing stop instantiation ───────────────────────────
def t_trailing():
    from trading.trailing_stop import trailing_stop_monitor, TrailingStopMonitor
    assert isinstance(trailing_stop_monitor, TrailingStopMonitor)
    trailing_stop_monitor.reset_ticker("BTC")  # should not crash
    return "singleton OK, reset_ticker OK"
test("Trailing stop monitor: instantiation", t_trailing)

# ── 10. Signal scanner instantiation + status ─────────────────
def t_scanner():
    from trading.signal_scanner import signal_scanner, SCAN_LIST, BACKTEST_LIMIT
    assert BACKTEST_LIMIT == 1000, f"Expected 1000 got {BACKTEST_LIMIT}"
    assert len(SCAN_LIST) == 9
    status = signal_scanner.status()
    assert "Signal Scanner" in status
    assert "MTF" in status
    assert "Risk/trade" in status
    crypto = [t for _, t, _ in SCAN_LIST if t in {"BTC","ETH","SOL","DOGE","SUI"}]
    futures = [t for _, t, _ in SCAN_LIST if t in {"CL","GC","ES","NQ"}]
    return f"{len(crypto)} crypto + {len(futures)} futures, limit={BACKTEST_LIMIT}"
test("Signal scanner: 9 assets, 1000-bar limit, MTF in status", t_scanner)

# ── 11. State: Position has new fields ───────────────────────
def t_state():
    from trading.state import Position
    p = Position(
        token_in="USD", token_out="BTC",
        amount_in=1000.0, amount_out=0.01,
        entry_price=100000.0, stop_loss=97000.0,
        chain="hyperliquid", tx_hash="0xabc",
        take_profit_1=106000.0, take_profit_2=112000.0,
        size=0.01, trade_history_id=42,
    )
    assert p.take_profit_1 == 106000.0
    assert p.take_profit_2 == 112000.0
    assert p.size == 0.01
    assert p.trade_history_id == 42
    return "take_profit_1/2, size, trade_history_id all present"
test("State: Position dataclass has all new fields", t_state)

# ── 12. Config new fields ──────────────────────────────────────
def t_config_new():
    from config import cfg
    fields = ["RISK_PCT_PER_TRADE", "MTF_CONFIRMATION", "TRAILING_STOP"]
    for f in fields:
        assert hasattr(cfg, f), f"Missing cfg.{f}"
    return f"All 3 new config fields present"
test("Config: RISK_PCT, MTF_CONFIRMATION, TRAILING_STOP present", t_config_new)

# ── 13. Secret vault key list ─────────────────────────────────
def t_vault_keys():
    from security.secret_vault import VAULT_KEYS
    required = ["TELEGRAM_BOT_TOKEN", "STRIPE_SECRET_KEY", "POLYMARKET_API_KEY", "KALSHI_PASSWORD"]
    for k in required:
        assert k in VAULT_KEYS, f"Missing {k} from VAULT_KEYS"
    return f"{len(VAULT_KEYS)} keys in vault list"
test("Secret vault: all required keys in VAULT_KEYS list", t_vault_keys)

# ── 14. PatternStats properties ───────────────────────────────
def t_pattern_stats():
    from trading.pattern_engine import PatternStats
    s = PatternStats(label="BOTH_BUY", count=20, wins=14, losses=6,
                     total_gain_pct=42.0, total_loss_pct=9.0)
    assert abs(s.win_rate - 0.70) < 0.001
    assert abs(s.avg_win - 3.0) < 0.001
    assert abs(s.avg_loss - 1.5) < 0.001
    assert s.rr > 1.0
    ev = s.expectancy
    assert ev > 0, f"Positive EV expected, got {ev}"
    summary = s.summary()
    assert "70%" in summary
    return f"WR=70% EV={ev:.2f}% R:R={s.rr:.1f}"
test("PatternStats: win_rate/avg_win/avg_loss/expectancy/rr correct", t_pattern_stats)

# ── 15. SignalVerdict text output ─────────────────────────────
def t_signal_verdict():
    from trading.pattern_engine import SignalVerdict
    v = SignalVerdict(
        action="LONG", confidence=78.5, label="BOTH_BUY",
        win_rate=0.70, expectancy=1.85, rr=2.1, sample_size=25,
        entry_price=105000.0, stop_loss=102500.0,
        take_profit_1=110500.0, take_profit_2=115000.0,
        reasoning="Test reasoning string"
    )
    text = v.to_text()
    assert "LONG" in text
    assert "78%" in text
    assert "105,000" in text
    return "to_text() renders all fields"
test("SignalVerdict: to_text() renders correctly", t_signal_verdict)

# ── 16. Trade history equity curve with multiple trades ────────
def t_equity_curve():
    import tempfile, os
    from trading import trade_history as th
    orig = th._DB_PATH
    tmp = tempfile.mktemp(suffix=".db")
    th._DB_PATH = __import__("pathlib").Path(tmp)
    try:
        for i, (ticker, action, entry, exit_, sl, tp1) in enumerate([
            ("BTC", "LONG",  100000, 106000, 97000, 106000),   # win
            ("ETH", "SHORT",  3500,   3300,  3700,   3200),   # win
            ("SOL", "LONG",    180,    170,   174,    190),    # loss
        ]):
            tid = th.record_open(ticker, action, entry, 0.01, sl, tp1, tp1*1.05,
                                  "BOTH_BUY", "1h", 70.0)
            th.record_close(tid, exit_)

        curve = th.get_equity_curve()
        assert len(curve) == 3
        # Cumulative should go up, up, then down
        assert curve[0]["cumulative"] > 0
        assert curve[1]["cumulative"] > curve[0]["cumulative"]
        assert curve[2]["cumulative"] < curve[1]["cumulative"]

        summary = th.get_summary()
        assert summary["wins"] == 2
        assert summary["losses"] == 1
    finally:
        th._DB_PATH = orig
        if os.path.exists(tmp):
            os.unlink(tmp)
    return "3 trades, equity curve ascending then dip, 2W/1L"
test("Trade history: equity curve with 3 trades (2W/1L)", t_equity_curve)

# ── 17. Data fetcher routing ──────────────────────────────────
def t_data_routing():
    from analysis.data_fetcher import is_crypto, _HL_TICKERS, _YF_TICKERS
    assert is_crypto("BTC") == True
    assert is_crypto("ETH") == True
    assert is_crypto("SOL") == True
    assert is_crypto("CL")  == False
    assert is_crypto("GC")  == False
    assert is_crypto("ES")  == False
    assert "CL" in _YF_TICKERS
    assert _YF_TICKERS["CL"] == "CL=F"
    assert _YF_TICKERS["GC"] == "GC=F"
    return f"{len(_HL_TICKERS)} HL tickers, {len(_YF_TICKERS)} YF tickers, routing correct"
test("Data fetcher: crypto/futures routing logic correct", t_data_routing)

# ── Print summary ──────────────────────────────────────────────
print("\n" + "="*60)
passed = sum(1 for r in results if r[0] == PASS)
failed = sum(1 for r in results if r[0] == FAIL)
total  = len(results)
print(f"\n  RESULTS: {passed}/{total} passed  |  {failed} failed\n")
if failed:
    print("  FAILED TESTS:")
    for icon, name, msg in results:
        if icon == FAIL:
            print(f"    {icon} {name}")
            print(f"       → {msg}")
print("="*60 + "\n")
sys.exit(0 if failed == 0 else 1)
