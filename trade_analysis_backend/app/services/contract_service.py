from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.contract import Contract
from app.schemas.contract import ContractCreate, ContractUpdate


class ContractService:
    def __init__(self, session: Session):
        self.session = session

    def create_contract(self, payload: ContractCreate) -> Contract:
        self._validate_binary_flag(
            field_name="is_favorite",
            value=payload.is_favorite,
        )
        contract = Contract.model_validate(payload)
        self.session.add(contract)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Contract already exists for the exchange",
            ) from exc
        self.session.refresh(contract)
        return contract

    def update_contract(self, payload: ContractUpdate) -> Contract:
        contract = self.get_contract_by_id(payload.contract_id)
        update_data = payload.model_dump(
            exclude={"contract_id"},
            exclude_none=True,
            exclude_unset=True,
        )
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No contract fields to update",
            )
        if "is_favorite" in update_data:
            self._validate_binary_flag(
                field_name="is_favorite",
                value=update_data["is_favorite"],
            )

        for field_name, value in update_data.items():
            setattr(contract, field_name, value)
        contract.updated_at = datetime.now(timezone.utc)
        self.session.add(contract)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Contract already exists for the exchange",
            ) from exc
        self.session.refresh(contract)
        return contract

    def list_contracts(self) -> list[Contract]:
        statement = select(Contract).order_by(
            Contract.is_favorite.desc(),
            Contract.symbol,
        )
        return list(self.session.exec(statement).all())

    def get_contract_by_id(self, contract_id: int) -> Contract:
        contract = self.session.get(Contract, contract_id)
        if contract is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contract not found: {contract_id}",
            )
        return contract

    def get_contract_by_symbol(self, symbol: str) -> Contract:
        statement = select(Contract).where(Contract.symbol == symbol)
        contract = self.session.exec(statement).first()
        if contract is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contract not found: {symbol}",
            )
        return contract

    def touch_contract(self, contract: Contract) -> Contract:
        contract.updated_at = datetime.now(timezone.utc)
        self.session.add(contract)
        self.session.commit()
        self.session.refresh(contract)
        return contract

    def _validate_binary_flag(self, field_name: str, value: int) -> None:
        if value in (0, 1):
            return
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be 0 or 1",
        )
