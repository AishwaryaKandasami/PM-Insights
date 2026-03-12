"""
Bug Extractor — Phase 2, Prompt v1
Extracts bug items from a single review using Gemini Flash.
Only called when router routes review as 'bug'.
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
_BUG_SYSTEM = """\
You are a product bug analyst. Given an app review, extract all distinct \
bug reports the user describes. A bug is something broken, crashing, \
failing, or not working as expected.

For each bug, return a JSON object with:
  - title         : short, engineer-readable (max 10 words)
  - description   : 1-2 sentence explanation of the problem
  - evidence_spans: list of exact short quotes from the review (max 3)
  - product_area  : one of: Playback, Search, Download, Login, \
Payment, Notifications, UI, Performance, Other
  - severity_signal: your best severity estimate: P0, P1, P2, or P3
      P0 = crash / login blocked / data loss
      P1 = core feature broken for many users
      P2 = partial impairment or UI broken
      P3 = minor annoyance or edge case
  - confidence_score: float 0.0-1.0 (your certainty this is a real bug)

Reply with ONLY a valid JSON array. If no bugs found, return [].
No markdown, no explanation.
"""

_BUG_USER_TMPL = 'Review:\n"""\n{text}\n"""'


def extract_bugs(review_id: str, cleaned_text: str) -> list[dict[str, Any]]:
    """
    Extract bug items from a single review.

    Returns:
        List of bug atom dicts. Empty list if no bugs or on error.
    """
    prompt = _BUG_USER_TMPL.format(text=cleaned_text[:1500])
    try:
        model = genai.GenerativeModel(
            model_name=GEMINI_FLASH_MODEL,
            system_instruction=_BUG_SYSTEM,
            generation_config=genai.GenerationConfig(
                temperature=0,
                response_mime_type="application/json",
            ),
        )
        response = model.generate_content(prompt)
        raw = response.text.strip()
        items = json.loads(raw)
        if not isinstance(items, list):
            logger.warning("Bug extractor: non-list response for review_id=%s", review_id)
            return []
        atoms = []
        for item in items:
            atoms.append({
                "review_id": review_id,
                "atom_type": "bug",
                "title": item.get("title", "")[:200],
                "description": item.get("description", ""),
                "evidence_spans": json.dumps(item.get("evidence_spans", [])),
                "product_area": item.get("product_area", "Other"),
                "severity_signal": item.get("severity_signal", ""),
                "user_value": None,
                "confidence_score": float(item.get("confidence_score", 0.0)),
            })
        return atoms
    except Exception as exc:
        logger.error("Bug extractor error for review_id=%s: %s", review_id, exc)
        return []
    finally:
        time.sleep(MIN_DELAY_SECONDS)
