from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    nvidia_api_key: str
    # Optional extra keys (comma-separated) to pool alongside nvidia_api_key —
    # each free NVIDIA key has its own per-minute rate limit, so spreading calls
    # across several multiplies the concurrent-analysis headroom for free.
    # Leave empty to run on a single key (existing behavior, unchanged).
    nvidia_api_keys: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "nvidia/nemotron-3-ultra-550b-a55b"

    # Fallback chain — tried in order (this one, then GLM, then DeepSeek below)
    # once the primary NVIDIA key pool is exhausted or rate-limited ("queue is
    # full"). Each is independently optional; leave a key empty to skip that
    # backend entirely.
    fallback_api_key: str = ""
    fallback_base_url: str = "https://integrate.api.nvidia.com/v1"
    fallback_model: str = "moonshotai/kimi-k2.6"

    glm_api_key: str = ""
    glm_base_url: str = "https://integrate.api.nvidia.com/v1"
    glm_model: str = "z-ai/glm-5.2"

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://integrate.api.nvidia.com/v1"
    deepseek_model: str = "deepseek-ai/deepseek-v4-pro"

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

    # Optional — abuse guard on /auth/register. No-op until both are set.
    turnstile_site_key: str = ""
    turnstile_secret_key: str = ""

    # Optional — error tracking. No-op until set.
    sentry_dsn: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def nvidia_api_key_pool(self) -> list[str]:
        """All configured NVIDIA keys, primary first, de-duplicated."""
        extra = [k.strip() for k in self.nvidia_api_keys.split(",") if k.strip()]
        seen = {self.nvidia_api_key}
        pool = [self.nvidia_api_key]
        for k in extra:
            if k not in seen:
                pool.append(k)
                seen.add(k)
        return pool


settings = Settings()
