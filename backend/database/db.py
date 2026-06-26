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
    Excludes reviews that ALREADY have items in review_atoms for this run_id.
    """
    sql = """
        SELECT n.review_id, n.cleaned_text, r.rating
        FROM reviews_normalized n
        LEFT JOIN raw_reviews r USING (review_id)
        WHERE n.run_id = ?
          AND is_supported = 1
          AND is_low_quality = 0
          AND is_duplicate = 0
          AND n.review_id NOT IN (SELECT DISTINCT review_id FROM review_atoms WHERE run_id = ?)
        ORDER BY n.review_id
    """
    params: list = [run_id, run_id]
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


def fetch_recent_runs(limit: int = 10) -> list:
    """Return recent pipeline runs ordered by start time descending."""
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT run_id, status, current_step, total_reviews,
                   supported_reviews, started_at
            FROM pipeline_runs
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return cur.fetchall()


# ── Phase 3: Clustering helpers ───────────────────────────────────────


def fetch_atoms_by_type(run_id: str, atom_type: str) -> List[sqlite3.Row]:
    """Fetch all review_atoms of a given type for clustering."""
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT atom_id, review_id, atom_type, title, description,
                   evidence_spans, product_area, severity_signal,
                   user_value, confidence_score
            FROM review_atoms
            WHERE run_id = ? AND atom_type = ?
            ORDER BY atom_id
            """,
            (run_id, atom_type),
        )
        return cur.fetchall()


def insert_bug_clusters(rows: Iterable[Dict[str, Any]]) -> None:
    """Bulk insert into bug_clusters table."""
    with get_connection() as conn:
        conn.executemany(
            """
            INSERT INTO bug_clusters (
                cluster_label, severity, frequency, frequency_pct,
                product_area, top_evidence, review_ids, atom_ids,
                cohesion_score, signal_confidence, quality_flag,
                quality_notes, run_id, clustered_at
            ) VALUES (
                :cluster_label, :severity, :frequency, :frequency_pct,
                :product_area, :top_evidence, :review_ids, :atom_ids,
                :cohesion_score, :signal_confidence, :quality_flag,
                :quality_notes, :run_id, :clustered_at
            )
            """,
            list(rows),
        )
        conn.commit()


def insert_feature_clusters(rows: Iterable[Dict[str, Any]]) -> None:
    """Bulk insert into feature_clusters table."""
    with get_connection() as conn:
        conn.executemany(
            """
            INSERT INTO feature_clusters (
                cluster_label, theme, frequency, frequency_pct,
                product_area, user_value_summary, top_evidence,
                review_ids, atom_ids, cohesion_score, signal_confidence,
                quality_flag, quality_notes, run_id, clustered_at
            ) VALUES (
                :cluster_label, :theme, :frequency, :frequency_pct,
                :product_area, :user_value_summary, :top_evidence,
                :review_ids, :atom_ids, :cohesion_score, :signal_confidence,
                :quality_flag, :quality_notes, :run_id, :clustered_at
            )
            """,
            list(rows),
        )
        conn.commit()


def fetch_clusters(run_id: str, cluster_type: str) -> List[sqlite3.Row]:
    """Fetch clusters for verification. cluster_type: 'bug' or 'feature'."""
    table = "bug_clusters" if cluster_type == "bug" else "feature_clusters"
    with get_connection() as conn:
        cur = conn.execute(
            f"SELECT * FROM {table} WHERE run_id = ? ORDER BY frequency DESC",
            (run_id,),
        )
        return cur.fetchall()


# ── Phase 4: Artifact helpers ─────────────────────────────────────────


def insert_triage_matrix(rows: Iterable[Dict[str, Any]]) -> None:
    """Bulk insert into triage_matrix table."""
    rows_list = list(rows)
    if not rows_list:
        return
    run_id = rows_list[0]["run_id"]
    with get_connection() as conn:
        conn.execute("DELETE FROM triage_matrix WHERE run_id = ?", (run_id,))
        conn.executemany(
            """
            INSERT INTO triage_matrix (
                cluster_id, severity, title, frequency, frequency_pct,
                product_area, top_evidence, review_ids,
                signal_confidence, quality_flag, run_id, generated_at
            ) VALUES (
                :cluster_id, :severity, :title, :frequency, :frequency_pct,
                :product_area, :top_evidence, :review_ids,
                :signal_confidence, :quality_flag, :run_id, :generated_at
            )
            """,
            list(rows),
        )
        conn.commit()


def insert_feature_requests(rows: Iterable[Dict[str, Any]]) -> None:
    """Bulk insert into feature_requests table."""
    rows_list = list(rows)
    if not rows_list:
        return
    run_id = rows_list[0]["run_id"]
    with get_connection() as conn:
        conn.execute("DELETE FROM feature_requests WHERE run_id = ?", (run_id,))
        conn.executemany(
            """
            INSERT INTO feature_requests (
                cluster_id, title, theme, frequency, frequency_pct,
                product_area, user_value_summary, top_evidence,
                review_ids, signal_confidence, quality_flag,
                run_id, generated_at
            ) VALUES (
                :cluster_id, :title, :theme, :frequency, :frequency_pct,
                :product_area, :user_value_summary, :top_evidence,
                :review_ids, :signal_confidence, :quality_flag,
                :run_id, :generated_at
            )
            """,
            list(rows),
        )
        conn.commit()


def insert_rice_inputs(rows: Iterable[Dict[str, Any]]) -> None:
    """Bulk insert into rice_inputs table."""
    rows_list = list(rows)
    if not rows_list:
        return
    run_id = rows_list[0]["run_id"]
    with get_connection() as conn:
        conn.execute("DELETE FROM rice_inputs WHERE run_id = ?", (run_id,))
        conn.executemany(
            """
            INSERT INTO rice_inputs (
                source_type, cluster_id, title, reach, impact,
                signal_confidence, confidence_note, effort,
                rice_score, run_id, generated_at
            ) VALUES (
                :source_type, :cluster_id, :title, :reach, :impact,
                :signal_confidence, :confidence_note, :effort,
                :rice_score, :run_id, :generated_at
            )
            """,
            list(rows),
        )
        conn.commit()


def insert_dashboard_metrics(rows: Iterable[Dict[str, Any]]) -> None:
    """Bulk insert into dashboard_metrics table."""
    rows_list = list(rows)
    if not rows_list:
        return
    run_id = rows_list[0]["run_id"]
    with get_connection() as conn:
        conn.execute("DELETE FROM dashboard_metrics WHERE run_id = ?", (run_id,))
        conn.executemany(
            """
            INSERT INTO dashboard_metrics (
                metric_name, metric_value, category, run_id, generated_at
            ) VALUES (
                :metric_name, :metric_value, :category, :run_id, :generated_at
            )
            """,
            list(rows),
        )
        conn.commit()


def fetch_triage_matrix(run_id: str) -> List[sqlite3.Row]:
    """Fetch triage matrix rows for a run, ordered by severity then frequency."""
    sev_order = "CASE severity WHEN 'P0' THEN 0 WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 ELSE 3 END"
    with get_connection() as conn:
        cur = conn.execute(
            f"SELECT * FROM triage_matrix WHERE run_id = ? ORDER BY {sev_order}, frequency DESC",
            (run_id,),
        )
        return cur.fetchall()


def fetch_feature_requests(run_id: str) -> List[sqlite3.Row]:
    """Fetch feature request rows for a run, ordered by frequency."""
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT * FROM feature_requests WHERE run_id = ? ORDER BY frequency DESC",
            (run_id,),
        )
        return cur.fetchall()


def fetch_rice_inputs(run_id: str) -> List[sqlite3.Row]:
    """Fetch RICE input rows for a run, ordered by reach descending."""
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT * FROM rice_inputs WHERE run_id = ? ORDER BY reach DESC",
            (run_id,),
        )
        return cur.fetchall()


def fetch_dashboard_metrics(run_id: str) -> List[sqlite3.Row]:
    """Fetch dashboard metrics for a run."""
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT * FROM dashboard_metrics WHERE run_id = ? ORDER BY category, metric_name",
            (run_id,),
        )
        return cur.fetchall()

