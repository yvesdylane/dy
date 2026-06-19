from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./dy.db"

    telegram_token: str = ""
    telegram_group_id: str = ""
    mini_app_url: str = "not_yet_there"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
