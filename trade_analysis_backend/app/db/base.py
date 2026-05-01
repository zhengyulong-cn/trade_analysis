from sqlmodel import SQLModel

# Import ORM models so SQLModel metadata is populated before create_all.
from app.models.chart_persistence import ChartPersistence  # noqa: F401
from app.models.contract import Contract  # noqa: F401
from app.models.kline_data import KlineData  # noqa: F401

metadata = SQLModel.metadata
