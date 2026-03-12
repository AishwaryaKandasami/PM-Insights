"""
Multi-Task Extractor — Phase 2, Prompt v1
Extracts both bugs AND feature requests from a single review in one Gemini call.
Only called when router routes review as 'ambiguous'.
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
_MULTI_SYSTEM = """\
You are a product feedback analyst. Given an app review that contains BOTH \
bug reports AND feature requests, extract all distinct items.

Return a single JSON array where each item has:
  - atom_type     : "bug" or "feature"
  - title         : short, readable (max 10 words)
  - description   : 1-2 sentence explanation
  - evidence_spans: list of exact short quotes from the review (max 3)
  - product_area  : one of: Playback, Search, Download, Login, \
Payment, Notifications, UI, Performance, Other
  - severity_signal: for bugs only — P0, P1, P2, or P3; null for features
      P0 = crash / login blocked / data loss
      P1 = core feature broken for many users
      P2 = partial impairment or UI broken
      P3 = minor annoyance or edge case
  - user_value    : for features only — why it matters to the user; null for bugs
  - confidence_score: float 0.0-1.0

Reply with ONLY a valid JSON array. If nothing found, return [].
No markdown, no explanation.
"""

_MULTI_USER_TMPL = 'Review:\n"""\n{text}\n"""'


def extract_all(review_id: str, cleaned_text: str) -> list[dict[str, Any]]:
    """
    Extract both bugs and features from an ambiguous review in one call.

    Returns:
        Mixed list of bug + feature atom dicts. Empty list on error.
    """
    prompt = _MULTI_USER_TMPL.format(text=cleaned_text[:1500])
    try:
        model = genai.GenerativeModel(
            model_name=GEMINI_FLASH_MODEL,
            system_instruction=_MULTI_SYSTEM,
            generation_config=genai.GenerationConfig(
                temperature=0,
                response_mime_type="application/json",
            ),
        )
        response = model.generate_content(prompt)
        raw = response.text.strip()
        items = json.loads(raw)
        if not isinstance(items, list):
            logger.warning("Multi extractor: non-list response for review_id=%s", review_id)
            return []
        atoms = []
        for item in items:
            atom_type = item.get("atom_type", "").lower()
            if atom_type not in {"bug", "feature"}:
                logger.warning(
                    "Multi extractor: unknown atom_type=%r for review_id=%s — skipping",
                    atom_type, review_id,
                )
                continue
            atoms.append({
                "review_id": review_id,
                "atom_type": atom_type,
                "title": item.get("title", "")[:200],
                "description": item.get("description", ""),
                "evidence_spans": json.dumps(item.get("evidence_spans", [])),
                "product_area": item.get("product_area", "Other"),
                "severity_signal": item.get("severity_signal") if atom_type == "bug" else None,
                "user_value": item.get("user_value") if atom_type == "feature" else None,
                "confidence_score": float(item.get("confidence_score", 0.0)),
            })
        return atoms
    except Exception as exc:
        logger.error("Multi extractor error for review_id=%s: %s", review_id, exc)
        return []
    finally:
        time.sleep(MIN_DELAY_SECONDS)
