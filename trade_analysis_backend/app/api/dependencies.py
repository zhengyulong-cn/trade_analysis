from typing import Annotated

from fastapi import Depends
from sqlmodel import Session

from app.db.session import get_session
from app.services.contract_service import ContractService
from app.services.contract_interval_service import ContractIntervalService
from app.services.kline_service import KlineService
from app.services.market_data import KlineProvider, create_kline_provider
from app.services.strategy_analysis_service import StrategyAnalysisService

SessionDep = Annotated[Session, Depends(get_session)]


def get_kline_provider() -> KlineProvider:
    return create_kline_provider()


KlineProviderDep = Annotated[KlineProvider, Depends(get_kline_provider)]


def get_contract_service(session: SessionDep) -> ContractService:
    return ContractService(session)


def get_contract_interval_service(session: SessionDep) -> ContractIntervalService:
    return ContractIntervalService(session)


def get_kline_service(
    session: SessionDep,
    kline_provider: KlineProviderDep,
) -> KlineService:
    return KlineService(session, kline_provider=kline_provider)


def get_strategy_analysis_service(session: SessionDep) -> StrategyAnalysisService:
    return StrategyAnalysisService(session)


ContractServiceDep = Annotated[ContractService, Depends(get_contract_service)]
ContractIntervalServiceDep = Annotated[
    ContractIntervalService, Depends(get_contract_interval_service)
]
KlineServiceDep = Annotated[KlineService, Depends(get_kline_service)]
StrategyAnalysisServiceDep = Annotated[
    StrategyAnalysisService, Depends(get_strategy_analysis_service)
]
