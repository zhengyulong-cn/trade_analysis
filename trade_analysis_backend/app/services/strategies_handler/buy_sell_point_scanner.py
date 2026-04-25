from app.schemas.kline_data import KlineBarInput
from app.schemas.strategy_analysis import IntervalStrategy
from app.services.strategies_handler.analysis_launcher import BaseStrategyAnalyzer


class BuySellPointScanner(BaseStrategyAnalyzer):
    """买卖点扫描器。

    目前先只保留统一接口，不写具体买卖点算法。
    后续买卖点规则明确后，直接补充逐根 K 线扫描逻辑即可。
    """

    def on_kline(
        self,
        strategy: IntervalStrategy,
        kline: KlineBarInput,
    ) -> None:
        return None
