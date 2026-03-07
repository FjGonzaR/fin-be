from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql://finanzas:finanzas123@localhost:5432/finanzas_db"
    debug: bool = True
    upload_dir: str = "./data/uploads"

    # Supabase Storage
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_bucket: str = "source-files"

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


settings = Settings()
