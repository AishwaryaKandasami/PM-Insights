import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from config.settings import DB_PATH


logger = logging.getLogger(__name__)


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection, ensuring the database directory exists."""
    db_path = Path(DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(schema_path: Optional[Path] = None) -> None:
    """Initialize the database using schema.sql."""
    if schema_path is None:
        schema_path = Path(__file__).with_name("schema.sql")

    with get_connection() as conn, schema_path.open("r", encoding="utf-8") as f:
        schema_sql = f.read()
        conn.executescript(schema_sql)
        conn.commit()
    logger.info("Database initialized from %s", schema_path)


def insert_raw_reviews(rows: Iterable[Dict[str, Any]]) -> None:
    """Bulk insert raw reviews into raw_reviews table."""
    with get_connection() as conn:
        conn.executemany(
            """
            INSERT OR REPLACE INTO raw_reviews (
                review_id,
                source_file,
                source_type,
                app_id,
                raw_text,
                rating,
                date,
                app_version,
                device,
                locale,
                thumbs_up,
                ingested_at,
                run_id
            ) VALUES (
                :review_id,
                :source_file,
                :source_type,
                :app_id,
                :raw_text,
                :rating,
                :date,
                :app_version,
                :device,
                :locale,
                :thumbs_up,
                :ingested_at,
                :run_id
            )
            """,
            list(rows),
        )
        conn.commit()


def insert_reviews_normalized(rows: Iterable[Dict[str, Any]]) -> None:
    """Bulk insert normalized reviews into reviews_normalized table."""
    with get_connection() as conn:
        conn.executemany(
            """
            INSERT OR REPLACE INTO reviews_normalized (
                review_id,
                original_text,
                cleaned_text,
                detected_language,
                is_supported,
                is_duplicate,
                is_low_quality,
                pii_masked,
                word_count,
                char_count,
                normalized_at,
                run_id
            ) VALUES (
                :review_id,
                :original_text,
                :cleaned_text,
                :detected_language,
                :is_supported,
                :is_duplicate,
                :is_low_quality,
                :pii_masked,
                :word_count,
                :char_count,
                :normalized_at,
                :run_id
            )
            """,
            list(rows),
        )
        conn.commit()


def upsert_pipeline_run(run: Dict[str, Any]) -> None:
    """Insert or update a pipeline_runs record."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO pipeline_runs (
                run_id,
                status,
                source_type,
                source_file,
                app_id,
                total_reviews,
                supported_reviews,
                duplicate_count,
                low_quality_count,
                current_step,
                error_message,
                started_at,
                completed_at
            ) VALUES (
                :run_id,
                :status,
                :source_type,
                :source_file,
                :app_id,
                :total_reviews,
                :supported_reviews,
                :duplicate_count,
                :low_quality_count,
                :current_step,
                :error_message,
                :started_at,
                :completed_at
            )
            ON CONFLICT(run_id) DO UPDATE SET
                status = excluded.status,
                source_type = excluded.source_type,
                source_file = excluded.source_file,
                app_id = excluded.app_id,
                total_reviews = excluded.total_reviews,
                supported_reviews = excluded.supported_reviews,
                duplicate_count = excluded.duplicate_count,
                low_quality_count = excluded.low_quality_count,
                current_step = excluded.current_step,
                error_message = excluded.error_message,
                started_at = excluded.started_at,
                completed_at = excluded.completed_at
            """,
            run,
        )
        conn.commit()


def insert_scrape_log(entry: Dict[str, Any]) -> None:
    """Insert a new row into scrape_log."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO scrape_log (
                scrape_id,
                app_id,
                total_scraped,
                date_range_start,
                date_range_end,
                cutoff_date,
                stop_reason,
                output_file,
                duration_seconds,
                scraped_at
            ) VALUES (
                :scrape_id,
                :app_id,
                :total_scraped,
                :date_range_start,
                :date_range_end,
                :cutoff_date,
                :stop_reason,
                :output_file,
                :duration_seconds,
                :scraped_at
            )
            """,
            entry,
        )
        conn.commit()


def fetch_raw_reviews_by_run(run_id: str) -> List[sqlite3.Row]:
    """Fetch all raw_reviews rows for a given run."""
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT * FROM raw_reviews WHERE run_id = ? ORDER BY date", (run_id,)
        )
        return cur.fetchall()


def get_pipeline_run(run_id: str) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT * FROM pipeline_runs WHERE run_id = ?", (run_id,)
        )
        return cur.fetchone()


def fetch_usable_normalized(run_id: str, limit: Optional[int] = None) -> List[sqlite3.Row]:
    """
    Fetch normalized reviews that are usable for Phase 2 extraction:
    supported English, not low quality, not duplicates.
    """
    sql = """
        SELECT review_id, cleaned_text
        FROM reviews_normalized
        WHERE run_id = ?
          AND is_supported = 1
          AND is_low_quality = 0
          AND is_duplicate = 0
        ORDER BY review_id
    """
    params: list = [run_id]
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
    with get_connection() as conn:
        cur = conn.execute(sql, params)
        return cur.fetchall()


def insert_review_atoms(rows: Iterable[Dict[str, Any]]) -> None:
    """Bulk insert extracted atoms into the review_atoms Gold layer table."""
    with get_connection() as conn:
        conn.executemany(
            """
            INSERT INTO review_atoms (
                review_id,
                atom_type,
                title,
                description,
                evidence_spans,
                product_area,
                severity_signal,
                user_value,
                confidence_score,
                routed_as,
                router_confidence,
                run_id,
                extracted_at
            ) VALUES (
                :review_id,
                :atom_type,
                :title,
                :description,
                :evidence_spans,
                :product_area,
                :severity_signal,
                :user_value,
                :confidence_score,
                :routed_as,
                :router_confidence,
                :run_id,
                :extracted_at
            )
            """,
            list(rows),
        )
        conn.commit()


def fetch_review_atoms(run_id: str) -> List[sqlite3.Row]:
    """Fetch all extracted atoms for a given run (for verification)."""
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT * FROM review_atoms
            WHERE run_id = ?
            ORDER BY atom_type, extracted_at
            """,
            (run_id,),
        )
        return cur.fetchall()
