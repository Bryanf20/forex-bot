import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
import time
from config.settings import DATA_DIR

DATA_DIR.mkdir(parents=True, exist_ok=True)

# How old a cache file can be before it's considered stale (in minutes)
CACHE_TTL = {
    "5m":  10,
    "15m": 20,
    "30m": 40,
    "1h":  90,
    "4h":  300,
    "1d":  1440,
}

def cache_path(symbol: str, timeframe: str):
    filename = f"{symbol.replace('=', '').replace('/', '')}_{timeframe}.csv"
    return DATA_DIR / filename


def is_cache_fresh(timeframe: str, path: Path) -> bool:
    if not path.exists():
        return False
    ttl_minutes = CACHE_TTL.get(timeframe, 90)
    age_minutes = (time.time() - path.stat().st_mtime) / 60
    return age_minutes < ttl_minutes


def save_to_cache(df: pd.DataFrame, symbol: str, timeframe: str):
    path = cache_path(symbol, timeframe)
    df.to_csv(path)
    return path


def load_from_cache(symbol: str, timeframe: str):
    path = cache_path(symbol, timeframe)
    if path.exists():
        return pd.read_csv(path, index_col=0, parse_dates=True)
    return None