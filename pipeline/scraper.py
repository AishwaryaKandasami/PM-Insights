import csv
import logging
import random
import time
import uuid
from datetime import datetime
from datetime import timezone as dt_timezone
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Callable

from dateutil.relativedelta import relativedelta
from google_play_scraper import Sort, reviews

from config.settings import (
    RAW_DATA_PATH,
    SCRAPER_BASE_DELAY,
    SCRAPER_BATCH_SIZE,
    SCRAPER_MAX_JITTER,
)
from database.db import insert_scrape_log


logger = logging.getLogger(__name__)


class ScraperError(Exception):
    """Raised when scraping fails in a non-recoverable way."""


_progress_callback: Optional[Callable[[Dict], None]] = None


def set_progress_callback(callback: Optional[Callable[[Dict], None]]) -> None:
    """
    Set a callable that will receive progress updates during scraping.

    The callback will be invoked after each batch with a dict:
      {
        "batch_index": int,
        "total_collected": int,
        "latest_date": str | None,
        "oldest_date": str | None,
      }
    """
    global _progress_callback
    _progress_callback = callback


def _calculate_cutoff_date(months_back: int) -> datetime:
    today = datetime.now(dt_timezone.utc)
    # Use first day of the month `months_back` ago as cutoff
    target = today - relativedelta(months=months_back)
    cutoff = datetime(target.year, target.month, 1, tzinfo=dt_timezone.utc)
    return cutoff


def _sleep_with_jitter() -> None:
    delay = SCRAPER_BASE_DELAY + random.random() * SCRAPER_MAX_JITTER
    time.sleep(delay)


def _parse_review_dates(batch: List[Dict]) -> Tuple[Optional[datetime], Optional[datetime]]:
    dates = [r["at"] for r in batch if isinstance(r.get("at"), datetime)]
    if not dates:
        return None, None
    newest = max(dates)
    oldest = min(dates)
    return newest, oldest


def scrape_reviews(
    app_id: str,
    max_reviews: int = 10000,
    months_back: int = 3,
    lang: str = "en",
    country: str = "us",
) -> Dict:
    """
    Scrape Google Play reviews for the given app_id.

    Returns a summary dictionary as specified in the Phase 1 spec.
    """
    start_time = time.time()
    RAW_DATA_PATH.mkdir(parents=True, exist_ok=True)

    cutoff_date = _calculate_cutoff_date(months_back)
    today = datetime.now(dt_timezone.utc)
    logger.info("Scraping reviews from %s to %s", cutoff_date.isoformat(), today.isoformat())

    collected: List[Dict] = []
    continuation_token = None
    batch_index = 0
    stop_reason = "no_more_reviews"

    retries = 0

    try:
        while True:
            if len(collected) >= max_reviews:
                stop_reason = "max_reviews"
                logger.info("Reached max review limit: %s", max_reviews)
                break

            try:
                batch, continuation_token = reviews(
                    app_id,
                    lang=lang,
                    country=country,
                    sort=Sort.NEWEST,
                    count=SCRAPER_BATCH_SIZE,
                    continuation_token=continuation_token,
                )
            except Exception as exc:
                logger.warning("Error fetching reviews batch: %s", exc)
                retries += 1
                if retries >= 3:
                    stop_reason = "network_error"
                    logger.error("Network error after 3 retries, stopping scrape.")
                    break
                _sleep_with_jitter()
                continue

            if not batch:
                if not collected:
                    raise ScraperError(f"Google Play returned no reviews for app_id={app_id}")
                stop_reason = "no_more_reviews"
                break

            retries = 0
            batch_index += 1

            # Manual date filtering and early stop
            batch_kept: List[Dict] = []
            stop_for_date = False
            for r in batch:
                review_date = r.get("at")
                if not isinstance(review_date, datetime):
                    # Skip if date is missing or malformed
                    continue
                # google-play-scraper typically returns naive datetimes; make them UTC-aware
                if review_date.tzinfo is None:
                    review_date = review_date.replace(tzinfo=dt_timezone.utc)
                if review_date >= cutoff_date:
                    batch_kept.append({**r, "at": review_date})
                else:
                    stop_reason = "date_limit"
                    stop_for_date = True
                    break

            collected.extend(batch_kept)

            # Progress logging
            newest, oldest = _parse_review_dates(batch)
            newest_iso = newest.isoformat() if newest else None
            oldest_iso = oldest.isoformat() if oldest else None
            logger.info(
                "Batch %d: %d reviews collected, latest date: %s, oldest date in batch: %s",
                batch_index,
                len(collected),
                newest_iso or "n/a",
                oldest_iso or "n/a",
            )

            if _progress_callback is not None:
                try:
                    _progress_callback(
                        {
                            "batch_index": batch_index,
                            "total_collected": len(collected),
                            "latest_date": newest_iso,
                            "oldest_date": oldest_iso,
                        }
                    )
                except Exception:
                    logger.exception("Progress callback failed")

            if stop_for_date:
                break

            if continuation_token is None:
                stop_reason = "no_more_reviews"
                break

            if len(collected) >= max_reviews:
                stop_reason = "max_reviews"
                logger.info("Reached max review limit: %s", max_reviews)
                break

            _sleep_with_jitter()

    finally:
        # Save what we have so far, even on network error
        end_time = time.time()
        duration_seconds = end_time - start_time

        if collected:
            timestamp = datetime.now(dt_timezone.utc).strftime("%Y%m%d_%H%M%S")
            output_file = RAW_DATA_PATH / f"spotify_reviews_{timestamp}.csv"
            scrape_timestamp = datetime.now(dt_timezone.utc).isoformat()

            with output_file.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "review_id",
                        "text",
                        "rating",
                        "date",
                        "app_version",
                        "device",
                        "thumbs_up",
                        "scrape_timestamp",
                        "app_id",
                    ],
                )
                writer.writeheader()
                for r in collected:
                    writer.writerow(
                        {
                            "review_id": r.get("reviewId"),
                            "text": r.get("content"),
                            "rating": r.get("score"),
                            "date": (r.get("at") or today).isoformat(),
                            "app_version": r.get("reviewCreatedVersion"),
                            "device": r.get("device"),
                            "thumbs_up": r.get("thumbsUpCount"),
                            "scrape_timestamp": scrape_timestamp,
                            "app_id": app_id,
                        }
                    )

            dates = [r.get("at") for r in collected if isinstance(r.get("at"), datetime)]
            date_range_start = min(dates).isoformat() if dates else None
            date_range_end = max(dates).isoformat() if dates else None

            scrape_id = str(uuid.uuid4())
            scrape_entry = {
                "scrape_id": scrape_id,
                "app_id": app_id,
                "total_scraped": len(collected),
                "date_range_start": date_range_start,
                "date_range_end": date_range_end,
                "cutoff_date": cutoff_date.isoformat(),
                "stop_reason": stop_reason,
                "output_file": str(output_file),
                "duration_seconds": duration_seconds,
                "scraped_at": scrape_timestamp,
            }
            insert_scrape_log(scrape_entry)

            summary = {
                "app_id": app_id,
                "total_scraped": len(collected),
                "date_range_start": date_range_start,
                "date_range_end": date_range_end,
                "cutoff_date": cutoff_date.isoformat(),
                "stop_reason": stop_reason,
                "output_file": str(output_file),
                "scrape_duration_seconds": duration_seconds,
            }
        else:
            summary = {
                "app_id": app_id,
                "total_scraped": 0,
                "date_range_start": None,
                "date_range_end": None,
                "cutoff_date": cutoff_date.isoformat(),
                "stop_reason": "no_reviews" if stop_reason != "network_error" else "network_error",
                "output_file": None,
                "scrape_duration_seconds": duration_seconds,
            }

    return summary

