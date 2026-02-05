REQUIRED_COLUMNS = {"open", "high", "low", "close", "volume"}

def validate_ohlc(df):
    if df.empty:
        raise ValueError("DataFrame is empty")

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    if df.isnull().any().any():
        raise ValueError("Data contains NaN values")

    if not df.index.is_monotonic_increasing:
        raise ValueError("Timestamps are not sorted")

    return True
