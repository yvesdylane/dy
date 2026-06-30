from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str

    turso_auth_token: str = Field(
        alias="TURSO_AUTH_TOKEN"
    )

    bot_token: str = Field(
        alias="BOT_TOKEN"
    )
    telegram_group_id: int
    mini_app_url: str

    port: int = 8000

    allow_dev_telegram_id_auth: bool = False

    super_admin_telegram_id: int
    super_admin_name: str
    super_admin_surname: str
    super_admin_gender: str
    super_admin_phone: str
    super_admin_department: str
    super_admin_dob: str

    session_secret: str

    recognition_threshold: float = 0.4

    face_model_name: str = "insightface-arcface"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
settings = Settings()