"""
Notion Publisher — Phase 5
Handles creating pages and databases in Notion and populating them with PM artifacts.
"""
import logging
import json
from typing import Any, Optional
from notion_client import Client
from config.settings import (
    NOTION_TOKEN,
    NOTION_PAGE_ID,
    NOTION_DATABASE_NAME_BUGS,
    NOTION_DATABASE_NAME_FEATURES,
    NOTION_DATABASE_NAME_RICE
)

logger = logging.getLogger(__name__)

class NotionPublisher:
    def __init__(self):
        if not NOTION_TOKEN:
            raise ValueError("NOTION_TOKEN not found in environment.")
        self.notion = Client(auth=NOTION_TOKEN)
        
        # Clean the page_id in case it's a full URL
        raw_id = NOTION_PAGE_ID or ""
        logger.info("Raw NOTION_PAGE_ID: %s", raw_id)
        
        # Notion IDs are effectively 32-character hex strings
        # URL format: https://www.notion.so/workspace/Page-Title-334b30f5286ff80f6b0ecdeffbd3348eb
        
        # 1. Strip query params
        id_part = raw_id.split("?")[0]
        # 2. Get the last part of the path
        id_part = id_part.split("/")[-1]
        # 3. Get the last 32 hex characters
        import re
        all_hex = "".join(re.findall(r"[a-f0-9]", id_part.lower()))
        
        if len(all_hex) >= 32:
            # Usually the ID is the LAST 32 characters of the hex string in a Notion URL
            self.parent_page_id = all_hex[-32:]
        else:
            self.parent_page_id = all_hex
            
        logger.info("Extracted Notion Page ID: %s (length %d)", self.parent_page_id, len(self.parent_page_id))

    def create_run_page(self, run_id: str, title: str) -> str:
        """Creates a new sub-page for this run."""
        new_page = self.notion.pages.create(
            parent={"page_id": self.parent_page_id},
            properties={
                "title": [
                    {
                        "text": {
                            "content": title
                        }
                    }
                ]
            }
        )
        return new_page["id"]

    def add_summary_content(self, page_id: str, markdown_content: str):
        """Adds the executive summary as blocks to the page."""
        # Very basic MD to Notion block conversion for now
        # We can enhance this later
        lines = markdown_content.split("\n")
        blocks = []
        for line in lines:
            if not line.strip():
                continue
            if line.startswith("# "):
                blocks.append({
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {"rich_text": [{"type": "text", "text": {"content": line[2:].strip()}}]}
                })
            elif line.startswith("## "):
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {"rich_text": [{"type": "text", "text": {"content": line[3:].strip()}}]}
                })
            elif line.startswith("- "):
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": line[2:].strip()}}]}
                })
            else:
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"type": "text", "text": {"content": line.strip()}}]}
                })
        
        # Batch append (Notion limit is 100 per call)
        for i in range(0, len(blocks), 100):
            self.notion.blocks.children.append(block_id=page_id, children=blocks[i:i+100])

    def create_database(self, parent_page_id: str, title: str, properties: dict) -> str:
        """Creates a database in Notion."""
        db = self.notion.databases.create(
            parent={"page_id": parent_page_id},
            title=[{"type": "text", "text": {"content": title}}],
            properties=properties
        )
        return db["id"]

    def insert_rows(self, database_id: str, rows: list[dict]):
        """Inserts multiple rows into a database."""
        for row in rows:
            self.notion.pages.create(
                parent={"database_id": database_id},
                properties=row
            )

def publish_to_notion(run_id: str, summary_md: str, bugs: list[dict], features: list[dict], rice: list[dict]):
    """Orchestrates the full push to Notion."""
    try:
        publisher = NotionPublisher()
        run_title = f"PM Insights Run: {run_id}"
        logger.info("Publishing %s to Notion...", run_title)
        
        # 1. Create Parent Page
        run_page_id = publisher.create_run_page(run_id, run_title)
        logger.info("Created run page: %s", run_page_id)
        
        # 2. Add Executive Summary
        publisher.add_summary_content(run_page_id, summary_md)
        
        # 3. Create & Populate Bug Database
        bug_props = {
            "Title": {"title": {}},
            "Severity": {"select": {"options": [
                {"name": "P0", "color": "red"},
                {"name": "P1", "color": "orange"},
                {"name": "P2", "color": "yellow"},
                {"name": "P3", "color": "gray"}
            ]}},
            "Product Area": {"select": {}},
            "Frequency (%)": {"number": {"format": "percent"}},
            "Signal Confidence": {"number": {"format": "number"}},
            "Evidence Sample": {"rich_text": {}}
        }
        bug_db_id = publisher.create_database(run_page_id, NOTION_DATABASE_NAME_BUGS, bug_props)
        bug_rows = []
        for b in bugs:
            # Format Evidence properly (can be list or JSON string)
            evidence = b.get("top_evidence", "[]")
            try:
                evidence_list = json.loads(evidence) if isinstance(evidence, str) else evidence
                evidence_str = evidence_list[0] if evidence_list else "—"
            except (json.JSONDecodeError, IndexError):
                evidence_str = "—"
                
            bug_rows.append({
                "Title": {"title": [{"text": {"content": str(b.get("cluster_label", "Unknown"))}}]},
                "Severity": {"select": {"name": str(b.get("severity", "P3"))}},
                "Product Area": {"select": {"name": str(b.get("product_area", "Other"))}},
                "Frequency (%)": {"number": b.get("frequency_pct", 0) / 100},
                "Signal Confidence": {"number": float(b.get("signal_confidence", 0.0))},
                "Evidence Sample": {"rich_text": [{"text": {"content": evidence_str[:2000]}}]} # Notion limit
            })
        publisher.insert_rows(bug_db_id, bug_rows)
        logger.info("Published %d bugs", len(bug_rows))

        # 4. Create & Populate Feature Database
        feat_props = {
            "Title": {"title": {}},
            "Theme": {"select": {}},
            "Frequency (%)": {"number": {"format": "percent"}},
            "User Value Summary": {"rich_text": {}}
        }
        feat_db_id = publisher.create_database(run_page_id, NOTION_DATABASE_NAME_FEATURES, feat_props)
        feat_rows = []
        for f in features:
            feat_rows.append({
                "Title": {"title": [{"text": {"content": str(f.get("cluster_label", "Unknown"))}}]},
                "Theme": {"select": {"name": str(f.get("theme", "Other"))}},
                "Frequency (%)": {"number": f.get("frequency_pct", 0) / 100},
                "User Value Summary": {"rich_text": [{"text": {"content": str(f.get("user_value_summary", "—"))[:2000]}}]}
            })
        publisher.insert_rows(feat_db_id, feat_rows)
        logger.info("Published %d features", len(feat_rows))

        # 5. Create & Populate RICE Database
        rice_props = {
            "Title": {"title": {}},
            "Reach": {"number": {}},
            "Impact": {"number": {}},
            "Confidence": {"number": {"format": "percent"}},
            "Effort": {"number": {}},
            "Score": {"formula": {"expression": "(prop(\"Reach\") * prop(\"Impact\") * prop(\"Confidence\")) / prop(\"Effort\")"}}
        }
        # Note: Notion API doesn't support creating formulas via create_database easily in V1, 
        # so we'll just omit the formula if it causes issues or just use Number.
        rice_props = {
            "Title": {"title": {}},
            "Reach (Reviews)": {"number": {}},
            "Impact (Proxy)": {"number": {}},
            "Confidence (Signal)": {"number": {"format": "percent"}},
            "Effort (TBD)": {"number": {}}
        }
        rice_db_id = publisher.create_database(run_page_id, NOTION_DATABASE_NAME_RICE, rice_props)
        rice_rows = []
        for r in rice:
            raw_impact = r.get("impact", 0)
            if isinstance(raw_impact, str):
                # Map P0/P1/P2 to numerical impact weights
                impact_map = {"P0": 3.0, "P1": 2.0, "P2": 1.0, "P3": 0.5}
                impact_val = impact_map.get(raw_impact, 0.5)
            else:
                try:
                    impact_val = float(raw_impact or 0)
                except ValueError:
                    impact_val = 0.5
            
            rice_rows.append({
                "Title": {"title": [{"text": {"content": str(r.get("title", "Unknown"))}}]},
                "Reach (Reviews)": {"number": float(r.get("reach", 0))},
                "Impact (Proxy)": {"number": impact_val},
                "Confidence (Signal)": {"number": float(r.get("signal_confidence", 0.0))},
                "Effort (TBD)": {"number": float(r.get("effort", 0)) if r.get("effort") else 0}
            })
        publisher.insert_rows(rice_db_id, rice_rows)
        logger.info("Published %d RICE items", len(rice_rows))

        return {"page_id": run_page_id}

    except Exception as e:
        logger.error("Failed to publish to Notion: %s", e)
        raise e
