from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, func, select

from app.models.contract import Contract
from app.models.watchlist import Watchlist, WatchlistItem
from app.schemas.watchlist import WatchlistContractRead, WatchlistRead


class WatchlistService:
    def __init__(self, session: Session):
        self.session = session

    def list_watchlists(self) -> list[WatchlistRead]:
        watchlists = list(
            self.session.exec(select(Watchlist).order_by(Watchlist.display_order)).all()
        )
        if not watchlists:
            watchlists = [self.create_watchlist("我的自选")]
        return [self._map_watchlist(item) for item in watchlists]

    def create_watchlist(self, name: str) -> Watchlist:
        normalized_name = name.strip()
        if not normalized_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Watchlist name cannot be empty")
        max_order = self.session.exec(select(func.max(Watchlist.display_order))).one() or 0
        watchlist = Watchlist(name=normalized_name, display_order=max_order + 1000)
        self.session.add(watchlist)
        self._commit("Watchlist name already exists")
        self.session.refresh(watchlist)
        return watchlist

    def rename_watchlist(self, watchlist_id: int, name: str) -> Watchlist:
        watchlist = self._get_watchlist(watchlist_id)
        normalized_name = name.strip()
        if not normalized_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Watchlist name cannot be empty")
        watchlist.name = normalized_name
        watchlist.updated_at = datetime.now(timezone.utc)
        self.session.add(watchlist)
        self._commit("Watchlist name already exists")
        self.session.refresh(watchlist)
        return watchlist

    def delete_watchlist(self, watchlist_id: int) -> None:
        watchlist = self._get_watchlist(watchlist_id)
        items = list(self.session.exec(select(WatchlistItem).where(WatchlistItem.watchlist_id == watchlist_id)).all())
        for item in items:
            self.session.delete(item)
        self.session.delete(watchlist)
        self.session.commit()

    def list_contracts(self, watchlist_id: int) -> list[WatchlistContractRead]:
        self._get_watchlist(watchlist_id)
        rows = self.session.exec(
            select(WatchlistItem, Contract)
            .join(Contract, Contract.contract_id == WatchlistItem.contract_id)
            .where(WatchlistItem.watchlist_id == watchlist_id)
            .order_by(WatchlistItem.display_order, WatchlistItem.watchlist_item_id)
        ).all()
        return [
            WatchlistContractRead(
                contract_id=contract.contract_id,
                symbol=contract.symbol,
                exchange=contract.exchange,
                name=contract.name,
                create_at=contract.create_at,
                updated_at=contract.updated_at,
                display_order=item.display_order,
            )
            for item, contract in rows
        ]

    def add_contract(self, watchlist_id: int, contract_id: int) -> None:
        self._get_watchlist(watchlist_id)
        if self.session.get(Contract, contract_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")
        exists = self.session.exec(
            select(WatchlistItem).where(
                WatchlistItem.watchlist_id == watchlist_id,
                WatchlistItem.contract_id == contract_id,
            )
        ).first()
        if exists is not None:
            return
        max_order = self.session.exec(
            select(func.max(WatchlistItem.display_order)).where(WatchlistItem.watchlist_id == watchlist_id)
        ).one() or 0
        self.session.add(WatchlistItem(watchlist_id=watchlist_id, contract_id=contract_id, display_order=max_order + 1000))
        self.session.commit()

    def remove_contract(self, watchlist_id: int, contract_id: int) -> None:
        item = self.session.exec(
            select(WatchlistItem).where(
                WatchlistItem.watchlist_id == watchlist_id,
                WatchlistItem.contract_id == contract_id,
            )
        ).first()
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist contract not found")
        self.session.delete(item)
        self.session.commit()

    def reorder_contracts(self, watchlist_id: int, contract_ids: list[int]) -> None:
        items = list(self.session.exec(select(WatchlistItem).where(WatchlistItem.watchlist_id == watchlist_id)).all())
        item_by_contract_id = {item.contract_id: item for item in items}
        if len(contract_ids) != len(items) or len(set(contract_ids)) != len(contract_ids) or set(contract_ids) != set(item_by_contract_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contract ids must match the watchlist")
        for index, contract_id in enumerate(contract_ids, start=1):
            item = item_by_contract_id[contract_id]
            item.display_order = index * 1000
            self.session.add(item)
        self.session.commit()

    def _get_watchlist(self, watchlist_id: int) -> Watchlist:
        watchlist = self.session.get(Watchlist, watchlist_id)
        if watchlist is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found")
        return watchlist

    def _map_watchlist(self, watchlist: Watchlist) -> WatchlistRead:
        item_count = self.session.exec(
            select(func.count()).select_from(WatchlistItem).where(WatchlistItem.watchlist_id == watchlist.watchlist_id)
        ).one()
        return WatchlistRead(
            watchlist_id=watchlist.watchlist_id,
            name=watchlist.name,
            display_order=watchlist.display_order,
            item_count=int(item_count),
            create_at=watchlist.create_at,
            updated_at=watchlist.updated_at,
        )

    def _commit(self, detail: str) -> None:
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc
