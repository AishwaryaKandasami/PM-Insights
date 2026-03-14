"""
Judge Tool — Phase 3
LLM-as-Judge: Gemini Flash reviews each cluster for quality.
Flags low-quality outputs for PM review.
"""
import json
import logging
import time
from typing import Any

import google.generativeai as genai

from agent.prompts import judge_prompt
from config.settings import GEMINI_API_KEY, GEMINI_FLASH_MODEL, MIN_DELAY_SECONDS

logger = logging.getLogger(__name__)

genai.configure(api_key=GEMINI_API_KEY)


def _format_members_for_judge(atoms: list[dict]) -> str:
    """Format cluster member atoms for judge review."""
    lines = []
    for i, atom in enumerate(atoms, 1):
        title = atom.get("title", "")
        desc = atom.get("description", "")[:150]
        lines.append(f"    [{i}] {title} — {desc}")
    return "\n".join(lines)


def judge_clusters(clusters: list[dict], atom_type: str) -> list[dict]:
    """
    Run LLM-as-Judge on each cluster.

    Args:
        clusters: List of cluster dicts (must already be labeled + scored).
        atom_type: 'bug' or 'feature'

    Returns:
        Same clusters, enriched with quality_flag and quality_notes.
    """
    if atom_type == "bug":
        system = judge_prompt.BUG_SYSTEM
        user_tmpl = judge_prompt.BUG_USER_TMPL
    else:
        system = judge_prompt.FEATURE_SYSTEM
        user_tmpl = judge_prompt.FEATURE_USER_TMPL

    model = genai.GenerativeModel(
        model_name=GEMINI_FLASH_MODEL,
        system_instruction=system,
        generation_config=genai.GenerationConfig(
            temperature=0,
            response_mime_type="application/json",
        ),
    )

    flagged_count = 0

    for cluster in clusters:
        members_text = _format_members_for_judge(cluster["atoms"])

        if atom_type == "bug":
            prompt = user_tmpl.format(
                label=cluster.get("cluster_label", ""),
                severity=cluster.get("severity", "P3"),
                product_area=cluster.get("product_area", "Other"),
                count=len(cluster["atoms"]),
                members=members_text,
            )
        else:
            prompt = user_tmpl.format(
                label=cluster.get("cluster_label", ""),
                theme=cluster.get("theme", "Other"),
                product_area=cluster.get("product_area", "Other"),
                user_value=cluster.get("user_value_summary", ""),
                count=len(cluster["atoms"]),
                members=members_text,
            )

        try:
            response = model.generate_content(prompt)
            result = json.loads(response.text.strip())
            flag = result.get("quality_flag", "pass")
            notes = result.get("quality_notes", "")

            cluster["quality_flag"] = flag
            cluster["quality_notes"] = notes

            if flag == "review":
                flagged_count += 1
                # Penalize signal confidence for flagged clusters
                current_conf = cluster.get("signal_confidence", 1.0)
                cluster["signal_confidence"] = round(current_conf * 0.7, 4)
                logger.warning(
                    "Judge flagged %s cluster '%s': %s",
                    atom_type, cluster.get("cluster_label"), notes,
                )
            else:
                logger.info(
                    "Judge passed %s cluster '%s'",
                    atom_type, cluster.get("cluster_label"),
                )

        except Exception as exc:
            logger.error("Judge error for cluster '%s': %s", cluster.get("cluster_label"), exc)
            cluster["quality_flag"] = "pass"
            cluster["quality_notes"] = ""
        finally:
            time.sleep(MIN_DELAY_SECONDS)

    logger.info(
        "Judge complete: %d %s clusters evaluated, %d flagged for review",
        len(clusters), atom_type, flagged_count,
    )
    return clusters
