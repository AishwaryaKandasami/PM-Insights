import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Dict

import pandas as pd

from config.settings import RAW_DATA_PATH
from database.db import insert_raw_reviews, upsert_pipeline_run


logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when CSV validation fails."""


def _validate_csv(path: str) -> pd.DataFrame:
    if not path.lower().endswith(".csv"):
        raise ValidationError("File must be in CSV format.")

    try:
        df = pd.read_csv(path)
    except Exception as exc:
        raise ValidationError(f"Unable to read CSV file: {exc}") from exc

    required_cols = {"review_id", "text", "date"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValidationError(
            f"Missing required columns: {', '.join(sorted(missing))}"
        )

    if len(df) <= 10:
        raise ValidationError("CSV must contain more than 10 rows.")

    empty_text_mask = df["text"].isna() | (df["text"].astype(str).str.strip() == "")
    empty_text_count = int(empty_text_mask.sum())
    empty_pct = empty_text_count / len(df)
    if empty_pct > 0.20:
        pct_str = f"{empty_pct:.2%}"
        raise ValidationError(
            f"text column has {pct_str} empty rows (allowed maximum is 20%)."
        )

    return df


def load_and_validate(
    file_path: str,
    source_type: str = "uploaded",
    app_id: str | None = None,
) -> Dict:
    """
    Validate a CSV file and load rows into raw_reviews.

    Returns a validation summary dictionary.
    """
    RAW_DATA_PATH.mkdir(parents=True, exist_ok=True)

    df = _validate_csv(file_path)

    run_id = f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
    ingested_at = datetime.now(timezone.utc).isoformat()

    # Deduplication detection (by review_id, then text+date hash)
    seen_ids: set[str] = set()
    seen_text_date: set[tuple[str, str]] = set()
    duplicate_count = 0
    empty_text_count = 0

    rows = []
    for _, row in df.iterrows():
        review_id = str(row["review_id"])
        text = "" if pd.isna(row["text"]) else str(row["text"])
        date = "" if pd.isna(row["date"]) else str(row["date"])

        if not text.strip():
            empty_text_count += 1

        is_dup = False
        if review_id in seen_ids:
            is_dup = True
        else:
            key = (text.strip(), date.strip())
            if key in seen_text_date:
                is_dup = True
            else:
                seen_ids.add(review_id)
                seen_text_date.add(key)

        if is_dup:
            duplicate_count += 1

        rows.append(
            {
                "review_id": review_id,
                "source_file": os.path.abspath(file_path),
                "source_type": source_type,
                "app_id": app_id,
                "raw_text": text,
                "rating": int(row["rating"]) if "rating" in df.columns and not pd.isna(row["rating"]) else None,
                "date": date,
                "app_version": str(row["app_version"]) if "app_version" in df.columns and not pd.isna(row["app_version"]) else None,
                "device": str(row["device"]) if "device" in df.columns and not pd.isna(row["device"]) else None,
                "locale": str(row["locale"]) if "locale" in df.columns and not pd.isna(row["locale"]) else None,
                "thumbs_up": int(row["thumbs_up"]) if "thumbs_up" in df.columns and not pd.isna(row["thumbs_up"]) else None,
                "ingested_at": ingested_at,
                "run_id": run_id,
            }
        )

    insert_raw_reviews(rows)

    pipeline_run = {
        "run_id": run_id,
        "status": "INGESTED",
        "source_type": source_type,
        "source_file": os.path.abspath(file_path),
        "app_id": app_id,
        "total_reviews": len(df),
        "supported_reviews": None,
        "duplicate_count": duplicate_count,
        "low_quality_count": None,
        "current_step": "ingestion",
        "error_message": None,
        "started_at": ingested_at,
        "completed_at": None,
    }
    upsert_pipeline_run(pipeline_run)

    summary = {
        "total_rows": int(len(df)),
        "duplicate_count": int(duplicate_count),
        "empty_text_count": int(empty_text_count),
        "run_id": run_id,
        "output_file": os.path.abspath(file_path),
    }
    logger.info("Ingestion complete for run_id=%s: %s", run_id, summary)
    return summary

