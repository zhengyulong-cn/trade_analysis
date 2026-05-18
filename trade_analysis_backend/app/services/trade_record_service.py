from datetime import datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO

from fastapi import HTTPException, status
import pandas as pd
from sqlmodel import Session, select

from app.models.trade_record import TradeRecord
from app.schemas.trade_record import (
    TradeRecordCreate,
    TradeRecordImportResult,
    TradeRecordListQuery,
    TradeRecordUpdate,
)
from app.services.trade_record_storage import TradeRecordStorageService


TRADE_DETAIL_TRADE_NO = "成交序号"
TRADE_DETAIL_TIME = "成交时间"
TRADE_DETAIL_SIDE = "买/卖"
TRADE_DETAIL_FEE = "手续费"
TRADE_DETAIL_DATE = "实际成交日期"

CLOSE_DETAIL_CONTRACT = "合约"
CLOSE_DETAIL_TRADE_NO = "成交序号"
CLOSE_DETAIL_OPEN_PRICE = "开仓价"
CLOSE_DETAIL_CLOSE_PRICE = "成交价"
CLOSE_DETAIL_LOTS = "手数"
CLOSE_DETAIL_PNL = "平仓盈亏"
CLOSE_DETAIL_ORIGINAL_TRADE_NO = "原成交序号"


class TradeRecordService:
    def __init__(self, session: Session, storage_service: TradeRecordStorageService):
        self.session = session
        self.storage_service = storage_service

    def list_trade_records(self, query: TradeRecordListQuery) -> list[TradeRecord]:
        statement = select(TradeRecord)

        if query.contract:
            statement = statement.where(TradeRecord.contract.contains(query.contract.strip()))
        if query.open_direction:
            statement = statement.where(TradeRecord.open_direction == query.open_direction)
        if query.segment_type:
            statement = statement.where(TradeRecord.segment_type == query.segment_type)
        if query.open_time_start:
            statement = statement.where(TradeRecord.open_time >= query.open_time_start)
        if query.open_time_end:
            statement = statement.where(TradeRecord.open_time <= query.open_time_end)
        if query.close_time_start:
            statement = statement.where(TradeRecord.close_time >= query.close_time_start)
        if query.close_time_end:
            statement = statement.where(TradeRecord.close_time <= query.close_time_end)

        statement = statement.order_by(TradeRecord.open_time, TradeRecord.trade_record_id)
        return list(self.session.exec(statement).all())

    def create_trade_record(self, payload: TradeRecordCreate) -> TradeRecord:
        trade_record = TradeRecord.model_validate(payload.model_dump())
        self.session.add(trade_record)
        self.session.commit()
        self.session.refresh(trade_record)
        return trade_record

    def import_trade_records_from_excel(self, file_bytes: bytes) -> TradeRecordImportResult:
        try:
            trade_details = self._load_statement_sheet(file_bytes, sheet_index=2)
            close_details = self._load_statement_sheet(file_bytes, sheet_index=3)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to parse trade record workbook",
            ) from exc

        trade_details = self._clean_trade_detail_rows(trade_details)
        close_details = self._clean_close_detail_rows(close_details)

        trade_index = self._build_trade_detail_index(trade_details)
        close_fee_weights = self._build_lots_weight_map(close_details, CLOSE_DETAIL_TRADE_NO)
        open_fee_weights = self._build_lots_weight_map(close_details, CLOSE_DETAIL_ORIGINAL_TRADE_NO)
        existing_pairs = self._load_existing_import_pairs()

        imported = 0
        skipped = 0
        failed = 0

        for _, row in close_details.iterrows():
            try:
                open_trade_no = self._normalize_trade_no(row.get(CLOSE_DETAIL_ORIGINAL_TRADE_NO))
                close_trade_no = self._normalize_trade_no(row.get(CLOSE_DETAIL_TRADE_NO))
                if not open_trade_no or not close_trade_no:
                    failed += 1
                    continue

                pair = (open_trade_no, close_trade_no)
                if pair in existing_pairs:
                    skipped += 1
                    continue

                open_trade = trade_index.get(open_trade_no)
                close_trade = trade_index.get(close_trade_no)
                if open_trade is None or close_trade is None:
                    failed += 1
                    continue

                lots = self._to_int(row.get(CLOSE_DETAIL_LOTS))
                open_fee = self._allocate_fee(
                    open_trade.get(TRADE_DETAIL_FEE),
                    lots,
                    open_fee_weights.get(open_trade_no, lots),
                )
                close_fee = self._allocate_fee(
                    close_trade.get(TRADE_DETAIL_FEE),
                    lots,
                    close_fee_weights.get(close_trade_no, lots),
                )

                trade_record = TradeRecord(
                    contract=str(row.get(CLOSE_DETAIL_CONTRACT)).strip(),
                    open_direction=self._resolve_open_direction(open_trade.get(TRADE_DETAIL_SIDE)),
                    lots=lots,
                    open_time=self._combine_trade_datetime(
                        open_trade.get(TRADE_DETAIL_DATE),
                        open_trade.get(TRADE_DETAIL_TIME),
                    ),
                    open_price=self._to_decimal(row.get(CLOSE_DETAIL_OPEN_PRICE)),
                    close_time=self._combine_trade_datetime(
                        close_trade.get(TRADE_DETAIL_DATE),
                        close_trade.get(TRADE_DETAIL_TIME),
                    ),
                    close_price=self._to_decimal(row.get(CLOSE_DETAIL_CLOSE_PRICE)),
                    segment_type=None,
                    fee=open_fee + close_fee,
                    actual_pnl=self._to_decimal(row.get(CLOSE_DETAIL_PNL)),
                    import_open_trade_no=open_trade_no,
                    import_close_trade_no=close_trade_no,
                    screenshots=[],
                    comment=None,
                )
                self._validate_time_range(trade_record.open_time, trade_record.close_time)
                self.session.add(trade_record)
                existing_pairs.add(pair)
                imported += 1
            except Exception:
                failed += 1

        self.session.commit()
        return TradeRecordImportResult(
            imported=imported,
            skipped=skipped,
            failed=failed,
            message=f"Imported {imported}, skipped {skipped}, failed {failed}",
        )

    def update_trade_record(self, payload: TradeRecordUpdate) -> TradeRecord:
        trade_record = self.get_trade_record_by_id(payload.trade_record_id)
        update_data = payload.model_dump(exclude={"trade_record_id"}, exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No trade record fields to update",
            )

        old_screenshot_paths = self._extract_screenshot_paths(trade_record.screenshots)

        for field_name, value in update_data.items():
            setattr(trade_record, field_name, value)

        self._validate_time_range(trade_record.open_time, trade_record.close_time)

        trade_record.updated_at = datetime.now(timezone.utc)
        self.session.add(trade_record)
        self.session.commit()
        self.session.refresh(trade_record)

        current_screenshot_paths = self._extract_screenshot_paths(trade_record.screenshots)
        for orphan_path in old_screenshot_paths - current_screenshot_paths:
            self.storage_service.delete_relative_path(orphan_path)

        return trade_record

    def delete_trade_record(self, trade_record_id: int) -> None:
        trade_record = self.get_trade_record_by_id(trade_record_id)
        screenshot_paths = self._extract_screenshot_paths(trade_record.screenshots)
        self.session.delete(trade_record)
        self.session.commit()
        for screenshot_path in screenshot_paths:
            self.storage_service.delete_relative_path(screenshot_path)

    def get_trade_record_by_id(self, trade_record_id: int) -> TradeRecord:
        trade_record = self.session.get(TradeRecord, trade_record_id)
        if trade_record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trade record not found: {trade_record_id}",
            )
        return trade_record

    def _validate_time_range(self, open_time: datetime, close_time: datetime) -> None:
        if close_time < open_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="close_time must be greater than or equal to open_time",
            )

    def _extract_screenshot_paths(self, screenshots: list[dict] | None) -> set[str]:
        if not screenshots:
            return set()

        paths = set()
        for item in screenshots:
            path = item.get("path") if isinstance(item, dict) else None
            if path:
                paths.add(path)
        return paths

    def _clean_trade_detail_rows(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        cleaned = dataframe.copy()
        cleaned = cleaned[cleaned[CLOSE_DETAIL_CONTRACT].notna()]
        cleaned = cleaned[cleaned[CLOSE_DETAIL_CONTRACT] != "合计"]
        return cleaned

    def _clean_close_detail_rows(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        cleaned = dataframe.copy()
        cleaned = cleaned[cleaned[CLOSE_DETAIL_CONTRACT].notna()]
        cleaned = cleaned[cleaned[CLOSE_DETAIL_CONTRACT] != "合计"]
        return cleaned

    def _build_trade_detail_index(self, dataframe: pd.DataFrame) -> dict[str, dict]:
        trade_index: dict[str, dict] = {}
        for _, row in dataframe.iterrows():
            trade_no = self._normalize_trade_no(row.get(TRADE_DETAIL_TRADE_NO))
            if trade_no:
                trade_index[trade_no] = row.to_dict()
        return trade_index

    def _build_lots_weight_map(self, dataframe: pd.DataFrame, column_name: str) -> dict[str, int]:
        weights: dict[str, int] = {}
        for _, row in dataframe.iterrows():
            trade_no = self._normalize_trade_no(row.get(column_name))
            if not trade_no:
                continue
            weights[trade_no] = weights.get(trade_no, 0) + self._to_int(row.get(CLOSE_DETAIL_LOTS))
        return weights

    def _load_existing_import_pairs(self) -> set[tuple[str, str]]:
        statement = select(TradeRecord).where(
            TradeRecord.import_open_trade_no.is_not(None),
            TradeRecord.import_close_trade_no.is_not(None),
        )
        items = self.session.exec(statement).all()
        pairs: set[tuple[str, str]] = set()
        for item in items:
            if item.import_open_trade_no and item.import_close_trade_no:
                pairs.add((item.import_open_trade_no, item.import_close_trade_no))
        return pairs

    def _normalize_trade_no(self, value: object) -> str | None:
        if value is None or pd.isna(value):
            return None
        digits = "".join(ch for ch in str(value).strip() if ch.isdigit())
        if not digits:
            return None
        normalized = digits.lstrip("0")
        return normalized or "0"

    def _combine_trade_datetime(self, trade_date: object, trade_time: object) -> datetime:
        if trade_date is None or trade_time is None or pd.isna(trade_date) or pd.isna(trade_time):
            raise ValueError("Missing trade date or trade time")
        combined = datetime.strptime(
            f"{str(trade_date).strip()} {str(trade_time).strip()}",
            "%Y-%m-%d %H:%M:%S",
        )
        if combined.hour >= 20:
            combined = combined - timedelta(days=1)
        return combined

    def _resolve_open_direction(self, side_value: object) -> str:
        side = str(side_value).strip()
        if side == "买":
            return "long"
        if side == "卖":
            return "short"
        raise ValueError(f"Unsupported open direction side: {side}")

    def _to_decimal(self, value: object) -> Decimal:
        if value is None or pd.isna(value) or str(value).strip() == "--":
            return Decimal("0")
        return Decimal(str(value).strip())

    def _to_int(self, value: object) -> int:
        if value is None or pd.isna(value):
            return 0
        return int(Decimal(str(value).strip()))

    def _allocate_fee(self, total_fee_value: object, matched_lots: int, total_lots: int) -> Decimal:
        total_fee = self._to_decimal(total_fee_value)
        if total_lots <= 0:
            return total_fee
        return (total_fee * Decimal(matched_lots) / Decimal(total_lots)).quantize(Decimal("0.01"))

    def _load_statement_sheet(self, file_bytes: bytes, sheet_index: int) -> pd.DataFrame:
        dataframe = pd.read_excel(BytesIO(file_bytes), sheet_name=sheet_index, header=8)
        if dataframe.empty:
            raise ValueError("Statement sheet is empty")

        header_row = dataframe.iloc[0].tolist()
        normalized_headers = [str(value).strip() if not pd.isna(value) else "" for value in header_row]
        normalized_dataframe = dataframe.iloc[1:].copy().reset_index(drop=True)
        normalized_dataframe.columns = normalized_headers
        return normalized_dataframe
