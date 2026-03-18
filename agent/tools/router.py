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


def route_reviews_batch(reviews: list[dict]) -> dict[str, dict]:
    """
    Classify a batch of reviews into bug / feature / ambiguous / noise.

    Args:
        reviews: List of dicts with keys: review_id, cleaned_text, rating (optional)

    Returns:
        dict mapping review_id -> {"intent": str, "confidence": float}
        Defaults to "ambiguous" for any items missing from response.
    """
    input_batch = []
    for r in reviews:
        input_batch.append({
            "review_id": r["review_id"],
            "text": (r.get("cleaned_text") or "")[:1500],
            "rating": r.get("rating")
        })
        
    prompt = router_prompt.USER_TMPL.format(reviews_json=json.dumps(input_batch))
    max_retries = 3
    responses_map = {}
    
    for attempt in range(max_retries):
        try:
            model = genai.GenerativeModel(
                model_name=GEMINI_FLASH_MODEL,
                system_instruction=router_prompt.SYSTEM,
                generation_config=genai.GenerationConfig(
                    temperature=0,
                    response_mime_type="application/json",
                ),
            )
            response = model.generate_content(prompt, request_options={"timeout": 60.0})
            result = json.loads(response.text.strip())
            
            if not isinstance(result, list):
                logger.warning("Router batch: expected list response, got %s", type(result))
                return {}
                
            for item in result:
                r_id = item.get("review_id")
                intent = item.get("intent", "ambiguous")
                confidence = float(item.get("confidence", 0.0))
                if intent not in {"bug", "feature", "ambiguous", "noise"}:
                    intent = "ambiguous"
                if r_id:
                    responses_map[r_id] = {"intent": intent, "confidence": confidence}
                    
            return responses_map
            
        except Exception as exc:
            if attempt == max_retries - 1:
                logger.error("Router batch error after %d retries: %s", max_retries, exc)
                return responses_map
            logger.warning("Router batch attempt %d failed: %s - retrying...", attempt + 1, exc)
            time.sleep(2 ** attempt)
            
    return responses_map
