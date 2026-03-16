"""
Feature Request Builder — Phase 4
Reads feature_clusters → writes feature_requests table + CSV export.
"""
import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import OUTPUT_PATH
from database.db import fetch_clusters, insert_feature_requests

logger = logging.getLogger(__name__)


def build_feature_requests(run_id: str) -> dict[str, Any]:
    """
    Build the Feature Request artifact.

    Reads feature_clusters for the given run_id, maps each to a
    feature_requests row, writes to DB and exports CSV.

    Returns:
        {"rows": N, "csv_path": str}
    """
    clusters = fetch_clusters(run_id, "feature")
    if not clusters:
        logger.info("No feature clusters for run_id=%s — skipping", run_id)
        return {"rows": 0, "csv_path": None}

    generated_at = datetime.now(timezone.utc).isoformat()
    rows: list[dict[str, Any]] = []

    for c in clusters:
        row = dict(c)
        rows.append({
            "cluster_id": row["cluster_id"],
            "title": row["cluster_label"],
            "theme": row.get("theme", "Other"),
            "frequency": row.get("frequency", 0),
            "frequency_pct": float(row.get("frequency_pct", 0.0)),
            "product_area": row.get("product_area", "Other"),
            "user_value_summary": row.get("user_value_summary", ""),
            "top_evidence": row.get("top_evidence", "[]"),
            "review_ids": row.get("review_ids", "[]"),
            "signal_confidence": float(row.get("signal_confidence", 0.0)),
            "quality_flag": row.get("quality_flag", "pass"),
            "run_id": run_id,
            "generated_at": generated_at,
        })

    insert_feature_requests(rows)

    # ── CSV export ────────────────────────────────────────────────────
    OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
    csv_path = OUTPUT_PATH / f"{run_id}_feature_requests.csv"
    _export_csv(rows, csv_path)

    logger.info("Features: %d rows written, exported to %s", len(rows), csv_path)
    return {"rows": len(rows), "csv_path": str(csv_path)}


def _export_csv(rows: list[dict], path: Path) -> None:
    """Write rows to CSV."""
    fieldnames = [
        "title", "theme", "frequency", "frequency_pct",
        "product_area", "user_value_summary", "top_evidence",
        "signal_confidence", "quality_flag",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
