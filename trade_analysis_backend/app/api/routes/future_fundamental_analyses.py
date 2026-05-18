from fastapi import APIRouter, status

from app.api.dependencies import FutureFundamentalAnalysisServiceDep
from app.schemas.future_fundamental_analysis import (
    FutureFundamentalAnalysisCreate,
    FutureFundamentalAnalysisDeleteRequest,
    FutureFundamentalAnalysisListItem,
    FutureFundamentalAnalysisRead,
    FutureFundamentalAnalysisUpdate,
)

router = APIRouter()


@router.get("", response_model=list[FutureFundamentalAnalysisListItem])
def list_future_fundamental_analyses(
    service: FutureFundamentalAnalysisServiceDep,
) -> list[FutureFundamentalAnalysisListItem]:
    return service.list_items()


@router.post("/create", response_model=FutureFundamentalAnalysisRead, status_code=status.HTTP_201_CREATED)
def create_future_fundamental_analysis(
    payload: FutureFundamentalAnalysisCreate,
    service: FutureFundamentalAnalysisServiceDep,
) -> FutureFundamentalAnalysisRead:
    return FutureFundamentalAnalysisRead.model_validate(service.create_item(payload))


@router.post("/update", response_model=FutureFundamentalAnalysisRead)
def update_future_fundamental_analysis(
    payload: FutureFundamentalAnalysisUpdate,
    service: FutureFundamentalAnalysisServiceDep,
) -> FutureFundamentalAnalysisRead:
    return FutureFundamentalAnalysisRead.model_validate(service.update_item(payload))


@router.post("/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_future_fundamental_analysis(
    payload: FutureFundamentalAnalysisDeleteRequest,
    service: FutureFundamentalAnalysisServiceDep,
) -> None:
    service.delete_item(payload.analysis_id)
