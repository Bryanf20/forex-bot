from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data" / "cache"

DEFAULT_TIMEFRAME = "1h"
DEFAULT_LIMIT = 500
MAX_HOLD_BARS = 48  # 48 x 1h candles = 2 days max hold

# Signal filtering
MIN_CONFIDENCE        = 0.45
EMA_SPREAD_THRESHOLD  = 0.0001  # tune per pair — EURGBP needs ~0.0001, EURUSD ~0.0002

# Trade levels
ATR_SL_MULTIPLIER = 2.0   # 1.5 was too tight — widened after 3 consecutive SL hits
RR_RATIO          = 2.0   # TP = SL distance × RR_RATIO
