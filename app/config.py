from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _as_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer.") from exc


def _as_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    app_env: str
    app_name: str
    log_level: str
    export_dir: Path
    database_url: str
    review_source_mode: str
    google_maps_api_key: str | None
    google_places_language_code: str
    google_places_region_code: str
    gemini_mode: str
    gemini_api_key: str | None
    gemini_model: str
    analysis_provider: str
    openrouter_api_key: str | None
    openrouter_model: str
    fetch_limit_per_location: int
    fetch_timeout_seconds: int
    fetch_max_retry: int
    selenium_headless: bool
    selenium_default_target_reviews: int
    selenium_max_target_reviews: int
    selenium_scroll_delay_seconds: int
    selenium_max_scroll_attempts: int
    selenium_wait_timeout_seconds: int
    selenium_user_data_dir: Path | None
    analysis_batch_size: int
    prompt_version: str
    page_size: int
    show_raw_payload: bool

    def ensure_export_dir(self) -> Path:
        self.export_dir.mkdir(parents=True, exist_ok=True)
        return self.export_dir


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    review_mode = os.getenv("REVIEW_SOURCE_MODE", "mock").strip().lower()
    if review_mode not in {
        "mock",
        "google_places",
        "google_business_profile",
        "third_party",
        "selenium",
    }:
        raise ValueError(
            "REVIEW_SOURCE_MODE must be mock, google_places, "
            "google_business_profile, third_party, or selenium."
        )

    gemini_mode = os.getenv("GEMINI_MODE", "mock").strip().lower()
    if gemini_mode not in {"mock", "real"}:
        raise ValueError("GEMINI_MODE must be mock or real.")

    analysis_provider = os.getenv("ANALYSIS_PROVIDER", "gemini").strip().lower()
    if analysis_provider not in {"mock", "gemini", "openrouter"}:
        raise ValueError("ANALYSIS_PROVIDER must be mock, gemini, or openrouter.")

    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise ValueError("DATABASE_URL is required in .env.")

    export_value = os.getenv("EXPORT_DIR", "exports").strip() or "exports"
    export_dir = Path(export_value)
    if not export_dir.is_absolute():
        export_dir = BASE_DIR / export_dir

    selenium_profile_value = os.getenv(
        "SELENIUM_USER_DATA_DIR", ".selenium-profile"
    ).strip()
    selenium_user_data_dir = (
        Path(selenium_profile_value) if selenium_profile_value else None
    )
    if selenium_user_data_dir and not selenium_user_data_dir.is_absolute():
        selenium_user_data_dir = BASE_DIR / selenium_user_data_dir

    return Settings(
        app_env=os.getenv("APP_ENV", "local").strip(),
        app_name=os.getenv("APP_NAME", "Hermina Review Intelligence").strip(),
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
        export_dir=export_dir,
        database_url=database_url,
        review_source_mode=review_mode,
        google_maps_api_key=os.getenv("GOOGLE_MAPS_API_KEY") or None,
        google_places_language_code=os.getenv(
            "GOOGLE_PLACES_LANGUAGE_CODE", "id"
        ).strip(),
        google_places_region_code=os.getenv(
            "GOOGLE_PLACES_REGION_CODE", "ID"
        ).strip(),
        gemini_mode=gemini_mode,
        gemini_api_key=os.getenv("GEMINI_API_KEY") or None,
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip(),
        analysis_provider=analysis_provider,
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY") or None,
        openrouter_model=os.getenv(
            "OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct"
        ).strip(),
        fetch_limit_per_location=_as_int("FETCH_LIMIT_PER_LOCATION", 50),
        fetch_timeout_seconds=_as_int("FETCH_TIMEOUT_SECONDS", 30),
        fetch_max_retry=_as_int("FETCH_MAX_RETRY", 3),
        selenium_headless=_as_bool("SELENIUM_HEADLESS", False),
        selenium_default_target_reviews=_as_int(
            "SELENIUM_DEFAULT_TARGET_REVIEWS", 100
        ),
        selenium_max_target_reviews=_as_int(
            "SELENIUM_MAX_TARGET_REVIEWS", 300
        ),
        selenium_scroll_delay_seconds=max(
            2, _as_int("SELENIUM_SCROLL_DELAY_SECONDS", 2)
        ),
        selenium_max_scroll_attempts=min(
            100, max(1, _as_int("SELENIUM_MAX_SCROLL_ATTEMPTS", 100))
        ),
        selenium_wait_timeout_seconds=_as_int(
            "SELENIUM_WAIT_TIMEOUT_SECONDS", 20
        ),
        selenium_user_data_dir=selenium_user_data_dir,
        analysis_batch_size=_as_int("ANALYSIS_BATCH_SIZE", 20),
        prompt_version=os.getenv("PROMPT_VERSION", "v1").strip(),
        page_size=_as_int("PAGE_SIZE", 20),
        show_raw_payload=_as_bool("SHOW_RAW_PAYLOAD", False),
    )
