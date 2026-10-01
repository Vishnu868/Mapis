"""Runtime settings. Trust scale everywhere: 0 = malicious, 1 = safe."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="MAPIS_", extra="ignore")

    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "sqlite+aiosqlite:///./mapis.db"
    frontend_url: str = "http://localhost:3000"
    model_path: str = "artifacts/mapis_detector"  # falls back to the regex detector when absent

    # Tier boundaries on the trust score: PASS >= pass_at > FLAG >= flag_at > QUARANTINE >= quarantine_at > BLOCK
    pass_at: float = 0.75
    flag_at: float = 0.50
    quarantine_at: float = 0.25

    window_hops: int = 4          # causal context hops given to the classifier (plus the user's goal)
    session_ttl: int = 3600       # seconds of inactivity before a session expires
    sensitivity_step: float = 0.15  # risk boost per FLAG in the session
    sensitivity_cap: float = 0.60
    fail_mode: str = "closed"     # "closed": errors block; "open": errors pass (with alert)

    # Noisy-OR weights of the stateful features (the transformer score has weight 1)
    w_provenance: float = 0.80
    w_instruction: float = 0.50
    w_drift: float = 0.15
    w_behaviour: float = 0.15


@lru_cache
def get_settings() -> Settings:
    return Settings()
