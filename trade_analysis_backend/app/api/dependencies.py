from typing import Annotated

from fastapi import Depends
from redis import Redis
from sqlmodel import Session

from app.db.session import get_session
from app.services.chart_persistence_service import ChartPersistenceService
from app.services.contract_service import ContractService
from app.services.contract_interval_service import ContractIntervalService
from app.services.kline_service import KlineService
from app.services.market_data import (
    KlineProvider,
    QuoteProvider,
    create_kline_provider,
    create_quote_provider,
)
from app.services.realtime_bar_service import RealtimeBarService
from app.services.redis_client import redis_client_manager

SessionDep = Annotated[Session, Depends(get_session)]


def get_kline_provider() -> KlineProvider:
    return create_kline_provider()


KlineProviderDep = Annotated[KlineProvider, Depends(get_kline_provider)]


def get_quote_provider() -> QuoteProvider:
    return create_quote_provider()


QuoteProviderDep = Annotated[QuoteProvider, Depends(get_quote_provider)]


def get_redis_client() -> Redis:
    return redis_client_manager.get_client()


RedisClientDep = Annotated[Redis, Depends(get_redis_client)]


def get_contract_service(session: SessionDep) -> ContractService:
    return ContractService(session)


def get_chart_persistence_service(session: SessionDep) -> ChartPersistenceService:
    return ChartPersistenceService(session)


def get_contract_interval_service(session: SessionDep) -> ContractIntervalService:
    return ContractIntervalService(session)


def get_kline_service(
    session: SessionDep,
    kline_provider: KlineProviderDep,
) -> KlineService:
    return KlineService(session, kline_provider=kline_provider)


def get_realtime_bar_service(
    session: SessionDep,
    redis_client: RedisClientDep,
    quote_provider: QuoteProviderDep,
) -> RealtimeBarService:
    return RealtimeBarService(
        session=session,
        redis_client=redis_client,
        kline_provider=quote_provider,
    )


ContractServiceDep = Annotated[ContractService, Depends(get_contract_service)]
ChartPersistenceServiceDep = Annotated[
    ChartPersistenceService, Depends(get_chart_persistence_service)
]
ContractIntervalServiceDep = Annotated[
    ContractIntervalService, Depends(get_contract_interval_service)
]
KlineServiceDep = Annotated[KlineService, Depends(get_kline_service)]
RealtimeBarServiceDep = Annotated[
    RealtimeBarService, Depends(get_realtime_bar_service)
]
