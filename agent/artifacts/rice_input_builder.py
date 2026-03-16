"""
RICE Input Builder — Phase 4
Merges bug + feature clusters → writes rice_inputs table + CSV export.
Effort column left blank for PM to complete.
"""
import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import OUTPUT_PATH
from database.db import fetch_clusters, insert_rice_inputs

logger = logging.getLogger(__name__)

_CONFIDENCE_NOTE = (
    "Reflects data quality only — PM completes Confidence column"
)


def build_rice_inputs(run_id: str) -> dict[str, Any]:
    """
    Build RICE-ready Prioritisation Inputs.

    Merges bug and feature clusters into a single RICE table.
    - Reach = cluster frequency (unique review count)
    - Impact = severity band (bugs) or theme (features)
    - Signal Confidence = data quality score (NOT RICE Confidence)
    - Effort = blank — PM to complete
    - RICE Score = blank — PM to complete

    Returns:
        {"rows": N, "csv_path": str}
    """
    bug_clusters = fetch_clusters(run_id, "bug")
    feature_clusters = fetch_clusters(run_id, "feature")

    if not bug_clusters and not feature_clusters:
        logger.info("No clusters for run_id=%s — skipping RICE", run_id)
        return {"rows": 0, "csv_path": None}

    generated_at = datetime.now(timezone.utc).isoformat()
    rows: list[dict[str, Any]] = []

    for c in bug_clusters:
        row = dict(c)
        rows.append({
            "source_type": "bug",
            "cluster_id": row["cluster_id"],
            "title": row["cluster_label"],
            "reach": row.get("frequency", 0),
            "impact": row.get("severity", "P3"),
            "signal_confidence": float(row.get("signal_confidence", 0.0)),
            "confidence_note": _CONFIDENCE_NOTE,
            "effort": "",
            "rice_score": "",
            "run_id": run_id,
            "generated_at": generated_at,
        })

    for c in feature_clusters:
        row = dict(c)
        rows.append({
            "source_type": "feature",
            "cluster_id": row["cluster_id"],
            "title": row["cluster_label"],
            "reach": row.get("frequency", 0),
            "impact": row.get("theme", "Other"),
            "signal_confidence": float(row.get("signal_confidence", 0.0)),
            "confidence_note": _CONFIDENCE_NOTE,
            "effort": "",
            "rice_score": "",
            "run_id": run_id,
            "generated_at": generated_at,
        })

    insert_rice_inputs(rows)

    # ── CSV export ────────────────────────────────────────────────────
    OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
    csv_path = OUTPUT_PATH / f"{run_id}_rice_inputs.csv"
    _export_csv(rows, csv_path)

    logger.info("RICE: %d rows written, exported to %s", len(rows), csv_path)
    return {"rows": len(rows), "csv_path": str(csv_path)}


def _export_csv(rows: list[dict], path: Path) -> None:
    """Write rows to CSV."""
    fieldnames = [
        "source_type", "title", "reach", "impact",
        "signal_confidence", "confidence_note", "effort", "rice_score",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
