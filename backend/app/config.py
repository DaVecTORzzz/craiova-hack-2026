from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    database_url: str = "sqlite:///./safesight.db"
    snapshot_dir: str = "./snapshots"
    snapshot_base_url: str = ""          # prefix for snapshot_url; empty = same origin
    retention_days: int = 7
    edge_token: str = "dev-edge-token"
    default_escalate_after_s: int = 30   # fallback only; zones decide
    slack_webhook_url: str = ""          # empty = notifications are simulated (logged, notified_at stays null)
    app_base_url: str = "http://localhost:5173"  # used to build the incident link in Slack
    use_mock: bool = False
    mock_interval_s: float = 5.0
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    ppe_observations_per_shift: int = 200   # see OPEN QUESTION Q3
    seed_demo_events: bool = False          # true = insert past events so the shift report is not empty


@lru_cache
def get_settings() -> Settings:
    return Settings()
