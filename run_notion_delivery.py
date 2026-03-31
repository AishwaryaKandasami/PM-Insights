"""
Run Notion Delivery — Phase 5
Top-level script to push artifacts from a run to Notion.
"""
import sys
import os
import argparse
import logging
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

from agent.tools.notion_publisher import publish_to_notion
from database.db import fetch_clusters, get_pipeline_run
from config.settings import OUTPUT_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Deliver artifacts to Notion.")
    parser.add_argument("--run_id", type=str, required=True, help="Run ID to deliver.")
    args = parser.parse_args()

    run_id = args.run_id
    logger.info("Starting Notion delivery for run_id: %s", run_id)

    # 1. Fetch Summary MD
    summary_md_path = OUTPUT_PATH / f"{run_id}_executive_summary.md"
    if not summary_md_path.exists():
        logger.error("Executive summary MD not found at %s. Please run Phase 4 first.", summary_md_path)
        return

    summary_md = summary_md_path.read_text(encoding="utf-8")

    # 2. Fetch Data from Gold Tables
    try:
        # Bugs
        bug_rows = fetch_clusters(run_id, "bug")
        bugs = [dict(r) for r in bug_rows] if bug_rows else []
        
        # Features
        feature_rows = fetch_clusters(run_id, "feature")
        features = [dict(r) for r in feature_rows] if feature_rows else []
        
        # RICE (Note: RICE inputs are usually in a separate table)
        from database.db import get_connection
        rice = []
        with get_connection() as conn:
            cur = conn.execute("SELECT * FROM rice_inputs WHERE run_id = ?", (run_id,))
            cols = [desc[0] for desc in cur.description]
            rice = [dict(zip(cols, row)) for row in cur.fetchall()]

        if not bugs and not features and not rice:
            logger.warning("No artifacts found in database for run_id: %s", run_id)
            # Proceed anyway? Maybe just to push the summary?
        
        # 3. Publish to Notion
        result = publish_to_notion(run_id, summary_md, bugs, features, rice)
        
        logger.info("✅ Successfully published to Notion!")
        logger.info("View your Insights at: https://www.notion.so/%s", result["page_id"].replace("-", ""))

    except Exception as e:
        logger.error("❌ Notion delivery failed: %s", e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
