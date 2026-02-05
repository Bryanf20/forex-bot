import ccxt
import pandas as pd


class CCXTProvider:
    def __init__(self, exchange="binance"):
        self.exchange = getattr(ccxt, exchange)()
        self.exchange.load_markets()

    def get_ohlc(self, symbol, timeframe, limit):
        ohlcv = self.exchange.fetch_ohlcv(
            symbol,
            timeframe=timeframe,
            limit=limit
        )

        df = pd.DataFrame(
            ohlcv,
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        )

        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)

        return df
