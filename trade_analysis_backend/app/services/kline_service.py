from datetime import datetime, timezone
from decimal import Decimal

import akshare as ak
import pandas as pd
from fastapi import HTTPException, status
from sqlmodel import Session, func, select

from app.models.contract import Contract
from app.models.contract_interval import ContractInterval
from app.models.kline_data import KlineData
from app.schemas.kline_data import (
    AkshareSyncRequest,
    AkshareSyncResult,
    KlineBarInput,
    KlineBatchCreate,
    KlineBatchWriteResult,
    KlineDataCreate,
    KlineListItem,
    KlineListResult,
    KlineDataQueryResult,
    KlinePage,
)


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
        date_times = [self._normalize_datetime(item.date_time) for item in payload.items]

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

        for item in payload.items:
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
            total=len(payload.items),
            inserted=inserted,
            updated=updated,
        )

    def list_klines(
        self,
        symbol: str,
        interval_seconds: int,
        limit: int = 200,
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
            product_type=contract.product_type,
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

    def sync_from_akshare(self, payload: AkshareSyncRequest) -> AkshareSyncResult:
        contract = self._get_contract_by_symbol(payload.symbol)
        interval = self._get_interval_by_seconds(payload.interval)
        period = self._convert_interval_to_akshare_period(interval.seconds)

        try:
            dataframe = ak.futures_zh_minute_sina(
                symbol=contract.symbol,
                period=period,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to fetch kline data from akshare: {exc}",
            ) from exc

        fetched_items = self._convert_akshare_klines_to_inputs(dataframe)
        latest_kline = self._get_latest_kline_row(
            contract_id=contract.contract_id,
            interval_id=interval.contract_interval_id,
        )
        items = self._filter_items_at_or_after_latest_kline(
            items=fetched_items,
            latest_kline=latest_kline,
        )
        if not items:
            return AkshareSyncResult(
                symbol=payload.symbol,
                interval=payload.interval,
                ak_symbol=contract.symbol,
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
        return AkshareSyncResult(
            symbol=payload.symbol,
            interval=payload.interval,
            ak_symbol=contract.symbol,
            requested=len(items),
            inserted=write_result.inserted,
            updated=write_result.updated,
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
            product_type=contract.product_type,
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

    def _convert_akshare_klines_to_inputs(
        self,
        dataframe: pd.DataFrame,
    ) -> list[KlineBarInput]:
        items: list[KlineBarInput] = []
        if dataframe.empty:
            return items

        filtered = dataframe.dropna(
            subset=["datetime", "open", "close", "high", "low"]
        )
        for row in filtered.to_dict(orient="records"):
            items.append(
                KlineBarInput(
                    open=self._to_decimal(row["open"]),
                    close=self._to_decimal(row["close"]),
                    high=self._to_decimal(row["high"]),
                    low=self._to_decimal(row["low"]),
                    volume=self._to_decimal(row.get("volume", 0)),
                    hold=self._to_decimal(row.get("hold", 0)),
                    date_time=self._normalize_akshare_datetime(row["datetime"]),
                )
            )
        return items

    def _convert_interval_to_akshare_period(self, interval_seconds: int) -> str:
        if interval_seconds % 60 != 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Akshare minute interface requires interval in whole minutes, "
                    f"got {interval_seconds} seconds"
                ),
            )

        period = interval_seconds // 60
        if period not in {1, 5, 15, 30, 60}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Akshare futures_zh_minute_sina supports only "
                    "1, 5, 15, 30, 60 minute periods"
                ),
            )
        return str(period)

    def _normalize_akshare_datetime(self, raw_datetime: object) -> datetime:
        timestamp = pd.to_datetime(raw_datetime, errors="coerce")
        if pd.isna(timestamp):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid akshare datetime value: {raw_datetime}",
            )

        if timestamp.tzinfo is None:
            timestamp = timestamp.tz_localize("Asia/Shanghai")
        else:
            timestamp = timestamp.tz_convert("Asia/Shanghai")
        return timestamp.tz_convert(timezone.utc).to_pydatetime()

    def _normalize_datetime(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

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
