from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.logging import get_logger
from app.db.base import metadata
from app.db.session import engine, server_engine

logger = get_logger(__name__)


def create_database_if_not_exists() -> None:
    with server_engine.connect() as connection:
        connection.execute(
            text(
                f"CREATE DATABASE IF NOT EXISTS `{settings.mysql_database}` "
                "DEFAULT CHARACTER SET utf8mb4"
            )
        )
        connection.commit()
    logger.info("Database ensured: %s", settings.mysql_database)


def initialize_database() -> None:
    try:
        create_database_if_not_exists()
        metadata.create_all(engine)
        logger.info("Database tables initialized")
    except SQLAlchemyError:
        logger.exception("Failed to initialize database")
        raise
