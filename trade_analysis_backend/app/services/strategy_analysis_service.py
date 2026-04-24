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
    ManagedSegmentRole,
    ManagedTrendSegment,
    SegmentBatchDeleteRequest,
    SegmentBatchDeleteResult,
    SegmentBuildRequest,
    SegmentBuildResult,
    SegmentCreateRequest,
    SegmentListResult,
    SegmentUpdateRequest,
    SegmentStatus,
    StrategyAnalysisDetail,
    StrategyContent,
    TrendSegment,
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

    def list_interval_segments(
        self,
        symbol: str,
        interval_seconds: int,
    ) -> SegmentListResult:
        contract = self._get_contract_by_symbol(symbol)
        interval = self._get_interval_by_seconds(interval_seconds)
        strategy_row = self._get_strategy_by_contract_id(
            contract.contract_id, allow_missing=True
        )
        strategy_content = self._parse_strategy(
            None if strategy_row is None else strategy_row.strategy
        )
        interval_strategy = strategy_content.intervals.get(str(interval.seconds))

        return self._build_segment_list_result(
            contract=contract,
            interval=interval,
            strategy_row=strategy_row,
            items=(
                []
                if interval_strategy is None
                else self._list_managed_segments(interval_strategy)
            ),
        )

    def create_interval_segment(
        self,
        payload: SegmentCreateRequest,
    ) -> SegmentListResult:
        (
            contract,
            interval,
            strategy_row,
            strategy_content,
            interval_key,
            interval_strategy,
        ) = self._load_interval_strategy_for_write(
            symbol=payload.symbol,
            interval_seconds=payload.interval,
        )

        items = self._list_managed_segments(interval_strategy)
        items.append(
            self._payload_to_managed_segment(
                payload=payload,
                contract_id=contract.contract_id,
                interval_id=interval.contract_interval_id,
                segment_index=len(items) + 1,
            )
        )
        normalized_items = self._normalize_managed_segments(items)
        self._save_interval_strategy(
            strategy_row=strategy_row,
            strategy_content=strategy_content,
            interval_key=interval_key,
            interval_strategy=interval_strategy,
            items=normalized_items,
        )

        return self._build_segment_list_result(
            contract=contract,
            interval=interval,
            strategy_row=strategy_row,
            items=normalized_items,
        )

    def update_interval_segment(
        self,
        payload: SegmentUpdateRequest,
    ) -> SegmentListResult:
        (
            contract,
            interval,
            strategy_row,
            strategy_content,
            interval_key,
            interval_strategy,
        ) = self._load_interval_strategy_for_write(
            symbol=payload.symbol,
            interval_seconds=payload.interval,
        )

        items = self._list_managed_segments(interval_strategy)
        target_index = next(
            (
                index
                for index, item in enumerate(items)
                if item.segment_role == payload.original_segment_role
                and item.segment_index == payload.original_segment_index
            ),
            None,
        )
        if target_index is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target segment not found",
            )

        existing_item = items[target_index]
        items[target_index] = self._payload_to_managed_segment(
            payload=payload,
            contract_id=contract.contract_id,
            interval_id=interval.contract_interval_id,
            segment_index=existing_item.segment_index,
            existing_item=existing_item,
        )
        normalized_items = self._normalize_managed_segments(items)
        self._save_interval_strategy(
            strategy_row=strategy_row,
            strategy_content=strategy_content,
            interval_key=interval_key,
            interval_strategy=interval_strategy,
            items=normalized_items,
        )

        return self._build_segment_list_result(
            contract=contract,
            interval=interval,
            strategy_row=strategy_row,
            items=normalized_items,
        )

    def delete_interval_segments(
        self,
        payload: SegmentBatchDeleteRequest,
    ) -> SegmentBatchDeleteResult:
        (
            _contract,
            interval,
            strategy_row,
            strategy_content,
            interval_key,
            interval_strategy,
        ) = self._load_interval_strategy_for_write(
            symbol=payload.symbol,
            interval_seconds=payload.interval,
        )

        delete_keys = {
            (item.segment_role, item.segment_index) for item in payload.items
        }
        items = self._list_managed_segments(interval_strategy)
        remaining_items = [
            item
            for item in items
            if (item.segment_role, item.segment_index) not in delete_keys
        ]
        deleted = len(items) - len(remaining_items)
        if deleted == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No matching segments found to delete",
            )

        normalized_items = self._normalize_managed_segments(remaining_items)
        self._save_interval_strategy(
            strategy_row=strategy_row,
            strategy_content=strategy_content,
            interval_key=interval_key,
            interval_strategy=interval_strategy,
            items=normalized_items,
        )

        return SegmentBatchDeleteResult(
            symbol=payload.symbol,
            interval=interval.seconds,
            deleted=deleted,
            remaining=len(normalized_items),
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

    def _load_interval_strategy_for_write(
        self,
        symbol: str,
        interval_seconds: int,
    ) -> tuple[
        Contract,
        ContractInterval,
        StrategyAnalysis,
        StrategyContent,
        str,
        IntervalStrategy,
    ]:
        contract = self._get_contract_by_symbol(symbol)
        interval = self._get_interval_by_seconds(interval_seconds)
        strategy_row = self._get_or_create_strategy(contract.contract_id)
        strategy_content = self._parse_strategy(strategy_row.strategy)
        interval_key = str(interval.seconds)
        interval_strategy = strategy_content.intervals.get(interval_key)
        if interval_strategy is None:
            interval_strategy = IntervalStrategy(
                interval=interval.seconds,
                interval_name=interval.contract_interval_name,
            )
        else:
            interval_strategy.interval = interval.seconds
            interval_strategy.interval_name = interval.contract_interval_name

        return (
            contract,
            interval,
            strategy_row,
            strategy_content,
            interval_key,
            interval_strategy,
        )

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

    def _list_managed_segments(
        self,
        interval_strategy: IntervalStrategy,
    ) -> list[ManagedTrendSegment]:
        items = [
            ManagedTrendSegment(
                segment_role=ManagedSegmentRole.CONFIRMED,
                **segment.model_dump(),
            )
            for segment in interval_strategy.confirmed_segments
        ]
        if interval_strategy.current_segment is not None:
            items.append(
                ManagedTrendSegment(
                    segment_role=ManagedSegmentRole.CURRENT,
                    **interval_strategy.current_segment.model_dump(),
                )
            )
        if interval_strategy.pending_segment is not None:
            items.append(
                ManagedTrendSegment(
                    segment_role=ManagedSegmentRole.PENDING,
                    **interval_strategy.pending_segment.model_dump(),
                )
            )

        return self._sort_managed_segments(items)

    def _payload_to_managed_segment(
        self,
        payload: SegmentCreateRequest | SegmentUpdateRequest,
        contract_id: int,
        interval_id: int,
        segment_index: int,
        existing_item: ManagedTrendSegment | None = None,
    ) -> ManagedTrendSegment:
        first_kline_time, last_kline_time, kline_count = self._calculate_segment_kline_metrics(
            contract_id=contract_id,
            interval_id=interval_id,
            start_time=payload.start_time,
            end_time=payload.end_time,
        )
        return ManagedTrendSegment(
            segment_role=payload.segment_role,
            segment_index=segment_index,
            direction=payload.direction,
            status=(
                SegmentStatus.CONFIRMED
                if payload.segment_role == ManagedSegmentRole.CONFIRMED
                else SegmentStatus.BUILDING
            ),
            trigger_time=payload.start_time,
            first_kline_time=first_kline_time,
            last_kline_time=last_kline_time,
            start_time=payload.start_time,
            start_price=payload.start_price,
            end_time=payload.end_time,
            end_price=payload.end_price,
            kline_count=kline_count,
            bars_since_end=0,
            confirmed_at=(
                (
                    existing_item.confirmed_at
                    if existing_item is not None and existing_item.confirmed_at is not None
                    else payload.end_time
                )
                if payload.segment_role == ManagedSegmentRole.CONFIRMED
                else None
            ),
        )

    def _calculate_segment_kline_metrics(
        self,
        contract_id: int,
        interval_id: int,
        start_time: datetime,
        end_time: datetime,
    ) -> tuple[datetime, datetime, int]:
        if start_time > end_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Segment start_time cannot be later than end_time",
            )

        statement = (
            select(KlineData)
            .where(KlineData.contract_id == contract_id)
            .where(KlineData.interval_id == interval_id)
            .where(KlineData.date_time >= start_time)
            .where(KlineData.date_time <= end_time)
            .order_by(KlineData.date_time.asc())
        )
        rows = list(self.session.exec(statement).all())
        if not rows:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No K-line data found between start_time and end_time",
            )

        first_row = rows[0]
        last_row = rows[-1]
        return first_row.date_time, last_row.date_time, len(rows)

    def _normalize_managed_segments(
        self,
        items: list[ManagedTrendSegment],
    ) -> list[ManagedTrendSegment]:
        current_items = [
            item for item in items if item.segment_role == ManagedSegmentRole.CURRENT
        ]
        if len(current_items) > 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only one current segment is allowed",
            )

        pending_items = [
            item for item in items if item.segment_role == ManagedSegmentRole.PENDING
        ]
        if len(pending_items) > 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only one pending segment is allowed",
            )

        if pending_items and not current_items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pending segment requires a current segment",
            )

        confirmed_items = self._sort_managed_segments(
            [
                item.model_copy(update={"segment_role": ManagedSegmentRole.CONFIRMED})
                for item in items
                if item.segment_role == ManagedSegmentRole.CONFIRMED
            ]
        )

        normalized_items: list[ManagedTrendSegment] = []
        for index, item in enumerate(confirmed_items, start=1):
            normalized_items.append(
                item.model_copy(
                    update={
                        "segment_index": index,
                        "status": SegmentStatus.CONFIRMED,
                        "confirmed_at": item.confirmed_at or item.end_time,
                        "bars_since_end": 0,
                    }
                )
            )

        if current_items:
            normalized_items.append(
                current_items[0].model_copy(
                    update={
                        "segment_index": len(normalized_items) + 1,
                        "status": SegmentStatus.BUILDING,
                        "confirmed_at": None,
                        "bars_since_end": 0,
                    }
                )
            )

        if pending_items:
            normalized_items.append(
                pending_items[0].model_copy(
                    update={
                        "segment_index": len(normalized_items) + 1,
                        "status": SegmentStatus.BUILDING,
                        "confirmed_at": None,
                        "bars_since_end": 0,
                    }
                )
            )

        return self._sort_managed_segments(normalized_items)

    def _sort_managed_segments(
        self,
        items: list[ManagedTrendSegment],
    ) -> list[ManagedTrendSegment]:
        role_order = {
            ManagedSegmentRole.CONFIRMED: 0,
            ManagedSegmentRole.CURRENT: 1,
            ManagedSegmentRole.PENDING: 2,
        }
        return sorted(
            items,
            key=lambda item: (
                item.segment_index,
                role_order[item.segment_role],
                item.start_time,
                item.end_time,
            ),
        )

    def _managed_to_trend_segment(
        self,
        item: ManagedTrendSegment,
    ) -> TrendSegment:
        return TrendSegment(
            segment_index=item.segment_index,
            direction=item.direction,
            status=(
                SegmentStatus.CONFIRMED
                if item.segment_role == ManagedSegmentRole.CONFIRMED
                else SegmentStatus.BUILDING
            ),
            trigger_time=item.trigger_time,
            first_kline_time=item.first_kline_time,
            last_kline_time=item.last_kline_time,
            start_time=item.start_time,
            start_price=item.start_price,
            end_time=item.end_time,
            end_price=item.end_price,
            kline_count=item.kline_count,
            bars_since_end=item.bars_since_end,
            confirmed_at=(
                item.confirmed_at or item.end_time
                if item.segment_role == ManagedSegmentRole.CONFIRMED
                else None
            ),
        )

    def _save_interval_strategy(
        self,
        strategy_row: StrategyAnalysis,
        strategy_content: StrategyContent,
        interval_key: str,
        interval_strategy: IntervalStrategy,
        items: list[ManagedTrendSegment],
    ) -> None:
        confirmed_segments = [
            self._managed_to_trend_segment(item)
            for item in items
            if item.segment_role == ManagedSegmentRole.CONFIRMED
        ]
        current_segment = next(
            (
                self._managed_to_trend_segment(item)
                for item in items
                if item.segment_role == ManagedSegmentRole.CURRENT
            ),
            None,
        )
        pending_segment = next(
            (
                self._managed_to_trend_segment(item)
                for item in items
                if item.segment_role == ManagedSegmentRole.PENDING
            ),
            None,
        )

        interval_strategy.confirmed_segments = confirmed_segments
        interval_strategy.current_segment = current_segment
        interval_strategy.pending_segment = pending_segment
        strategy_content.intervals[interval_key] = interval_strategy
        strategy_row.strategy = strategy_content.model_dump_json()
        self.session.add(strategy_row)
        self.session.commit()
        self.session.refresh(strategy_row)

    def _build_segment_list_result(
        self,
        contract: Contract,
        interval: ContractInterval,
        strategy_row: StrategyAnalysis | None,
        items: list[ManagedTrendSegment],
    ) -> SegmentListResult:
        return SegmentListResult(
            strategy_id=(
                None if strategy_row is None else strategy_row.strategy_id
            ),
            contract_id=contract.contract_id,
            symbol=contract.symbol,
            exchange=contract.exchange,
            contract_name=contract.name,
            interval=interval.seconds,
            interval_name=interval.contract_interval_name,
            items=self._sort_managed_segments(items),
        )
