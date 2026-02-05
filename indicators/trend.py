def add_ema(df, period: int):
    """
    Adds an Exponential Moving Average (EMA) column to the DataFrame.

    EMA gives more weight to recent prices, making it more responsive
    to current market conditions than a simple moving average.
    """
    df[f"ema_{period}"] = df["close"].ewm(
        span=period,
        adjust=False
    ).mean()

    return df
