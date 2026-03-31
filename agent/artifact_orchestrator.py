"""
Artifact Orchestrator — Phase 4
Wires all 4 artifact builders: triage, features, RICE, executive summary.
"""
import logging
from datetime import datetime, timezone
from typing import Any

from database.db import get_pipeline_run, init_db, upsert_pipeline_run
from agent.artifacts.bug_triage_builder import build_triage_matrix
from agent.artifacts.feature_request_builder import build_feature_requests
from agent.artifacts.rice_input_builder import build_rice_inputs
from agent.artifacts.executive_summary_builder import build_executive_summary
from agent.tools.notion_publisher import publish_to_notion
from database.db import fetch_clusters, get_connection

logger = logging.getLogger(__name__)


def run_artifacts(run_id: str) -> dict[str, Any]:
    """
    Generate all 4 PM artifacts for a given run_id.

    Calls each builder sequentially:
    1. Bug Triage Matrix
    2. Feature Requests
    3. RICE Inputs
    4. Executive Summary (Gemini Flash)

    Updates pipeline status to ARTIFACTS_GENERATED on success.

    Returns:
        Combined summary dict with per-builder results.
    """
    init_db()  # Ensure artifact tables exist

    logger.info("Starting artifact generation for run_id=%s", run_id)

    # ── 1. Bug Triage ─────────────────────────────────────────────────
    triage = build_triage_matrix(run_id)
    logger.info("Triage: %s", triage)

    # ── 2. Feature Requests ───────────────────────────────────────────
    features = build_feature_requests(run_id)
    logger.info("Features: %s", features)

    # ── 3. RICE Inputs ────────────────────────────────────────────────
    rice = build_rice_inputs(run_id)
    logger.info("RICE: %s", rice)

    # ── 4. Executive Summary ──────────────────────────────────────────
    summary = build_executive_summary(run_id)
    logger.info("Summary: %s", summary)

    # ── 5. Notion Delivery — Phase 5 ─────────────────────────────────
    from pathlib import Path
    summary_md_path = Path(summary["md_path"])
    if summary_md_path.exists():
        summary_md = summary_md_path.read_text(encoding="utf-8")
        
        # Fetch detailed data for Notion
        bug_rows = fetch_clusters(run_id, "bug")
        bugs = [dict(r) for r in bug_rows] if bug_rows else []
        
        feature_rows = fetch_clusters(run_id, "feature")
        features = [dict(r) for r in feature_rows] if feature_rows else []
        
        with get_connection() as conn:
            cur = conn.execute("SELECT * FROM rice_inputs WHERE run_id = ?", (run_id,))
            cols = [desc[0] for desc in cur.description]
            rice_data = [dict(zip(cols, row)) for row in cur.fetchall()]
            
        try:
            notion_result = publish_to_notion(run_id, summary_md, bugs, features, rice_data)
            logger.info("Notion delivery complete: %s", notion_result)
            result_notion_url = f"https://www.notion.so/{notion_result['page_id'].replace('-', '')}"
        except Exception as e:
            logger.error("Notion delivery failed: %s", e)
            result_notion_url = None
    else:
        result_notion_url = None



    # ── Update pipeline status ────────────────────────────────────────
    existing = get_pipeline_run(run_id)
    now_iso = datetime.now(timezone.utc).isoformat()
    upsert_pipeline_run({
        "run_id": run_id,
        "status": "ARTIFACTS_GENERATED",
        "source_type": existing["source_type"] if existing else None,
        "source_file": existing["source_file"] if existing else None,
        "app_id": existing["app_id"] if existing else None,
        "total_reviews": existing["total_reviews"] if existing else None,
        "supported_reviews": existing["supported_reviews"] if existing else None,
        "duplicate_count": existing["duplicate_count"] if existing else None,
        "low_quality_count": existing["low_quality_count"] if existing else None,
        "current_step": "artifacts",
        "error_message": None,
        "started_at": existing["started_at"] if existing else now_iso,
        "completed_at": now_iso,
    })

    result = {
        "triage_rows": triage["rows"],
        "triage_csv": triage["csv_path"],
        "feature_rows": features["rows"],
        "feature_csv": features["csv_path"],
        "rice_rows": rice["rows"],
        "rice_csv": rice["csv_path"],
        "summary_metrics": summary["metrics"],
        "summary_md": summary["md_path"],
        "notion_url": result_notion_url,
    }
    logger.info("Artifact generation complete for run_id=%s: %s", run_id, result)
    return result
