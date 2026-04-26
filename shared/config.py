from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    app_name: str = "Transport Booking API"
    env: str = "development"
    secret_key: str = "change_me"
    access_token_expire_minutes: int = 120
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "transport_booking"
    redis_url: str = "redis://localhost:6379/0"
    smtp_enabled: bool = False
    smtp_host: str = "127.0.0.1"
    smtp_port: int = 1025
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@quickhaul.local"
    smtp_from_name: str = "Quick Haul Transits"
    smtp_use_tls: bool = False
    smtp_use_starttls: bool = False
    frontend_url: str = "http://localhost:5173"

    # Service URLs (for inter-service communication)
    auth_service_url: str = "http://127.0.0.1:8002"
    booking_service_url: str = "http://127.0.0.1:8003"
    notification_service_url: str = "http://127.0.0.1:8004"
    location_service_url: str = "http://127.0.0.1:8001"
    otp_service_url: str = "http://127.0.0.1:8005"

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent / ".env"),
        env_file_encoding="utf-8", 
        extra="ignore"
    )


settings = Settings()
