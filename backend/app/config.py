from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET = "change-me-in-production"


class Settings(BaseSettings):
    # Reads ./.env (when running from /backend) or ../.env (project root).
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    # "production" turns on strict startup checks (see main.py)
    app_env: str = "development"

    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/todo_app"

    secret_key: str = DEFAULT_SECRET
    access_token_expire_minutes: int = 60 * 12
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # OpenRouter (AI assistant)
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o-mini"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Default admin account, created on first start if no admin exists
    admin_email: str = "admin@example.com"
    admin_username: str = "admin"
    admin_password: str = "admin12345"

    # If true the admin chatbot may run INSERT/UPDATE/DELETE via run_sql (still guarded).
    # If false run_sql is read-only (it can still change data through the CRUD tools).
    admin_bot_allow_sql_write: bool = False

    # ---- Guardrails ----
    allow_registration: bool = True           # false: only admins can create accounts
    register_per_hour_per_ip: int = 10
    login_max_failures: int = 5               # failed logins per (IP + account) ...
    login_lockout_seconds: int = 900          # ... within this window => temporary lock
    chat_per_minute: int = 10                 # chat messages per user per minute
    chat_daily_limit_user: int = 50           # chat messages per user per day (protects your OpenRouter credit)
    chat_daily_limit_admin: int = 200
    max_tool_calls_per_message: int = 10      # actions the bot may take for one message
    max_todos_per_user: int = 500
    sql_statement_timeout_ms: int = 5000

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
