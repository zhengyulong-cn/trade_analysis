from fastapi import APIRouter

from app.api.routes.chart_persistences import router as chart_persistence_router
from app.api.routes.contract_intervals import router as contract_interval_router
from app.api.routes.contracts import router as contract_router
from app.api.routes.health import router as health_router
from app.api.routes.klines import router as kline_router
from app.api.routes.realtime_bars import router as realtime_bar_router
from app.api.routes.strategy_analysis import router as strategy_analysis_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(
    chart_persistence_router,
    prefix="/chart-persistences",
    tags=["chart-persistences"],
)
api_router.include_router(contract_router, prefix="/contracts", tags=["contracts"])
api_router.include_router(
    contract_interval_router,
    prefix="/contract-intervals",
    tags=["contract-intervals"],
)
api_router.include_router(kline_router, prefix="/klines", tags=["klines"])
api_router.include_router(
    realtime_bar_router,
    prefix="/realtime-bars",
    tags=["realtime-bars"],
)
api_router.include_router(
    strategy_analysis_router,
    prefix="/strategy-analyses",
    tags=["strategy-analyses"],
)
