from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CAHMA Edge"
    runtime_version: str = "v1"
    api_key: str = "change-me-before-deployment"
    database_path: Path = Path("./data/cahma.db")
    deep_budget: int = 1
    deep_dwell_seconds: float = 5.0
    cooldown_seconds: float = 4.0
    decision_interval_seconds: float = 1.0
    stale_frame_seconds: float = 2.0
    coordinator_feed_count: int = 3
    coordinator_collect_ms: int = 1000
    deep_timeout_seconds: float = 4.0
    environment: str = "development"
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    gate_checkpoint: Path | None = None
    scalar_router_checkpoint: Path | None = Path("./checkpoints/router-review1-v2.joblib")
    scalar_router_sha256: str = (
        "a098669583c43b93796f0d0fed1d1581183bada5c3852def14cbe74239dc8509"
    )
    formal_runs_path: Path = Path("./data/formal-runs")
    model_config = SettingsConfigDict(env_file=".env", env_prefix="CAHMA_")


settings = Settings()


def origins() -> list[str]:
    return [origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()]
