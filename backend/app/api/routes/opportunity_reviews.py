from fastapi import APIRouter, status

from app.api.dependencies import OpportunityReviewServiceDep
from app.schemas.opportunity_review import (
    OpportunityReviewCreate,
    OpportunityReviewDeleteRequest,
    OpportunityReviewRead,
    OpportunityReviewUpdate,
)

router = APIRouter()


@router.get("", response_model=list[OpportunityReviewRead])
def list_opportunity_reviews(service: OpportunityReviewServiceDep) -> list[OpportunityReviewRead]:
    return [
        OpportunityReviewRead.model_validate(item, from_attributes=True)
        for item in service.list_opportunity_reviews()
    ]


@router.post("/create", response_model=OpportunityReviewRead, status_code=status.HTTP_201_CREATED)
def create_opportunity_review(
    payload: OpportunityReviewCreate,
    service: OpportunityReviewServiceDep,
) -> OpportunityReviewRead:
    return OpportunityReviewRead.model_validate(
        service.create_opportunity_review(payload),
        from_attributes=True,
    )


@router.post("/update", response_model=OpportunityReviewRead)
def update_opportunity_review(
    payload: OpportunityReviewUpdate,
    service: OpportunityReviewServiceDep,
) -> OpportunityReviewRead:
    return OpportunityReviewRead.model_validate(
        service.update_opportunity_review(payload),
        from_attributes=True,
    )


@router.post("/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_opportunity_review(
    payload: OpportunityReviewDeleteRequest,
    service: OpportunityReviewServiceDep,
) -> None:
    service.delete_opportunity_review(payload.opportunity_review_id)
