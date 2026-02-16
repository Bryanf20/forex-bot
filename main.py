from data.fetcher import MarketDataFetcher
from indicators.trend import add_ema
from indicators.momentum import add_rsi
from strategies.ema_rsi import EMARsiStrategy
from signals.engine import SignalEngine
from visualization.charts import plot_with_signal, plot_chart


ASSET_TYPE = "forex"
SYMBOL = "USDJPY=X"
# ASSET_TYPE = "crypto"   # or "forex"
# SYMBOL = "BTC/USDT"
TIMEFRAME = "1h"
LIMIT = 500

def main():
    fetcher = MarketDataFetcher(asset_type=ASSET_TYPE, use_cache=True)
    df = fetcher.fetch(SYMBOL, TIMEFRAME, LIMIT)

    # Indicators
    df = add_ema(df, 20)
    df = add_ema(df, 50)
    df = add_rsi(df)

    # Strategy
    strategy = EMARsiStrategy()
    decision, reasons, confidence = strategy.apply(df)

    # Debug snapshot of latest indicators driving the decision
    latest = df.iloc[-1]
    previous = df.iloc[-2]
    print("=== Decision Debug ===")
    print(f"pair: {SYMBOL}  timeframe: {TIMEFRAME}")
    print(f"close: {latest['close']:.6f}")
    print(f"ema_20: {latest['ema_20']:.6f}  ema_50: {latest['ema_50']:.6f}")
    print(f"rsi (prev -> latest): {previous['rsi']:.2f} -> {latest['rsi']:.2f}")
    print(f"decision: {decision}  confidence: {confidence}")
    print("reasons:")
    for reason in reasons:
        print(f" - {reason}")

    # Signal
    engine = SignalEngine()
    signal = engine.generate(
        pair=SYMBOL,
        timeframe=TIMEFRAME,
        decision=decision,
        reasons=reasons,
        confidence=confidence
    )
    for attr, value in vars(signal).items():
        print(f"{attr}: {value}")

    # Chart
    # plot_with_signal(df, signal)
    plot_chart(df, SYMBOL, TIMEFRAME, signal)

if __name__ == "__main__":
    main()
