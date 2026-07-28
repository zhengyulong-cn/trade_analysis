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
        _drop_legacy_contract_favorite_column()
        logger.info("Database tables initialized")
    except SQLAlchemyError:
        logger.exception("Failed to initialize database")
        raise


def _drop_legacy_contract_favorite_column() -> None:
    statement = text(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = :database_name "
        "AND TABLE_NAME = 'contracts' AND COLUMN_NAME = 'is_favorite'"
    )
    with engine.begin() as connection:
        has_legacy_column = connection.execute(
            statement,
            {"database_name": settings.mysql_database},
        ).scalar_one()
        if has_legacy_column:
            connection.execute(text("ALTER TABLE contracts DROP COLUMN is_favorite"))
