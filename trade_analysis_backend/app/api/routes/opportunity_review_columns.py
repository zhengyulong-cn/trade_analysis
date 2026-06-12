from fastapi import APIRouter, status

from app.api.dependencies import OpportunityReviewColumnServiceDep
from app.schemas.opportunity_review_column import (
    OpportunityReviewColumnCreate,
    OpportunityReviewColumnDeleteRequest,
    OpportunityReviewColumnRead,
    OpportunityReviewColumnUpdate,
)

router = APIRouter()


@router.get("", response_model=list[OpportunityReviewColumnRead])
def list_opportunity_review_columns(
    service: OpportunityReviewColumnServiceDep,
) -> list[OpportunityReviewColumnRead]:
    return [
        OpportunityReviewColumnRead.model_validate(item, from_attributes=True)
        for item in service.list_opportunity_review_columns()
    ]


@router.post("/create", response_model=OpportunityReviewColumnRead, status_code=status.HTTP_201_CREATED)
def create_opportunity_review_column(
    payload: OpportunityReviewColumnCreate,
    service: OpportunityReviewColumnServiceDep,
) -> OpportunityReviewColumnRead:
    return OpportunityReviewColumnRead.model_validate(
        service.create_opportunity_review_column(payload),
        from_attributes=True,
    )


@router.post("/update", response_model=OpportunityReviewColumnRead)
def update_opportunity_review_column(
    payload: OpportunityReviewColumnUpdate,
    service: OpportunityReviewColumnServiceDep,
) -> OpportunityReviewColumnRead:
    return OpportunityReviewColumnRead.model_validate(
        service.update_opportunity_review_column(payload),
        from_attributes=True,
    )


@router.post("/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_opportunity_review_column(
    payload: OpportunityReviewColumnDeleteRequest,
    service: OpportunityReviewColumnServiceDep,
) -> None:
    service.delete_opportunity_review_column(payload.column_id)
