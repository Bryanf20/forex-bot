import pandas as pd

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
        rsi_slope = latest["rsi"] - previous["rsi"] if pd.notna(previous["rsi"]) and pd.notna(latest["rsi"]) else 0

        if pd.isna(previous["rsi"]) or pd.isna(latest["rsi"]):
            momentum = "neutral"
            reasons.append("RSI unavailable for latest candles")
        elif previous["rsi"] < 30 and latest["rsi"] > 30:
            momentum = "bullish"
            reasons.append("RSI crossed above oversold (30)")
        elif previous["rsi"] > 70 and latest["rsi"] < 70:
            momentum = "bearish"
            reasons.append("RSI crossed below overbought (70)")
        elif latest["rsi"] <= 30:
            momentum = "bullish"
            reasons.append("RSI is oversold (<= 30)")
        elif latest["rsi"] >= 70:
            momentum = "bearish"
            reasons.append("RSI is overbought (>= 70)")
        elif latest["rsi"] >= 55 and rsi_slope > 0:
            momentum = "bullish"
            reasons.append("RSI is above 55 and rising")
        elif latest["rsi"] <= 45 and rsi_slope < 0:
            momentum = "bearish"
            reasons.append("RSI is below 45 and falling")
        else:
            momentum = "neutral"
            reasons.append("RSI is neutral (30-70)")

        # -------- Final Decision --------
        if trend == "bullish" and momentum == "bullish":
            decision = "BUY"
        elif trend == "bearish" and momentum == "bearish":
            decision = "SELL"
        else:
            decision = "HOLD"

        # Confidence model: combine trend separation + RSI distance from 50
        ema_spread = abs(latest["ema_20"] - latest["ema_50"]) / max(latest["close"], 1e-9)
        trend_strength = min(ema_spread * 50, 1.0)
        if pd.isna(latest["rsi"]):
            momentum_strength = 0.0
        else:
            momentum_strength = min(abs(latest["rsi"] - 50) / 50, 1.0)

        confidence = 0.2 + (0.4 * trend_strength) + (0.4 * momentum_strength)
        if decision == "HOLD":
            confidence = min(confidence, 0.6)

        return decision, reasons, round(confidence, 2)
