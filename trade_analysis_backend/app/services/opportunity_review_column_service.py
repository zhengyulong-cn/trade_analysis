from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.opportunity_review_column import OpportunityReviewColumn
from app.schemas.opportunity_review_column import (
    OpportunityReviewColumnCreate,
    OpportunityReviewColumnUpdate,
)


class OpportunityReviewColumnService:
    def __init__(self, session: Session):
        self.session = session

    def list_opportunity_review_columns(self) -> list[OpportunityReviewColumn]:
        statement = select(OpportunityReviewColumn).order_by(
            OpportunityReviewColumn.sort_order,
            OpportunityReviewColumn.column_id,
        )
        return list(self.session.exec(statement).all())

    def create_opportunity_review_column(
        self,
        payload: OpportunityReviewColumnCreate,
    ) -> OpportunityReviewColumn:
        self._ensure_unique_column_key(payload.column_key)
        column = OpportunityReviewColumn.model_validate(payload.model_dump())
        self.session.add(column)
        self.session.commit()
        self.session.refresh(column)
        return column

    def update_opportunity_review_column(
        self,
        payload: OpportunityReviewColumnUpdate,
    ) -> OpportunityReviewColumn:
        column = self.get_opportunity_review_column_by_id(payload.column_id)
        update_data = payload.model_dump(exclude={"column_id"}, exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No opportunity review column fields to update",
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

    def delete_opportunity_review_column(self, column_id: int) -> None:
        column = self.get_opportunity_review_column_by_id(column_id)
        self.session.delete(column)
        self.session.commit()

    def get_opportunity_review_column_by_id(self, column_id: int) -> OpportunityReviewColumn:
        column = self.session.get(OpportunityReviewColumn, column_id)
        if column is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Opportunity review column not found: {column_id}",
            )
        return column

    def _ensure_unique_column_key(self, column_key: str) -> None:
        statement = select(OpportunityReviewColumn).where(OpportunityReviewColumn.column_key == column_key)
        existing = self.session.exec(statement).first()
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Opportunity review column key already exists: {column_key}",
            )
