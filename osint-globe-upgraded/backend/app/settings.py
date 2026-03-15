from pathlib import Path

from pydantic_settings import BaseSettings

# Resolve .env relative to backend directory so it loads regardless of cwd
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"

class Settings(BaseSettings):
    DATABASE_URL: str

    INGEST_FLIGHTS_SECONDS: int = 10
    INGEST_CONFLICTS_MINUTES: int = 60
    INGEST_PRICES_MINUTES: int = 30
    INGEST_FUEL_MINUTES: int = 60
    INGEST_CAMERAS_MINUTES: int = 5

    FLIGHT_TRACK_RETENTION_HOURS: int = 24
    FUEL_PRICE_RETENTION_HOURS: int = 72
    CAMERAS_RETENTION_DAYS: int = 7
    STATUS_HISTORY_DAYS: int = 7

    AOIS: str = ""
    UCDP_TOKEN: str | None = None
    # Optional: override airplanes.live API base (e.g. "http://api.airplanes.live/v2" if HTTPS fails)
    AIRPLANES_LIVE_BASE_URL: str | None = None
    # OpenSky polling controls to reduce 429/rate-limit pressure while keeping data fresh.
    # Anonymous access should poll less often than authenticated access.
    OPENSKY_MIN_POLL_SECONDS_ANON: int = 300
    OPENSKY_MIN_POLL_SECONDS_AUTH: int = 45
    OPENSKY_RATE_LIMIT_COOLDOWN_SECONDS_ANON: int = 900
    OPENSKY_RATE_LIMIT_COOLDOWN_SECONDS_AUTH: int = 180
    # If latest flight state is fresher than this, skip expensive fallback polling.
    FLIGHTS_STALE_AFTER_SECONDS: int = 180
    # When rate limited, keep showing planes up to this age (seconds) so they don't disappear.
    FLIGHTS_DISPLAY_MAX_AGE_WHEN_RATE_LIMITED_SECONDS: int = 86400  # 24 hours
    OPENSKY_USERNAME: str | None = None
    OPENSKY_PASSWORD: str | None = None

    # Shodan API for IP cameras layer (optional)
    SHODAN_API_KEY: str | None = None

    class Config:
        env_file = str(_ENV_FILE) if _ENV_FILE.exists() else ".env"

settings = Settings()
