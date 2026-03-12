"""
Feature Extractor — Phase 2, Prompt v1
Extracts feature request items from a single review using Gemini Flash.
Only called when router routes review as 'feature'.
"""
import json
import logging
import time
from typing import Any

import google.generativeai as genai

from config.settings import GEMINI_API_KEY, GEMINI_FLASH_MODEL, MIN_DELAY_SECONDS

logger = logging.getLogger(__name__)

genai.configure(api_key=GEMINI_API_KEY)

# --------------------------------------------------------------------------
# Pinned prompt — v1 (2026-03-12)
# --------------------------------------------------------------------------
_FEATURE_SYSTEM = """\
You are a product feature analyst. Given an app review, extract all distinct \
feature requests the user expresses. A feature request is a wish, suggestion, \
or improvement the user wants to see — something that doesn't exist yet or \
needs to be better.

For each feature request, return a JSON object with:
  - title         : short, PM-readable (max 10 words)
  - description   : 1-2 sentence explanation of what is requested
  - user_value    : why this matters to the user (1 sentence)
  - evidence_spans: list of exact short quotes from the review (max 3)
  - product_area  : one of: Playback, Search, Download, Login, \
Payment, Notifications, UI, Performance, Other
  - confidence_score: float 0.0-1.0 (your certainty this is a real feature request)

Reply with ONLY a valid JSON array. If no feature requests found, return [].
No markdown, no explanation.
"""

_FEATURE_USER_TMPL = 'Review:\n"""\n{text}\n"""'


def extract_features(review_id: str, cleaned_text: str) -> list[dict[str, Any]]:
    """
    Extract feature request items from a single review.

    Returns:
        List of feature atom dicts. Empty list if no features or on error.
    """
    prompt = _FEATURE_USER_TMPL.format(text=cleaned_text[:1500])
    try:
        model = genai.GenerativeModel(
            model_name=GEMINI_FLASH_MODEL,
            system_instruction=_FEATURE_SYSTEM,
            generation_config=genai.GenerationConfig(
                temperature=0,
                response_mime_type="application/json",
            ),
        )
        response = model.generate_content(prompt)
        raw = response.text.strip()
        items = json.loads(raw)
        if not isinstance(items, list):
            logger.warning("Feature extractor: non-list response for review_id=%s", review_id)
            return []
        atoms = []
        for item in items:
            atoms.append({
                "review_id": review_id,
                "atom_type": "feature",
                "title": item.get("title", "")[:200],
                "description": item.get("description", ""),
                "evidence_spans": json.dumps(item.get("evidence_spans", [])),
                "product_area": item.get("product_area", "Other"),
                "severity_signal": None,
                "user_value": item.get("user_value", ""),
                "confidence_score": float(item.get("confidence_score", 0.0)),
            })
        return atoms
    except Exception as exc:
        logger.error("Feature extractor error for review_id=%s: %s", review_id, exc)
        return []
    finally:
        time.sleep(MIN_DELAY_SECONDS)
