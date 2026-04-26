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


def ensure_contract_auto_load_segments_column() -> None:
    with engine.connect() as connection:
        column_exists = connection.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.columns "
                "WHERE table_schema = :database_name "
                "AND table_name = 'contracts' "
                "AND column_name = 'auto_load_segments'"
            ),
            {"database_name": settings.mysql_database},
        ).scalar_one()
        if column_exists:
            return

        connection.execute(
            text(
                "ALTER TABLE contracts "
                "ADD COLUMN auto_load_segments INT NOT NULL DEFAULT 0"
            )
        )
        connection.commit()
        logger.info("Column ensured: contracts.auto_load_segments")


def ensure_contract_is_favorite_column() -> None:
    with engine.connect() as connection:
        column_exists = connection.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.columns "
                "WHERE table_schema = :database_name "
                "AND table_name = 'contracts' "
                "AND column_name = 'is_favorite'"
            ),
            {"database_name": settings.mysql_database},
        ).scalar_one()
        if column_exists:
            return

        connection.execute(
            text(
                "ALTER TABLE contracts "
                "ADD COLUMN is_favorite INT NOT NULL DEFAULT 0"
            )
        )
        connection.commit()
        logger.info("Column ensured: contracts.is_favorite")


def initialize_database() -> None:
    try:
        create_database_if_not_exists()
        metadata.create_all(engine)
        ensure_contract_auto_load_segments_column()
        ensure_contract_is_favorite_column()
        logger.info("Database tables initialized")
    except SQLAlchemyError:
        logger.exception("Failed to initialize database")
        raise
