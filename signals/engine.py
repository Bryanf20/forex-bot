from datetime import datetime
from signals.models import Signal

class SignalEngine:

    def generate(self, pair, timeframe, decision, reasons, confidence=None):
        if confidence is None:
            confidence = min(len(reasons) * 0.3, 1.0)
        else:
            confidence = max(0.0, min(float(confidence), 1.0))

        return Signal(
            pair=pair,
            timeframe=timeframe,
            signal=decision,
            confidence=confidence,
            reasons=reasons,
            timestamp=datetime.utcnow()
        )
