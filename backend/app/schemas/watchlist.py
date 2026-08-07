from datetime import datetime

from sqlmodel import SQLModel


class WatchlistCreate(SQLModel):
    name: str


class WatchlistRename(SQLModel):
    name: str


class WatchlistRead(SQLModel):
    watchlist_id: int
    name: str
    display_order: int
    item_count: int
    create_at: datetime
    updated_at: datetime


class WatchlistItemCreate(SQLModel):
    contract_id: int


class WatchlistItemRemove(SQLModel):
    contract_id: int


class WatchlistReorder(SQLModel):
    contract_ids: list[int]


class WatchlistContractRead(SQLModel):
    contract_id: int
    symbol: str
    exchange: str
    name: str
    create_at: datetime
    updated_at: datetime
    display_order: int
