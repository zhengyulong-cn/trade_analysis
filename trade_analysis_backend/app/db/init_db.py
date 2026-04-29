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


def drop_obsolete_contract_columns() -> None:
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
            connection.execute(
                text("ALTER TABLE contracts DROP COLUMN auto_load_segments")
            )
            logger.info("Column dropped: contracts.auto_load_segments")
        connection.commit()


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


def drop_obsolete_chart_persistence_columns() -> None:
    with engine.connect() as connection:
        for column_name in ("chart_content", "settings_content"):
            column_exists = connection.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.columns "
                    "WHERE table_schema = :database_name "
                    "AND table_name = 'chart_persistences' "
                    "AND column_name = :column_name"
                ),
                {
                    "database_name": settings.mysql_database,
                    "column_name": column_name,
                },
            ).scalar_one()

            if not column_exists:
                continue

            connection.execute(
                text(
                    "ALTER TABLE chart_persistences "
                    f"DROP COLUMN {column_name}"
                )
            )
            logger.info("Column dropped: chart_persistences.%s", column_name)

        connection.commit()


def drop_obsolete_strategy_analysis_table() -> None:
    with engine.connect() as connection:
        table_exists = connection.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = :database_name "
                "AND table_name = 'strategy_analysis'"
            ),
            {"database_name": settings.mysql_database},
        ).scalar_one()
        if table_exists:
            connection.execute(text("DROP TABLE strategy_analysis"))
            logger.info("Table dropped: strategy_analysis")
        connection.commit()


def initialize_database() -> None:
    try:
        create_database_if_not_exists()
        metadata.create_all(engine)
        drop_obsolete_chart_persistence_columns()
        drop_obsolete_contract_columns()
        drop_obsolete_strategy_analysis_table()
        ensure_contract_is_favorite_column()
        logger.info("Database tables initialized")
    except SQLAlchemyError:
        logger.exception("Failed to initialize database")
        raise
