"""
Cluster Labeler Tool — Phase 3
Uses Gemini Flash to generate human-readable labels for clusters.
"""
import json
import logging
import time
from typing import Any

import google.generativeai as genai

from agent.prompts import cluster_label_prompt
from config.settings import GEMINI_API_KEY, GEMINI_FLASH_MODEL, MIN_DELAY_SECONDS

logger = logging.getLogger(__name__)

genai.configure(api_key=GEMINI_API_KEY)


def _format_members(atoms: list[dict], atom_type: str) -> str:
    """Format cluster member atoms into a readable text block."""
    lines = []
    for i, atom in enumerate(atoms, 1):
        title = atom.get("title", "")
        desc = atom.get("description", "")
        if atom_type == "bug":
            sev = atom.get("severity_signal", "?")
            lines.append(f"  [{i}] {title} (severity: {sev})\n      {desc}")
        else:
            val = atom.get("user_value", "")
            lines.append(f"  [{i}] {title}\n      {desc}\n      Value: {val}")
    return "\n".join(lines)


def label_clusters(clusters: list[dict], atom_type: str) -> list[dict]:
    """
    Generate LLM labels for each cluster.

    Args:
        clusters: List of cluster dicts (each has 'atoms' list).
        atom_type: 'bug' or 'feature'

    Returns:
        Same clusters list, enriched with label fields.
    """
    if atom_type == "bug":
        system = cluster_label_prompt.BUG_SYSTEM
        user_tmpl = cluster_label_prompt.BUG_USER_TMPL
    else:
        system = cluster_label_prompt.FEATURE_SYSTEM
        user_tmpl = cluster_label_prompt.FEATURE_USER_TMPL

    model = genai.GenerativeModel(
        model_name=GEMINI_FLASH_MODEL,
        system_instruction=system,
        generation_config=genai.GenerationConfig(
            temperature=0,
            response_mime_type="application/json",
        ),
    )

    for cluster in clusters:
        members_text = _format_members(cluster["atoms"], atom_type)
        prompt = user_tmpl.format(
            count=len(cluster["atoms"]),
            members=members_text,
        )
        try:
            response = model.generate_content(prompt)
            result = json.loads(response.text.strip())
            cluster["cluster_label"] = result.get("cluster_label", "Unlabeled")
            if atom_type == "bug":
                cluster["severity"] = result.get("severity", "P3")
                cluster["product_area"] = result.get("product_area", "Other")
            else:
                cluster["theme"] = result.get("theme", "Other")
                cluster["product_area"] = result.get("product_area", "Other")
                cluster["user_value_summary"] = result.get("user_value_summary", "")
            logger.info(
                "Labeled %s cluster (%d atoms): %s",
                atom_type, len(cluster["atoms"]), cluster["cluster_label"],
            )
        except Exception as exc:
            logger.error("Labeling error for %s cluster: %s", atom_type, exc)
            cluster["cluster_label"] = "Unlabeled"
            if atom_type == "bug":
                cluster["severity"] = "P3"
                cluster["product_area"] = "Other"
            else:
                cluster["theme"] = "Other"
                cluster["product_area"] = "Other"
                cluster["user_value_summary"] = ""
        finally:
            time.sleep(MIN_DELAY_SECONDS)

    return clusters
