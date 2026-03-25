import pandas_ta as ta

def add_atr(df, period: int = 14):
    """
    Average True Range — measures recent volatility.
    Used to set a dynamic SL distance rather than arbitrary pips.
    """
    df["atr"] = ta.atr(
        high=df["high"],
        low=df["low"],
        close=df["close"],
        length=period
    )
    return df