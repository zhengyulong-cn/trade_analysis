from app.schemas.kline_data import KlineBarInput
from app.schemas.strategy_analysis import IntervalStrategy
from app.services.strategies_handler.analysis_launcher import BaseStrategyAnalyzer


class MomentumChecker(BaseStrategyAnalyzer):
    """动能检查器。

    目前先只保留统一接口，不写具体动能算法。
    等后续明确“动能”的定义后，只需要补 initialize / on_kline / finalize。
    """

    def on_kline(
        self,
        strategy: IntervalStrategy,
        kline: KlineBarInput,
    ) -> None:
        return None
