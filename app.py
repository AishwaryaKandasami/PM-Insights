import logging
import os
from datetime import datetime
from typing import Optional

import pandas as pd
import streamlit as st

from config.settings import RAW_DATA_PATH
from database.db import get_pipeline_run, init_db
from pipeline.ingestion import ValidationError, load_and_validate
from pipeline.normalization import normalize_reviews
from agent.orchestrator import run_extraction
from pipeline.scraper import ScraperError, scrape_reviews, set_progress_callback


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _ensure_dirs() -> None:
    RAW_DATA_PATH.mkdir(parents=True, exist_ok=True)


def _load_preview(path: str) -> Optional[pd.DataFrame]:
    if not path or not os.path.exists(path):
        return None
    try:
        return pd.read_csv(path)
    except Exception:
        return None


def _rating_distribution_chart(df: pd.DataFrame) -> None:
    if "rating" not in df.columns:
        st.info("Rating column not found; cannot show rating distribution.")
        return
    counts = df["rating"].value_counts().sort_index()
    st.bar_chart(counts)


def main() -> None:
    st.set_page_config(page_title="PM Insights Engine", layout="wide")
    st.title("PM Insights Engine")

    _ensure_dirs()
    init_db()

    if "current_run_id" not in st.session_state:
        st.session_state.current_run_id = None
    if "current_source_file" not in st.session_state:
        st.session_state.current_source_file = None

    tab_scrape, tab_upload = st.tabs(["Scrape Reviews", "Upload CSV"])

    with tab_scrape:
        st.subheader("Scrape Reviews from Google Play")
        app_id = st.text_input(
            "App ID",
            value="com.spotify.music",
            help="Find the app ID in the Google Play Store URL.",
        )
        date_range_option = st.selectbox(
            "Date range",
            options=[
                "Last 3 months (recommended)",
                "Last 1 month",
                "Last 6 months",
            ],
        )
        if "3 months" in date_range_option:
            months_back = 3
        elif "1 month" in date_range_option:
            months_back = 1
        else:
            months_back = 6

        max_reviews = st.number_input(
            "Max reviews",
            min_value=1,
            max_value=10000,
            value=10000,
            help="Capped at 10,000 reviews.",
        )
        lang = st.selectbox("Language", options=["en"], index=0)
        country = st.selectbox("Country", options=["us"], index=0)

        progress_placeholder = st.empty()
        latest_date_placeholder = st.empty()

        def _on_progress(update: dict) -> None:
            progress_placeholder.write(
                f"Scraping in progress...\n\n"
                f"Batch {update.get('batch_index')} — "
                f"Reviews collected: {update.get('total_collected')}"
            )
            latest = update.get("latest_date") or "n/a"
            latest_date_placeholder.write(f"Latest review date seen: {latest}")

        if st.button("Start Scraping"):
            set_progress_callback(_on_progress)
            try:
                summary = scrape_reviews(
                    app_id=app_id,
                    max_reviews=int(max_reviews),
                    months_back=months_back,
                    lang=lang,
                    country=country,
                )
            except ScraperError as exc:
                set_progress_callback(None)
                st.error(str(exc))
                return
            finally:
                # Ensure callback is cleared
                set_progress_callback(None)

            if summary["total_scraped"] > 0 and summary["output_file"]:
                st.session_state.current_source_file = summary["output_file"]
                st.success(
                    "Scraping complete\n\n"
                    f"- Total reviews collected: {summary['total_scraped']}\n"
                    f"- Date range: {summary['date_range_start']} to {summary['date_range_end']}\n"
                    f"- Stop reason: {summary['stop_reason']}\n"
                    f"- Saved to: {summary['output_file']}"
                )
                st.info("Proceeding to ingestion step with the scraped CSV.")

                try:
                    ingest_summary = load_and_validate(
                        summary["output_file"],
                        source_type="scraped",
                        app_id=app_id,
                    )
                except ValidationError as exc:
                    st.error(f"Ingestion failed: {exc}")
                    return

                st.session_state.current_run_id = ingest_summary["run_id"]
                st.write("Ingestion summary:", ingest_summary)
            else:
                st.warning("No reviews were scraped.")

    with tab_upload:
        st.subheader("Upload CSV")
        uploaded = st.file_uploader(
            "Upload CSV file",
            type=["csv"],
            help="Required columns: review_id, text, date",
        )
        if uploaded is not None:
            # Save uploaded file to raw data path
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            dest_path = RAW_DATA_PATH / f"uploaded_reviews_{timestamp}.csv"
            with open(dest_path, "wb") as f:
                f.write(uploaded.getbuffer())

            try:
                ingest_summary = load_and_validate(str(dest_path), source_type="uploaded")
            except ValidationError as exc:
                st.error(f"Validation failed: {exc}")
            else:
                st.success("File validated and ingested successfully.")
                st.session_state.current_run_id = ingest_summary["run_id"]
                st.session_state.current_source_file = str(dest_path)
                st.write("Ingestion summary:", ingest_summary)

    st.markdown("---")
    st.subheader("Data Preview")
    df_preview = _load_preview(st.session_state.current_source_file)
    if df_preview is not None:
        st.write("First 5 rows:")
        st.dataframe(df_preview.head())
        st.write("Detected columns:", list(df_preview.columns))
        if "date" in df_preview.columns:
            try:
                dates = pd.to_datetime(df_preview["date"], errors="coerce").dropna()
                if not dates.empty:
                    st.write(
                        f"Date range: {dates.min().isoformat()} to {dates.max().isoformat()}"
                    )
            except Exception:
                pass

        st.write("Rating distribution:")
        _rating_distribution_chart(df_preview)
    else:
        st.info("No data loaded yet. Scrape or upload a CSV to preview.")

    st.markdown("---")
    st.subheader("Phase 1 — Prepare Reviews")
    if st.button("Clean and Prepare Reviews", disabled=st.session_state.current_run_id is None):
        if st.session_state.current_run_id is None:
            st.error("No run_id available. Please scrape or upload data first.")
        else:
            with st.spinner("Normalizing reviews..."):
                summary = normalize_reviews(st.session_state.current_run_id)
            st.success("Normalization complete.")
            st.write("Normalization summary:", summary)

    st.markdown("---")
    st.subheader("Phase 2 — AI Extraction (50-review sample)")
    st.caption(
        "Agent routes each review (bug / feature / ambiguous / noise) then "
        "calls the matching extractor. Writes atoms to Gold layer."
    )
    if st.button(
        "▶ Run AI Extraction (50-review sample)",
        disabled=st.session_state.current_run_id is None,
        key="btn_phase2",
    ):
        run_id_p2 = st.session_state.current_run_id
        with st.spinner("Agent running… routing + extracting (≈50 Gemini calls, ~5-10 min)..."):
            try:
                result = run_extraction(run_id_p2, sample_limit=50)
                st.success(f"Extraction complete — {result['atoms_written']} atoms written to DB.")
                st.table([
                    {"Route": "Bug",       "Count": result["routed_bug"]},
                    {"Route": "Feature",   "Count": result["routed_feature"]},
                    {"Route": "Ambiguous", "Count": result["routed_ambiguous"]},
                    {"Route": "Noise (skipped)", "Count": result["skipped_noise"]},
                    {"Route": "Total reviewed",  "Count": result["total_reviewed"]},
                ])
            except Exception as exc:
                st.error(f"Extraction failed: {exc}")

    st.markdown("---")
    st.subheader("Pipeline Status")
    run_id = st.session_state.current_run_id
    if run_id:
        st.write(f"Current run_id: `{run_id}`")
        run_row = get_pipeline_run(run_id)
        if run_row:
            st.write("Status:", run_row["status"])
            st.write("Current step:", run_row["current_step"])
    else:
        st.write("No active run yet.")


if __name__ == "__main__":
    main()

