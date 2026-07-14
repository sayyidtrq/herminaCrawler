from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Only ever reachable when APP_ENV=local; get_settings refuses to start without a
# real INTEGRATION_CURSOR_SECRET anywhere else.
LOCAL_CURSOR_SECRET_FALLBACK = "local-only-cursor-secret-never-deploy-this"


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


def _as_list(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_env: str
    app_name: str
    log_level: str
    export_dir: Path
    database_url: str
    cors_allowed_origins: tuple[str, ...]
    review_source_mode: str
    google_maps_api_key: str | None
    google_places_language_code: str
    google_places_region_code: str
    local_llm_base_url: str
    local_llm_api_key: str | None
    local_llm_model: str
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
    # Default is for tests that build Settings directly; get_settings() still
    # refuses to boot outside local without a real INTEGRATION_CURSOR_SECRET.
    integration_cursor_secret: str = LOCAL_CURSOR_SECRET_FALLBACK

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

    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise ValueError("DATABASE_URL is required in .env.")

    app_env = os.getenv("APP_ENV", "local").strip()
    integration_cursor_secret = os.getenv("INTEGRATION_CURSOR_SECRET", "").strip()
    if not integration_cursor_secret:
        # This secret signs the pagination cursors. A shared or guessable value
        # lets a caller forge a cursor for another tenant, so anywhere with real
        # data must refuse to boot without its own.
        if app_env.lower() != "local":
            raise ValueError(
                "INTEGRATION_CURSOR_SECRET is required when APP_ENV is not local. "
                "Generate a unique value per environment."
            )
        integration_cursor_secret = LOCAL_CURSOR_SECRET_FALLBACK

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
        app_env=app_env,
        app_name=os.getenv("APP_NAME", "Review System").strip(),
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
        export_dir=export_dir,
        database_url=database_url,
        cors_allowed_origins=tuple(
            _as_list(
                "CORS_ALLOWED_ORIGINS",
                ["http://localhost:3000", "http://127.0.0.1:3000"],
            )
        ),
        review_source_mode=review_mode,
        google_maps_api_key=os.getenv("GOOGLE_MAPS_API_KEY") or None,
        google_places_language_code=os.getenv(
            "GOOGLE_PLACES_LANGUAGE_CODE", "id"
        ).strip(),
        google_places_region_code=os.getenv(
            "GOOGLE_PLACES_REGION_CODE", "ID"
        ).strip(),
        local_llm_base_url=os.getenv("LOCAL_LLM_BASE_URL", "http://192.168.1.115:11434/v1/").strip(),
        local_llm_api_key=os.getenv("LOCAL_LLM_API_KEY", "ollama") or None,
        local_llm_model=os.getenv("LOCAL_LLM_MODEL", "qwen2.5:7b").strip(),
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
        integration_cursor_secret=integration_cursor_secret,
    )
