CREATE TABLE IF NOT EXISTS raw_reviews (
    review_id TEXT PRIMARY KEY,
    source_file TEXT,
    source_type TEXT,
    app_id TEXT,
    raw_text TEXT NOT NULL,
    rating INTEGER,
    date TEXT,
    app_version TEXT,
    device TEXT,
    locale TEXT,
    thumbs_up INTEGER,
    ingested_at TEXT,
    run_id TEXT
);

CREATE TABLE IF NOT EXISTS reviews_normalized (
    review_id TEXT PRIMARY KEY,
    original_text TEXT,
    cleaned_text TEXT NOT NULL,
    detected_language TEXT,
    is_supported BOOLEAN,
    is_duplicate BOOLEAN,
    is_low_quality BOOLEAN,
    pii_masked BOOLEAN,
    word_count INTEGER,
    char_count INTEGER,
    normalized_at TEXT,
    run_id TEXT
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id TEXT PRIMARY KEY,
    status TEXT,
    source_type TEXT,
    source_file TEXT,
    app_id TEXT,
    total_reviews INTEGER,
    supported_reviews INTEGER,
    duplicate_count INTEGER,
    low_quality_count INTEGER,
    current_step TEXT,
    error_message TEXT,
    started_at TEXT,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS scrape_log (
    scrape_id TEXT PRIMARY KEY,
    app_id TEXT,
    total_scraped INTEGER,
    date_range_start TEXT,
    date_range_end TEXT,
    cutoff_date TEXT,
    stop_reason TEXT,
    output_file TEXT,
    duration_seconds REAL,
    scraped_at TEXT
);

-- Gold Layer: atomic extracted items from Phase 2
CREATE TABLE IF NOT EXISTS review_atoms (
    atom_id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id TEXT NOT NULL,          -- FK to reviews_normalized
    atom_type TEXT NOT NULL,          -- 'bug' | 'feature'
    title TEXT NOT NULL,
    description TEXT,
    evidence_spans TEXT,              -- JSON array of quote strings
    product_area TEXT,
    severity_signal TEXT,             -- bug only: 'P0' | 'P1' | 'P2' | 'P3'
    user_value TEXT,                  -- feature only: user value statement
    confidence_score REAL,            -- extractor confidence 0.0-1.0
    routed_as TEXT NOT NULL,          -- router decision: 'bug' | 'feature' | 'ambiguous'
    router_confidence REAL,           -- router confidence 0.0-1.0
    run_id TEXT NOT NULL,
    extracted_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_review_atoms_run_id
    ON review_atoms (run_id);

CREATE INDEX IF NOT EXISTS idx_review_atoms_review_id
    ON review_atoms (review_id);

-- Gold Layer: consolidated bug clusters from Phase 3
CREATE TABLE IF NOT EXISTS bug_clusters (
    cluster_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_label TEXT NOT NULL,
    severity TEXT,
    frequency INTEGER,
    frequency_pct REAL,
    product_area TEXT,
    top_evidence TEXT,
    review_ids TEXT,
    atom_ids TEXT,
    cohesion_score REAL,
    signal_confidence REAL,
    quality_flag TEXT,
    quality_notes TEXT,
    run_id TEXT NOT NULL,
    clustered_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_bug_clusters_run_id
    ON bug_clusters (run_id);

-- Gold Layer: consolidated feature clusters from Phase 3
CREATE TABLE IF NOT EXISTS feature_clusters (
    cluster_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_label TEXT NOT NULL,
    theme TEXT,
    frequency INTEGER,
    frequency_pct REAL,
    product_area TEXT,
    user_value_summary TEXT,
    top_evidence TEXT,
    review_ids TEXT,
    atom_ids TEXT,
    cohesion_score REAL,
    signal_confidence REAL,
    quality_flag TEXT,
    quality_notes TEXT,
    run_id TEXT NOT NULL,
    clustered_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_feature_clusters_run_id
    ON feature_clusters (run_id);

-- Gold Layer: Phase 4 artifact tables

CREATE TABLE IF NOT EXISTS triage_matrix (
    triage_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_id INTEGER,
    severity TEXT,
    title TEXT NOT NULL,
    frequency INTEGER,
    frequency_pct REAL,
    product_area TEXT,
    top_evidence TEXT,
    review_ids TEXT,
    signal_confidence REAL,
    quality_flag TEXT,
    run_id TEXT NOT NULL,
    generated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_triage_matrix_run_id
    ON triage_matrix (run_id);

CREATE TABLE IF NOT EXISTS feature_requests (
    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_id INTEGER,
    title TEXT NOT NULL,
    theme TEXT,
    frequency INTEGER,
    frequency_pct REAL,
    product_area TEXT,
    user_value_summary TEXT,
    top_evidence TEXT,
    review_ids TEXT,
    signal_confidence REAL,
    quality_flag TEXT,
    run_id TEXT NOT NULL,
    generated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_feature_requests_run_id
    ON feature_requests (run_id);

CREATE TABLE IF NOT EXISTS rice_inputs (
    rice_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT,
    cluster_id INTEGER,
    title TEXT NOT NULL,
    reach INTEGER,
    impact TEXT,
    signal_confidence REAL,
    confidence_note TEXT,
    effort TEXT,
    rice_score TEXT,
    run_id TEXT NOT NULL,
    generated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rice_inputs_run_id
    ON rice_inputs (run_id);

CREATE TABLE IF NOT EXISTS dashboard_metrics (
    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_name TEXT NOT NULL,
    metric_value TEXT NOT NULL,
    category TEXT,
    run_id TEXT NOT NULL,
    generated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dashboard_metrics_run_id
    ON dashboard_metrics (run_id);

