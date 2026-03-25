"""
main.py — v0.2
--------------
Runs the full pipeline:
  1. Fetch market data
  2. Compute indicators
  3. (Optional) Multi-timeframe signal
  4. Score signal with the new scorer
  5. Backtest strategy on historical data
  6. Print report + save charts
"""

from data.fetcher import MarketDataFetcher
from indicators.trend import add_ema
from indicators.momentum import add_rsi
from strategies.ema_rsi import EMARsiStrategy
from strategies.multi_tf import MultiTimeframeStrategy
from signals.engine import SignalEngine
from signals.scorer import score_signal, CONFIDENCE_THRESHOLD
from backtesting.engine import BacktestEngine
from backtesting.metrics import compute_metrics, print_report, plot_backtest_results, trades_to_dataframe
from visualization.charts import plot_chart


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ASSET_TYPE  = "forex"
SYMBOL      = "USDJPY=X"
LTF         = "1h"    # lower timeframe (entry)
HTF         = "4h"    # higher timeframe (trend filter)
LIMIT       = 500

# Set to False to run single-TF mode (same as v0.1)
USE_MULTI_TF = True

# Set to False to skip backtesting (faster for live signal checks)
RUN_BACKTEST = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def prepare(df):
    """Attach all indicators to a DataFrame."""
    df = add_ema(df, 20)
    df = add_ema(df, 50)
    df = add_rsi(df)
    return df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    fetcher = MarketDataFetcher(asset_type=ASSET_TYPE, use_cache=True)

    # ---- 1. Fetch & prepare -------------------------------------------
    df_ltf = prepare(fetcher.fetch(SYMBOL, LTF, LIMIT))

    df_htf = None
    if USE_MULTI_TF:
        try:
            df_htf = prepare(fetcher.fetch(SYMBOL, HTF, LIMIT))
        except Exception as e:
            print(f"⚠️  Could not fetch HTF data: {e}. Falling back to single-TF.")

    # ---- 2. Generate signal -------------------------------------------
    base_strategy  = EMARsiStrategy()
    mtf_strategy   = MultiTimeframeStrategy(base=base_strategy)

    if USE_MULTI_TF and df_htf is not None:
        decision, reasons, raw_confidence = mtf_strategy.apply(df_ltf, df_htf)
        htf_decision = base_strategy.apply(df_htf)[0]
    else:
        decision, reasons, raw_confidence = base_strategy.apply(df_ltf)
        htf_decision = None

    # ---- 3. Score signal ----------------------------------------------
    score = score_signal(df_ltf, decision, htf_decision=htf_decision)
    confidence = score["confidence"]

    # ---- 4. Debug output ----------------------------------------------
    latest   = df_ltf.iloc[-1]
    previous = df_ltf.iloc[-2]

    print("\n=== Signal Debug ===")
    print(f"pair: {SYMBOL}  ltf: {LTF}  htf: {HTF if USE_MULTI_TF else 'n/a'}")
    print(f"close   : {latest['close']:.6f}")
    print(f"ema_20  : {latest['ema_20']:.6f}  ema_50: {latest['ema_50']:.6f}")
    print(f"rsi     : {previous['rsi']:.2f} → {latest['rsi']:.2f}")
    print(f"decision: {decision}  raw_confidence: {raw_confidence}")
    print(f"\nScorer breakdown:")
    for k, v in score["components"].items():
        print(f"  {k:<12}: {v}")
    print(f"  {'composite':<12}: {confidence}")
    print(f"  {'label':<12}: {score['label']}")
    print(f"  {'filter':<12}: {'PASS ✅' if score['passed_filter'] else 'BLOCKED ❌'}")

    print("\nReasons:")
    for r in reasons:
        print(f"  - {r}")

    # ---- 5. Emit signal -----------------------------------------------
    engine = SignalEngine()
    signal = engine.generate(
        pair=SYMBOL,
        timeframe=LTF,
        decision=decision,
        reasons=reasons,
        confidence=confidence,
    )

    # ---- 6. Chart (current signal) ------------------------------------
    plot_chart(df_ltf, SYMBOL, LTF, signal)

    # ---- 7. Backtest --------------------------------------------------
    if RUN_BACKTEST:
        print("\n⏳ Running backtest…")

        bt_engine = BacktestEngine(
            initial_balance=10_000,
            risk_per_trade=0.01,
            tp_atr_mult=2.0,
            sl_atr_mult=1.0,
            warmup_bars=100,
        )

        results = bt_engine.run(df_ltf, base_strategy)

        trades   = results["trades"]
        equity   = results["equity_curve"]

        metrics  = compute_metrics(trades, equity, initial_balance=10_000)
        print_report(metrics)

        # Save per-trade log
        trades_df = trades_to_dataframe(trades)
        trades_df.to_csv("charts/trade_log.csv", index=False)
        print("Trade log saved → charts/trade_log.csv")

        # Save chart
        plot_backtest_results(equity, trades, df_ltf, SYMBOL, LTF)


if __name__ == "__main__":
    main()