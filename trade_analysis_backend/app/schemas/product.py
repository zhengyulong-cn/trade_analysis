from datetime import datetime

from pydantic import ConfigDict
from sqlmodel import SQLModel


class ProductBase(SQLModel):
    product_code: str
    exchange: str
    name: str


class ProductCreate(ProductBase):
    pass


class ProductUpdate(SQLModel):
    product_id: int
    product_code: str | None = None
    exchange: str | None = None
    name: str | None = None


class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    create_at: datetime
    updated_at: datetime
