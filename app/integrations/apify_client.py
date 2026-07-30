from __future__ import annotations

import logging

import requests

from app.config import Settings
from app.db.models import Location
from app.integrations.review_source_client import (
    ReviewSourceClient,
    ReviewSourceError,
)


logger = logging.getLogger(__name__)


class ApifyReviewClient(ReviewSourceClient):
    """Menarik review Google Maps lewat Apify actor.

    Ini "paket scraper" alternatif Selenium: dari sisi OneBox tidak kelihatan —
    hasilnya tetap keluar lewat kontrak review yang sama. Memakai REST API Apify
    langsung (tanpa SDK tambahan, cukup `requests` seperti GooglePlacesClient),
    via endpoint ``run-sync-get-dataset-items``: satu panggilan menjalankan actor
    sampai selesai lalu mengembalikan item dataset-nya.

    Actor id dan skema field-nya sengaja configurable + toleran — tiap actor
    Apify punya nama field berbeda. Default menyasar Google Maps Reviews scraper
    (input ``placeIds`` + ``maxReviews``). Kalau memakai actor lain, sesuaikan
    ``APIFY_ACTOR_ID`` dan, bila perlu, ``_build_actor_input``.
    """

    source_name = "apify_google_maps"

    def __init__(
        self, settings: Settings, http_session: requests.Session | None = None
    ):
        self.settings = settings
        self.http_session = http_session or requests.Session()
        self.last_metadata: dict = {}

    def fetch_reviews(self, location: Location, limit: int = 50) -> list[dict]:
        token = (self.settings.apify_api_token or "").strip()
        if not token:
            raise ReviewSourceError(
                "Apify API token is missing. Set APIFY_API_TOKEN in your .env."
            )

        actor = (self.settings.apify_actor_id or "").strip()
        if not actor:
            raise ReviewSourceError(
                "Apify actor id is missing. Set APIFY_ACTOR_ID in your .env."
            )

        place_id = (location.external_place_id or "").strip()
        review_url = (
            (getattr(location, "google_reviews_url", None) or "").strip()
            or (getattr(location, "google_maps_url", None) or "").strip()
        )
        if not place_id and not review_url:
            raise ReviewSourceError(
                "Location needs an external_place_id or a Google Maps URL "
                "for the Apify scraper."
            )

        effective_limit = (
            max(0, int(limit or 0)) or self.settings.fetch_limit_per_location
        )
        actor_input = self._build_actor_input(place_id, review_url, effective_limit)

        # run-sync-get-dataset-items menjalankan actor lalu langsung mengembalikan
        # item dataset. Query `timeout` (detik) membatasi lama run di sisi Apify;
        # HTTP timeout dibuat sedikit lebih longgar agar kegagalan datang sebagai
        # error Apify yang jelas, bukan timeout klien duluan.
        base = (self.settings.apify_base_url or "https://api.apify.com/v2").rstrip("/")
        url = f"{base}/acts/{actor}/run-sync-get-dataset-items"
        run_timeout = max(30, int(self.settings.apify_timeout_seconds))
        params = {"token": token, "timeout": run_timeout, "format": "json"}

        try:
            response = self.http_session.post(
                url,
                params=params,
                json=actor_input,
                timeout=run_timeout + 30,
            )
        except (requests.Timeout, requests.ConnectionError) as exc:
            raise ReviewSourceError(
                f"Apify request failed: {exc}", retriable=True
            ) from exc
        except requests.RequestException as exc:
            raise ReviewSourceError(f"Apify request failed: {exc}") from exc

        if not response.ok:
            retriable = response.status_code in {408, 429, 500, 502, 503, 504}
            raise ReviewSourceError(
                self._error_message(response), retriable=retriable
            )

        try:
            items = response.json()
        except ValueError as exc:
            raise ReviewSourceError(
                "Apify returned an invalid JSON response."
            ) from exc

        # Sukses selalu berupa array item. Kalau Apify balas objek (mis. error
        # dengan HTTP 2xx), jangan diperlakukan sebagai daftar review.
        if not isinstance(items, list):
            message = ""
            if isinstance(items, dict):
                error = items.get("error")
                if isinstance(error, dict):
                    message = error.get("message") or ""
                message = message or str(items)[:200]
            raise ReviewSourceError(
                f"Apify returned an unexpected payload: {message}"
            )

        reviews = [
            self._normalize_apify_review(item, place_id)
            for item in items
            if isinstance(item, dict)
        ]
        if effective_limit:
            reviews = reviews[:effective_limit]

        self.last_metadata = {
            "actor_id": actor,
            "target_review_count": effective_limit,
            "returned_items": len(items),
            "scraped_review_cards": len(reviews),
            "source": self.source_name,
        }
        logger.info(
            "Apify actor %s returned %s items (%s reviews) for place %s",
            actor,
            len(items),
            len(reviews),
            place_id or review_url,
        )
        return reviews

    def _build_actor_input(
        self, place_id: str, review_url: str, limit: int
    ) -> dict:
        """Input actor Apify.

        Google Maps Reviews scraper populer (mis. compass) menerima ``placeIds``
        atau ``startUrls`` plus ``maxReviews``. Sesuaikan bila actor pilihanmu
        memakai nama field berbeda.
        """
        actor_input: dict = {
            "maxReviews": limit,
            "reviewsSort": "newest",
            "language": self.settings.google_places_language_code or "id",
        }
        if place_id:
            actor_input["placeIds"] = [place_id]
        elif review_url:
            actor_input["startUrls"] = [{"url": review_url}]
        return actor_input

    @staticmethod
    def _first(item: dict, *keys):
        """Ambil nilai non-kosong pertama dari beberapa alias field."""
        for key in keys:
            value = item.get(key)
            if value not in (None, ""):
                return value
        return None

    @classmethod
    def _normalize_apify_review(cls, item: dict, place_id: str) -> dict:
        # Nama field berbeda antar actor — coba alias yang umum. FetchService
        # yang akan mem-parse tanggal, memvalidasi rating, dan menghasilkan hash.
        return {
            "source": cls.source_name,
            "external_place_id": cls._first(item, "placeId", "place_id")
            or place_id
            or None,
            "external_review_id": cls._first(item, "reviewId", "review_id", "id"),
            "reviewer_name": cls._first(item, "name", "reviewerName", "author")
            or "Anonymous",
            "reviewer_profile_url": cls._first(
                item, "reviewerUrl", "reviewerProfileUrl"
            ),
            "reviewer_photo_url": cls._first(
                item, "reviewerPhotoUrl", "reviewerAvatar"
            ),
            "reviewer_total_reviews": cls._first(
                item, "reviewerNumberOfReviews", "reviewsCount"
            ),
            "rating": cls._first(item, "stars", "rating", "reviewRating"),
            "review_text": cls._first(item, "text", "reviewText", "review") or "",
            "review_time": cls._first(
                item,
                "publishedAtDate",
                "publishAtDate",
                "publishedAt",
                "reviewDate",
            ),
            "review_relative_time": cls._first(
                item, "publishAt", "reviewRelativeTime"
            ),
            "language": cls._first(item, "language", "originalLanguage")
            or "unknown",
            "like_count": cls._first(item, "likesCount", "likes") or 0,
            "owner_response_text": cls._first(
                item, "responseFromOwnerText", "ownerResponseText"
            ),
            "owner_response_time": cls._first(
                item, "responseFromOwnerDate", "ownerResponseDate"
            ),
            "raw_payload": item,
        }

    @staticmethod
    def _error_message(response: requests.Response) -> str:
        default = f"Apify API error (HTTP {response.status_code})."
        try:
            payload = response.json()
        except ValueError:
            return default
        error = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(error, dict):
            message = error.get("message")
            error_type = error.get("type")
            if message and error_type:
                return f"Apify API error [{error_type}]: {message}"
            if message:
                return str(message)
        return default
