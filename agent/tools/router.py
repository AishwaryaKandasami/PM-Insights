"""
Router Tool — Phase 2
Classifies each review into: bug | feature | ambiguous | noise
Prompt imported from agent/prompts/router_prompt.py
"""
import json
import logging
import time

import google.generativeai as genai

from agent.prompts import router_prompt
from config.settings import GEMINI_API_KEY, GEMINI_FLASH_MODEL, MIN_DELAY_SECONDS

logger = logging.getLogger(__name__)

genai.configure(api_key=GEMINI_API_KEY)


def route_review(cleaned_text: str, rating: int | None = None) -> dict:
    """
    Classify a single review into bug / feature / ambiguous / noise.

    Args:
        cleaned_text: Pre-processed review text.
        rating:       Star rating (1–5) from the original review, or None if unknown.

    Returns:
        dict with keys: intent (str), confidence (float)
        Falls back to {"intent": "ambiguous", "confidence": 0.0} on any error.
    """
    rating_str = str(rating) if rating is not None else "?"
    prompt = router_prompt.USER_TMPL.format(text=cleaned_text[:1500], rating=rating_str)
    try:
        model = genai.GenerativeModel(
            model_name=GEMINI_FLASH_MODEL,
            system_instruction=router_prompt.SYSTEM,
            generation_config=genai.GenerationConfig(
                temperature=0,
                response_mime_type="application/json",
            ),
        )
        response = model.generate_content(prompt)
        result = json.loads(response.text.strip())
        intent = result.get("intent", "ambiguous")
        confidence = float(result.get("confidence", 0.0))
        if intent not in {"bug", "feature", "ambiguous", "noise"}:
            logger.warning("Router returned unexpected intent=%r — defaulting to ambiguous", intent)
            intent = "ambiguous"
        return {"intent": intent, "confidence": confidence}
    except Exception as exc:
        logger.error("Router error: %s", exc)
        return {"intent": "ambiguous", "confidence": 0.0}
    finally:
        time.sleep(MIN_DELAY_SECONDS)
