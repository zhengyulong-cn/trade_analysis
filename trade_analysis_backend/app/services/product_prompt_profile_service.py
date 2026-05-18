from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.product import Product
from app.models.product_prompt_profile import ProductPromptProfile
from app.schemas.product_prompt_profile import (
    ProductPromptProfileCreate,
    ProductPromptProfileUpdate,
)


class ProductPromptProfileService:
    def __init__(self, session: Session):
        self.session = session

    def list_profiles(self) -> list[ProductPromptProfile]:
        statement = select(ProductPromptProfile).order_by(ProductPromptProfile.product_id)
        return list(self.session.exec(statement).all())

    def get_profile_by_id(self, profile_id: int) -> ProductPromptProfile:
        profile = self.session.get(ProductPromptProfile, profile_id)
        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product prompt profile not found: {profile_id}",
            )
        return profile

    def get_profile_by_product_id(self, product_id: int) -> ProductPromptProfile:
        statement = select(ProductPromptProfile).where(ProductPromptProfile.product_id == product_id)
        profile = self.session.exec(statement).first()
        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product prompt profile not found for product: {product_id}",
            )
        return profile

    def create_profile(self, payload: ProductPromptProfileCreate) -> ProductPromptProfile:
        self._validate_product_exists(payload.product_id)
        self._validate_binary_flag("is_active", payload.is_active)
        profile = ProductPromptProfile.model_validate(payload)
        self.session.add(profile)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Product prompt profile already exists for the product",
            ) from exc
        self.session.refresh(profile)
        return profile

    def update_profile(self, payload: ProductPromptProfileUpdate) -> ProductPromptProfile:
        profile = self.get_profile_by_id(payload.profile_id)
        update_data = payload.model_dump(exclude={"profile_id"}, exclude_none=True, exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No product prompt profile fields to update",
            )
        if "is_active" in update_data:
            self._validate_binary_flag("is_active", update_data["is_active"])
        for field_name, value in update_data.items():
            setattr(profile, field_name, value)
        profile.updated_at = datetime.now(timezone.utc)
        self.session.add(profile)
        self.session.commit()
        self.session.refresh(profile)
        return profile

    def delete_profile(self, profile_id: int) -> None:
        profile = self.get_profile_by_id(profile_id)
        self.session.delete(profile)
        self.session.commit()

    def _validate_product_exists(self, product_id: int) -> None:
        product = self.session.get(Product, product_id)
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product not found: {product_id}",
            )

    def _validate_binary_flag(self, field_name: str, value: int) -> None:
        if value not in (0, 1):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} must be 0 or 1",
            )
