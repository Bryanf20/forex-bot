from datetime import datetime, timezone
from signals.models import Signal
from config.settings import ATR_SL_MULTIPLIER, RR_RATIO


class SignalEngine:

    def generate(self, pair, timeframe, decision, reasons,
                 confidence=None, entry=None, atr=None,
                 rr_ratio=RR_RATIO, atr_multiplier=ATR_SL_MULTIPLIER):

        if confidence is None:
            confidence = min(len(reasons) * 0.3, 1.0)
        else:
            confidence = max(0.0, min(float(confidence), 1.0))

        sl, tp = None, None

        if decision in ("BUY", "SELL") and entry is not None and atr is not None:
            sl_distance = atr * atr_multiplier

            if decision == "BUY":
                sl = round(entry - sl_distance, 6)
                tp = round(entry + sl_distance * rr_ratio, 6)
            elif decision == "SELL":
                sl = round(entry + sl_distance, 6)
                tp = round(entry - sl_distance * rr_ratio, 6)

        return Signal(
            pair=pair,
            timeframe=timeframe,
            signal=decision,
            confidence=confidence,
            reasons=reasons,
            # timestamp = datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M"),
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
            entry=round(entry, 6) if entry is not None else None,
            sl=sl,
            tp=tp,
            rr_ratio=rr_ratio,
        )
