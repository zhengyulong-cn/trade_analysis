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
    def __init__(self, session: Session):
        self.session = session
        self.segment_builder = SegmentBuilder()

    def get_strategy_by_symbol(self, symbol: str) -> StrategyAnalysisDetail:
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
        contract = self._get_contract_by_symbol(payload.symbol)
        interval = self._get_interval_by_seconds(payload.interval)
        strategy_row = self._get_or_create_strategy(contract.contract_id)
        strategy_content = self._parse_strategy(strategy_row.strategy)
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
            interval_strategy = IntervalStrategy(
                interval=interval.seconds,
                interval_name=interval.contract_interval_name,
            )

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
        statement = select(Contract).where(Contract.symbol == symbol)
        contract = self.session.exec(statement).first()
        if contract is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contract not found: {symbol}",
            )
        return contract

    def _get_interval_by_seconds(self, interval_seconds: int) -> ContractInterval:
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
