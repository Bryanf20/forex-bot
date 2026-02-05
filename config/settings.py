from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data" / "cache"

DEFAULT_TIMEFRAME = "1h"
DEFAULT_LIMIT = 500
