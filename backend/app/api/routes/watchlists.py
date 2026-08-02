from fastapi import APIRouter, status

from app.api.dependencies import WatchlistServiceDep
from app.schemas.watchlist import (
    WatchlistContractRead,
    WatchlistCreate,
    WatchlistItemCreate,
    WatchlistItemRemove,
    WatchlistRead,
    WatchlistReorder,
    WatchlistRename,
)

router = APIRouter()


@router.get("", response_model=list[WatchlistRead])
def list_watchlists(service: WatchlistServiceDep) -> list[WatchlistRead]:
    return service.list_watchlists()


@router.post("", response_model=WatchlistRead, status_code=status.HTTP_201_CREATED)
def create_watchlist(payload: WatchlistCreate, service: WatchlistServiceDep) -> WatchlistRead:
    return service._map_watchlist(service.create_watchlist(payload.name))


@router.post("/{watchlist_id}/rename", response_model=WatchlistRead)
def rename_watchlist(watchlist_id: int, payload: WatchlistRename, service: WatchlistServiceDep) -> WatchlistRead:
    return service._map_watchlist(service.rename_watchlist(watchlist_id, payload.name))


@router.post("/{watchlist_id}/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_watchlist(watchlist_id: int, service: WatchlistServiceDep) -> None:
    service.delete_watchlist(watchlist_id)


@router.get("/{watchlist_id}/contracts", response_model=list[WatchlistContractRead])
def list_watchlist_contracts(watchlist_id: int, service: WatchlistServiceDep) -> list[WatchlistContractRead]:
    return service.list_contracts(watchlist_id)


@router.post("/{watchlist_id}/contracts", status_code=status.HTTP_204_NO_CONTENT)
def add_watchlist_contract(watchlist_id: int, payload: WatchlistItemCreate, service: WatchlistServiceDep) -> None:
    service.add_contract(watchlist_id, payload.contract_id)


@router.post("/{watchlist_id}/contracts/remove", status_code=status.HTTP_204_NO_CONTENT)
def remove_watchlist_contract(watchlist_id: int, payload: WatchlistItemRemove, service: WatchlistServiceDep) -> None:
    service.remove_contract(watchlist_id, payload.contract_id)


@router.post("/{watchlist_id}/contracts/reorder", status_code=status.HTTP_204_NO_CONTENT)
def reorder_watchlist_contracts(watchlist_id: int, payload: WatchlistReorder, service: WatchlistServiceDep) -> None:
    service.reorder_contracts(watchlist_id, payload.contract_ids)
