from typing import Annotated

from fastapi import Depends
from redis import Redis
from sqlmodel import Session

from app.db.session import get_session
from app.services.chart_persistence_service import ChartPersistenceService
from app.services.contract_service import ContractService
from app.services.kline_service import KlineService
from app.services.market_data import (
    KlineProvider,
    QuoteProvider,
    create_kline_provider,
    create_quote_provider,
)
from app.services.opportunity_review_column_service import OpportunityReviewColumnService
from app.services.opportunity_review_service import OpportunityReviewService
from app.services.pine_script_service import PineScriptService
from app.services.pine_indicator_service import PineIndicatorService
from app.services.pine_runner_client import PineRunnerClient
from app.services.realtime_bar_service import RealtimeBarService
from app.services.signal_filter_service import SignalFilterService
from app.services.trade_record_service import TradeRecordService
from app.services.trade_record_storage import TradeRecordStorageService
from app.services.trade_record_column_service import TradeRecordColumnService
from app.services.trade_account_service import TradeAccountService
# from app.services.analysis_service import AnalysisService
from app.services.analysis_service_v2 import AnalysisServiceV2
from app.services.redis_client import redis_client_manager
from app.services.trade_thought_service import TradeThoughtService
from app.services.trade_thought_storage import TradeThoughtStorageService
from app.services.upload_service import UploadService
from app.services.watchlist_service import WatchlistService

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


def get_watchlist_service(session: SessionDep) -> WatchlistService:
    return WatchlistService(session)


def get_chart_persistence_service(session: SessionDep) -> ChartPersistenceService:
    return ChartPersistenceService(session)


def get_trade_account_service(session: SessionDep) -> TradeAccountService:
    return TradeAccountService(session)


def get_trade_record_column_service(session: SessionDep) -> TradeRecordColumnService:
    return TradeRecordColumnService(session)


def get_opportunity_review_column_service(session: SessionDep) -> OpportunityReviewColumnService:
    return OpportunityReviewColumnService(session)


def get_opportunity_review_service(session: SessionDep) -> OpportunityReviewService:
    return OpportunityReviewService(session)


def get_pine_script_service(session: SessionDep) -> PineScriptService:
    return PineScriptService(session)


def get_trade_record_service(session: SessionDep) -> TradeRecordService:
    return TradeRecordService(session)


def get_trade_record_storage_service() -> TradeRecordStorageService:
    return TradeRecordStorageService()


def get_trade_thought_storage_service() -> TradeThoughtStorageService:
    return TradeThoughtStorageService()


def get_upload_service() -> UploadService:
    return UploadService()


TradeThoughtStorageServiceDep = Annotated[
    TradeThoughtStorageService, Depends(get_trade_thought_storage_service)
]
UploadServiceDep = Annotated[UploadService, Depends(get_upload_service)]


def get_trade_thought_service(
    session: SessionDep,
    storage_service: TradeThoughtStorageServiceDep,
) -> TradeThoughtService:
    return TradeThoughtService(session=session, storage_service=storage_service)


def get_kline_service(
    session: SessionDep,
    kline_provider: KlineProviderDep,
) -> KlineService:
    return KlineService(session, kline_provider=kline_provider)


PineScriptServiceDep = Annotated[
    PineScriptService, Depends(get_pine_script_service)
]
KlineServiceDep = Annotated[KlineService, Depends(get_kline_service)]


def get_pine_indicator_service(
    pine_script_service: PineScriptServiceDep,
    kline_service: KlineServiceDep,
) -> PineIndicatorService:
    return PineIndicatorService(
        pine_script_service=pine_script_service,
        kline_service=kline_service,
        pine_runner_client=PineRunnerClient(),
    )


PineIndicatorServiceDep = Annotated[
    PineIndicatorService, Depends(get_pine_indicator_service)
]


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
WatchlistServiceDep = Annotated[WatchlistService, Depends(get_watchlist_service)]
ChartPersistenceServiceDep = Annotated[
    ChartPersistenceService, Depends(get_chart_persistence_service)
]
TradeAccountServiceDep = Annotated[
    TradeAccountService, Depends(get_trade_account_service)
]
TradeRecordColumnServiceDep = Annotated[
    TradeRecordColumnService, Depends(get_trade_record_column_service)
]
OpportunityReviewColumnServiceDep = Annotated[
    OpportunityReviewColumnService, Depends(get_opportunity_review_column_service)
]
OpportunityReviewServiceDep = Annotated[
    OpportunityReviewService, Depends(get_opportunity_review_service)
]
TradeRecordServiceDep = Annotated[
    TradeRecordService, Depends(get_trade_record_service)
]
TradeRecordStorageServiceDep = Annotated[
    TradeRecordStorageService, Depends(get_trade_record_storage_service)
]
RealtimeBarServiceDep = Annotated[
    RealtimeBarService, Depends(get_realtime_bar_service)
]
TradeThoughtServiceDep = Annotated[
    TradeThoughtService, Depends(get_trade_thought_service)
]


def get_analysis_service(kline_service: KlineServiceDep) -> AnalysisServiceV2:
    return AnalysisServiceV2(kline_service=kline_service)


AnalysisServiceDep = Annotated[AnalysisServiceV2, Depends(get_analysis_service)]


def get_signal_filter_service(
    kline_service: KlineServiceDep,
    contract_service: ContractServiceDep,
) -> SignalFilterService:
    return SignalFilterService(
        kline_service=kline_service,
        contract_service=contract_service,
    )


SignalFilterServiceDep = Annotated[
    SignalFilterService, Depends(get_signal_filter_service)
]
