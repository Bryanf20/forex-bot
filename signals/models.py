from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass
class Signal:
    pair: str
    timeframe: str
    signal: str
    confidence: float
    reasons: List[str]
    timestamp: datetime
