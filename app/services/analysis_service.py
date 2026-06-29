from __future__ import annotations

import logging

from sqlalchemy import exists, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings
from app.db.models import Review, ReviewAnalysis
from app.db.session import get_session_factory
from app.integrations.gemini_client import GeminiClient, GeminiClientBase
from app.integrations.mock_gemini_client import MockGeminiClient


logger = logging.getLogger(__name__)
ALLOWED_SENTIMENTS = {"positive", "neutral", "negative", "mixed", "unknown"}
ALLOWED_URGENCIES = {"low", "medium", "high", "critical", "unknown"}
ALLOWED_CATEGORIES = {
    "doctor_service",
    "nurse_service",
    "administration",
    "waiting_time",
    "cleanliness",
    "facility",
    "parking",
    "billing",
    "pharmacy",
    "emergency_room",
    "inpatient",
    "customer_service",
    "booking_system",
    "staff_communication",
    "security",
    "food",
    "general_praise",
    "other",
}


class AnalysisService:
    def __init__(
        self,
        session_factory: sessionmaker[Session] | None = None,
        settings: Settings | None = None,
        client: GeminiClientBase | None = None,
    ):
        self.session_factory = session_factory or get_session_factory()
        self.settings = settings or get_settings()
        self.client = client or (
            MockGeminiClient()
            if self.settings.gemini_mode == "mock"
            else GeminiClient(self.settings)
        )

    def analyze_pending(
        self, location_id: int | None = None, rating: int | None = None
    ) -> dict:
        pending_exists = exists(
            select(ReviewAnalysis.id).where(ReviewAnalysis.review_id == Review.id)
        )
        statement = select(Review).where(~pending_exists).order_by(Review.id)
        if location_id is not None:
            statement = statement.where(Review.location_id == location_id)
        if rating is not None:
            statement = statement.where(Review.rating == rating)
        with self.session_factory() as session:
            reviews = list(session.scalars(statement))
            review_data = [self._review_to_dict(review) for review in reviews]
        return self._analyze_items(review_data)

    def rerun_review(self, review_id: int) -> dict:
        with self.session_factory() as session:
            review = session.get(Review, review_id)
            if review is None:
                raise ValueError("Review not found.")
            review_data = self._review_to_dict(review)
        return self._analyze_items([review_data])

    def rerun_location(self, location_id: int) -> dict:
        with self.session_factory() as session:
            reviews = list(
                session.scalars(
                    select(Review)
                    .where(Review.location_id == location_id)
                    .order_by(Review.id)
                )
            )
            review_data = [self._review_to_dict(review) for review in reviews]
        return self._analyze_items(review_data)

    def _analyze_items(self, reviews: list[dict]) -> dict:
        result = {
            "total": len(reviews),
            "success": 0,
            "failed": 0,
            "skipped_empty": 0,
            "sentiments": {
                "positive": 0,
                "neutral": 0,
                "negative": 0,
                "mixed": 0,
                "unknown": 0,
            },
            "errors": [],
        }
        batch_size = max(1, self.settings.analysis_batch_size)
        for start in range(0, len(reviews), batch_size):
            for review in reviews[start : start + batch_size]:
                if not review["review_text"].strip():
                    result["failed"] += 1
                    result["skipped_empty"] += 1
                    result["errors"].append(
                        {
                            "review_id": review["id"],
                            "error": "Review text is empty.",
                        }
                    )
                    continue
                try:
                    raw_result = self.client.analyze_review(review)
                    cleaned = self._validate_result(raw_result)
                    self._store_analysis(review["id"], cleaned, raw_result)
                    result["success"] += 1
                    result["sentiments"][cleaned["sentiment"]] += 1
                except Exception as exc:
                    result["failed"] += 1
                    result["errors"].append(
                        {"review_id": review["id"], "error": str(exc)}
                    )
                    logger.exception("Analysis failed for review %s", review["id"])
        return result

    def _store_analysis(
        self, review_id: int, cleaned: dict, raw_result: dict
    ) -> None:
        with self.session_factory() as session:
            session.add(
                ReviewAnalysis(
                    review_id=review_id,
                    sentiment=cleaned["sentiment"],
                    sentiment_score=cleaned["sentiment_score"],
                    issue_category=cleaned["issue_category"],
                    urgency=cleaned["urgency"],
                    summary=cleaned["summary"],
                    recommended_action=cleaned["recommended_action"],
                    keywords=cleaned["keywords"],
                    is_potential_viral=cleaned["is_potential_viral"],
                    is_patient_safety_issue=cleaned[
                        "is_patient_safety_issue"
                    ],
                    model_name=self.client.model_name,
                    prompt_version=self.settings.prompt_version,
                    raw_response=raw_result,
                )
            )
            session.commit()

    @staticmethod
    def _review_to_dict(review: Review) -> dict:
        return {
            "id": review.id,
            "rating": review.rating,
            "review_text": review.review_text,
            "reviewer_name": review.reviewer_name,
            "review_time": review.review_time,
            "location_id": review.location_id,
        }

    @staticmethod
    def _validate_result(result: dict) -> dict:
        sentiment = str(result.get("sentiment") or "unknown").lower()
        if sentiment not in ALLOWED_SENTIMENTS:
            sentiment = "unknown"
        urgency = str(result.get("urgency") or "unknown").lower()
        if urgency not in ALLOWED_URGENCIES:
            urgency = "unknown"
        category = str(result.get("issue_category") or "other").lower()
        if category not in ALLOWED_CATEGORIES:
            category = "other"
        try:
            score = float(result.get("sentiment_score", 0))
        except (TypeError, ValueError):
            score = 0.0
        score = max(0.0, min(1.0, score))
        keywords = result.get("keywords")
        if not isinstance(keywords, list):
            keywords = []
        return {
            "sentiment": sentiment,
            "sentiment_score": score,
            "issue_category": category,
            "urgency": urgency,
            "summary": str(result.get("summary") or ""),
            "recommended_action": str(result.get("recommended_action") or ""),
            "keywords": [str(keyword) for keyword in keywords],
            "is_potential_viral": bool(result.get("is_potential_viral", False)),
            "is_patient_safety_issue": bool(
                result.get("is_patient_safety_issue", False)
            ),
        }

