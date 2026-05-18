from fastapi import APIRouter, status

from app.api.dependencies import FutureProductServiceDep
from app.schemas.future_product import (
    FutureProductCreate,
    FutureProductRead,
    FutureProductUpdate,
)

router = APIRouter()


@router.get("", response_model=list[FutureProductRead])
def list_future_products(service: FutureProductServiceDep) -> list[FutureProductRead]:
    return [FutureProductRead.model_validate(item) for item in service.list_products()]


@router.post("/create", response_model=FutureProductRead, status_code=status.HTTP_201_CREATED)
def create_future_product(
    payload: FutureProductCreate,
    service: FutureProductServiceDep,
) -> FutureProductRead:
    return FutureProductRead.model_validate(service.create_product(payload))


@router.post("/update", response_model=FutureProductRead)
def update_future_product(
    payload: FutureProductUpdate,
    service: FutureProductServiceDep,
) -> FutureProductRead:
    return FutureProductRead.model_validate(service.update_product(payload))
