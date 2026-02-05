import pandas_ta as ta

def add_rsi(df, period: int = 14):
    """
    Adds Relative Strength Index (RSI) to the DataFrame.

    RSI measures momentum and identifies overbought / oversold conditions.
    """
    df["rsi"] = ta.rsi(
        close=df["close"],
        length=period
    )

    return df

def add_macd(df):
    """
    Adds MACD indicator to the DataFrame.

    MACD shows trend strength and momentum shifts.
    """
    macd = ta.macd(df["close"])

    df["macd"] = macd["MACD_12_26_9"]
    df["macd_signal"] = macd["MACDs_12_26_9"]
    df["macd_hist"] = macd["MACDh_12_26_9"]

    return df
