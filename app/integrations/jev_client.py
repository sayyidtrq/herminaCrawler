from __future__ import annotations

import logging

import httpx

from app.config import Settings
from app.integrations.gemini_client import GeminiClientBase

logger = logging.getLogger(__name__)

TAXONOMY_CATEGORIES = {
    "professional service": "professional_service",
    "staff service": "staff_service",
    "registration": "administration",
    "waiting time": "waiting_time",
    "service speed": "waiting_time",
    "cleanliness": "cleanliness",
    "facilities": "facility",
    "parking": "parking",
    "price & value": "price_value",
    "billing & payment": "billing_payment",
    "availability": "availability",
    "delivery & fulfillment": "delivery_fulfillment",
    "customer service": "customer_service",
    "service quality": "service_quality",
    "booking & ordering": "booking_ordering",
    "digital experience": "digital_experience",
    "security & safety": "safety_security",
    "food & beverage": "food_beverage",
    "product quality": "product_quality",
}


class JevAiClient(GeminiClientBase):
    def __init__(
        self, settings: Settings, *, http_client: httpx.Client | None = None
    ) -> None:
        self.settings = settings
        self.model_name = settings.typesafe_model
        self.last_usage: dict[str, int] = {}
        headers = {}
        if settings.typesafe_api_key:
            headers["Authorization"] = f"Bearer {settings.typesafe_api_key}"
        self._http = http_client or httpx.Client(
            base_url=settings.typesafe_base_url.rstrip("/"),
            timeout=settings.typesafe_timeout_seconds,
            headers=headers,
        )

    def list_models(self) -> list[str]:
        response = self._http.get("/v1/models")
        if response.status_code >= 400:
            raise RuntimeError(
                f"TypeSafe returned HTTP {response.status_code}: {response.text}"
            )
        return [str(model["name"]) for model in response.json().get("models", [])]

    def analyze_review(self, review: dict) -> dict:
        text = review.get("review_text") or ""

        payload = {
            "state": text,
            "model": self.model_name,
            "questions": {
                "sentiment": {
                    "type": "choice",
                    "instructions": "What is the primary sentiment of this review?",
                    "criteria": {
                        "positive": "The customer or user is happy or satisfied with the service or product.",
                        "negative": "The customer or user is unhappy, complaining, or angry.",
                        "neutral": "The review is objective or lacks strong emotion.",
                        "mixed": "The review contains both positive and negative points.",
                    },
                },
                "category": {
                    "type": "choice",
                    "instructions": "Which department, aspect, or service category is this review primarily about?",
                    "criteria": {
                        "product quality": "Product quality, durability, condition, or performance",
                        "service quality": "Overall service quality and reliability",
                        "professional service": "Professional or specialist service and advice",
                        "staff service": "Staff attitude, responsiveness, friendliness, or courtesy",
                        "registration": "Registration, front desk, check-in, or administration",
                        "waiting time": "Waiting times, queues, service speed, delays",
                        "cleanliness": "Cleanliness of the premises, facility, or location",
                        "facilities": "Facilities, rooms, building, amenities",
                        "parking": "Parking area, vehicle access",
                        "price & value": "Price, cost, and value for money",
                        "billing & payment": "Invoices, billing, payments, or refunds",
                        "availability": "Stock, capacity, schedule, or service availability",
                        "delivery & fulfillment": "Delivery, fulfillment, pickup, or completion",
                        "customer service": "Customer support, helpdesk, or complaint handling",
                        "booking & ordering": "Booking, ordering, reservations, or checkout",
                        "digital experience": "Mobile app, website, portal, or other digital channel",
                        "security & safety": "Security, physical safety, danger, or incidents",
                        "food & beverage": "Food, beverages, meals, or catering",
                    },
                },
                "is_safety_issue": {
                    "type": "noul",
                    "instructions": "Does this review mention a critical safety issue, physical harm, danger, accident, malpractice, wrong medication, or emergency?",
                },
                "is_viral_risk": {
                    "type": "noul",
                    "instructions": "Does the reviewer threaten to make the issue viral, share it on social media, or report it to the media?",
                },
            },
        }

        response = self._http.post(
            "/v1/systemone",
            json=payload,
        )
        if response.status_code >= 400:
            raise RuntimeError(
                f"TypeSafe returned HTTP {response.status_code}: {response.text}"
            )

        result_payload = response.json()
        usage = result_payload.get("usage", {})
        input_tokens = int(usage.get("input_tokens") or 0)
        output_tokens = int(usage.get("output_tokens") or 0)
        total_tokens = input_tokens + output_tokens
        self.last_usage = {
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
            "total_tokens": total_tokens,
        }
        return self._to_analysis(result_payload, review)

    @staticmethod
    def _to_analysis(payload: dict, review: dict) -> dict:
        answers = payload.get("answers", {})

        # Extract sentiment
        sentiment_ans = answers.get("sentiment", {})
        sentiment = str(sentiment_ans.get("choice", "unknown")).lower()
        sentiment_score = float(sentiment_ans.get("confidence", 0.0))

        # Extract category
        category_ans = answers.get("category", {})
        raw_category = str(category_ans.get("choice", "other")).lower()
        category = TAXONOMY_CATEGORIES.get(raw_category, "other")
        if sentiment == "positive" and category == "other":
            category = "general_praise"

        # Extract safety and viral risk
        safety_ans = answers.get("is_safety_issue", {})
        safety_prob = float(safety_ans.get("noul", safety_ans.get("probability", 0.0)))
        safety = safety_prob > 0.5

        viral_ans = answers.get("is_viral_risk", {})
        viral_prob = float(viral_ans.get("noul", viral_ans.get("probability", 0.0)))
        viral = viral_prob > 0.5

        rating = review.get("rating")
        urgency = (
            "critical"
            if safety
            else "high"
            if viral or (rating == 1 and sentiment == "negative")
            else "medium"
            if sentiment in {"negative", "mixed"}
            else "low"
        )

        summaries = {
            "negative": "Pelanggan menyampaikan keluhan yang memerlukan tindak lanjut.",
            "mixed": "Pelanggan memberi apresiasi sekaligus menyampaikan kendala.",
            "positive": "Pelanggan menyampaikan pengalaman pelayanan yang positif.",
        }

        return {
            "sentiment": sentiment,
            "sentiment_score": sentiment_score,
            "issue_category": category,
            "urgency": urgency,
            "summary": summaries.get(
                sentiment, "Ulasan belum memiliki aspek yang cukup meyakinkan."
            ),
            "recommended_action": (
                "Tinjau aspek layanan yang terdeteksi dan tindak lanjuti pola serupa."
            ),
            "keywords": [],  # Jev is a decision model, it doesn't extract freeform keywords easily
            "is_potential_viral": viral,
            "is_safety_issue": safety,
            "jev": payload,
        }
