from datetime import datetime

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.contract import Contract
from app.models.contract_interval import ContractInterval
from app.models.kline_data import KlineData
from app.models.strategy_analysis import StrategyAnalysis
from app.schemas.kline_data import KlineBarInput
from app.schemas.strategy_analysis import (
    IntervalStrategy,
    SegmentBuildRequest,
    SegmentBuildResult,
    StrategyAnalysisDetail,
    StrategyContent,
)
from app.services.segment_builder import SegmentBuilder


class StrategyAnalysisService:
    """策略分析服务。

    这个服务的职责不是直接计算线段，而是负责把：
    - 合约查询
    - 周期查询
    - 数据库存取
    - 线段构建器 SegmentBuilder

    这几部分串起来，形成“读取旧状态 -> 增量构建 -> 写回数据库”的完整流程。
    """

    def __init__(self, session: Session):
        # session: 当前请求对应的数据库会话，用来查表和保存 strategy JSON。
        self.session = session
        # segment_builder: 真正执行线段推演的核心算法对象。
        self.segment_builder = SegmentBuilder()

    def get_strategy_by_symbol(self, symbol: str) -> StrategyAnalysisDetail:
        """按合约代码读取完整的策略分析结果。"""
        contract = self._get_contract_by_symbol(symbol)
        strategy_row = self._get_strategy_by_contract_id(contract.contract_id)
        return StrategyAnalysisDetail(
            strategy_id=strategy_row.strategy_id,
            contract_id=contract.contract_id,
            symbol=contract.symbol,
            exchange=contract.exchange,
            contract_name=contract.name,
            strategy=self._parse_strategy(strategy_row.strategy),
        )

    def build_single_interval_segments(
        self,
        payload: SegmentBuildRequest,
    ) -> SegmentBuildResult:
        """构建单个周期的线段，并把结果写回 strategy JSON。

        主体逻辑：
        1. 根据 symbol 找到合约；
        2. 根据 interval 找到周期配置；
        3. 读取数据库中该合约已有的 strategy 记录；
        4. 取出当前周期对应的 IntervalStrategy；
        5. 只拉取上次处理之后的新 K 线；
        6. 把“旧状态 + 新 K 线”交给 SegmentBuilder 增量推演；
        7. 将当前周期结果回写到 strategy_content.intervals 中；
        8. 最后把整份 strategy JSON 保存回数据库。
        """
        contract = self._get_contract_by_symbol(payload.symbol)
        interval = self._get_interval_by_seconds(payload.interval)
        strategy_row = self._get_or_create_strategy(contract.contract_id)
        strategy_content = self._parse_strategy(strategy_row.strategy)
        # interval_key: strategy JSON 中的周期键，直接用秒数转字符串，例如 "300"。
        interval_key = str(interval.seconds)

        interval_strategy = (
            IntervalStrategy(
                interval=interval.seconds,
                interval_name=interval.contract_interval_name,
            )
            if payload.reset
            else strategy_content.intervals.get(interval_key)
        )
        if interval_strategy is None:
            # 说明该周期还从未构建过，先创建一个空状态。
            interval_strategy = IntervalStrategy(
                interval=interval.seconds,
                interval_name=interval.contract_interval_name,
            )

        # new_klines: 本次需要增量处理的 K 线列表。
        # reset=True 时从头开始重算；否则只取 last_processed_at 之后的新数据。
        new_klines = self._list_new_klines(
            contract_id=contract.contract_id,
            interval_id=interval.contract_interval_id,
            last_processed_at=(
                None if payload.reset else interval_strategy.last_processed_at
            ),
        )
        interval_strategy = self.segment_builder.build(
            klines=new_klines,
            existing=interval_strategy,
            interval=interval.seconds,
            interval_name=interval.contract_interval_name,
        )

        # 将当前周期结果放回整份 strategy JSON。
        strategy_content.intervals[interval_key] = interval_strategy
        strategy_row.strategy = strategy_content.model_dump_json()
        self.session.add(strategy_row)
        self.session.commit()
        self.session.refresh(strategy_row)

        return SegmentBuildResult(
            strategy_id=strategy_row.strategy_id,
            contract_id=contract.contract_id,
            symbol=contract.symbol,
            exchange=contract.exchange,
            contract_name=contract.name,
            interval=interval.seconds,
            interval_name=interval.contract_interval_name,
            strategy=strategy_content,
            interval_strategy=interval_strategy,
        )

    def _parse_strategy(self, raw_strategy: str | None) -> StrategyContent:
        """把数据库里的 strategy JSON 字符串解析成结构化对象。"""
        if not raw_strategy:
            return StrategyContent()
        try:
            return StrategyContent.model_validate_json(raw_strategy)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stored strategy JSON is invalid",
            ) from exc

    def _get_or_create_strategy(self, contract_id: int) -> StrategyAnalysis:
        """读取某个合约的策略记录；不存在则创建空记录。"""
        strategy_row = self._get_strategy_by_contract_id(contract_id, allow_missing=True)
        if strategy_row is not None:
            return strategy_row

        strategy_row = StrategyAnalysis(contract_id=contract_id, strategy="{}")
        self.session.add(strategy_row)
        self.session.commit()
        self.session.refresh(strategy_row)
        return strategy_row

    def _get_strategy_by_contract_id(
        self,
        contract_id: int,
        allow_missing: bool = False,
    ) -> StrategyAnalysis | None:
        """按 contract_id 查策略记录。"""
        statement = select(StrategyAnalysis).where(
            StrategyAnalysis.contract_id == contract_id
        )
        strategy_row = self.session.exec(statement).first()
        if strategy_row is None and not allow_missing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy analysis not found for contract_id={contract_id}",
            )
        return strategy_row

    def _get_contract_by_symbol(self, symbol: str) -> Contract:
        """按合约代码查合约。"""
        statement = select(Contract).where(Contract.symbol == symbol)
        contract = self.session.exec(statement).first()
        if contract is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contract not found: {symbol}",
            )
        return contract

    def _get_interval_by_seconds(self, interval_seconds: int) -> ContractInterval:
        """按秒数查周期配置，例如 300 对应 5F。"""
        statement = select(ContractInterval).where(
            ContractInterval.seconds == interval_seconds
        )
        interval = self.session.exec(statement).first()
        if interval is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contract interval not found: {interval_seconds}",
            )
        return interval

    def _list_new_klines(
        self,
        contract_id: int,
        interval_id: int,
        last_processed_at: datetime | None,
    ) -> list[KlineBarInput]:
        """读取指定合约、指定周期、指定时间之后的 K 线。

        这里返回的是 KlineBarInput，而不是 ORM 模型。
        这样 SegmentBuilder 只依赖纯数据结构，不依赖数据库层。
        """
        statement = (
            select(KlineData)
            .where(KlineData.contract_id == contract_id)
            .where(KlineData.interval_id == interval_id)
        )
        if last_processed_at is not None:
            statement = statement.where(KlineData.date_time > last_processed_at)
        statement = statement.order_by(KlineData.date_time.asc())

        rows = self.session.exec(statement).all()
        return [
            KlineBarInput(
                open=row.open,
                close=row.close,
                high=row.high,
                low=row.low,
                volume=row.volume,
                hold=row.hold,
                date_time=row.date_time,
            )
            for row in rows
        ]
