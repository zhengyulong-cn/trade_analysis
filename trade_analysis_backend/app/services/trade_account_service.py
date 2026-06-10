from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.trade_account import TradeAccount
from app.schemas.trade_account import TradeAccountCreate, TradeAccountUpdate


class TradeAccountService:
    def __init__(self, session: Session):
        self.session = session

    def list_trade_accounts(self) -> list[TradeAccount]:
        statement = select(TradeAccount).order_by(TradeAccount.account_id)
        return list(self.session.exec(statement).all())

    def create_trade_account(self, payload: TradeAccountCreate) -> TradeAccount:
        account = TradeAccount.model_validate(payload.model_dump())
        self.session.add(account)
        self.session.commit()
        self.session.refresh(account)
        return account

    def update_trade_account(self, payload: TradeAccountUpdate) -> TradeAccount:
        account = self.get_trade_account_by_id(payload.account_id)
        update_data = payload.model_dump(exclude={"account_id"}, exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No trade account fields to update",
            )

        for field_name, value in update_data.items():
            setattr(account, field_name, value)

        account.updated_at = datetime.now(timezone.utc)
        self.session.add(account)
        self.session.commit()
        self.session.refresh(account)
        return account

    def delete_trade_account(self, account_id: int) -> None:
        account = self.get_trade_account_by_id(account_id)
        self.session.delete(account)
        self.session.commit()

    def get_trade_account_by_id(self, account_id: int) -> TradeAccount:
        account = self.session.get(TradeAccount, account_id)
        if account is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trade account not found: {account_id}",
            )
        return account
