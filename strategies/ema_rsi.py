import pandas as pd

from config.settings import EMA_SPREAD_THRESHOLD
from strategies.base import Strategy
from signals.scorer import score_signal


class EMARsiStrategy(Strategy):
    """
    EMA + RSI rule-based strategy.

    v0.2 change: confidence is now delegated to signals.scorer.score_signal()
    instead of being computed inline, keeping strategy logic clean and
    confidence calculation centralised.
    """

    def apply(self, df):
        """
        Returns (decision, reasons, confidence).
        """
        if len(df) < 2:
            return "HOLD", ["Not enough data"], 0.20

        latest   = df.iloc[-1]
        previous = df.iloc[-2]

        reasons = []

        # ── Trend: EMA crossover state ────────────────────────────────
        if latest["ema_20"] > latest["ema_50"]:
            trend = "bullish"
            reasons.append("EMA(20) is above EMA(50)")
        else:
            trend = "bearish"
            reasons.append("EMA(20) is below EMA(50)")

        # ── Momentum: RSI behaviour ───────────────────────────────────
        rsi_slope = (
            latest["rsi"] - previous["rsi"]
            if pd.notna(previous["rsi"]) and pd.notna(latest["rsi"])
            else 0
        )

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
            reasons.append("RSI is neutral (30–70)")

        # # ──EMA Spread Filter ──────────────────────────────────────────
        # ema_spread_raw = abs(latest["ema_20"] - latest["ema_50"])

        # if ema_spread_raw < EMA_SPREAD_THRESHOLD:
        #     return "HOLD", [
        #         *reasons,
        #         f"⚠️ EMA spread too narrow ({ema_spread_raw:.6f}) — crossover not confirmed"
        #     ], 0.2

        # ── Decision ──────────────────────────────────────────────────
        if trend == "bullish" and momentum == "bullish":
            decision = "BUY"
        elif trend == "bearish" and momentum == "bearish":
            decision = "SELL"
        else:
            decision = "HOLD"

        # ── Confidence via centralised scorer ─────────────────────────
        confidence = score_signal(df=df, decision=decision)

        return decision, reasons, confidence