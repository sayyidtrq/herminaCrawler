"""Projection for the OneBox v1 integration contract.

Separate from ``ReviewService`` on purpose. ReviewService serves the FE and is
free to change shape; this one is pinned to the published contract. The
projection lists every exported field explicitly rather than dumping the model
and popping a blacklist, so a new column on ``Review`` (or a new secret on
``ReviewAnalysis``) can never leak to the consumer by default.
"""

from __future__ import annotations

import base64
import binascii
import json
from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Location, Review, ReviewAnalysis
from app.db.session import get_session_factory

CURSOR_VERSION = 1


class IntegrationRequestError(Exception):
    """Maps 1:1 onto the contract's error envelope."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def _latest_analysis_subquery():
    # Intentionally not imported from review_service: that helper exists to serve
    # the FE, and the contract must not shift if it is retuned for FE reasons.
    return (
        select(
            ReviewAnalysis.review_id.label("review_id"),
            func.max(ReviewAnalysis.id).label("analysis_id"),
        )
        .group_by(ReviewAnalysis.review_id)
        .subquery()
    )


def _analysis_watermark_subquery():
    return (
        select(
            ReviewAnalysis.review_id.label("review_id"),
            func.max(ReviewAnalysis.created_at).label("last_analysis_at"),
        )
        .group_by(ReviewAnalysis.review_id)
        .subquery()
    )


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def encode_cursor(offset: int, location_id: int | None) -> str:
    payload = json.dumps(
        {"v": CURSOR_VERSION, "o": offset, "loc": location_id},
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[int, int | None]:
    padding = "=" * (-len(cursor) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor + padding))
        if payload["v"] != CURSOR_VERSION:
            raise ValueError("cursor version")
        offset = int(payload["o"])
        location_id = payload["loc"]
    except (
        KeyError,
        TypeError,
        ValueError,
        binascii.Error,
        json.JSONDecodeError,
    ) as exc:
        raise IntegrationRequestError(
            400, "INVALID_CURSOR", "Cursor is invalid."
        ) from exc
    if offset < 0 or (location_id is not None and not isinstance(location_id, int)):
        raise IntegrationRequestError(400, "INVALID_CURSOR", "Cursor is invalid.")
    return offset, location_id


class IntegrationReviewService:
    def __init__(
        self,
        company_id: int,
        session_factory: sessionmaker[Session] | None = None,
    ) -> None:
        self.company_id = company_id
        self.session_factory = session_factory or get_session_factory()

    def list_reviews(
        self,
        limit: int,
        cursor: str | None = None,
        updated_since: datetime | None = None,
        location_id: int | None = None,
    ) -> dict:
        offset = 0
        if cursor is not None:
            if updated_since is not None:
                raise IntegrationRequestError(
                    400,
                    "INVALID_CURSOR_CONTEXT",
                    "cursor cannot be combined with updated_since.",
                )
            offset, cursor_location_id = decode_cursor(cursor)
            if location_id is not None and location_id != cursor_location_id:
                raise IntegrationRequestError(
                    400,
                    "INVALID_CURSOR_CONTEXT",
                    "location_id does not match the cursor it was issued with.",
                )
            location_id = cursor_location_id

        snapshot_at = datetime.now(timezone.utc)

        with self.session_factory() as session:
            if location_id is not None:
                owned = session.scalar(
                    select(Location.id).where(
                        Location.id == location_id,
                        Location.company_id == self.company_id,
                    )
                )
                # Same 404 whether the location is absent or owned by another
                # tenant: distinguishing them would confirm its existence.
                if owned is None:
                    raise IntegrationRequestError(
                        404, "LOCATION_NOT_FOUND", "Location not found."
                    )

            latest = _latest_analysis_subquery()
            watermark = _analysis_watermark_subquery()
            statement = (
                select(Review, Location.branch_name, ReviewAnalysis, watermark.c.last_analysis_at)
                .join(Location, Location.id == Review.location_id)
                .outerjoin(latest, latest.c.review_id == Review.id)
                .outerjoin(ReviewAnalysis, ReviewAnalysis.id == latest.c.analysis_id)
                .outerjoin(watermark, watermark.c.review_id == Review.id)
                .where(Review.company_id == self.company_id)
            )
            if location_id is not None:
                statement = statement.where(Review.location_id == location_id)
            if updated_since is not None:
                # sync_updated_at is max(updated_at, created_at, last_analysis_at),
                # and max(a,b,c) >= X exactly when any one of them is >= X. Written
                # as an OR because SQLite has no GREATEST.
                statement = statement.where(
                    or_(
                        Review.updated_at >= updated_since,
                        Review.created_at >= updated_since,
                        watermark.c.last_analysis_at >= updated_since,
                    )
                )

            # Placeholder ordering + offset cursor. CS-02 replaces both with a
            # signed keyset over (sync_updated_at, id); the response shape here is
            # already the final one, so that swap will not move the contract.
            statement = statement.order_by(Review.updated_at.asc(), Review.id.asc())
            rows = session.execute(statement.offset(offset).limit(limit + 1)).all()

        has_more = len(rows) > limit
        rows = rows[:limit]
        items = [self._project(row) for row in rows]
        next_cursor = (
            encode_cursor(offset + len(items), location_id) if has_more else None
        )
        return {
            "items": items,
            "has_more": has_more,
            "next_cursor": next_cursor,
            "snapshot_at": snapshot_at,
        }

    @staticmethod
    def _project(row) -> dict:
        review: Review = row[0]
        branch_name: str = row[1]
        analysis: ReviewAnalysis | None = row[2]
        last_analysis_at: datetime | None = row[3]

        # CS-02 materialises this as an indexed column and backfills it with the
        # same expression; computing it here keeps the contract stable across
        # that migration instead of publishing a field we would later redefine.
        candidates = [review.updated_at, review.created_at]
        if last_analysis_at is not None:
            candidates.append(last_analysis_at)
        sync_updated_at = max(_as_utc(value) for value in candidates if value)

        return {
            "id": review.id,
            "location_id": review.location_id,
            "location": branch_name,
            "source": review.source,
            "external_place_id": review.external_place_id,
            "external_review_id": review.external_review_id,
            "review_hash": review.review_hash,
            "reviewer_name": review.reviewer_name,
            "reviewer_profile_url": review.reviewer_profile_url,
            "rating": review.rating,
            "review_text": review.review_text,
            "review_time": _as_utc(review.review_time),
            "owner_response_text": review.owner_response_text,
            "owner_response_time": _as_utc(review.owner_response_time),
            "updated_at": _as_utc(review.updated_at),
            "sync_updated_at": sync_updated_at,
            "analyzed": analysis is not None,
            "sentiment": analysis.sentiment if analysis else None,
            "sentiment_score": (
                float(analysis.sentiment_score)
                if analysis and analysis.sentiment_score is not None
                else None
            ),
            "issue_category": analysis.issue_category if analysis else None,
            "urgency": analysis.urgency if analysis else None,
            "summary": analysis.summary if analysis else None,
            "recommended_action": analysis.recommended_action if analysis else None,
            "keywords": list(analysis.keywords) if analysis else [],
            "is_potential_viral": bool(analysis.is_potential_viral) if analysis else False,
            "is_patient_safety_issue": (
                bool(analysis.is_patient_safety_issue) if analysis else False
            ),
        }
