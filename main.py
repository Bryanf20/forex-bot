from data.fetcher import MarketDataFetcher
from indicators.trend import add_ema
from indicators.momentum import add_rsi
from strategies.ema_rsi import EMARsiStrategy
from signals.engine import SignalEngine
from visualization.charts import plot_with_signal, plot_chart


ASSET_TYPE = "forex"
SYMBOL = "EURUSD=X"
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
    decision, reasons = strategy.apply(df)

    # Signal
    engine = SignalEngine()
    signal = engine.generate(
        pair=SYMBOL,
        timeframe=TIMEFRAME,
        decision=decision,
        reasons=reasons
    )
    for attr, value in vars(signal).items():
        print(f"{attr}: {value}")

    # Chart
    # plot_with_signal(df, signal)
    plot_chart(df, SYMBOL, TIMEFRAME, signal)

if __name__ == "__main__":
    main()
