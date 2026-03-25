from data.router import get_provider
from data.cache import load_from_cache, save_to_cache, cache_path, is_cache_fresh
from data.validator import validate_ohlc


class MarketDataFetcher:
    def __init__(self, asset_type: str, use_cache=True):
        self.provider = get_provider(asset_type)
        self.use_cache = use_cache

    def fetch(self, symbol, timeframe, limit):
        # 1. Only use cache if it's fresh
        if self.use_cache:
            path = cache_path(symbol, timeframe)
            if is_cache_fresh(timeframe, path):
                cached = load_from_cache(symbol, timeframe)
                if cached is not None and len(cached) >= limit:
                    print(f"  [cache] Using fresh cache for {symbol} {timeframe}")
                    return cached.tail(limit)
            else:
                print(f"  [cache] Stale or missing — fetching fresh data")

        # 2. Fetch from provider
        try:
            df = self.provider.get_ohlc(symbol, timeframe, limit)
            validate_ohlc(df)
            save_to_cache(df, symbol, timeframe)
            return df

        # 3. Graceful fallback
        except Exception as e:
            cached = load_from_cache(symbol, timeframe)
            if cached is not None:
                print("⚠️  Provider failed, using cached data (may be stale)")
                return cached.tail(limit)
            raise RuntimeError("No data available from provider or cache") from e



# class MarketDataFetcher:

#     def fetch(self, symbol, timeframe, limit):
#         if self.use_cache:
#             cached = load_from_cache(symbol, timeframe)
#             if cached is not None and is_cache_fresh(timeframe, cached):
#                 return cached.tail(limit)

#         df = self.provider.get_ohlc(symbol, timeframe, limit)
#         validate_ohlc(df)
#         save_to_cache(df, symbol, timeframe)
#         return df

