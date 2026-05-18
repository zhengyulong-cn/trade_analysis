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


def ensure_report_document_columns() -> None:
    statements = [
        text(
            """
            SELECT COUNT(*)
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = :schema
              AND TABLE_NAME = 'report_documents'
              AND COLUMN_NAME = 'published_at'
            """
        ),
        text(
            """
            SELECT COUNT(*)
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = :schema
              AND TABLE_NAME = 'report_documents'
              AND COLUMN_NAME = 'source'
            """
        ),
    ]
    with engine.connect() as connection:
        published_exists = connection.execute(
            statements[0], {"schema": settings.mysql_database}
        ).scalar_one()
        if not published_exists:
            connection.execute(
                text("ALTER TABLE report_documents ADD COLUMN published_at DATE NULL")
            )
        source_exists = connection.execute(
            statements[1], {"schema": settings.mysql_database}
        ).scalar_one()
        if not source_exists:
            connection.execute(
                text("ALTER TABLE report_documents ADD COLUMN source VARCHAR(255) NULL")
            )
        connection.commit()


def ensure_contract_product_column() -> None:
    with engine.connect() as connection:
        exists = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = :schema
                  AND TABLE_NAME = 'contracts'
                  AND COLUMN_NAME = 'product_id'
                """
            ),
            {"schema": settings.mysql_database},
        ).scalar_one()
        if not exists:
            connection.execute(text("ALTER TABLE contracts ADD COLUMN product_id BIGINT NULL"))
            connection.commit()


def initialize_database() -> None:
    try:
        create_database_if_not_exists()
        metadata.create_all(engine)
        ensure_report_document_columns()
        ensure_contract_product_column()
        logger.info("Database tables initialized")
    except SQLAlchemyError:
        logger.exception("Failed to initialize database")
        raise
