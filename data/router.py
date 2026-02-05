from data.providers.yfinance_provider import YahooFinanceProvider
from data.providers.ccxt_provider import CCXTProvider


def get_provider(asset_type: str):
    """
    Selects the correct data provider.

    asset_type:
        - 'forex'
        - 'crypto'
    """

    asset_type = asset_type.lower()

    if asset_type == "forex":
        return YahooFinanceProvider()

    if asset_type == "crypto":
        return CCXTProvider()

    raise ValueError(f"Unsupported asset_type: {asset_type}")
