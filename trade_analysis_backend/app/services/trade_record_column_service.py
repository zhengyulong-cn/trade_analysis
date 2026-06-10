from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.trade_record_column import TradeRecordColumn
from app.schemas.trade_record_column import TradeRecordColumnCreate, TradeRecordColumnUpdate


class TradeRecordColumnService:
    def __init__(self, session: Session):
        self.session = session

    def list_trade_record_columns(self) -> list[TradeRecordColumn]:
        statement = select(TradeRecordColumn).order_by(
            TradeRecordColumn.sort_order,
            TradeRecordColumn.column_id,
        )
        return list(self.session.exec(statement).all())

    def create_trade_record_column(self, payload: TradeRecordColumnCreate) -> TradeRecordColumn:
        self._ensure_unique_column_key(payload.column_key)
        column = TradeRecordColumn.model_validate(payload.model_dump())
        self.session.add(column)
        self.session.commit()
        self.session.refresh(column)
        return column

    def update_trade_record_column(self, payload: TradeRecordColumnUpdate) -> TradeRecordColumn:
        column = self.get_trade_record_column_by_id(payload.column_id)
        update_data = payload.model_dump(exclude={"column_id"}, exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No trade record column fields to update",
            )

        next_column_key = update_data.get("column_key")
        if next_column_key and next_column_key != column.column_key:
            self._ensure_unique_column_key(next_column_key)

        for field_name, value in update_data.items():
            setattr(column, field_name, value)

        column.updated_at = datetime.now(timezone.utc)
        self.session.add(column)
        self.session.commit()
        self.session.refresh(column)
        return column

    def delete_trade_record_column(self, column_id: int) -> None:
        column = self.get_trade_record_column_by_id(column_id)
        self.session.delete(column)
        self.session.commit()

    def get_trade_record_column_by_id(self, column_id: int) -> TradeRecordColumn:
        column = self.session.get(TradeRecordColumn, column_id)
        if column is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trade record column not found: {column_id}",
            )
        return column

    def _ensure_unique_column_key(self, column_key: str) -> None:
        statement = select(TradeRecordColumn).where(TradeRecordColumn.column_key == column_key)
        existing = self.session.exec(statement).first()
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Trade record column key already exists: {column_key}",
            )
