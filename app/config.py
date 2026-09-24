"""
Application Configuration Settings
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    DATABASE_URL: str = "sqlite:///./patients.db"

    # Telephony & Voice Configuration
    VAPI_API_KEY: str = ""
    VAPI_PHONE_NUMBER_ID: str = ""
    OPENAI_API_KEY: str = ""
    WEBHOOK_BASE_URL: str = ""

    # Supabase Configuration
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
