from typing import Protocol

from app.schemas.kline_data import KlineBarInput
from app.schemas.strategy_analysis import EmaBuildState, IntervalStrategy


class StrategyAnalyzer(Protocol):
    """策略分析器协议。

    所有逐根 K 线运行的分析器都遵循同一套生命周期：
    - initialize: 在开始循环 K 线前做状态初始化
    - on_kline: 对每一根 K 线执行增量分析
    - finalize: 在整批 K 线处理完成后做收尾
    """

    def initialize(
        self,
        strategy: IntervalStrategy,
        *,
        interval: int | None = None,
        interval_name: str | None = None,
    ) -> None: ...

    def on_kline(
        self,
        strategy: IntervalStrategy,
        kline: KlineBarInput,
    ) -> None: ...

    def finalize(self, strategy: IntervalStrategy) -> None: ...


class BaseStrategyAnalyzer:
    """分析器基类。

    目前 MomentumChecker、BuySellPointScanner 还没有正式逻辑，
    先通过这个基类提供统一空实现，后续只需要覆盖需要的方法。
    """

    def initialize(
        self,
        strategy: IntervalStrategy,
        *,
        interval: int | None = None,
        interval_name: str | None = None,
    ) -> None:
        if interval is not None:
            strategy.interval = interval
        if interval_name is not None:
            strategy.interval_name = interval_name
        if strategy.ema_state is None:
            strategy.ema_state = EmaBuildState()

    def on_kline(
        self,
        strategy: IntervalStrategy,
        kline: KlineBarInput,
    ) -> None:
        return None

    def finalize(self, strategy: IntervalStrategy) -> None:
        return None


class StrategyAnalysisLauncher:
    """策略分析启动器。

    这个对象只负责两件事：
    - 初始化当前周期的 strategy 状态
    - 以时间升序逐根循环 K 线，并分发给各个分析器

    这样以后新增 MomentumChecker、BuySellPointScanner 时，
    不需要再把 K 线循环逻辑复制到每个分析器内部。
    """

    def __init__(self, analyzers: list[StrategyAnalyzer]):
        self.analyzers = analyzers

    def run(
        self,
        klines: list[KlineBarInput],
        existing: IntervalStrategy | None = None,
        *,
        interval: int | None = None,
        interval_name: str | None = None,
    ) -> IntervalStrategy:
        strategy = existing.model_copy(deep=True) if existing is not None else None
        if strategy is None:
            strategy = IntervalStrategy(
                interval=interval or 0,
                interval_name=interval_name,
            )

        for analyzer in self.analyzers:
            analyzer.initialize(
                strategy,
                interval=interval,
                interval_name=interval_name,
            )

        for kline in sorted(klines, key=lambda item: item.date_time):
            for analyzer in self.analyzers:
                analyzer.on_kline(strategy, kline)

        for analyzer in self.analyzers:
            analyzer.finalize(strategy)

        return strategy
