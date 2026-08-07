import json
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.chart_persistence import ChartPersistence
from app.schemas.chart_persistence import ChartPersistenceSave


PERSISTENCE_USER_KEY = "default"
JSON_CONTENT_FIELDS = {"drawings_content"}


class ChartPersistenceService:
    def __init__(self, session: Session):
        self.session = session

    def get_persistence(
        self,
        symbol: str,
        interval: str,
    ) -> ChartPersistence:
        normalized_symbol = self._normalize_required_text(symbol, "symbol")
        normalized_interval = self._normalize_required_text(interval, "interval")
        return self._get_or_create_persistence(normalized_symbol, normalized_interval)

    def save_persistence(self, payload: ChartPersistenceSave) -> ChartPersistence:
        normalized_symbol = self._normalize_required_text(payload.symbol, "symbol")
        normalized_interval = self._normalize_required_text(payload.interval, "interval")
        update_data = payload.model_dump(
            exclude={"symbol", "interval"},
            exclude_unset=True,
        )

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No chart persistence fields to update",
            )

        for field_name, value in update_data.items():
            if field_name in JSON_CONTENT_FIELDS:
                self._validate_json_content(field_name, value)

        persistence = self._get_or_create_persistence(
            normalized_symbol,
            normalized_interval,
        )

        for field_name, value in update_data.items():
            setattr(persistence, field_name, value)

        persistence.updated_at = datetime.now(timezone.utc)
        self.session.add(persistence)
        self.session.commit()
        self.session.refresh(persistence)
        return persistence

    def _get_or_create_persistence(
        self,
        symbol: str,
        interval: str,
    ) -> ChartPersistence:
        statement = select(ChartPersistence).where(
            ChartPersistence.user_key == PERSISTENCE_USER_KEY,
            ChartPersistence.symbol == symbol,
            ChartPersistence.interval == interval,
        )
        persistence = self.session.exec(statement).first()
        if persistence is not None:
            return persistence

        persistence = ChartPersistence(
            user_key=PERSISTENCE_USER_KEY,
            symbol=symbol,
            interval=interval,
        )
        self.session.add(persistence)
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            persistence = self.session.exec(statement).first()
            if persistence is not None:
                return persistence
            raise

        self.session.refresh(persistence)
        return persistence

    def _normalize_required_text(self, value: str, field_name: str) -> str:
        normalized = value.strip()
        if normalized:
            return normalized
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} is required",
        )

    def _validate_json_content(self, field_name: str, value: str | None) -> None:
        if value is None:
            return

        try:
            json.loads(value)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} must be a valid JSON string",
            ) from exc
