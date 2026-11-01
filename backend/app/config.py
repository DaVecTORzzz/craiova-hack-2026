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
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173"
    ppe_observations_per_shift: int = 200   # see OPEN QUESTION Q3
    seed_demo_events: bool = False          # true = insert past events so the shift report is not empty

    # Outbox: o alertă se reîncearcă până e livrată sau până se dovedește că nu se poate.
    outbox_interval_s: float = 0.25
    outbox_backoff_s: str = "1,2,4,8,15,30,60"
    outbox_max_attempts: int = 8

    # Watchdog: o cameră fără heartbeat devine incident. 0 = oprit.
    camera_offline_after_s: int = 90
    watchdog_interval_s: float = 10.0

    # Sumarul turei se refolosește cât timp cifrele nu se schimbă.
    summary_ttl_s: int = 900


@lru_cache
def get_settings() -> Settings:
    return Settings()
