from strategies.ema_rsi import EMARsiStrategy
from signals.scorer import score_signal


class MultiTimeframeStrategy:
    """
    Wraps EMARsiStrategy to add higher-timeframe confirmation.

    Usage
    -----
        strategy = MultiTimeframeStrategy()
        decision, reasons, confidence = strategy.apply(df_1h, df_4h)

    The 4H DataFrame must have the same indicator columns as the 1H one
    (ema_20, ema_50, rsi).  Pass df_htf=None to skip HTF confirmation.

    Signal logic
    ------------
    1H BUY  + 4H BUY   → STRONG BUY   (full confidence)
    1H SELL + 4H SELL  → STRONG SELL  (full confidence)
    1H BUY  + 4H HOLD  → WEAK BUY     (reduced confidence)
    1H SELL + 4H HOLD  → WEAK SELL    (reduced confidence)
    1H BUY  + 4H SELL  → HOLD         (conflicting — skip)
    1H SELL + 4H BUY   → HOLD         (conflicting — skip)
    """

    def __init__(self):
        self._strategy = EMARsiStrategy()

    def apply(self, df_ltf, df_htf=None):
        """
        Parameters
        ----------
        df_ltf : DataFrame — lower timeframe (e.g. 1H), indicators pre-applied
        df_htf : DataFrame — higher timeframe (e.g. 4H), indicators pre-applied.
                             Pass None to disable HTF confirmation.

        Returns
        -------
        (decision: str, reasons: List[str], confidence: float)
        """

        # ── 1. Get signal from lower timeframe ────────────────────────
        ltf_decision, ltf_reasons, _ = self._strategy.apply(df_ltf)

        # ── 2. Get signal from higher timeframe ───────────────────────
        htf_decision = None
        htf_reasons  = []

        if df_htf is not None and len(df_htf) >= 2:
            try:
                htf_decision, htf_reasons, _ = self._strategy.apply(df_htf)
            except Exception as e:
                htf_reasons = [f"HTF strategy error: {e}"]
                htf_decision = None

        # ── 3. Combine signals ────────────────────────────────────────
        final_decision, combined_reasons = self._combine(
            ltf_decision, ltf_reasons,
            htf_decision, htf_reasons,
        )

        # ── 4. Score confidence with the improved scorer ──────────────
        confidence = score_signal(
            df=df_ltf,
            decision=final_decision,
            higher_tf_decision=htf_decision,
        )

        return final_decision, combined_reasons, confidence

    # ------------------------------------------------------------------

    def _combine(self, ltf_decision, ltf_reasons, htf_decision, htf_reasons):
        reasons = list(ltf_reasons)

        if htf_decision is None:
            reasons.append("No higher-timeframe data — single TF signal")
            return ltf_decision, reasons

        if ltf_decision == "HOLD":
            reasons.append("Lower TF is HOLD — no entry")
            return "HOLD", reasons

        # Agreement
        if ltf_decision == htf_decision:
            reasons.append(f"✅ Higher TF confirms: {htf_decision} — STRONG signal")
            return ltf_decision, reasons

        # HTF is neutral
        if htf_decision == "HOLD":
            reasons.append(f"⚠️ Higher TF is HOLD — WEAK {ltf_decision} signal")
            return ltf_decision, reasons

        # Conflict
        reasons.append(
            f"❌ Higher TF contradicts: LTF={ltf_decision}, HTF={htf_decision} — HOLD"
        )
        return "HOLD", reasons