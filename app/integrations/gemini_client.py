from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Literal

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from app.config import Settings


class ReviewAnalysisResult(BaseModel):
    sentiment: Literal["positive", "neutral", "negative", "mixed", "unknown"]
    sentiment_score: float = Field(ge=0, le=1)
    issue_category: Literal[
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
    ]
    urgency: Literal["low", "medium", "high", "critical", "unknown"]
    summary: str
    recommended_action: str
    keywords: list[str]
    is_potential_viral: bool
    is_patient_safety_issue: bool


class GeminiClientBase(ABC):
    model_name: str

    @abstractmethod
    def analyze_review(self, review: dict) -> dict:
        raise NotImplementedError


class GeminiClient(GeminiClientBase):
    def __init__(self, settings: Settings, sdk_client=None):
        self.settings = settings
        self.model_name = settings.gemini_model
        self.client = sdk_client
        prompt_path = (
            Path(__file__).resolve().parent.parent
            / "prompts"
            / "review_analysis_prompt.md"
        )
        self.system_instruction = prompt_path.read_text(encoding="utf-8")

    def analyze_review(self, review: dict) -> dict:
        if not self.settings.gemini_api_key:
            raise RuntimeError(
                "Gemini API key is missing. Please check your .env configuration."
            )
        if self.client is None:
            self.client = genai.Client(api_key=self.settings.gemini_api_key)

        prompt = (
            "Analisis review rumah sakit berikut sesuai instruksi sistem.\n\n"
            f"Rating: {review.get('rating')}\n"
            f"Reviewer: {review.get('reviewer_name') or 'Anonymous'}\n"
            f"Waktu review: {review.get('review_time') or 'unknown'}\n"
            f"Teks review:\n{review.get('review_text') or ''}"
        )
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=self.system_instruction,
                response_mime_type="application/json",
                response_json_schema=ReviewAnalysisResult.model_json_schema(),
                temperature=0.1,
            ),
        )
        if response.parsed is not None:
            if isinstance(response.parsed, ReviewAnalysisResult):
                return response.parsed.model_dump()
            if isinstance(response.parsed, dict):
                return ReviewAnalysisResult.model_validate(
                    response.parsed
                ).model_dump()
        if not response.text:
            raise RuntimeError("Gemini returned an empty response.")
        try:
            return ReviewAnalysisResult.model_validate(
                json.loads(response.text)
            ).model_dump()
        except (json.JSONDecodeError, ValueError) as exc:
            raise RuntimeError(
                "Gemini returned a response that does not match the analysis schema."
            ) from exc
