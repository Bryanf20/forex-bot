import pandas as pd

CONFIDENCE_THRESHOLD = 0.5

def score_signal(
    df: pd.DataFrame,
    decision: str,
    higher_tf_decision: str = None,
) -> float:
    """
    Weighted, indicator-driven confidence scorer.

    Replaces the ad-hoc confidence formula inside EMARsiStrategy so that
    confidence is computed consistently and tunable from one place.

    Weights
    -------
    EMA trend alignment      : 0.35
    RSI signal strength      : 0.30
    Volatility filter        : 0.15  (ATR-based; computed on-the-fly if needed)
    Higher-TF confirmation   : 0.20

    Returns a float in [0.20, 1.00].
    HOLD signals always return 0.20.
    """
    if decision == "HOLD":
        return 0.20

    latest   = df.iloc[-1]
    previous = df.iloc[-2] if len(df) >= 2 else latest

    score = 0.0
    score += _score_ema(latest, decision)         * 0.35
    score += _score_rsi(latest, previous, decision) * 0.30
    score += _score_volatility(df, latest)         * 0.15
    score += _score_higher_tf(decision, higher_tf_decision) * 0.20

    return round(max(0.20, min(score, 1.00)), 3)


# ── Component scorers (each returns 0.0 – 1.0) ───────────────────────

def _score_ema(row, decision: str) -> float:
    try:
        ema20 = row["ema_20"]
        ema50 = row["ema_50"]
        close = row["close"]
    except KeyError:
        return 0.5

    spread = (ema20 - ema50) / max(close, 1e-9)
    bullish_ema = ema20 > ema50

    if decision == "BUY" and bullish_ema:
        return min(abs(spread) * 100, 1.0)
    if decision == "SELL" and not bullish_ema:
        return min(abs(spread) * 100, 1.0)
    return 0.0   # decision contradicts EMA → penalise


def _score_rsi(row, prev_row, decision: str) -> float:
    rsi      = row.get("rsi", None)
    prev_rsi = prev_row.get("rsi", None)

    if rsi is None or pd.isna(rsi):
        return 0.5

    rsi_slope = (rsi - prev_rsi) if (prev_rsi is not None and not pd.isna(prev_rsi)) else 0

    if decision == "BUY":
        if rsi < 30:                           return 1.0
        if prev_rsi is not None and not pd.isna(prev_rsi) and prev_rsi < 30 and rsi > 30:
                                               return 0.95
        if rsi >= 55 and rsi_slope > 0:        return 0.70
        if 45 <= rsi <= 55:                    return 0.40
        return 0.10

    else:  # SELL
        if rsi > 70:                           return 1.0
        if prev_rsi is not None and not pd.isna(prev_rsi) and prev_rsi > 70 and rsi < 70:
                                               return 0.95
        if rsi <= 45 and rsi_slope < 0:        return 0.70
        if 45 <= rsi <= 55:                    return 0.40
        return 0.10


def _score_volatility(df: pd.DataFrame, row) -> float:
    atr = None

    if "atr" in df.columns:
        atr = row.get("atr", None)
    elif len(df) >= 14 and {"high", "low", "close"}.issubset(df.columns):
        try:
            import pandas_ta as ta
            atr_series = ta.atr(df["high"], df["low"], df["close"], length=14)
            if atr_series is not None:
                atr = atr_series.iloc[-1]
        except Exception:
            pass

    if atr is None or pd.isna(atr):
        return 0.5

    close = float(row.get("close", 1))
    if close == 0:
        return 0.5

    atr_pct = atr / close
    if 0.003 <= atr_pct <= 0.02:
        return 1.0          # healthy volatility — signals are reliable
    if atr_pct < 0.003:
        return 0.2          # too quiet — likely ranging market
    return 0.5              # high volatility — tradeable but less ideal


def _score_higher_tf(decision: str, higher_tf_decision: str) -> float:
    if higher_tf_decision is None:
        return 0.5          # no HTF data → neutral
    if higher_tf_decision == decision:
        return 1.0          # full confirmation
    if higher_tf_decision == "HOLD":
        return 0.5          # HTF undecided
    return 0.0              # HTF opposes → penalise strongly