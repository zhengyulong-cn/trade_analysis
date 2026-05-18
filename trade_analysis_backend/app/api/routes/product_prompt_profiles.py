from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import ProductPromptProfileServiceDep
from app.schemas.product_prompt_profile import (
    ProductPromptProfileCreate,
    ProductPromptProfileDeleteRequest,
    ProductPromptProfileRead,
    ProductPromptProfileUpdate,
)

router = APIRouter()


@router.get("", response_model=list[ProductPromptProfileRead])
def list_product_prompt_profiles(service: ProductPromptProfileServiceDep) -> list[ProductPromptProfileRead]:
    return [ProductPromptProfileRead.model_validate(item) for item in service.list_profiles()]


@router.get("/item", response_model=ProductPromptProfileRead)
def get_product_prompt_profile(
    service: ProductPromptProfileServiceDep,
    profile_id: int | None = Query(default=None),
    product_id: int | None = Query(default=None),
) -> ProductPromptProfileRead:
    if profile_id is not None:
        return ProductPromptProfileRead.model_validate(service.get_profile_by_id(profile_id))
    if product_id is not None:
        return ProductPromptProfileRead.model_validate(service.get_profile_by_product_id(product_id))
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="profile_id or product_id is required")


@router.post("/create", response_model=ProductPromptProfileRead, status_code=status.HTTP_201_CREATED)
def create_product_prompt_profile(
    payload: ProductPromptProfileCreate,
    service: ProductPromptProfileServiceDep,
) -> ProductPromptProfileRead:
    return ProductPromptProfileRead.model_validate(service.create_profile(payload))


@router.post("/update", response_model=ProductPromptProfileRead)
def update_product_prompt_profile(
    payload: ProductPromptProfileUpdate,
    service: ProductPromptProfileServiceDep,
) -> ProductPromptProfileRead:
    return ProductPromptProfileRead.model_validate(service.update_profile(payload))


@router.post("/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_prompt_profile(
    payload: ProductPromptProfileDeleteRequest,
    service: ProductPromptProfileServiceDep,
) -> None:
    service.delete_profile(payload.profile_id)
