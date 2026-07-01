from __future__ import annotations

import json
from pathlib import Path

from openai import OpenAI

from app.config import Settings
from app.integrations.gemini_client import GeminiClientBase, ReviewAnalysisResult


class OpenRouterClient(GeminiClientBase):
    def __init__(self, settings: Settings, sdk_client: OpenAI | None = None):
        self.settings = settings
        self.model_name = settings.openrouter_model
        
        if not self.settings.openrouter_api_key:
            raise RuntimeError(
                "OpenRouter API key is missing. Please check your .env configuration."
            )
            
        self.client = sdk_client or OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.settings.openrouter_api_key,
        )
        
        prompt_path = (
            Path(__file__).resolve().parent.parent
            / "prompts"
            / "review_analysis_prompt.md"
        )
        self.system_instruction = prompt_path.read_text(encoding="utf-8")
        
        # OpenRouter doesn't always support strict JSON schema response_format out of the box for all models.
        # We append a strong instruction to return raw JSON matching the schema.
        self.system_instruction += (
            "\n\nIMPORTANT: You must return ONLY raw JSON that strictly matches the following JSON schema. "
            "Do not include markdown code blocks, explanations, or any other text.\n\n"
            f"{json.dumps(ReviewAnalysisResult.model_json_schema(), indent=2)}"
        )

    def analyze_review(self, review: dict) -> dict:
        prompt = (
            "Analisis review rumah sakit berikut sesuai instruksi sistem.\n\n"
            f"Rating: {review.get('rating')}\n"
            f"Reviewer: {review.get('reviewer_name') or 'Anonymous'}\n"
            f"Waktu review: {review.get('review_time') or 'unknown'}\n"
            f"Teks review:\n{review.get('review_text') or ''}"
        )

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": self.system_instruction},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            # We use standard text generation because many open-weights models on OpenRouter 
            # don't support structured outputs / response_format={"type": "json_object"}.
            # The system prompt ensures it returns JSON.
        )
        
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("OpenRouter returned an empty response.")
            
        # Clean up in case the model wraps the response in markdown blocks
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        try:
            parsed = json.loads(content)
            return ReviewAnalysisResult.model_validate(parsed).model_dump()
        except (json.JSONDecodeError, ValueError) as exc:
            raise RuntimeError(
                f"OpenRouter returned a response that does not match the analysis schema.\nRaw response: {content}"
            ) from exc
