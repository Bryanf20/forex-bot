from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

@dataclass
class Signal:
    pair: str
    timeframe: str
    signal: str
    confidence: float
    reasons: List[str]
    timestamp: datetime

    # Execution levels
    entry: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    rr_ratio: float = 2.0