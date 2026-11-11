from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RuntimeSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parents[3] / '.env', extra='ignore')
    redis_url: str | None = None
    redis_prefix: str = 'shopping'
    session_ttl_seconds: int = Field(default=1800, ge=60)
    rate_limit_per_minute: int = Field(default=60, ge=1)
    otel_exporter_otlp_endpoint: str | None = None
