"""
Executive Summary Builder — Phase 4
Calls Gemini Flash to generate a structured markdown summary,
writes key metrics to dashboard_metrics, exports MD file.
"""
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import os
from groq import Groq

from agent.prompts import executive_summary_prompt
from config.settings import (
    MIN_DELAY_SECONDS,
    OUTPUT_PATH,
)
from database.db import (
    fetch_clusters,
    get_pipeline_run,
    insert_dashboard_metrics,
)

logger = logging.getLogger(__name__)


def _format_bug_data(clusters: list[dict]) -> str:
    """Format bug clusters into a text block for the prompt."""
    if not clusters:
        return "(none)"
    lines = []
    for c in clusters:
        evidence = c.get("top_evidence", "[]")
        try:
            quotes = json.loads(evidence) if isinstance(evidence, str) else evidence
            quote = quotes[0] if quotes else "—"
        except (json.JSONDecodeError, IndexError):
            quote = "—"
        lines.append(
            f"- [{c.get('severity', 'P3')}] {c.get('cluster_label', '?')} "
            f"| freq={c.get('frequency', 0)} ({c.get('frequency_pct', 0):.1f}%) "
            f"| area={c.get('product_area', '?')} "
            f"| evidence: \"{quote}\""
        )
    return "\n".join(lines)


def _format_feature_data(clusters: list[dict]) -> str:
    """Format feature clusters into a text block for the prompt."""
    if not clusters:
        return "(none)"
    lines = []
    for c in clusters:
        lines.append(
            f"- [{c.get('theme', 'Other')}] {c.get('cluster_label', '?')} "
            f"| freq={c.get('frequency', 0)} ({c.get('frequency_pct', 0):.1f}%) "
            f"| area={c.get('product_area', '?')} "
            f"| value: \"{c.get('user_value_summary', '—')}\""
        )
    return "\n".join(lines)


def build_executive_summary(run_id: str) -> dict[str, Any]:
    """
    Generate an executive summary using Groq Llama with a strict 1-page template.

    Reads clusters + pipeline metadata, calls LLM, writes metrics
    to dashboard_metrics, exports markdown to outputs/.

    Returns:
        {"metrics": N, "md_path": str}
    """
    from database.db import get_connection

    bug_rows = fetch_clusters(run_id, "bug")
    feature_rows = fetch_clusters(run_id, "feature")
    pipeline = get_pipeline_run(run_id)

    bug_clusters = [dict(r) for r in bug_rows] if bug_rows else []
    feature_clusters = [dict(r) for r in feature_rows] if feature_rows else []

    total_reviews = pipeline["total_reviews"] if pipeline else 0
    usable_reviews = pipeline["supported_reviews"] if pipeline else 0

    flagged_bugs = sum(1 for c in bug_clusters if c.get("quality_flag") == "review")
    flagged_features = sum(1 for c in feature_clusters if c.get("quality_flag") == "review")

    # ── Fetch Date Range ──────────────────────────────────────────────
    date_range = "Recent"
    try:
        with get_connection() as conn:
            cur = conn.execute(
                "SELECT MIN(date), MAX(date) FROM raw_reviews WHERE run_id = ?",
                (run_id,)
            )
            dates = cur.fetchone()
            if dates and dates[0] and dates[1]:
                # Simplify to YYYY-MM-DD
                d_min = str(dates[0])[:10]
                d_max = str(dates[1])[:10]
                date_range = f"{d_min} to {d_max}"
    except Exception:
        pass

    # ── Calculate Avg Confidence ──────────────────────────────────────
    all_clusters = bug_clusters + feature_clusters
    avg_conf = 0.0
    if all_clusters:
        avg_conf = sum(float(c.get("signal_confidence", 0.0)) for c in all_clusters) / len(all_clusters)

    # ── Generate summary via Groq Llama ───────────────────────────────
    prompt = executive_summary_prompt.USER_TMPL.format(
        date_range=date_range,
        total_reviews=total_reviews or "0",
        bug_count=len(bug_clusters),
        bug_data=_format_bug_data(bug_clusters[:3]),
        feature_count=len(feature_clusters),
        feature_data=_format_feature_data(feature_clusters[:3]),
        flagged_total=flagged_bugs + flagged_features,
        avg_confidence=avg_conf,
    )

    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": executive_summary_prompt.SYSTEM},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0,
        )
        summary_md = response.choices[0].message.content.strip()
        logger.info("Executive summary generated (%d chars)", len(summary_md))
    except Exception as exc:
        logger.error("Executive summary generation failed: %s", exc)
        summary_md = f"## Executive Summary\n\n_Generation failed: {exc}_"
    finally:
        time.sleep(MIN_DELAY_SECONDS)



    # ── Write dashboard_metrics ───────────────────────────────────────
    generated_at = datetime.now(timezone.utc).isoformat()
    metrics: list[dict[str, Any]] = [
        {"metric_name": "total_reviews", "metric_value": str(total_reviews or 0),
         "category": "overview", "run_id": run_id, "generated_at": generated_at},
        {"metric_name": "usable_reviews", "metric_value": str(usable_reviews or 0),
         "category": "overview", "run_id": run_id, "generated_at": generated_at},
        {"metric_name": "bug_clusters", "metric_value": str(len(bug_clusters)),
         "category": "bugs", "run_id": run_id, "generated_at": generated_at},
        {"metric_name": "feature_clusters", "metric_value": str(len(feature_clusters)),
         "category": "features", "run_id": run_id, "generated_at": generated_at},
        {"metric_name": "flagged_bugs", "metric_value": str(flagged_bugs),
         "category": "quality", "run_id": run_id, "generated_at": generated_at},
        {"metric_name": "flagged_features", "metric_value": str(flagged_features),
         "category": "quality", "run_id": run_id, "generated_at": generated_at},
    ]
    insert_dashboard_metrics(metrics)

    # ── Export markdown ───────────────────────────────────────────────
    OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
    md_path = OUTPUT_PATH / f"{run_id}_executive_summary.md"
    md_path.write_text(summary_md, encoding="utf-8")

    logger.info("Executive summary: %d metrics, exported to %s", len(metrics), md_path)
    return {"metrics": len(metrics), "md_path": str(md_path)}
