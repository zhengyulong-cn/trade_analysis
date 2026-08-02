from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import HTTPException, status
from pydantic import TypeAdapter
from sqlmodel import Session, select

from app.models.trade_record import TradeRecord
from app.models.trade_record_column import TradeRecordColumn
from app.schemas.trade_record import TradeRecordCreate, TradeRecordUpdate

_MULTI_SELECT_ADAPTER = TypeAdapter(list[str])
_IMAGES_ADAPTER = TypeAdapter(list[dict[str, Any]])


class TradeRecordService:
    def __init__(self, session: Session):
        self.session = session

    def list_trade_records(self) -> list[TradeRecord]:
        statement = select(TradeRecord).order_by(TradeRecord.created_at.desc(), TradeRecord.trade_record_id.desc())
        return list(self.session.exec(statement).all())

    def create_trade_record(self, payload: TradeRecordCreate) -> TradeRecord:
        normalized_data = self._validate_and_normalize_data_json(payload.data_json)
        record = TradeRecord(data_json=normalized_data)
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def update_trade_record(self, payload: TradeRecordUpdate) -> TradeRecord:
        record = self.get_trade_record_by_id(payload.trade_record_id)
        update_data = payload.model_dump(exclude={"trade_record_id"}, exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No trade record fields to update",
            )

        if "data_json" in update_data:
            record.data_json = self._validate_and_normalize_data_json(update_data["data_json"])

        record.updated_at = datetime.now(UTC)
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def delete_trade_record(self, trade_record_id: int) -> None:
        record = self.get_trade_record_by_id(trade_record_id)
        self.session.delete(record)
        self.session.commit()

    def get_trade_record_by_id(self, trade_record_id: int) -> TradeRecord:
        record = self.session.get(TradeRecord, trade_record_id)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trade record not found: {trade_record_id}",
            )
        return record

    def _validate_and_normalize_data_json(self, data_json: dict[str, Any]) -> dict[str, Any]:
        columns = self._get_enabled_columns()
        normalized = dict(data_json)

        for column in columns:
            value = normalized.get(column.column_key)
            if self._is_missing_required_value(value):
                if column.is_required:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Required field missing: {column.column_key}",
                    )
                continue

            normalized[column.column_key] = self._normalize_column_value(column, value)

        return normalized

    def _get_enabled_columns(self) -> list[TradeRecordColumn]:
        statement = (
            select(TradeRecordColumn)
            .where(TradeRecordColumn.is_enabled.is_(True))
            .order_by(TradeRecordColumn.sort_order, TradeRecordColumn.column_id)
        )
        return list(self.session.exec(statement).all())

    def _normalize_column_value(self, column: TradeRecordColumn, value: Any):
        data_type = column.data_type

        if data_type == "bool":
            if not isinstance(value, bool):
                raise self._invalid_type_error(column.column_key, "bool")
            return value

        if data_type == "string":
            if not isinstance(value, str):
                raise self._invalid_type_error(column.column_key, "string")
            return value.strip()

        if data_type == "number":
            return self._normalize_number_value(column.column_key, value)

        if data_type == "datetime":
            return self._normalize_datetime_value(column.column_key, value)

        if data_type == "single_select":
            return self._normalize_single_select_value(column, value)

        if data_type == "multi_select":
            return self._normalize_multi_select_value(column, value)

        if data_type == "images":
            return self._normalize_images_value(column.column_key, value)

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported trade record column data type: {data_type}",
        )

    def _normalize_number_value(self, column_key: str, value: Any) -> float | int:
        if isinstance(value, bool):
            raise self._invalid_type_error(column_key, "number")

        try:
            number = Decimal(str(value))
        except (InvalidOperation, ValueError):
            raise self._invalid_type_error(column_key, "number") from None

        if number == number.to_integral_value():
            return int(number)
        return float(number)

    def _normalize_datetime_value(self, column_key: str, value: Any) -> str:
        if not isinstance(value, str):
            raise self._invalid_type_error(column_key, "datetime")

        text = value.strip()
        if not text:
            raise self._invalid_type_error(column_key, "datetime")

        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid datetime format for field: {column_key}",
            ) from None

        return parsed.isoformat(sep=" ")

    def _normalize_single_select_value(self, column: TradeRecordColumn, value: Any) -> Any:
        if column.option_source_type == "static":
            if not isinstance(value, str):
                raise self._invalid_type_error(column.column_key, "single_select")
            option_values = self._extract_static_option_values(column)
            if option_values and value not in option_values:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid option value for field: {column.column_key}",
                )
            return value

        return value

    def _normalize_multi_select_value(self, column: TradeRecordColumn, value: Any) -> list[str]:
        try:
            items = _MULTI_SELECT_ADAPTER.validate_python(value)
        except Exception:
            raise self._invalid_type_error(column.column_key, "multi_select") from None

        normalized_items = [item.strip() for item in items if item.strip()]
        if column.option_source_type == "static":
            option_values = self._extract_static_option_values(column)
            invalid_values = [item for item in normalized_items if item not in option_values]
            if invalid_values:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid option values for field: {column.column_key}",
                )
        return normalized_items

    def _normalize_images_value(self, column_key: str, value: Any) -> list[dict[str, Any]]:
        try:
            images = _IMAGES_ADAPTER.validate_python(value)
        except Exception:
            raise self._invalid_type_error(column_key, "images") from None

        normalized_images: list[dict[str, Any]] = []
        for item in images:
            if not isinstance(item, dict):
                raise self._invalid_type_error(column_key, "images")
            normalized_images.append(item)
        return normalized_images

    def _extract_static_option_values(self, column: TradeRecordColumn) -> set[str]:
        values: set[str] = set()
        for item in column.options_json or []:
            if isinstance(item, dict):
                option_value = item.get("value")
                if isinstance(option_value, str) and option_value.strip():
                    values.add(option_value.strip())
        return values

    def _is_missing_required_value(self, value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str) and not value.strip():
            return True
        if isinstance(value, list) and len(value) == 0:
            return True
        return False

    def _invalid_type_error(self, column_key: str, expected_type: str) -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid value type for field {column_key}, expected {expected_type}",
        )
