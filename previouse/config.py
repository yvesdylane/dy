from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./dy.db"

    telegram_token: str = ""
    telegram_group_id: str = ""
    mini_app_url: str = "not_yet_there"

    super_admin_telegram_id: str = ""
    super_admin_name: str = "Super"
    super_admin_surname: str = "Admin"
    super_admin_phone: str = ""
    super_admin_department: str = "SWE"

    allow_dev_telegram_id_auth: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
