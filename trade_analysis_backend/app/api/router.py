from fastapi import APIRouter

from app.api.routes.chart_persistences import router as chart_persistence_router
from app.api.routes.contracts import router as contract_router
from app.api.routes.contract_prompt_profiles import router as contract_prompt_profile_router
from app.api.routes.report_documents import router as report_document_router
from app.api.routes.analysis import router as analysis_router
from app.api.routes.health import router as health_router
from app.api.routes.klines import router as kline_router
from app.api.routes.realtime_bars import router as realtime_bar_router
from app.api.routes.trade_records import router as trade_record_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(
    chart_persistence_router,
    prefix="/chart-persistences",
    tags=["chart-persistences"],
)
api_router.include_router(contract_router, prefix="/contracts", tags=["contracts"])
api_router.include_router(
    contract_prompt_profile_router,
    prefix="/contract-prompt-profiles",
    tags=["contract-prompt-profiles"],
)
api_router.include_router(
    report_document_router,
    prefix="/report-documents",
    tags=["report-documents"],
)
api_router.include_router(kline_router, prefix="/klines", tags=["klines"])
api_router.include_router(
    trade_record_router,
    prefix="/trade-records",
    tags=["trade-records"],
)
api_router.include_router(
    realtime_bar_router,
    prefix="/realtime-bars",
    tags=["realtime-bars"],
)
api_router.include_router(
    analysis_router,
    prefix="/analysis",
    tags=["analysis"],
)
