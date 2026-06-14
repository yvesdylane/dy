from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./dy.db"

    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""

    telegram_token: str = ""
    mini_app_url: str = "not_yet_there"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
