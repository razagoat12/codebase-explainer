from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    nvidia_api_key: str
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "nvidia/nemotron-3-ultra-550b-a55b"

    # Fallback LLM — used only if the primary model call raises (timeout,
    # rate limit, outage). Leave fallback_api_key empty to disable.
    fallback_api_key: str = ""
    fallback_base_url: str = "https://integrate.api.nvidia.com/v1"
    fallback_model: str = "moonshotai/kimi-k2.6"

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    database_url: str = "sqlite+aiosqlite:///./codebase_explainer.db"

    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    rate_limit_per_hour: int = 10
    max_file_size_bytes: int = 512_000
    max_total_content_bytes: int = 2_097_152

    # Queue settings — opt-in. Defaults to FastAPI BackgroundTasks (no Redis needed).
    use_celery: bool = False
    redis_url: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()
