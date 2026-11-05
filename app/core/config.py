from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://jjo:jjo@localhost:5432/jjo"

    # AI 피드백(LLM). 성능이 부족하면 .env의 GEMINI_MODEL만 바꾸면 된다.
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"


settings = Settings()
