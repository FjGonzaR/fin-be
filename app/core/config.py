from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql://finanzas:finanzas123@localhost:5432/finanzas_db"
    debug: bool = True
    upload_dir: str = "./data/uploads"

    # LLM / OpenRouter
    llm_provider: str = "openrouter"
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o-mini"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_confidence_threshold: float = 0.70

    model_config = SettingsConfigDict(env_file=".env", extra="allow")


settings = Settings()
