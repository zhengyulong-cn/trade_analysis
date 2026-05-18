from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.future_product import FutureProduct
from app.schemas.future_product import FutureProductCreate, FutureProductUpdate


class FutureProductService:
    def __init__(self, session: Session):
        self.session = session

    def list_products(self) -> list[FutureProduct]:
        statement = select(FutureProduct).order_by(
            FutureProduct.product_code,
        )
        return list(self.session.exec(statement).all())

    def get_product_by_id(self, product_id: int) -> FutureProduct:
        product = self.session.get(FutureProduct, product_id)
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Future product not found: {product_id}",
            )
        return product

    def create_product(self, payload: FutureProductCreate) -> FutureProduct:
        product = FutureProduct(
            product_code=payload.product_code.upper(),
            display_name=payload.display_name,
            alias_names=payload.alias_names,
        )
        self.session.add(product)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Future product already exists",
            ) from exc
        self.session.refresh(product)
        return product

    def update_product(self, payload: FutureProductUpdate) -> FutureProduct:
        product = self.get_product_by_id(payload.product_id)
        update_data = payload.model_dump(
            exclude={"product_id"},
            exclude_none=True,
            exclude_unset=True,
        )
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No future product fields to update",
            )

        for field_name, value in update_data.items():
            if field_name == "product_code":
                setattr(product, field_name, value.upper())
            else:
                setattr(product, field_name, value)
        product.updated_at = datetime.now(timezone.utc)
        self.session.add(product)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Future product already exists",
            ) from exc
        self.session.refresh(product)
        return product
