import pandas as pd
from pathlib import Path
from config.settings import DATA_DIR

DATA_DIR.mkdir(parents=True, exist_ok=True)

def cache_path(symbol: str, timeframe: str):
    filename = f"{symbol.replace('=', '').replace('/', '')}_{timeframe}.csv"
    return DATA_DIR / filename


def save_to_cache(df: pd.DataFrame, symbol: str, timeframe: str):
    path = cache_path(symbol, timeframe)
    df.to_csv(path)
    return path


def load_from_cache(symbol: str, timeframe: str):
    path = cache_path(symbol, timeframe)
    if path.exists():
        return pd.read_csv(path, index_col=0, parse_dates=True)
    return None
