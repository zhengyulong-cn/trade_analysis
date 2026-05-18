from fastapi import APIRouter, status

from app.api.dependencies import ProductServiceDep
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate

router = APIRouter()


@router.get("", response_model=list[ProductRead])
def list_products(service: ProductServiceDep) -> list[ProductRead]:
    return [ProductRead.model_validate(item) for item in service.list_products()]


@router.post("/create", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, service: ProductServiceDep) -> ProductRead:
    return ProductRead.model_validate(service.create_product(payload))


@router.post("/update", response_model=ProductRead)
def update_product(payload: ProductUpdate, service: ProductServiceDep) -> ProductRead:
    return ProductRead.model_validate(service.update_product(payload))
