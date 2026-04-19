from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.contract import Contract
from app.schemas.contract import ContractCreate


class ContractService:
    def __init__(self, session: Session):
        self.session = session

    def create_contract(self, payload: ContractCreate) -> Contract:
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

    def list_contracts(self) -> list[Contract]:
        statement = select(Contract).order_by(Contract.symbol)
        return list(self.session.exec(statement).all())

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
