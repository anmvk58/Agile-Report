from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Agile Daily Report"
    database_url: str = "sqlite:///./agile_report.db"
    jwt_secret_key: str = "development-only-change-me"
    access_token_expire_minutes: int = 480
    admin_initial_password: str = "ChangeMe123!"
    timezone: str = "Asia/Ho_Chi_Minh"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()

