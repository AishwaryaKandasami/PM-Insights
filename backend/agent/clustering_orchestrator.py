"""
Clustering Orchestrator — Phase 3
Agent loop: embed → cluster → label → score → judge → write clusters.
Processes bugs and features separately.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from database.db import (
    fetch_atoms_by_type,
    get_pipeline_run,
    init_db,
    insert_bug_clusters,
    insert_feature_clusters,
    upsert_pipeline_run,
)
from agent.tools.embedder import embed_texts
from agent.tools.clusterer import cluster_atoms
from agent.tools.cluster_labeler import label_clusters
from agent.tools.scorer import score_clusters
from agent.tools.judge import judge_clusters

logger = logging.getLogger(__name__)


def _atoms_to_dicts(rows) -> list[dict]:
    """Convert sqlite3.Row objects to plain dicts."""
    return [dict(r) for r in rows]


def _embed_key(atom: dict) -> str:
    """Build the text to embed for an atom (title + description)."""
    title = atom.get("title", "")
    desc = atom.get("description", "")
    return f"{title}. {desc}".strip()


def _process_type(
    run_id: str,
    atom_type: str,
    clustered_at: str,
) -> dict[str, Any]:
    """
    Full clustering pipeline for one atom type.

    Returns summary dict with cluster count and flagged count.
    """
    # ── Step 1: Fetch atoms ───────────────────────────────────────────
    rows = fetch_atoms_by_type(run_id, atom_type)
    atoms = _atoms_to_dicts(rows)
    if not atoms:
        logger.info("No %s atoms found for run_id=%s — skipping", atom_type, run_id)
        return {"clusters": 0, "flagged": 0, "atoms": 0}

    logger.info("Processing %d %s atoms for clustering", len(atoms), atom_type)

    # ── Step 2: Embed ─────────────────────────────────────────────────
    texts = [_embed_key(a) for a in atoms]
    embeddings = embed_texts(texts)

    # ── Step 3: Cluster ───────────────────────────────────────────────
    clusters = cluster_atoms(atoms, embeddings)

    # ── Step 4: Label ─────────────────────────────────────────────────
    clusters = label_clusters(clusters, atom_type)

    # ── Step 5: Score ─────────────────────────────────────────────────
    clusters = score_clusters(clusters, len(atoms), atom_type)

    # ── Step 6: Judge ─────────────────────────────────────────────────
    clusters = judge_clusters(clusters, atom_type)

    # ── Step 7: Write to DB ───────────────────────────────────────────
    db_rows = []
    for cluster in clusters:
        row: dict[str, Any] = {
            "cluster_label": cluster.get("cluster_label", "Unlabeled"),
            "frequency": cluster.get("frequency", 0),
            "frequency_pct": cluster.get("frequency_pct", 0.0),
            "product_area": cluster.get("product_area", "Other"),
            "top_evidence": cluster.get("top_evidence", "[]"),
            "review_ids": cluster.get("review_ids", "[]"),
            "atom_ids": cluster.get("atom_ids", "[]"),
            "cohesion_score": cluster.get("cohesion_score", 0.0),
            "signal_confidence": cluster.get("signal_confidence", 0.0),
            "quality_flag": cluster.get("quality_flag", "pass"),
            "quality_notes": cluster.get("quality_notes", ""),
            "run_id": run_id,
            "clustered_at": clustered_at,
        }
        if atom_type == "bug":
            row["severity"] = cluster.get("severity", "P3")
        else:
            row["theme"] = cluster.get("theme", "Other")
            row["user_value_summary"] = cluster.get("user_value_summary", "")
        db_rows.append(row)

    if atom_type == "bug":
        insert_bug_clusters(db_rows)
    else:
        insert_feature_clusters(db_rows)

    flagged = sum(1 for c in clusters if c.get("quality_flag") == "review")
    logger.info(
        "Wrote %d %s clusters (%d flagged) for run_id=%s",
        len(clusters), atom_type, flagged, run_id,
    )
    return {"clusters": len(clusters), "flagged": flagged, "atoms": len(atoms)}


def run_clustering(run_id: str) -> dict:
    """
    Full Phase 3 agent loop:
    Process bugs and features separately through embed → cluster → label → score → judge.

    Args:
        run_id: Pipeline run_id that has extracted atoms.

    Returns:
        Summary dict with bug/feature cluster counts and flagged counts.
    """
    init_db()  # Ensure cluster tables exist
    clustered_at = datetime.now(timezone.utc).isoformat()

    logger.info("Starting clustering for run_id=%s", run_id)

    # ── Process bugs ──────────────────────────────────────────────────
    bug_summary = _process_type(run_id, "bug", clustered_at)

    # ── Process features ──────────────────────────────────────────────
    feature_summary = _process_type(run_id, "feature", clustered_at)

    # ── Update pipeline status ────────────────────────────────────────
    existing = get_pipeline_run(run_id)
    now_iso = datetime.now(timezone.utc).isoformat()
    upsert_pipeline_run({
        "run_id": run_id,
        "status": "CLUSTERED",
        "source_type": existing["source_type"] if existing else None,
        "source_file": existing["source_file"] if existing else None,
        "app_id": existing["app_id"] if existing else None,
        "total_reviews": existing["total_reviews"] if existing else None,
        "supported_reviews": existing["supported_reviews"] if existing else None,
        "duplicate_count": existing["duplicate_count"] if existing else None,
        "low_quality_count": existing["low_quality_count"] if existing else None,
        "current_step": "clustering",
        "error_message": None,
        "started_at": existing["started_at"] if existing else now_iso,
        "completed_at": now_iso,
    })

    result = {
        "bug_clusters": bug_summary["clusters"],
        "bug_flagged": bug_summary["flagged"],
        "bug_atoms": bug_summary["atoms"],
        "feature_clusters": feature_summary["clusters"],
        "feature_flagged": feature_summary["flagged"],
        "feature_atoms": feature_summary["atoms"],
    }
    logger.info("Clustering complete for run_id=%s: %s", run_id, result)
    return result
