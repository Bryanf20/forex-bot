import yfinance as yf
import pandas as pd
from .base import DataProvider

TIMEFRAME_TO_PERIOD = {
    "1h": "3mo",
    "30m": "1mo",
    "15m": "1mo",
    "5m": "5d",
    "1d": "1y",
}

# Timeframes that must be built by resampling from a base interval
RESAMPLE_MAP = {
    "4h": ("1h", "3mo"),
    "2h": ("1h", "3mo"),
    "12h": ("1h", "6mo"),
    "3d": ("1d", "2y"),
    "1w": ("1d", "5y"),
}

PANDAS_RESAMPLE_RULE = {
    "4h": "4h",
    "2h": "2h",
    "12h": "12h",
    "3d": "3D",
    "1w": "W",
}

class YahooFinanceProvider(DataProvider):

    def get_ohlc(self, symbol: str, timeframe: str, limit: int):
        tf = timeframe.lower()

        if tf in RESAMPLE_MAP:
            return self._get_resampled(symbol, tf, limit)

        if tf not in TIMEFRAME_TO_PERIOD:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        return self._download(symbol, tf, limit)

    def _download(self, symbol: str, timeframe: str, limit: int):
        period = TIMEFRAME_TO_PERIOD[timeframe]

        df = yf.download(
            tickers=symbol,
            interval=timeframe,
            period=period,
            progress=False
        )

        if df.empty:
            raise ValueError("No data returned from yfinance")

        df.columns = df.columns.get_level_values(0)
        df = df.rename(columns=str.lower)
        df = df[["open", "high", "low", "close", "volume"]]

        return df.tail(limit)

    def _get_resampled(self, symbol: str, timeframe: str, limit: int):
        base_tf, period = RESAMPLE_MAP[timeframe]
        rule = PANDAS_RESAMPLE_RULE[timeframe]

        df = yf.download(
            tickers=symbol,
            interval=base_tf,
            period=period,
            progress=False
        )

        if df.empty:
            raise ValueError("No data returned from yfinance")

        df.columns = df.columns.get_level_values(0)
        df = df.rename(columns=str.lower)
        df = df[["open", "high", "low", "close", "volume"]]

        # Resample OHLCV correctly
        df = df.resample(rule).agg({
            "open":   "first",
            "high":   "max",
            "low":    "min",
            "close":  "last",
            "volume": "sum"
        }).dropna()

        return df.tail(limit)