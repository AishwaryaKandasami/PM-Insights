"""
Feature Extractor Tool — Phase 2
Extracts feature request items from a single review using Gemini Flash.
Only called when router routes the review as 'feature'.
Prompt imported from agent/prompts/feature_extractor_prompt.py
"""
import json
import logging
import time
from typing import Any

import google.generativeai as genai

from agent.prompts import feature_extractor_prompt
from config.settings import GEMINI_API_KEY, GEMINI_FLASH_MODEL, MIN_DELAY_SECONDS

logger = logging.getLogger(__name__)

genai.configure(api_key=GEMINI_API_KEY)


def extract_features(review_id: str, cleaned_text: str) -> list[dict[str, Any]]:
    """
    Extract feature request items from a single review.

    Returns:
        List of feature atom dicts. Empty list if no features found or on error.
    """
    prompt = feature_extractor_prompt.USER_TMPL.format(text=cleaned_text[:1500])
    try:
        model = genai.GenerativeModel(
            model_name=GEMINI_FLASH_MODEL,
            system_instruction=feature_extractor_prompt.SYSTEM,
            generation_config=genai.GenerationConfig(
                temperature=0,
                response_mime_type="application/json",
            ),
        )
        response = model.generate_content(prompt)
        items = json.loads(response.text.strip())
        if not isinstance(items, list):
            logger.warning("Feature extractor: non-list response for review_id=%s", review_id)
            return []
        return [
            {
                "review_id": review_id,
                "atom_type": "feature",
                "title": item.get("title", "")[:200],
                "description": item.get("description", ""),
                "evidence_spans": json.dumps(item.get("evidence_spans", [])),
                "product_area": item.get("product_area", "Other"),
                "severity_signal": None,
                "user_value": item.get("user_value", ""),
                "confidence_score": float(item.get("confidence_score", 0.0)),
            }
            for item in items
        ]
    except Exception as exc:
        logger.error("Feature extractor error for review_id=%s: %s", review_id, exc)
        return []
    finally:
        time.sleep(MIN_DELAY_SECONDS)
