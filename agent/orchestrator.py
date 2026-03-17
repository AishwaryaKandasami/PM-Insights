"""
Orchestrator — Phase 2
The agent loop: routes each review, selects the right extractor tool,
writes atoms to the Gold layer (review_atoms table).

The agent decides per review which tool to call — no hardcoded step order.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from database.db import (
    fetch_usable_normalized,
    get_pipeline_run,
    init_db,
    insert_review_atoms,
    upsert_pipeline_run,
)
from agent.tools.router import route_review
from agent.tools.bug_extractor import extract_bugs
from agent.tools.feature_extractor import extract_features
from agent.tools.multi_extractor import extract_all

logger = logging.getLogger(__name__)

# Default sample size for Phase 2 (None = all usable reviews)
DEFAULT_SAMPLE_LIMIT = None


def run_extraction(run_id: str, sample_limit: Optional[int] = DEFAULT_SAMPLE_LIMIT) -> dict:
    """
    Agent loop: route each review, call the right extractor tool, write atoms.

    Args:
        run_id:       The pipeline run_id to process (must have normalized data).
        sample_limit: Max reviews to process. None = all usable reviews.

    Returns:
        Summary dict with routing breakdown and atom counts.
    """
    init_db()  # Ensure review_atoms table exists

    reviews = fetch_usable_normalized(run_id, limit=sample_limit)
    if not reviews:
        logger.warning("No usable reviews found for run_id=%s", run_id)
        return {
            "total_reviewed": 0,
            "routed_bug": 0,
            "routed_feature": 0,
            "routed_ambiguous": 0,
            "skipped_noise": 0,
            "atoms_written": 0,
        }

    counters = {
        "total_reviewed": len(reviews),
        "routed_bug": 0,
        "routed_feature": 0,
        "routed_ambiguous": 0,
        "skipped_noise": 0,
        "atoms_written": 0,
    }

    all_atoms: list[dict] = []
    extracted_at = datetime.now(timezone.utc).isoformat()

    for row in reviews:
        review_id = row["review_id"]
        cleaned_text = row["cleaned_text"] or ""

        # ── Step 1: Route ────────────────────────────────────────────────
        rating = row["rating"] if "rating" in row.keys() else None
        route = route_review(cleaned_text, rating=rating)
        intent = route["intent"]
        router_confidence = route["confidence"]

        # Low-confidence noise → reroute to ambiguous rather than silently drop
        if intent == "noise" and router_confidence < 0.75:
            logger.info(
                "review_id=%s noise confidence=%.2f < 0.75 → rerouted to ambiguous",
                review_id, router_confidence,
            )
            intent = "ambiguous"

        logger.info(
            "review_id=%s → intent=%s (confidence=%.2f)",
            review_id, intent, router_confidence,
        )

        # ── Step 2: Agent selects and calls the right extractor tool ─────
        if intent == "noise":
            counters["skipped_noise"] += 1
            continue

        elif intent == "bug":
            counters["routed_bug"] += 1
            atoms = extract_bugs(review_id, cleaned_text)

        elif intent == "feature":
            counters["routed_feature"] += 1
            atoms = extract_features(review_id, cleaned_text)

        else:  # ambiguous
            counters["routed_ambiguous"] += 1
            atoms = extract_all(review_id, cleaned_text)

        # ── Step 3: Enrich atoms with routing metadata ───────────────────
        for atom in atoms:
            atom["routed_as"] = intent
            atom["router_confidence"] = router_confidence
            atom["run_id"] = run_id
            atom["extracted_at"] = extracted_at

        all_atoms.extend(atoms)

    # ── Step 4: Bulk write all atoms to Gold layer ────────────────────────
    if all_atoms:
        insert_review_atoms(all_atoms)
        counters["atoms_written"] = len(all_atoms)
        logger.info(
            "Extraction complete for run_id=%s: %d atoms written", run_id, len(all_atoms)
        )

    # ── Step 5: Update pipeline_runs status ──────────────────────────────
    existing = get_pipeline_run(run_id)
    now_iso = datetime.now(timezone.utc).isoformat()
    upsert_pipeline_run({
        "run_id": run_id,
        "status": "EXTRACTED",
        "source_type": existing["source_type"] if existing else None,
        "source_file": existing["source_file"] if existing else None,
        "app_id": existing["app_id"] if existing else None,
        "total_reviews": existing["total_reviews"] if existing else len(reviews),
        "supported_reviews": existing["supported_reviews"] if existing else None,
        "duplicate_count": existing["duplicate_count"] if existing else None,
        "low_quality_count": existing["low_quality_count"] if existing else None,
        "current_step": "extraction",
        "error_message": None,
        "started_at": existing["started_at"] if existing else now_iso,
        "completed_at": now_iso,
    })

    logger.info("Agent summary for run_id=%s: %s", run_id, counters)
    return counters
