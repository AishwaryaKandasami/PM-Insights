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


def extract_all_batch(reviews: list[dict]) -> list[dict[str, Any]]:
    """
    Extract both bugs and features from a batch of ambiguous reviews.

    Args:
        reviews: List of dicts with review_id and cleaned_text

    Returns:
        Mixed list of bug + feature atom dicts. Empty list on error.
    """
    input_batch = [{"review_id": r["review_id"], "text": (r.get("cleaned_text") or "")[:1500]} for r in reviews]
    prompt = multi_extractor_prompt.USER_TMPL.format(reviews_json=json.dumps(input_batch))
    max_retries = 3
    items = []

    for attempt in range(max_retries):
        try:
            model = genai.GenerativeModel(
                model_name=GEMINI_FLASH_MODEL,
                system_instruction=multi_extractor_prompt.SYSTEM,
                generation_config=genai.GenerationConfig(
                    temperature=0,
                    response_mime_type="application/json",
                ),
            )
            response = model.generate_content(prompt, request_options={"timeout": 60.0})
            items = json.loads(response.text.strip())
            
            if not isinstance(items, list):
                logger.warning("Multi extractor batch: non-list response")
                return []
            break
            
        except Exception as exc:
            if attempt == max_retries - 1:
                logger.error("Multi extractor batch error after %d retries: %s", max_retries, exc)
                return []
            logger.warning("Multi extractor batch attempt %d failed: %s - retrying...", attempt + 1, exc)
            time.sleep(2 ** attempt)

    atoms = []
    for item in items:
        r_id = item.get("review_id")
        if not r_id:
            continue
        atom_type = item.get("atom_type", "").lower()
        if atom_type not in {"bug", "feature"}:
            continue
        atoms.append({
            "review_id": r_id,
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
