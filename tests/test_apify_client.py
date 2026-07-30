from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.integrations.apify_client import ApifyReviewClient
from app.integrations.review_source_client import ReviewSourceError


def _settings(**overrides):
    # ApifyReviewClient hanya membaca field-field ini dari Settings, jadi cukup
    # SimpleNamespace — tidak perlu membangun dataclass Settings penuh.
    base = dict(
        apify_api_token="tok-123",
        apify_actor_id="compass~google-maps-reviews-scraper",
        apify_base_url="https://api.apify.com/v2",
        apify_timeout_seconds=120,
        fetch_limit_per_location=50,
        google_places_language_code="id",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _location(**overrides):
    base = dict(
        external_place_id="ChIJtest",
        google_reviews_url=None,
        google_maps_url=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


class _FakeResponse:
    def __init__(self, payload, ok=True, status_code=200):
        self._payload = payload
        self.ok = ok
        self.status_code = status_code

    def json(self):
        if isinstance(self._payload, ValueError):
            raise self._payload
        return self._payload


class _FakeSession:
    def __init__(self, response):
        self._response = response
        self.calls = []

    def post(self, url, params=None, json=None, timeout=None):
        self.calls.append(
            {"url": url, "params": params, "json": json, "timeout": timeout}
        )
        return self._response


def test_missing_token_raises():
    client = ApifyReviewClient(_settings(apify_api_token=None))
    with pytest.raises(ReviewSourceError):
        client.fetch_reviews(_location())


def test_missing_place_and_url_raises():
    client = ApifyReviewClient(_settings())
    with pytest.raises(ReviewSourceError):
        client.fetch_reviews(_location(external_place_id=None))


def test_build_actor_input_prefers_place_id():
    client = ApifyReviewClient(_settings())
    payload = client._build_actor_input("ChIJx", "https://maps/x", 25)
    assert payload["placeIds"] == ["ChIJx"]
    assert "startUrls" not in payload
    assert payload["maxReviews"] == 25
    assert payload["language"] == "id"


def test_build_actor_input_falls_back_to_url():
    client = ApifyReviewClient(_settings())
    payload = client._build_actor_input("", "https://maps/x", 10)
    assert payload["startUrls"] == [{"url": "https://maps/x"}]
    assert "placeIds" not in payload


def test_normalize_maps_common_fields():
    item = {
        "reviewId": "r1",
        "name": "Budi",
        "stars": 4,
        "text": "pelayanan bagus",
        "publishedAtDate": "2026-07-01T00:00:00Z",
        "reviewerUrl": "http://profile/budi",
        "likesCount": 3,
        "responseFromOwnerText": "terima kasih",
        "language": "id",
    }
    normalized = ApifyReviewClient._normalize_apify_review(item, "ChIJx")
    assert normalized["source"] == "apify_google_maps"
    assert normalized["external_review_id"] == "r1"
    assert normalized["reviewer_name"] == "Budi"
    assert normalized["rating"] == 4
    assert normalized["review_text"] == "pelayanan bagus"
    assert normalized["review_time"] == "2026-07-01T00:00:00Z"
    assert normalized["owner_response_text"] == "terima kasih"
    assert normalized["like_count"] == 3
    assert normalized["raw_payload"] is item


def test_normalize_anonymous_and_alias_fields():
    # Nama field alternatif (actor berbeda) tetap terbaca; reviewer kosong → Anonymous.
    item = {"id": "r9", "reviewText": "ok", "reviewRating": 5}
    normalized = ApifyReviewClient._normalize_apify_review(item, "ChIJx")
    assert normalized["external_review_id"] == "r9"
    assert normalized["reviewer_name"] == "Anonymous"
    assert normalized["review_text"] == "ok"
    assert normalized["rating"] == 5


def test_fetch_reviews_happy_path():
    items = [
        {"reviewId": "r1", "name": "A", "stars": 5, "text": "x",
         "publishedAtDate": "2026-07-01T00:00:00Z"},
        {"reviewId": "r2", "name": "B", "stars": 2, "text": "y",
         "publishedAtDate": "2026-07-02T00:00:00Z"},
    ]
    session = _FakeSession(_FakeResponse(items))
    client = ApifyReviewClient(_settings(), http_session=session)

    out = client.fetch_reviews(_location(), limit=10)

    assert [r["external_review_id"] for r in out] == ["r1", "r2"]
    assert client.last_metadata["scraped_review_cards"] == 2
    assert client.last_metadata["returned_items"] == 2
    # token dikirim sebagai query param, bukan ditempel di URL; endpoint benar.
    call = session.calls[0]
    assert call["params"]["token"] == "tok-123"
    assert call["url"].endswith("run-sync-get-dataset-items")
    assert "compass~google-maps-reviews-scraper" in call["url"]
    assert call["json"]["placeIds"] == ["ChIJtest"]


def test_fetch_reviews_respects_limit():
    items = [{"reviewId": f"r{i}", "stars": 5, "text": "x"} for i in range(5)]
    session = _FakeSession(_FakeResponse(items))
    client = ApifyReviewClient(_settings(), http_session=session)
    out = client.fetch_reviews(_location(), limit=2)
    assert len(out) == 2


def test_fetch_reviews_http_error_is_retriable_on_5xx():
    session = _FakeSession(
        _FakeResponse(
            {"error": {"type": "server", "message": "boom"}},
            ok=False,
            status_code=503,
        )
    )
    client = ApifyReviewClient(_settings(), http_session=session)
    with pytest.raises(ReviewSourceError) as excinfo:
        client.fetch_reviews(_location())
    assert excinfo.value.retriable is True


def test_fetch_reviews_rejects_non_list_payload():
    session = _FakeSession(_FakeResponse({"error": {"message": "bad input"}}))
    client = ApifyReviewClient(_settings(), http_session=session)
    with pytest.raises(ReviewSourceError):
        client.fetch_reviews(_location())
