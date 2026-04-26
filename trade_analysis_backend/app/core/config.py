import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Trade Analysis Backend")
    app_version: str = os.getenv("APP_VERSION", "0.1.0")
    api_prefix: str = os.getenv("API_PREFIX", "/api/v1")
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8000"))
    app_reload: bool = os.getenv("APP_RELOAD", "false").lower() == "true"
    mysql_user: str = os.getenv("MYSQL_USER", "root")
    mysql_password: str = os.getenv("MYSQL_PASSWORD", "root")
    mysql_host: str = os.getenv("MYSQL_HOST", "127.0.0.1")
    mysql_port: str = os.getenv("MYSQL_PORT", "3306")
    mysql_database: str = os.getenv("MYSQL_DATABASE", "trade_analysis_mysql")
    sqlalchemy_echo: bool = os.getenv("SQLALCHEMY_ECHO", "false").lower() == "true"
    market_data_kline_provider: str = os.getenv(
        "MARKET_DATA_KLINE_PROVIDER", "tqsdk"
    )
    tqsdk_username: str = os.getenv("TQSDK_USERNAME", "Zhengyu")
    tqsdk_password: str = os.getenv("TQSDK_PASSWORD", "lzy523024")
    tqsdk_web_gui: bool = os.getenv("TQSDK_WEB_GUI", "false").lower() == "true"
    tqsdk_kline_length: int = int(os.getenv("TQSDK_KLINE_LENGTH", "1000"))
    tqsdk_wait_timeout_seconds: int = int(os.getenv("TQSDK_WAIT_TIMEOUT_SECONDS", "15"))

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"
        )

    @property
    def server_database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/?charset=utf8mb4"
        )


settings = Settings()
