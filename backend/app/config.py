from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_provider: str = "groq"
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    github_token: str = ""
    webhook_secret: str = ""
    max_chunk_chars: int = 12000
    simulate_llm_failure: bool = False
    llm_max_retries: int = 3
    retry_base_delay: float = 1.0
    standards_path: str = "../.review-standards.yml"


settings = Settings()