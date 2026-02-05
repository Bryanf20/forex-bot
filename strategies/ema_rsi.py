from strategies.base import Strategy

class EMARsiStrategy(Strategy):

    def apply(self, df):
        """
        Applies EMA + RSI logic to the latest candles.
        Returns a tuple:
        (decision, reasons)
        """

        # We only care about the last two candles
        latest = df.iloc[-1]
        previous = df.iloc[-2]

        reasons = []

        # -------- Trend Check (EMA crossover state) --------
        if latest["ema_20"] > latest["ema_50"]:
            trend = "bullish"
            reasons.append("EMA(20) is above EMA(50)")
        else:
            trend = "bearish"
            reasons.append("EMA(20) is below EMA(50)")

        # -------- Momentum Check (RSI behavior) --------
        if previous["rsi"] < 30 and latest["rsi"] > 30:
            momentum = "bullish"
            reasons.append("RSI crossed above oversold (30)")
        elif previous["rsi"] > 70 and latest["rsi"] < 70:
            momentum = "bearish"
            reasons.append("RSI crossed below overbought (70)")
        else:
            momentum = "neutral"

        # -------- Final Decision --------
        if trend == "bullish" and momentum == "bullish":
            return "BUY", reasons

        if trend == "bearish" and momentum == "bearish":
            return "SELL", reasons

        return "HOLD", ["No strong trend + momentum confluence"]
