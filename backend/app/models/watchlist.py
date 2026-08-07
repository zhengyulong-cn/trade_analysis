from datetime import datetime, timezone

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Watchlist(SQLModel, table=True):
    __tablename__ = "watchlists"

    watchlist_id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True, min_length=1, max_length=100)
    display_order: int = Field(default=1000, nullable=False, index=True)
    create_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)


class WatchlistItem(SQLModel, table=True):
    __tablename__ = "watchlist_items"
    __table_args__ = (
        UniqueConstraint("watchlist_id", "contract_id", name="uq_watchlist_contract"),
    )

    watchlist_item_id: int | None = Field(default=None, primary_key=True)
    watchlist_id: int = Field(foreign_key="watchlists.watchlist_id", index=True)
    contract_id: int = Field(foreign_key="contracts.contract_id", index=True)
    display_order: int = Field(default=1000, nullable=False, index=True)
    create_at: datetime = Field(default_factory=utc_now, nullable=False)
