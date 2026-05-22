from typing import Annotated

from fastapi import Depends
from redis import Redis
from sqlmodel import Session

from app.db.session import get_session
from app.services.chart_persistence_service import ChartPersistenceService
from app.services.contract_service import ContractService
from app.services.future_product_service import FutureProductService
from app.services.future_report_document_service import FutureReportDocumentService
from app.services.future_report_document_storage import FutureReportDocumentStorageService
from app.services.future_fundamental_analysis_service import FutureFundamentalAnalysisService
from app.services.kline_service import KlineService
from app.services.market_data import (
    KlineProvider,
    QuoteProvider,
    create_kline_provider,
    create_quote_provider,
)
from app.services.opportunity_analysis_service_v2 import OpportunityAnalysisServiceV2
from app.services.realtime_bar_service import RealtimeBarService
# from app.services.analysis_service import AnalysisService
from app.services.analysis_service_v2 import AnalysisServiceV2
from app.services.redis_client import redis_client_manager
from app.services.trade_record_service import TradeRecordService
from app.services.trade_record_storage import TradeRecordStorageService
from app.services.trade_thought_service import TradeThoughtService
from app.services.trade_thought_storage import TradeThoughtStorageService

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


def get_future_product_service(session: SessionDep) -> FutureProductService:
    return FutureProductService(session)


def get_future_report_document_storage_service() -> FutureReportDocumentStorageService:
    return FutureReportDocumentStorageService()


def get_future_report_document_service(
    session: SessionDep,
    storage_service: Annotated[
        FutureReportDocumentStorageService, Depends(get_future_report_document_storage_service)
    ],
) -> FutureReportDocumentService:
    return FutureReportDocumentService(session=session, storage_service=storage_service)


def get_future_fundamental_analysis_service(
    session: SessionDep,
) -> FutureFundamentalAnalysisService:
    return FutureFundamentalAnalysisService(session)


def get_chart_persistence_service(session: SessionDep) -> ChartPersistenceService:
    return ChartPersistenceService(session)


def get_trade_record_storage_service() -> TradeRecordStorageService:
    return TradeRecordStorageService()


TradeRecordStorageServiceDep = Annotated[
    TradeRecordStorageService, Depends(get_trade_record_storage_service)
]


def get_trade_record_service(
    session: SessionDep,
    storage_service: TradeRecordStorageServiceDep,
) -> TradeRecordService:
    return TradeRecordService(session=session, storage_service=storage_service)


def get_trade_thought_storage_service() -> TradeThoughtStorageService:
    return TradeThoughtStorageService()


TradeThoughtStorageServiceDep = Annotated[
    TradeThoughtStorageService, Depends(get_trade_thought_storage_service)
]


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
FutureProductServiceDep = Annotated[FutureProductService, Depends(get_future_product_service)]
FutureReportDocumentStorageServiceDep = Annotated[
    FutureReportDocumentStorageService, Depends(get_future_report_document_storage_service)
]
FutureReportDocumentServiceDep = Annotated[
    FutureReportDocumentService, Depends(get_future_report_document_service)
]
FutureFundamentalAnalysisServiceDep = Annotated[
    FutureFundamentalAnalysisService, Depends(get_future_fundamental_analysis_service)
]
ChartPersistenceServiceDep = Annotated[
    ChartPersistenceService, Depends(get_chart_persistence_service)
]
KlineServiceDep = Annotated[KlineService, Depends(get_kline_service)]
RealtimeBarServiceDep = Annotated[
    RealtimeBarService, Depends(get_realtime_bar_service)
]
TradeRecordServiceDep = Annotated[
    TradeRecordService, Depends(get_trade_record_service)
]
TradeThoughtServiceDep = Annotated[
    TradeThoughtService, Depends(get_trade_thought_service)
]


def get_analysis_service(kline_service: KlineServiceDep) -> AnalysisServiceV2:
    return AnalysisServiceV2(kline_service=kline_service)


AnalysisServiceDep = Annotated[AnalysisServiceV2, Depends(get_analysis_service)]


def get_opportunity_analysis_service(
    contract_service: ContractServiceDep,
    kline_service: KlineServiceDep,
    analysis_service: AnalysisServiceDep,
) -> OpportunityAnalysisServiceV2:
    return OpportunityAnalysisServiceV2(
        contract_service=contract_service,
        kline_service=kline_service,
        analysis_service=analysis_service,
    )


OpportunityAnalysisServiceDep = Annotated[
    OpportunityAnalysisServiceV2, Depends(get_opportunity_analysis_service)
]
