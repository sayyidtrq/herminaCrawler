from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel, Field


class ReviewAnalysisResult(BaseModel):
    sentiment: Literal["positive", "neutral", "negative", "mixed", "unknown"]
    sentiment_score: float = Field(ge=0, le=1)
    issue_category: Literal[
        "product_quality",
        "service_quality",
        "professional_service",
        "staff_service",
        "administration",
        "waiting_time",
        "cleanliness",
        "facility",
        "parking",
        "accessibility",
        "price_value",
        "billing_payment",
        "availability",
        "delivery_fulfillment",
        "customer_service",
        "booking_ordering",
        "digital_experience",
        "safety_security",
        "food_beverage",
        "general_praise",
        "other",
    ]
    urgency: Literal["low", "medium", "high", "critical", "unknown"]
    summary: str
    recommended_action: str
    keywords: list[str]
    is_potential_viral: bool
    is_safety_issue: bool


class GeminiClientBase(ABC):
    model_name: str

    @abstractmethod
    def analyze_review(self, review: dict) -> dict:
        raise NotImplementedError
