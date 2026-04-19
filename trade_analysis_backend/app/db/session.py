from collections.abc import Generator

from sqlmodel import Session, create_engine

from app.core.config import settings

engine = create_engine(settings.database_url, echo=settings.sqlalchemy_echo)
server_engine = create_engine(
    settings.server_database_url, echo=settings.sqlalchemy_echo
)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
