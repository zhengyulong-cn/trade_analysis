from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.db.init_db import initialize_database
from app.middlewares.logging import RequestLoggingMiddleware
from app.services.market_data import tqsdk_client_manager
from app.services.redis_client import redis_client_manager
from app.services.realtime_quote_worker import realtime_quote_worker

configure_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting %s", settings.app_name)
    initialize_database()
    redis_client_manager.start()
    try:
        tqsdk_client_manager.start()
    except Exception as exc:
        logger.warning("TqSdk client unavailable during startup: %s", exc)
    try:
        realtime_quote_worker.start()
    except Exception as exc:
        logger.warning("Realtime quote worker unavailable during startup: %s", exc)
    yield
    realtime_quote_worker.stop()
    tqsdk_client_manager.close()
    redis_client_manager.close()
    logger.info("Stopping %s", settings.app_name)


def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )
    application.add_middleware(RequestLoggingMiddleware)
    register_exception_handlers(application)
    application.include_router(api_router, prefix=settings.api_prefix)
    return application


app = create_application()
