from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    groq_api_key: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    database_url: str = "sqlite+aiosqlite:///./codebase_explainer.db"

    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    rate_limit_per_hour: int = 10
    max_file_size_bytes: int = 512_000
    max_total_content_bytes: int = 2_097_152

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()
