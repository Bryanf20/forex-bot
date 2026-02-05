from abc import ABC, abstractmethod

class DataProvider(ABC):
    @abstractmethod
    def get_ohlc(self, symbol: str, timeframe: str, limit: int):
        """
        Return a pandas DataFrame with:
        ['open', 'high', 'low', 'close', 'volume']
        indexed by datetime
        """
        pass
