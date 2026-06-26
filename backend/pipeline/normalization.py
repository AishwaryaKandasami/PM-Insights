import logging
import re
from datetime import datetime, timezone
from typing import Dict

from langdetect import DetectorFactory, LangDetectException, detect

from database.db import (
    fetch_raw_reviews_by_run,
    get_pipeline_run,
    insert_reviews_normalized,
    upsert_pipeline_run,
)


logger = logging.getLogger(__name__)

# Make langdetect deterministic
DetectorFactory.seed = 0


EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(
    r"(\+?\d{1,3}[-.\s]?)?(\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}"
)


def _clean_text(text: str) -> str:
    # Normalize whitespace, preserve emojis, strip leading/trailing spaces
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse runs of whitespace to single spaces, but keep newlines
    text = re.sub(r"[ \t\f\v]+", " ", text)
    # Remove obvious repeated boilerplate lines if they appear more than once
    lines = [line.strip() for line in text.split("\n")]
    seen = set()
    deduped_lines = []
    for line in lines:
        key = line.lower()
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        deduped_lines.append(line)
    cleaned = "\n".join(deduped_lines).strip()
    return cleaned


def _detect_language(text: str) -> str:
    try:
        return detect(text)
    except LangDetectException:
        # Assume English if detection fails
        return "en"


def _mask_pii(text: str) -> tuple[str, bool]:
    pii_found = False

    def _replace_email(match: re.Match) -> str:
        nonlocal pii_found
        pii_found = True
        return "[EMAIL]"

    def _replace_phone(match: re.Match) -> str:
        nonlocal pii_found
        pii_found = True
        return "[PHONE]"

    text = EMAIL_REGEX.sub(_replace_email, text)
    text = PHONE_REGEX.sub(_replace_phone, text)
    return text, pii_found


def normalize_reviews(run_id: str) -> Dict:
    """
    Normalize and enrich reviews for a given run_id and write to reviews_normalized.
    """
    raw_rows = fetch_raw_reviews_by_run(run_id)
    if not raw_rows:
        logger.warning("No raw reviews found for run_id=%s", run_id)
        return {
            "total_processed": 0,
            "supported_count": 0,
            "unsupported_count": 0,
            "pii_masked_count": 0,
            "low_quality_count": 0,
        }

    normalized_rows = []
    now_iso = datetime.now(timezone.utc).isoformat()

    supported_count = 0
    unsupported_count = 0
    pii_masked_count = 0
    low_quality_count = 0

    seen_ids: set[str] = set()
    seen_text_date: set[tuple[str, str]] = set()
    duplicate_count = 0

    for row in raw_rows:
        review_id = str(row["review_id"])
        original_text = row["raw_text"] or ""
        cleaned = _clean_text(original_text)

        masked_text, has_pii = _mask_pii(cleaned)
        if has_pii:
            pii_masked_count += 1

        words = masked_text.split()
        word_count = len(words)
        char_count = len(masked_text)
        is_low_quality = word_count < 3

        # Skip langdetect for very short reviews — insufficient signal causes
        # misclassification of common English words as other languages.
        # Strings under 5 words are assumed to be English.
        if word_count < 5:
            lang = "en"
        else:
            lang = _detect_language(masked_text or original_text or "")
        is_supported = lang == "en"
        if is_supported:
            supported_count += 1
        else:
            unsupported_count += 1

        # Duplicate detection using the same strategy as ingestion
        date_str = row["date"] or ""
        key = (cleaned.strip(), date_str.strip())
        is_duplicate = False
        if review_id in seen_ids or key in seen_text_date:
            is_duplicate = True
            duplicate_count += 1
        else:
            seen_ids.add(review_id)
            seen_text_date.add(key)
        if is_low_quality:
            low_quality_count += 1

        normalized_rows.append(
            {
                "review_id": review_id,
                "original_text": original_text,
                "cleaned_text": masked_text,
                "detected_language": lang,
                "is_supported": bool(is_supported),
                "is_duplicate": bool(is_duplicate),
                "is_low_quality": bool(is_low_quality),
                "pii_masked": bool(has_pii),
                "word_count": word_count,
                "char_count": char_count,
                "normalized_at": now_iso,
                "run_id": run_id,
            }
        )

    insert_reviews_normalized(normalized_rows)

    # Update pipeline_runs aggregate fields
    existing = get_pipeline_run(run_id)
    started_at = existing["started_at"] if existing and existing["started_at"] else now_iso
    run_record = {
        "run_id": run_id,
        "status": "NORMALIZED",
        "source_type": existing["source_type"] if existing else None,
        "source_file": existing["source_file"] if existing else None,
        "app_id": existing["app_id"] if existing else None,
        "total_reviews": existing["total_reviews"] if existing else len(raw_rows),
        "supported_reviews": supported_count,
        "duplicate_count": duplicate_count,
        "low_quality_count": low_quality_count,
        "current_step": "normalization",
        "error_message": None,
        "started_at": started_at,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    upsert_pipeline_run(run_record)

    summary = {
        "total_processed": len(raw_rows),
        "supported_count": supported_count,
        "unsupported_count": unsupported_count,
        "pii_masked_count": pii_masked_count,
        "low_quality_count": low_quality_count,
    }
    logger.info("Normalization complete for run_id=%s: %s", run_id, summary)
    return summary

