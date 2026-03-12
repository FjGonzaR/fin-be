from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"  # "local" | "production"

    # Database
    database_url: str = "postgresql://finanzas:finanzas123@localhost:5432/finanzas_db"
    direct_database_url: str = ""  # Supabase Postgres — used when app_env=production

    debug: bool = True
    upload_dir: str = "./data/uploads"

    # Supabase Storage
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_bucket: str = "source-files"
    supabase_upload_prefix: str = "uploads/test"

    # CORS
    allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:4173"]

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_expire_minutes: int = 60 * 8  # 8 hours

    # LLM / OpenRouter
    llm_provider: str = "openrouter"
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o-mini"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_confidence_threshold: float = 0.70

    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    @property
    def effective_database_url(self) -> str:
        if self.app_env == "production" and self.direct_database_url:
            return self.direct_database_url
        return self.database_url


settings = Settings()
