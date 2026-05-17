from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.contract import Contract
from app.models.contract_prompt_profile import ContractPromptProfile
from app.schemas.contract_prompt_profile import (
    ContractPromptProfileCreate,
    ContractPromptProfileUpdate,
)


class ContractPromptProfileService:
    def __init__(self, session: Session):
        self.session = session

    def list_profiles(self) -> list[ContractPromptProfile]:
        statement = select(ContractPromptProfile).order_by(ContractPromptProfile.contract_id)
        return list(self.session.exec(statement).all())

    def get_profile_by_id(self, profile_id: int) -> ContractPromptProfile:
        profile = self.session.get(ContractPromptProfile, profile_id)
        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contract prompt profile not found: {profile_id}",
            )
        return profile

    def get_profile_by_contract_id(self, contract_id: int) -> ContractPromptProfile:
        statement = select(ContractPromptProfile).where(
            ContractPromptProfile.contract_id == contract_id
        )
        profile = self.session.exec(statement).first()
        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contract prompt profile not found for contract: {contract_id}",
            )
        return profile

    def create_profile(self, payload: ContractPromptProfileCreate) -> ContractPromptProfile:
        self._validate_contract_exists(payload.contract_id)
        self._validate_binary_flag("is_active", payload.is_active)

        profile = ContractPromptProfile.model_validate(payload)
        self.session.add(profile)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Contract prompt profile already exists for the contract",
            ) from exc
        self.session.refresh(profile)
        return profile

    def update_profile(self, payload: ContractPromptProfileUpdate) -> ContractPromptProfile:
        profile = self.get_profile_by_id(payload.profile_id)
        update_data = payload.model_dump(
            exclude={"profile_id"},
            exclude_none=True,
            exclude_unset=True,
        )
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No contract prompt profile fields to update",
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

    def _validate_contract_exists(self, contract_id: int) -> None:
        contract = self.session.get(Contract, contract_id)
        if contract is not None:
            return
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract not found: {contract_id}",
        )

    def _validate_binary_flag(self, field_name: str, value: int) -> None:
        if value in (0, 1):
            return
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be 0 or 1",
        )
