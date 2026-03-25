"""
main_v2.py — Signal Bot v0.2 entry point

What's new vs v0.1
------------------
✅  Backtesting engine    (backtesting/engine.py)
✅  Backtest metrics      (backtesting/metrics.py)
✅  Improved confidence   (signals/scorer.py)
✅  Multi-TF confirmation (strategies/multi_tf.py)
✅  Backtest chart        (visualization/backtest_chart.py)

Run modes
---------
  MODE = "signal"    → live signal (same as v0.1, but with better confidence)
  MODE = "backtest"  → walk-forward backtest on historical data
  MODE = "both"      → signal + backtest in one run

Run & Save result to file
-------------------------
  1. run signal and capture it
    python main-v2.py | tee last_signal.txt

  2. log the trade — form pre-fills automatically
    python trade_log.py log
"""

from config.settings import MAX_HOLD_BARS, MIN_CONFIDENCE
from data.fetcher import MarketDataFetcher
from indicators.trend import add_ema
from indicators.momentum import add_rsi
from indicators.volatility import add_atr
from strategies.multi_tf import MultiTimeframeStrategy   # v0.2 (replaces EMARsiStrategy)
from signals.engine import SignalEngine
from backtesting.engine import BacktestEngine
from backtesting.metrics import compute_metrics, trades_to_dataframe, print_summary
from visualization.backtest_chart import plot_backtest
from visualization.charts import plot_chart

# ── Config ────────────────────────────────────────────────────────────

MODE        = "signal"        # "signal" | "backtest" | "both"

ASSET_TYPE  = "forex"        # "forex" | "crypto" | "stocks"
SYMBOL      = "audusd=X"
# ASSET_TYPE  = "crypto"         # "forex" | "crypto" | "stocks"
# SYMBOL      = "BTC/USD"
# SYMBOL      = "CL=F"
SYMBOL = SYMBOL.upper().replace(" ", "")
TIMEFRAME   = "1h"          # Lower timeframe
HTF         = "4H"          # Higher timeframe for confirmation
LIMIT       = 500

# Backtest settings
BT_TP       = 0.02          # 2% take-profit
BT_SL       = 0.01          # 1% stop-loss
BT_BALANCE  = 1_000.0
BT_MIN_CONF = 0.45          # Skip signals below this confidence


def _prepare(symbol, timeframe, limit, asset_type):
    """Fetch + add indicators, return a ready DataFrame."""
    timeframe = timeframe.lower()  # "4H" → "4h"
    fetcher = MarketDataFetcher(asset_type=asset_type, use_cache=True)
    df = fetcher.fetch(symbol, timeframe, limit)
    df = add_ema(df, 20)
    df = add_ema(df, 50)
    df = add_rsi(df)
    df = add_atr(df)
    return df


def run_signal(df_ltf, df_htf):
    print("\n── LIVE SIGNAL ──────────────────────────────────────")
    strategy = MultiTimeframeStrategy()
    decision, reasons, confidence = strategy.apply(df_ltf, df_htf)

    latest   = df_ltf.iloc[-1]
    previous = df_ltf.iloc[-2]

    is_filtered = decision in ("BUY", "SELL") and confidence < MIN_CONFIDENCE

    print(f"pair      : {SYMBOL}  ({TIMEFRAME} + {HTF} confirmation)")
    print(f"close     : {latest['close']:.6f}")
    print(f"ema_20    : {latest['ema_20']:.6f}  ema_50 : {latest['ema_50']:.6f}")
    print(f"rsi       : {previous['rsi']:.2f} → {latest['rsi']:.2f}")

    # if is_filtered:
    #     print(f"decision  : {decision} → FILTERED  confidence : {confidence}  (min: {MIN_CONFIDENCE})")
    #     print("reasons:")
    #     for r in reasons:
    #         print(f"  {r}")
    #     print("⛔ Signal suppressed — below confidence threshold")
    #     return None                          # caller must handle None
    
    print(f"decision  : {decision}  confidence : {confidence}")
    print("reasons:")
    for r in reasons:
        print(f"  {r}")

    engine = SignalEngine()
    signal = engine.generate(
        pair=SYMBOL,
        timeframe=TIMEFRAME,
        decision=decision,
        reasons=reasons,
        confidence=confidence,
        entry=latest["close"],
        atr=latest["atr"],
        rr_ratio=2.0,
    )

    if signal.signal in ("BUY", "SELL"):
        print(f"entry     : {signal.entry:.6f}")
        print(f"sl        : {signal.sl:.6f}")
        print(f"tp        : {signal.tp:.6f}")
        print(f"R:R       : 1:{int(signal.rr_ratio)}")

    plot_chart(df_ltf, SYMBOL, TIMEFRAME, signal)
    return signal


def run_backtest(df_ltf):
    print("\n── BACKTEST ─────────────────────────────────────────")

    # Use base EMARsiStrategy for backtesting (single TF for speed)
    # You can swap in MultiTimeframeStrategy if you fetch HTF slices too.
    from strategies.ema_rsi import EMARsiStrategy
    strategy = EMARsiStrategy()

    engine = BacktestEngine(
        take_profit_pct=BT_TP,
        stop_loss_pct=BT_SL,
        initial_balance=BT_BALANCE,
        min_confidence=BT_MIN_CONF,
        warmup=100,
        max_bars=MAX_HOLD_BARS,
    )

    results      = engine.run(df_ltf, strategy)
    trades       = results["trades"]
    equity_curve = results["equity_curve"]

    metrics = compute_metrics(trades, equity_curve, initial_balance=BT_BALANCE)
    print_summary(metrics)

    # Per-trade log
    trades_df = trades_to_dataframe(trades)
    trades_df.to_csv(f"charts/{SYMBOL.replace('=','').replace('/','_')}_{TIMEFRAME}_trades.csv", index=False)
    print(f"Trade log saved → charts/ directory")

    plot_backtest(df_ltf, trades, equity_curve, SYMBOL, TIMEFRAME, metrics)

    return metrics


def main():
    print(f"Loading {SYMBOL} {TIMEFRAME}...")
    df_ltf = _prepare(SYMBOL, TIMEFRAME, LIMIT, ASSET_TYPE)

    df_htf = None
    if MODE in ("signal", "both"):
        print(f"Loading {SYMBOL} {HTF} for higher-TF confirmation...")
        df_htf = _prepare(SYMBOL, HTF, LIMIT, ASSET_TYPE)

    if MODE == "signal":
        run_signal(df_ltf, df_htf)

    elif MODE == "backtest":
        # No signal filter here — backtest applies min_confidence internally
        run_backtest(df_ltf)

    elif MODE == "both":
        signal = run_signal(df_ltf, df_htf)
        if signal is not None:
            run_backtest(df_ltf)
        else:
            print("\n── BACKTEST skipped — no valid signal ──")

    else:
        raise ValueError(f"Unknown MODE: {MODE!r}. Use 'signal', 'backtest', or 'both'.")


if __name__ == "__main__":
    main()
