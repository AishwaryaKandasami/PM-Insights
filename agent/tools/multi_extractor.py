"""
Multi Extractor Tool — Phase 2
Extracts both bugs AND features from an ambiguous review in one Gemini call.
Only called when router routes the review as 'ambiguous'.
Prompt imported from agent/prompts/multi_extractor_prompt.py
"""
import json
import logging
import time
from typing import Any

import google.generativeai as genai

from agent.prompts import multi_extractor_prompt
from config.settings import GEMINI_API_KEY, GEMINI_FLASH_MODEL, MIN_DELAY_SECONDS

logger = logging.getLogger(__name__)

genai.configure(api_key=GEMINI_API_KEY)


def extract_all(review_id: str, cleaned_text: str) -> list[dict[str, Any]]:
    """
    Extract both bugs and features from an ambiguous review in one call.

    Returns:
        Mixed list of bug + feature atom dicts. Empty list on error.
    """
    prompt = multi_extractor_prompt.USER_TMPL.format(text=cleaned_text[:1500])
    try:
        model = genai.GenerativeModel(
            model_name=GEMINI_FLASH_MODEL,
            system_instruction=multi_extractor_prompt.SYSTEM,
            generation_config=genai.GenerationConfig(
                temperature=0,
                response_mime_type="application/json",
            ),
        )
        response = model.generate_content(prompt)
        items = json.loads(response.text.strip())
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
