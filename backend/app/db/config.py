"""从项目根目录的 .env 或环境变量读取数据库配置。"""

from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class DatabaseSettings(BaseSettings):
    """数据库配置；环境变量的优先级高于 .env 文件。"""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[3] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = Field(default="127.0.0.1", validation_alias="PGHOST", min_length=1)
    port: int = Field(default=5432, validation_alias="PGPORT", ge=1, le=65535)
    database: str = Field(default="shopping_agent", validation_alias="PGDATABASE", min_length=1)
    username: str = Field(default="shopping_agent", validation_alias="PGUSER", min_length=1)
    password: SecretStr = Field(validation_alias="PGPASSWORD", min_length=1)

    @property
    def url(self) -> URL:
        """构造支持特殊字符密码的 psycopg 连接地址。

        :return: SQLAlchemy URL；打印时默认隐藏密码。
        """
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.username,
            password=self.password.get_secret_value(),
            host=self.host,
            port=self.port,
            database=self.database,
        )

