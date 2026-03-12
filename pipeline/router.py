"""
Confidence Router — Phase 2, Prompt v1
Classifies each review into: bug | feature | ambiguous | noise
Uses Gemini Flash at temperature=0 for determinism.
"""
import json
import logging
import time

import google.generativeai as genai

from config.settings import GEMINI_API_KEY, GEMINI_FLASH_MODEL, MIN_DELAY_SECONDS

logger = logging.getLogger(__name__)

genai.configure(api_key=GEMINI_API_KEY)

# --------------------------------------------------------------------------
# Pinned prompt — v1 (2026-03-12)
# --------------------------------------------------------------------------
_ROUTER_SYSTEM = """\
You are a product feedback classifier. Given a single app review, \
classify the PRIMARY intent into exactly one of:
  - bug        : the user reports something broken, crashing, or not working
  - feature    : the user requests a new capability or improvement
  - ambiguous  : the review clearly contains both a bug and a feature request
  - noise      : the review is spam, gibberish, a rating-only comment, or \
contains no actionable product signal

Reply with ONLY valid JSON, no markdown. Schema:
{"intent": "<bug|feature|ambiguous|noise>", "confidence": <float 0.0-1.0>}
"""

_ROUTER_USER_TMPL = 'Review:\n"""\n{text}\n"""'


def route_review(cleaned_text: str) -> dict:
    """
    Classify a single review into bug / feature / ambiguous / noise.

    Returns:
        dict with keys: intent (str), confidence (float)
        Falls back to {"intent": "ambiguous", "confidence": 0.0} on any error.
    """
    prompt = _ROUTER_USER_TMPL.format(text=cleaned_text[:1500])
    try:
        model = genai.GenerativeModel(
            model_name=GEMINI_FLASH_MODEL,
            system_instruction=_ROUTER_SYSTEM,
            generation_config=genai.GenerationConfig(
                temperature=0,
                response_mime_type="application/json",
            ),
        )
        response = model.generate_content(prompt)
        raw = response.text.strip()
        result = json.loads(raw)
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
