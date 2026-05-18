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


def ensure_future_product_schema() -> None:
    with engine.connect() as connection:
        exchange_exists = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = :schema
                  AND TABLE_NAME = 'future_products'
                  AND COLUMN_NAME = 'exchange'
                """
            ),
            {"schema": settings.mysql_database},
        ).scalar_one()
        if exchange_exists:
            index_exists = connection.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA = :schema
                      AND TABLE_NAME = 'future_products'
                      AND INDEX_NAME = 'uq_future_product_code_exchange'
                    """
                ),
                {"schema": settings.mysql_database},
            ).scalar_one()
            if index_exists:
                connection.execute(
                    text("ALTER TABLE future_products DROP INDEX uq_future_product_code_exchange")
                )
            connection.execute(text("ALTER TABLE future_products DROP COLUMN exchange"))
        name_exists = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = :schema
                  AND TABLE_NAME = 'future_products'
                  AND COLUMN_NAME = 'name'
                """
            ),
            {"schema": settings.mysql_database},
        ).scalar_one()
        display_name_exists = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = :schema
                  AND TABLE_NAME = 'future_products'
                  AND COLUMN_NAME = 'display_name'
                """
            ),
            {"schema": settings.mysql_database},
        ).scalar_one()
        if name_exists and not display_name_exists:
            connection.execute(text("ALTER TABLE future_products CHANGE COLUMN name display_name VARCHAR(100) NOT NULL"))
        alias_names_exists = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = :schema
                  AND TABLE_NAME = 'future_products'
                  AND COLUMN_NAME = 'alias_names'
                """
            ),
            {"schema": settings.mysql_database},
        ).scalar_one()
        if not alias_names_exists:
            connection.execute(text("ALTER TABLE future_products ADD COLUMN alias_names JSON NOT NULL"))
            connection.execute(text("UPDATE future_products SET alias_names = JSON_ARRAY() WHERE alias_names IS NULL"))
        connection.commit()

def initialize_database() -> None:
    try:
        create_database_if_not_exists()
        metadata.create_all(engine)
        ensure_future_product_schema()
        logger.info("Database tables initialized")
    except SQLAlchemyError:
        logger.exception("Failed to initialize database")
        raise
