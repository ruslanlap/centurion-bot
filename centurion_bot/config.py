from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    telegram_bot_token: str
    admin_id: int
    bot_name: str = "centurion_bot"

    database_url: str = f"sqlite+aiosqlite:///{Path('data') / 'centurion.db'}"

    log_level: str = "INFO"

    webhook_url: str = ""
    webhook_host: str = "0.0.0.0"
    webhook_port: int = 8080
    webhook_secret: str = ""

    daily_reminder_hour: int = 8
    daily_reminder_minute: int = 0
    weekly_review_weekday: int = 6  # 0=Mon … 6=Sun
    weekly_review_hour: int = 18
    weekly_review_minute: int = 0


settings = Settings()  # type: ignore[call-arg]
