from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate


class ProductService:
    def __init__(self, session: Session):
        self.session = session

    def list_products(self) -> list[Product]:
        statement = select(Product).order_by(Product.exchange, Product.product_code)
        return list(self.session.exec(statement).all())

    def get_product_by_id(self, product_id: int) -> Product:
        product = self.session.get(Product, product_id)
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product not found: {product_id}",
            )
        return product

    def get_product_by_code_exchange(self, product_code: str, exchange: str) -> Product | None:
        statement = select(Product).where(
            Product.product_code == product_code,
            Product.exchange == exchange,
        )
        return self.session.exec(statement).first()

    def create_product(self, payload: ProductCreate) -> Product:
        product = Product.model_validate(payload)
        self.session.add(product)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Product already exists for the exchange",
            ) from exc
        self.session.refresh(product)
        return product

    def update_product(self, payload: ProductUpdate) -> Product:
        product = self.get_product_by_id(payload.product_id)
        update_data = payload.model_dump(
            exclude={"product_id"},
            exclude_none=True,
            exclude_unset=True,
        )
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No product fields to update",
            )

        for field_name, value in update_data.items():
            setattr(product, field_name, value)
        product.updated_at = datetime.now(timezone.utc)
        self.session.add(product)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Product already exists for the exchange",
            ) from exc
        self.session.refresh(product)
        return product
