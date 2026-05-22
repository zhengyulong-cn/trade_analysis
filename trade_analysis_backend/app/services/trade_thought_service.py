from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.trade_thought import TradeThought
from app.schemas.trade_thought import TradeThoughtCreate, TradeThoughtUpdate
from app.services.trade_thought_storage import TradeThoughtStorageService


class TradeThoughtService:
    def __init__(self, session: Session, storage_service: TradeThoughtStorageService):
        self.session = session
        self.storage_service = storage_service

    def list_trade_thoughts(self) -> list[TradeThought]:
        statement = select(TradeThought).order_by(TradeThought.created_at.desc(), TradeThought.thought_id.desc())
        return list(self.session.exec(statement).all())

    def create_trade_thought(self, payload: TradeThoughtCreate) -> TradeThought:
        thought = TradeThought.model_validate(payload.model_dump())
        self.session.add(thought)
        self.session.commit()
        self.session.refresh(thought)
        return thought

    def update_trade_thought(self, payload: TradeThoughtUpdate) -> TradeThought:
        thought = self.get_trade_thought_by_id(payload.thought_id)
        update_data = payload.model_dump(exclude={"thought_id"}, exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No trade thought fields to update",
            )

        old_image_paths = self._extract_image_paths(thought.images)
        for field_name, value in update_data.items():
            setattr(thought, field_name, value)

        thought.updated_at = datetime.now(timezone.utc)
        self.session.add(thought)
        self.session.commit()
        self.session.refresh(thought)

        current_image_paths = self._extract_image_paths(thought.images)
        for orphan_path in old_image_paths - current_image_paths:
            self.storage_service.delete_relative_path(orphan_path)

        return thought

    def delete_trade_thought(self, thought_id: int) -> None:
        thought = self.get_trade_thought_by_id(thought_id)
        image_paths = self._extract_image_paths(thought.images)
        self.session.delete(thought)
        self.session.commit()
        for image_path in image_paths:
            self.storage_service.delete_relative_path(image_path)

    def get_trade_thought_by_id(self, thought_id: int) -> TradeThought:
        thought = self.session.get(TradeThought, thought_id)
        if thought is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trade thought not found: {thought_id}",
            )
        return thought

    def _extract_image_paths(self, images: list[dict] | None) -> set[str]:
        if not images:
            return set()

        paths: set[str] = set()
        for item in images:
            path = item.get("path") if isinstance(item, dict) else None
            if path:
                paths.add(path)
        return paths
