from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Reads ./.env (when running from /backend) or ../.env (project root).
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/todo_app"

    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60 * 12
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # OpenRouter (AI assistant)
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o-mini"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Default admin account, created on first start if it does not exist
    admin_email: str = "admin@example.com"
    admin_username: str = "admin"
    admin_password: str = "admin12345"

    # If true the admin chatbot may run INSERT/UPDATE/DELETE/DDL via run_sql.
    # If false run_sql is read-only (it can still change data through the CRUD tools).
    admin_bot_allow_sql_write: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
