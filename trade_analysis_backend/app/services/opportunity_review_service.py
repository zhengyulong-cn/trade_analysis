from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.opportunity_review import OpportunityReview
from app.schemas.opportunity_review import OpportunityReviewCreate, OpportunityReviewUpdate


class OpportunityReviewService:
    def __init__(self, session: Session):
        self.session = session

    def list_opportunity_reviews(self) -> list[OpportunityReview]:
        statement = select(OpportunityReview).order_by(OpportunityReview.opportunity_review_id.desc())
        return list(self.session.exec(statement).all())

    def create_opportunity_review(self, payload: OpportunityReviewCreate) -> OpportunityReview:
        review = OpportunityReview(data_json=self._validate_and_normalize_data_json(payload.data_json))
        self.session.add(review)
        self.session.commit()
        self.session.refresh(review)
        return review

    def update_opportunity_review(self, payload: OpportunityReviewUpdate) -> OpportunityReview:
        review = self.get_opportunity_review_by_id(payload.opportunity_review_id)
        update_data = payload.model_dump(exclude={"opportunity_review_id"}, exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No opportunity review fields to update",
            )

        if "data_json" in update_data:
            review.data_json = self._validate_and_normalize_data_json(update_data["data_json"])

        review.updated_at = datetime.now(timezone.utc)
        self.session.add(review)
        self.session.commit()
        self.session.refresh(review)
        return review

    def delete_opportunity_review(self, opportunity_review_id: int) -> None:
        review = self.get_opportunity_review_by_id(opportunity_review_id)
        self.session.delete(review)
        self.session.commit()

    def get_opportunity_review_by_id(self, opportunity_review_id: int) -> OpportunityReview:
        review = self.session.get(OpportunityReview, opportunity_review_id)
        if review is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Opportunity review not found: {opportunity_review_id}",
            )
        return review

    def _validate_and_normalize_data_json(self, data_json: dict[str, object]) -> dict[str, object]:
        return dict(data_json)
