from datetime import datetime
from decimal import Decimal
import time

import pandas as pd
from fastapi import HTTPException, status
from sqlmodel import Session, func, select
from tqsdk import TqApi, TqAuth

from app.core.config import settings
from app.models.contract import Contract
from app.models.contract_interval import ContractInterval
from app.models.kline_data import KlineData
from app.schemas.kline_data import (
    KlineBarInput,
    KlineBatchCreate,
    KlineBatchWriteResult,
    KlineDataCreate,
    KlineDeleteRequest,
    KlineDeleteResult,
    KlineItemDeleteRequest,
    KlineItemDeleteResult,
    KlineListItem,
    KlineListResult,
    KlineDataQueryResult,
    KlinePage,
    TqSdkBulkSyncError,
    TqSdkBulkSyncRequest,
    TqSdkBulkSyncResult,
    TqSdkSyncRequest,
    TqSdkSyncResult,
)

SHANGHAI_TIMEZONE = "Asia/Shanghai"


class KlineService:
    def __init__(self, session: Session):
        self.session = session

    def create_kline(self, payload: KlineDataCreate) -> KlineData:
        result = self.create_klines_batch(
            KlineBatchCreate(
                symbol=payload.symbol,
                interval=payload.interval,
                items=[
                    KlineBarInput(
                        open=payload.open,
                        close=payload.close,
                        high=payload.high,
                        low=payload.low,
                        volume=payload.volume,
                        hold=payload.hold,
                        date_time=payload.date_time,
                    )
                ],
            )
        )
        if result.total != 1:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to write kline data",
            )
        return self._get_kline_by_unique_key(
            symbol=payload.symbol,
            interval_seconds=payload.interval,
            date_time=payload.date_time,
        )

    def create_klines_batch(self, payload: KlineBatchCreate) -> KlineBatchWriteResult:
        if not payload.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kline batch items cannot be empty",
            )

        contract = self._get_contract_by_symbol(payload.symbol)
        interval = self._get_interval_by_seconds(payload.interval)
        items = self._deduplicate_kline_items(payload.items)
        date_times = [self._normalize_datetime(item.date_time) for item in items]

        existing_statement = select(KlineData).where(
            KlineData.contract_id == contract.contract_id,
            KlineData.interval_id == interval.contract_interval_id,
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
                    interval_id=interval.contract_interval_id,
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
        interval = self._get_interval_by_seconds(interval_seconds)
        statement = self._build_kline_query(
            symbol=symbol,
            interval_seconds=interval_seconds,
            start_time=start_time,
            end_time=end_time,
        )
        statement = statement.order_by(KlineData.date_time.desc()).limit(limit)
        rows = self.session.exec(statement).all()
        rows = list(reversed(rows))
        return KlineListResult(
            contract_id=contract.contract_id,
            symbol=contract.symbol,
            exchange=contract.exchange,
            name=contract.name,
            count=len(rows),
            kline_data=[
                self._map_kline_list_item(kline, interval)
                for kline, _, _ in rows
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
        base_statement = self._build_kline_query(
            symbol=symbol,
            interval_seconds=interval_seconds,
            start_time=start_time,
            end_time=end_time,
        )
        count_statement = (
            select(func.count())
            .select_from(KlineData)
            .join(Contract, Contract.contract_id == KlineData.contract_id)
            .join(
                ContractInterval,
                ContractInterval.contract_interval_id == KlineData.interval_id,
            )
            .where(Contract.symbol == symbol)
            .where(ContractInterval.seconds == interval_seconds)
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
                self._map_query_row(kline, contract, interval)
                for kline, contract, interval in rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def delete_klines(self, payload: KlineDeleteRequest) -> KlineDeleteResult:
        contract = self._get_contract_by_symbol(payload.symbol)
        interval = self._get_interval_by_seconds(payload.interval)
        statement = select(KlineData).where(
            KlineData.contract_id == contract.contract_id,
            KlineData.interval_id == interval.contract_interval_id,
        )
        klines = list(self.session.exec(statement).all())

        for kline in klines:
            self.session.delete(kline)
        self.session.commit()

        return KlineDeleteResult(
            symbol=contract.symbol,
            interval=interval.seconds,
            deleted=len(klines),
        )

    def delete_kline_item(
        self,
        payload: KlineItemDeleteRequest,
    ) -> KlineItemDeleteResult:
        kline = self.session.get(KlineData, payload.kline_id)
        if kline is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Kline data not found: {payload.kline_id}",
            )

        self.session.delete(kline)
        self.session.commit()

        return KlineItemDeleteResult(kline_id=payload.kline_id, deleted=1)

    def get_latest_kline(
        self,
        symbol: str,
        interval_seconds: int,
    ) -> KlineDataQueryResult:
        statement = self._build_kline_query(
            symbol=symbol,
            interval_seconds=interval_seconds,
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
        kline, contract, interval = row
        return self._map_query_row(kline, contract, interval)

    def sync_from_tqsdk(self, payload: TqSdkSyncRequest) -> TqSdkSyncResult:
        contract = self._get_contract_by_symbol(payload.symbol)
        interval = self._get_interval_by_seconds(payload.interval)
        tq_symbol = self._build_tqsdk_symbol(contract)

        try:
            dataframe = self._fetch_tqsdk_kline_dataframe(tq_symbol, interval.seconds)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to fetch kline data from tqsdk: {exc}",
            ) from exc

        fetched_items = self._convert_tqsdk_klines_to_inputs(
            dataframe,
            interval.seconds,
        )
        latest_kline = self._get_latest_kline_row(
            contract_id=contract.contract_id,
            interval_id=interval.contract_interval_id,
        )
        items = self._filter_items_at_or_after_latest_kline(
            items=fetched_items,
            latest_kline=latest_kline,
        )
        if not items:
            return TqSdkSyncResult(
                symbol=payload.symbol,
                interval=payload.interval,
                tq_symbol=tq_symbol,
                requested=0,
                inserted=0,
                updated=0,
            )

        write_result = self.create_klines_batch(
            KlineBatchCreate(
                symbol=payload.symbol,
                interval=payload.interval,
                items=items,
            )
        )
        return TqSdkSyncResult(
            symbol=payload.symbol,
            interval=payload.interval,
            tq_symbol=tq_symbol,
            requested=len(items),
            inserted=write_result.inserted,
            updated=write_result.updated,
        )

    def sync_bulk_from_tqsdk(
        self,
        payload: TqSdkBulkSyncRequest,
    ) -> TqSdkBulkSyncResult:
        contracts = self._list_contracts_for_sync(payload.symbols)
        intervals = self._list_intervals_for_sync(payload.intervals)
        total = len(contracts) * len(intervals)
        items: list[TqSdkSyncResult] = []
        errors: list[TqSdkBulkSyncError] = []

        for contract in contracts:
            for interval in intervals:
                request = TqSdkSyncRequest(
                    symbol=contract.symbol,
                    interval=interval.seconds,
                )
                try:
                    items.append(self.sync_from_tqsdk(request))
                except HTTPException as exc:
                    errors.append(
                        TqSdkBulkSyncError(
                            symbol=contract.symbol,
                            interval=interval.seconds,
                            detail=self._format_exception_detail(exc.detail),
                        )
                    )
                except Exception as exc:
                    errors.append(
                        TqSdkBulkSyncError(
                            symbol=contract.symbol,
                            interval=interval.seconds,
                            detail=str(exc),
                        )
                    )

        return TqSdkBulkSyncResult(
            total=total,
            succeeded=len(items),
            failed=len(errors),
            requested=sum(item.requested for item in items),
            inserted=sum(item.inserted for item in items),
            updated=sum(item.updated for item in items),
            items=items,
            errors=errors,
        )

    def _build_kline_query(
        self,
        symbol: str,
        interval_seconds: int,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ):
        statement = (
            select(KlineData, Contract, ContractInterval)
            .join(Contract, Contract.contract_id == KlineData.contract_id)
            .join(
                ContractInterval,
                ContractInterval.contract_interval_id == KlineData.interval_id,
            )
            .where(Contract.symbol == symbol)
            .where(ContractInterval.seconds == interval_seconds)
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

    def _get_latest_kline_row(
        self,
        contract_id: int,
        interval_id: int,
    ) -> KlineData | None:
        statement = (
            select(KlineData)
            .where(KlineData.contract_id == contract_id)
            .where(KlineData.interval_id == interval_id)
            .order_by(KlineData.date_time.desc())
            .limit(1)
        )
        return self.session.exec(statement).first()

    def _filter_items_at_or_after_latest_kline(
        self,
        items: list[KlineBarInput],
        latest_kline: KlineData | None,
    ) -> list[KlineBarInput]:
        if latest_kline is None:
            return items

        latest_date_time = self._normalize_datetime(latest_kline.date_time)
        return [
            item
            for item in items
            if self._normalize_datetime(item.date_time) >= latest_date_time
        ]

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
        interval: ContractInterval,
    ) -> KlineDataQueryResult:
        return KlineDataQueryResult(
            kline_id=kline.kline_id,
            contract_id=contract.contract_id,
            interval_id=interval.contract_interval_id,
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
            interval=interval.seconds,
        )

    def _map_kline_list_item(
        self,
        kline: KlineData,
        interval: ContractInterval,
    ) -> KlineListItem:
        return KlineListItem(
            kline_id=kline.kline_id,
            contract_id=kline.contract_id,
            interval_id=kline.interval_id,
            open=kline.open,
            close=kline.close,
            high=kline.high,
            low=kline.low,
            volume=kline.volume,
            hold=kline.hold,
            date_time=kline.date_time,
            interval=interval.seconds,
        )

    def _get_kline_by_unique_key(
        self,
        symbol: str,
        interval_seconds: int,
        date_time: datetime,
    ) -> KlineData:
        contract = self._get_contract_by_symbol(symbol)
        interval = self._get_interval_by_seconds(interval_seconds)
        statement = select(KlineData).where(
            KlineData.contract_id == contract.contract_id,
            KlineData.interval_id == interval.contract_interval_id,
            KlineData.date_time == self._normalize_datetime(date_time),
        )
        kline = self.session.exec(statement).first()
        if kline is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Kline data was not found after write",
            )
        return kline

    def _fetch_tqsdk_kline_dataframe(
        self,
        tq_symbol: str,
        interval_seconds: int,
    ) -> pd.DataFrame:
        api = TqApi(
            web_gui=settings.tqsdk_web_gui,
            auth=TqAuth(settings.tqsdk_username, settings.tqsdk_password),
        )
        try:
            dataframe = api.get_kline_serial(
                tq_symbol,
                interval_seconds,
                data_length=settings.tqsdk_kline_length,
            )
            deadline = time.time() + settings.tqsdk_wait_timeout_seconds
            api.wait_update(deadline=deadline)
            return dataframe.copy()
        finally:
            api.close()

    def _convert_tqsdk_klines_to_inputs(
        self,
        dataframe: pd.DataFrame,
        interval_seconds: int,
    ) -> list[KlineBarInput]:
        items: list[KlineBarInput] = []
        if dataframe.empty:
            return items

        datetime_column = "datetime"
        hold_column = "close_oi" if "close_oi" in dataframe.columns else "hold"
        filtered = dataframe.dropna(
            subset=[datetime_column, "open", "close", "high", "low"]
        ).tail(settings.tqsdk_kline_length)
        for row in filtered.to_dict(orient="records"):
            items.append(
                KlineBarInput(
                    open=self._to_decimal(row["open"]),
                    close=self._to_decimal(row["close"]),
                    high=self._to_decimal(row["high"]),
                    low=self._to_decimal(row["low"]),
                    volume=self._to_decimal(row.get("volume", 0)),
                    hold=self._to_decimal(row.get(hold_column, 0)),
                    date_time=self._get_tqsdk_kline_close_time(
                        row[datetime_column],
                        interval_seconds,
                    ),
                )
            )
        return items

    def _normalize_tqsdk_datetime(self, raw_datetime: object) -> datetime:
        if isinstance(raw_datetime, (int, float)) and not pd.isna(raw_datetime):
            timestamp = pd.to_datetime(
                raw_datetime,
                unit="ns",
                utc=True,
                errors="coerce",
            )
        else:
            timestamp = pd.to_datetime(raw_datetime, errors="coerce")
        if pd.isna(timestamp):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tqsdk datetime value: {raw_datetime}",
            )
        if timestamp.tzinfo is not None:
            timestamp = timestamp.tz_convert(SHANGHAI_TIMEZONE)
        return timestamp.to_pydatetime().replace(tzinfo=None)

    def _get_tqsdk_kline_close_time(
        self,
        raw_datetime: object,
        interval_seconds: int,
    ) -> datetime:
        open_time = self._normalize_tqsdk_datetime(raw_datetime)
        return open_time + pd.Timedelta(seconds=interval_seconds).to_pytimedelta()

    def _build_tqsdk_symbol(self, contract: Contract) -> str:
        if "." in contract.symbol:
            return contract.symbol
        return f"{contract.exchange.upper()}.{contract.symbol}"

    def _normalize_datetime(self, value: datetime) -> datetime:
        return value.replace(tzinfo=None)

    def _canonical_datetime_key(self, value: datetime) -> str:
        return self._normalize_datetime(value).isoformat()

    def _to_decimal(self, value: object) -> Decimal:
        if value is None or pd.isna(value):
            return Decimal("0")
        return Decimal(str(value))

    def _get_contract_by_symbol(self, symbol: str) -> Contract:
        statement = select(Contract).where(Contract.symbol == symbol)
        contract = self.session.exec(statement).first()
        if contract is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contract not found: {symbol}",
            )
        return contract

    def _list_contracts_for_sync(self, symbols: list[str] | None) -> list[Contract]:
        statement = select(Contract).order_by(Contract.symbol)
        if symbols:
            unique_symbols = sorted(set(symbols))
            statement = (
                select(Contract)
                .where(Contract.symbol.in_(unique_symbols))
                .order_by(Contract.symbol)
            )
        contracts = list(self.session.exec(statement).all())
        if symbols:
            found_symbols = {contract.symbol for contract in contracts}
            missing_symbols = sorted(set(symbols) - found_symbols)
            if missing_symbols:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Contract not found: {', '.join(missing_symbols)}",
                )
        return contracts

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

    def _list_intervals_for_sync(
        self,
        intervals: list[int] | None,
    ) -> list[ContractInterval]:
        statement = select(ContractInterval).order_by(ContractInterval.seconds)
        if intervals:
            unique_intervals = sorted(set(intervals))
            statement = (
                select(ContractInterval)
                .where(ContractInterval.seconds.in_(unique_intervals))
                .order_by(ContractInterval.seconds)
            )
        contract_intervals = list(self.session.exec(statement).all())
        if intervals:
            found_intervals = {interval.seconds for interval in contract_intervals}
            missing_intervals = sorted(set(intervals) - found_intervals)
            if missing_intervals:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=(
                        "Contract interval not found: "
                        f"{', '.join(str(item) for item in missing_intervals)}"
                    ),
                )
        return contract_intervals

    def _format_exception_detail(self, detail: object) -> str:
        if isinstance(detail, str):
            return detail
        return str(detail)
