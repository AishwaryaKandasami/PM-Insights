"""
Orchestrator — Phase 2
The agent loop: routes each review, selects the right extractor tool,
writes atoms to the Gold layer (review_atoms table).

The agent decides per review which tool to call — no hardcoded step order.
"""
import logging
from datetime import datetime, timezone
from typing import Optional
import concurrent.futures
import threading

from database.db import (
    fetch_usable_normalized,
    get_pipeline_run,
    init_db,
    insert_review_atoms,
    upsert_pipeline_run,
)
from agent.tools.router import route_reviews_batch
from agent.tools.bug_extractor import extract_bugs_batch
from agent.tools.feature_extractor import extract_features_batch
from agent.tools.multi_extractor import extract_all_batch

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
    db_lock = threading.Lock()

    def process_batch(batch):
        # Convert sqlite3.Row objects to dicts
        batch_dicts = [dict(r) for r in batch]
        
        # 1. Route batch
        route_map = route_reviews_batch(batch_dicts)
        
        bug_batch = []
        feature_batch = []
        all_batch = []
        batch_atoms = []
        skipped_noise = 0
        
        for r in batch_dicts:
            r_id = r["review_id"]
            route = route_map.get(r_id, {"intent": "ambiguous", "confidence": 0.0})
            intent = route["intent"]
            confidence = route["confidence"]
            
            if intent == "noise" and confidence < 0.75:
                intent = "ambiguous"
                
            logger.info("review_id=%s → intent=%s (confidence=%.2f)", r_id, intent, confidence)
            
            if intent == "noise":
                skipped_noise += 1
                continue
            if intent == "bug":
                bug_batch.append(r)
            elif intent == "feature":
                feature_batch.append(r)
            else:
                all_batch.append(r)

        # 2. Extract
        extracted_subset = []
        if bug_batch:
            atoms = extract_bugs_batch(bug_batch)
            for a in atoms: 
                a["routed_as"] = "bug"
            extracted_subset.extend(atoms)
            
        if feature_batch:
            atoms = extract_features_batch(feature_batch)
            for a in atoms: 
                a["routed_as"] = "feature"
            extracted_subset.extend(atoms)
            
        if all_batch:
            atoms = extract_all_batch(all_batch)
            for a in atoms: 
                if "routed_as" not in a:
                    a["routed_as"] = "ambiguous"
            extracted_subset.extend(atoms)

        # 3. Enrich with generic metadata
        for atom in extracted_subset:
            r_id = atom.get("review_id")
            atom["router_confidence"] = route_map.get(r_id, {}).get("confidence", 0.0)
            atom["run_id"] = run_id
            atom["extracted_at"] = extracted_at
            # Default keys required for SQLite bind queries
            if "severity_signal" not in atom:
                atom["severity_signal"] = None
            if "user_value" not in atom:
                atom["user_value"] = None

        if extracted_subset:
            with db_lock:
                insert_review_atoms(extracted_subset)
                
        return (extracted_subset, len(bug_batch), len(feature_batch), len(all_batch), skipped_noise)

    BATCH_SIZE = 10
    batches = [reviews[i:i + BATCH_SIZE] for i in range(0, len(reviews), BATCH_SIZE)]
    
    logger.info("Starting Batch extraction for %d reviews (Total Batches: %d)", len(reviews), len(batches))
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        futures = [executor.submit(process_batch, b) for b in batches]
        for future in concurrent.futures.as_completed(futures):
            try:
                atoms, bug_c, feat_c, amb_c, noise_c = future.result()
                all_atoms.extend(atoms)
                counters["atoms_written"] += len(atoms)
                counters["routed_bug"] += bug_c
                counters["routed_feature"] += feat_c
                counters["routed_ambiguous"] += amb_c
                counters["skipped_noise"] += noise_c
            except Exception as e:
                logger.error("Batch processing crashed: %s", e)

    # ── Step 4: Final verification ────────────────────────────────────────
    if all_atoms:
        logger.info(
            "Extraction complete for run_id=%s: %d total atoms written", 
            run_id, counters["atoms_written"]
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
