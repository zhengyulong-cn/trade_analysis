from sqlmodel import SQLModel

# Import ORM models so SQLModel metadata is populated before create_all.
from app.models.chart_persistence import ChartPersistence  # noqa: F401
from app.models.contract import Contract  # noqa: F401
from app.models.kline_data import KlineData  # noqa: F401
from app.models.product import Product  # noqa: F401
from app.models.product_prompt_profile import ProductPromptProfile  # noqa: F401
from app.models.report_document import ReportDocument  # noqa: F401
from app.models.single_contract_report_analysis import SingleContractReportAnalysis  # noqa: F401
from app.models.trade_record import TradeRecord  # noqa: F401

metadata = SQLModel.metadata
