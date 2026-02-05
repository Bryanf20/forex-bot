import yfinance as yf
from .base import DataProvider

TIMEFRAME_TO_PERIOD = {
    "1h": "3mo",
    "30m": "1mo",
    "15m": "1mo",
    "5m": "5d",
    "1d": "1y",
}

class YahooFinanceProvider(DataProvider):

    def get_ohlc(self, symbol: str, timeframe: str, limit: int):
        if timeframe not in TIMEFRAME_TO_PERIOD:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        period = TIMEFRAME_TO_PERIOD[timeframe]

        df = yf.download(
            tickers=symbol,
            interval=timeframe,
            period=period,
            progress=False
        )

        if df.empty:
            raise ValueError("No data returned from yfinance")

        # ✅ flatten columns (CRITICAL)
        df.columns = df.columns.get_level_values(0)

        df = df.rename(columns=str.lower)
        df = df[["open", "high", "low", "close", "volume"]]

        return df.tail(limit)
