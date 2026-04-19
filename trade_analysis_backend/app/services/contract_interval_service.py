from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.contract_interval import ContractInterval
from app.schemas.contract_interval import ContractIntervalCreate


class ContractIntervalService:
    def __init__(self, session: Session):
        self.session = session

    def create_interval(self, payload: ContractIntervalCreate) -> ContractInterval:
        interval = ContractInterval.model_validate(payload)
        self.session.add(interval)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Contract interval already exists",
            ) from exc
        self.session.refresh(interval)
        return interval

    def list_intervals(self) -> list[ContractInterval]:
        statement = select(ContractInterval).order_by(ContractInterval.seconds)
        return list(self.session.exec(statement).all())

    def get_interval_by_seconds(self, seconds: int) -> ContractInterval:
        statement = select(ContractInterval).where(ContractInterval.seconds == seconds)
        interval = self.session.exec(statement).first()
        if interval is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contract interval not found: {seconds}",
            )
        return interval
