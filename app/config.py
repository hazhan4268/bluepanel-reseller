from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'BluePanel Reseller'
    environment: str = 'production'
    debug: bool = False
    api_secret_key: str = ''

    database_url: str = 'postgresql+asyncpg://bluepanel:bluepanel@postgres:5432/bluepanel'
    redis_url: str = 'redis://redis:6379/0'
    auto_create_tables: bool = False

    telegram_bot_token: str = ''

    pasarguard_base_url: str = ''
    pasarguard_dashboard_url: str = ''
    pasarguard_admin_username: str = ''
    pasarguard_admin_secret: str = ''
    default_pasarguard_role_id: int = 0

    default_price_per_gb_toman: int = Field(default=5000, ge=0)
    default_debt_limit_toman: int = Field(default=50000, ge=0)
    low_balance_threshold_toman: int = Field(default=20000, ge=0)
    usage_poll_interval_seconds: int = Field(default=300, ge=30)

    disable_admin_when_debt_limit_reached: bool = True
    disable_users_when_debt_limit_reached: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
