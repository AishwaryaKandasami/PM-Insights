"""
Bug Triage Builder — Phase 4
Reads bug_clusters → writes triage_matrix table + CSV export.
"""
import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import OUTPUT_PATH
from database.db import fetch_clusters, insert_triage_matrix

logger = logging.getLogger(__name__)


def build_triage_matrix(run_id: str) -> dict[str, Any]:
    """
    Build the Bug Triage Matrix artifact.

    Reads bug_clusters for the given run_id, maps each to a
    triage_matrix row, writes to DB and exports CSV.

    Returns:
        {"rows": N, "csv_path": str}
    """
    clusters = fetch_clusters(run_id, "bug")
    if not clusters:
        logger.info("No bug clusters for run_id=%s — skipping triage", run_id)
        return {"rows": 0, "csv_path": None}

    generated_at = datetime.now(timezone.utc).isoformat()
    rows: list[dict[str, Any]] = []

    for c in clusters:
        row = dict(c)
        if row.get("cluster_label") == "Unlabeled":
            continue
        rows.append({

            "cluster_id": row["cluster_id"],
            "severity": row.get("severity", "P3"),
            "title": row["cluster_label"],
            "frequency": row.get("frequency", 0),
            "frequency_pct": float(row.get("frequency_pct", 0.0)),
            "product_area": row.get("product_area", "Other"),
            "top_evidence": row.get("top_evidence", "[]"),
            "review_ids": row.get("review_ids", "[]"),
            "signal_confidence": float(row.get("signal_confidence", 0.0)),
            "quality_flag": row.get("quality_flag", "pass"),
            "run_id": run_id,
            "generated_at": generated_at,
        })

    insert_triage_matrix(rows)

    # ── CSV export ────────────────────────────────────────────────────
    OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
    csv_path = OUTPUT_PATH / f"{run_id}_bug_triage.csv"
    _export_csv(rows, csv_path)

    logger.info("Bug triage: %d rows written, exported to %s", len(rows), csv_path)
    return {"rows": len(rows), "csv_path": str(csv_path)}


def _export_csv(rows: list[dict], path: Path) -> None:
    """Write rows to CSV."""
    fieldnames = [
        "severity", "title", "frequency", "frequency_pct",
        "product_area", "top_evidence", "signal_confidence",
        "quality_flag",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
