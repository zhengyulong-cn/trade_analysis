from app.core.config import settings
from app.services.market_data.base import KlineProvider, MarketDataProviderName
from app.services.market_data.tqsdk_provider import TqSdkMarketDataProvider


def create_kline_provider(
    provider_name: MarketDataProviderName | None = None,
) -> KlineProvider:
    # Keep provider selection in one place so services stay decoupled from SDK choices.
    provider = provider_name or settings.market_data_kline_provider
    if provider == "tqsdk":
        return TqSdkMarketDataProvider()
    raise ValueError(f"Unsupported kline market data provider: {provider}")
