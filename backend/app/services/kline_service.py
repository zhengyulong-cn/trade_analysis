from datetime import datetime

from fastapi import HTTPException, status
from sqlmodel import Session, func, select

from app.core.kline_intervals import is_supported_kline_interval
from app.models.contract import Contract
from app.models.kline_data import KlineData
from app.schemas.kline_data import (
    KlineBarInput,
    KlineBatchCreate,
    KlineBatchWriteResult,
    KlineDeleteRequest,
    KlineDeleteResult,
    KlineListResult,
    KlineDataQueryResult,
    KlineItemsDeleteRequest,
    KlineItemsDeleteResult,
    KlineListItem,
    KlinePage,
    MarketDataSyncRequest,
    MarketDataSyncResult,
)
from app.services.kline_aggregation import (
    BASE_KLINE_INTERVAL_SECONDS,
    AggregatedKlineBar,
    aggregate_klines,
)
from app.services.market_data import KlineProvider, MarketKlineBar


class KlineService:
    def __init__(self, session: Session, kline_provider: KlineProvider):
        self.session = session
        self.kline_provider = kline_provider

    def create_klines_batch(self, payload: KlineBatchCreate) -> KlineBatchWriteResult:
        if not payload.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kline batch items cannot be empty",
            )

        contract = self._get_contract_by_symbol(payload.symbol)
        self._validate_storage_interval_seconds(payload.interval)
        items = self._deduplicate_kline_items(payload.items)
        date_times = [self._normalize_datetime(item.date_time) for item in items]

        existing_statement = select(KlineData).where(
            KlineData.contract_id == contract.contract_id,
            KlineData.date_time.in_(date_times),
        )
        existing_rows = self.session.exec(existing_statement).all()
        existing_map = {
            self._canonical_datetime_key(row.date_time): row for row in existing_rows
        }

        inserted = 0
        updated = 0

        for item in items:
            normalized_date_time = self._normalize_datetime(item.date_time)
            current = existing_map.get(
                self._canonical_datetime_key(normalized_date_time)
            )
            if current is None:
                current = KlineData(
                    contract_id=contract.contract_id,
                )
                inserted += 1
            else:
                updated += 1

            current.open = item.open
            current.close = item.close
            current.high = item.high
            current.low = item.low
            current.volume = item.volume
            current.hold = item.hold
            current.date_time = normalized_date_time
            self.session.add(current)

        self.session.commit()
        return KlineBatchWriteResult(
            total=len(items),
            inserted=inserted,
            updated=updated,
        )

    def list_klines(
        self,
        symbol: str,
        interval_seconds: int,
        limit: int = 1000,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> KlineListResult:
        contract = self._get_contract_by_symbol(symbol)
        self._validate_interval_seconds(interval_seconds)
        if interval_seconds == BASE_KLINE_INTERVAL_SECONDS:
            statement = self._build_kline_query(
                symbol=symbol,
                start_time=start_time,
                end_time=end_time,
            )
            statement = statement.order_by(KlineData.date_time.desc()).limit(limit)
            rows = list(reversed(self.session.exec(statement).all()))
            return KlineListResult(
                contract_id=contract.contract_id,
                symbol=contract.symbol,
                exchange=contract.exchange,
                name=contract.name,
                count=len(rows),
                kline_data=[
                    self._map_kline_list_item(kline, interval_seconds)
                    for kline, _ in rows
                ],
            )

        query_limit = self._get_base_query_limit(limit, interval_seconds)
        statement = self._build_kline_query(
            symbol=symbol,
            start_time=start_time,
            end_time=end_time,
        )
        statement = statement.order_by(KlineData.date_time.desc()).limit(query_limit)
        rows = self.session.exec(statement).all()
        rows = list(reversed(rows))
        base_klines = [kline for kline, _ in rows]
        bars = aggregate_klines(base_klines, interval_seconds)[-limit:]
        return KlineListResult(
            contract_id=contract.contract_id,
            symbol=contract.symbol,
            exchange=contract.exchange,
            name=contract.name,
            count=len(bars),
            kline_data=[
                self._map_aggregated_kline_list_item(
                    bar=bar,
                    contract=contract,
                    interval_seconds=interval_seconds,
                    index=index,
                )
                for index, bar in enumerate(bars)
            ],
        )

    def paginate_klines(
        self,
        symbol: str,
        interval_seconds: int,
        page: int,
        page_size: int,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> KlinePage:
        if interval_seconds != BASE_KLINE_INTERVAL_SECONDS:
            rows = self._list_aggregated_page_rows(
                symbol=symbol,
                interval_seconds=interval_seconds,
                start_time=start_time,
                end_time=end_time,
            )
            total = len(rows)
            offset = (page - 1) * page_size
            return KlinePage(
                items=rows[offset : offset + page_size],
                total=total,
                page=page,
                page_size=page_size,
            )

        base_statement = self._build_kline_query(
            symbol=symbol,
            start_time=start_time,
            end_time=end_time,
        )
        count_statement = (
            select(func.count())
            .select_from(KlineData)
            .join(Contract, Contract.contract_id == KlineData.contract_id)
            .where(Contract.symbol == symbol)
        )
        if start_time is not None:
            count_statement = count_statement.where(
                KlineData.date_time >= self._normalize_datetime(start_time)
            )
        if end_time is not None:
            count_statement = count_statement.where(
                KlineData.date_time <= self._normalize_datetime(end_time)
            )

        total = int(self.session.exec(count_statement).one())
        offset = (page - 1) * page_size
        rows = self.session.exec(
            base_statement.order_by(KlineData.date_time.desc())
            .offset(offset)
            .limit(page_size)
        ).all()
        rows = list(reversed(rows))

        return KlinePage(
            items=[
                self._map_query_row(
                    kline,
                    contract,
                    BASE_KLINE_INTERVAL_SECONDS,
                )
                for kline, contract in rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def delete_klines(self, payload: KlineDeleteRequest) -> KlineDeleteResult:
        contract = self._get_contract_by_symbol(payload.symbol)
        self._validate_storage_interval_seconds(payload.interval)
        statement = select(KlineData).where(
            KlineData.contract_id == contract.contract_id,
        )
        klines = list(self.session.exec(statement).all())

        for kline in klines:
            self.session.delete(kline)
        self.session.commit()

        return KlineDeleteResult(
            symbol=contract.symbol,
            interval=payload.interval,
            deleted=len(klines),
        )

    def delete_kline_items(
        self,
        payload: KlineItemsDeleteRequest,
    ) -> KlineItemsDeleteResult:
        kline_ids = list(dict.fromkeys(payload.kline_ids))
        if not kline_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kline ids cannot be empty",
            )

        statement = select(KlineData).where(KlineData.kline_id.in_(kline_ids))
        klines = list(self.session.exec(statement).all())

        for kline in klines:
            self.session.delete(kline)
        self.session.commit()

        return KlineItemsDeleteResult(
            requested=len(kline_ids),
            deleted=len(klines),
        )

    def get_latest_kline(
        self,
        symbol: str,
        interval_seconds: int,
    ) -> KlineDataQueryResult:
        if interval_seconds == BASE_KLINE_INTERVAL_SECONDS:
            statement = self._build_kline_query(
                symbol=symbol,
            )
            row = self.session.exec(
                statement.order_by(KlineData.date_time.desc()).limit(1)
            ).first()
            if row is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=(
                        f"Kline data not found for symbol={symbol}, "
                        f"interval={interval_seconds}"
                    ),
                )
            kline, contract = row
            return self._map_query_row(
                kline,
                contract,
                BASE_KLINE_INTERVAL_SECONDS,
            )

        statement = self._build_kline_query(
            symbol=symbol,
        )
        query_limit = self._get_base_query_limit(1, interval_seconds)
        row = self.session.exec(
            statement.order_by(KlineData.date_time.desc()).limit(query_limit)
        ).all()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Kline data not found for symbol={symbol}, "
                    f"interval={interval_seconds}"
                ),
            )
        rows = list(reversed(row))
        contract = rows[0][1]
        bars = aggregate_klines([kline for kline, _ in rows], interval_seconds)
        if not bars:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Kline data not found for symbol={symbol}, "
                    f"interval={interval_seconds}"
                ),
            )
        return self._map_aggregated_query_row(
            bar=bars[-1],
            contract=contract,
            interval_seconds=interval_seconds,
            index=len(bars) - 1,
        )

    def sync_from_market_data(
        self,
        payload: MarketDataSyncRequest,
    ) -> MarketDataSyncResult:
        contract = self._get_contract_by_symbol(payload.symbol)
        try:
            fetch_result = self.kline_provider.get_klines(
                symbol=contract.symbol,
                exchange=contract.exchange,
                interval_seconds=BASE_KLINE_INTERVAL_SECONDS,
                limit=payload.limit,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    "Failed to fetch kline data from "
                    f"{self.kline_provider.provider}: {exc}"
                ),
            ) from exc

        fetched_items = self._convert_market_klines_to_inputs(fetch_result.bars)
        items = fetched_items
        if not items:
            return MarketDataSyncResult(
                symbol=payload.symbol,
                interval=BASE_KLINE_INTERVAL_SECONDS,
                provider=fetch_result.provider,
                provider_symbol=fetch_result.provider_symbol,
                requested=0,
                inserted=0,
                updated=0,
            )

        write_result = self.create_klines_batch(
            KlineBatchCreate(
                symbol=payload.symbol,
                interval=BASE_KLINE_INTERVAL_SECONDS,
                items=items,
            )
        )
        return MarketDataSyncResult(
            symbol=payload.symbol,
            interval=BASE_KLINE_INTERVAL_SECONDS,
            provider=fetch_result.provider,
            provider_symbol=fetch_result.provider_symbol,
            requested=len(items),
            inserted=write_result.inserted,
            updated=write_result.updated,
        )

    def _list_aggregated_page_rows(
        self,
        symbol: str,
        interval_seconds: int,
        start_time: datetime | None,
        end_time: datetime | None,
    ) -> list[KlineDataQueryResult]:
        contract = self._get_contract_by_symbol(symbol)
        self._validate_interval_seconds(interval_seconds)
        statement = self._build_kline_query(
            symbol=symbol,
            start_time=start_time,
            end_time=end_time,
        )
        rows = self.session.exec(statement.order_by(KlineData.date_time)).all()
        bars = aggregate_klines(
            [kline for kline, _ in rows],
            interval_seconds,
        )
        return [
            self._map_aggregated_query_row(
                bar=bar,
                contract=contract,
                interval_seconds=interval_seconds,
                index=index,
            )
            for index, bar in enumerate(bars)
        ]

    def _build_kline_query(
        self,
        symbol: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ):
        statement = (
            select(KlineData, Contract)
            .join(Contract, Contract.contract_id == KlineData.contract_id)
            .where(Contract.symbol == symbol)
        )
        if start_time is not None:
            statement = statement.where(
                KlineData.date_time >= self._normalize_datetime(start_time)
            )
        if end_time is not None:
            statement = statement.where(
                KlineData.date_time <= self._normalize_datetime(end_time)
        )
        return statement

    def _deduplicate_kline_items(
        self,
        items: list[KlineBarInput],
    ) -> list[KlineBarInput]:
        item_map: dict[str, KlineBarInput] = {}
        for item in items:
            key = self._canonical_datetime_key(item.date_time)
            item_map[key] = item
        return sorted(
            item_map.values(),
            key=lambda item: self._normalize_datetime(item.date_time),
        )

    def _map_query_row(
        self,
        kline: KlineData,
        contract: Contract,
        interval_seconds: int,
    ) -> KlineDataQueryResult:
        return KlineDataQueryResult(
            kline_id=kline.kline_id,
            contract_id=contract.contract_id,
            open=kline.open,
            close=kline.close,
            high=kline.high,
            low=kline.low,
            volume=kline.volume,
            hold=kline.hold,
            date_time=kline.date_time,
            symbol=contract.symbol,
            exchange=contract.exchange,
            contract_name=contract.name,
            interval=interval_seconds,
        )

    def _map_kline_list_item(
        self,
        kline: KlineData,
        interval_seconds: int,
    ) -> KlineListItem:
        return KlineListItem(
            kline_id=kline.kline_id,
            contract_id=kline.contract_id,
            open=kline.open,
            close=kline.close,
            high=kline.high,
            low=kline.low,
            volume=kline.volume,
            hold=kline.hold,
            date_time=kline.date_time,
            interval=interval_seconds,
        )

    def _map_aggregated_query_row(
        self,
        bar: AggregatedKlineBar,
        contract: Contract,
        interval_seconds: int,
        index: int,
    ) -> KlineDataQueryResult:
        return KlineDataQueryResult(
            kline_id=-(index + 1),
            contract_id=contract.contract_id,
            open=bar.open,
            close=bar.close,
            high=bar.high,
            low=bar.low,
            volume=bar.volume,
            hold=bar.hold,
            date_time=bar.date_time,
            symbol=contract.symbol,
            exchange=contract.exchange,
            contract_name=contract.name,
            interval=interval_seconds,
        )

    def _map_aggregated_kline_list_item(
        self,
        bar: AggregatedKlineBar,
        contract: Contract,
        interval_seconds: int,
        index: int,
    ) -> KlineListItem:
        return KlineListItem(
            kline_id=-(index + 1),
            contract_id=contract.contract_id,
            open=bar.open,
            close=bar.close,
            high=bar.high,
            low=bar.low,
            volume=bar.volume,
            hold=bar.hold,
            date_time=bar.date_time,
            interval=interval_seconds,
        )

    def _convert_market_klines_to_inputs(
        self,
        bars: list[MarketKlineBar],
    ) -> list[KlineBarInput]:
        return [
            KlineBarInput(
                open=bar.open,
                close=bar.close,
                high=bar.high,
                low=bar.low,
                volume=bar.volume,
                hold=bar.hold,
                date_time=bar.date_time,
            )
            for bar in bars
        ]

    def _normalize_datetime(self, value: datetime) -> datetime:
        return value.replace(tzinfo=None)

    def _canonical_datetime_key(self, value: datetime) -> str:
        return self._normalize_datetime(value).isoformat()

    def _get_base_query_limit(self, display_limit: int, interval_seconds: int) -> int:
        if interval_seconds <= BASE_KLINE_INTERVAL_SECONDS:
            return display_limit
        group_size = max(interval_seconds // BASE_KLINE_INTERVAL_SECONDS, 1)
        return min(max(display_limit * group_size + group_size, display_limit), 50000)

    def _get_contract_by_symbol(self, symbol: str) -> Contract:
        statement = select(Contract).where(Contract.symbol == symbol)
        contract = self.session.exec(statement).first()
        if contract is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contract not found: {symbol}",
            )
        return contract

    def _validate_interval_seconds(self, interval_seconds: int) -> None:
        if not is_supported_kline_interval(interval_seconds):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contract interval not found: {interval_seconds}",
            )

    def _validate_storage_interval_seconds(self, interval_seconds: int) -> None:
        if interval_seconds != BASE_KLINE_INTERVAL_SECONDS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Only 5-minute kline data can be stored. "
                    f"Unsupported storage interval: {interval_seconds}"
                ),
            )
