-- PM Insights — Initial PostgreSQL Schema
-- Sprint 1 | Supabase PostgreSQL
-- Run this in Supabase SQL Editor
-- ─────────────────────────────────────────────────────────────────────

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── apps ─────────────────────────────────────────────────────────────
CREATE TABLE apps (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    play_store_id   TEXT,
    app_store_id    TEXT,
    category        TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT apps_user_must_have_store_id CHECK (
        play_store_id IS NOT NULL OR app_store_id IS NOT NULL
    )
);
ALTER TABLE apps ENABLE ROW LEVEL SECURITY;
CREATE POLICY "users see own apps" ON apps
    FOR ALL USING (auth.uid() = user_id);

-- ── runs ─────────────────────────────────────────────────────────────
CREATE TABLE runs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    app_id          UUID NOT NULL REFERENCES apps(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','processing','complete','failed')),
    date_from       DATE NOT NULL,
    date_to         DATE NOT NULL,
    review_count    INTEGER,
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);
ALTER TABLE runs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "users see own runs" ON runs
    FOR ALL USING (auth.uid() = user_id);

-- ── atoms ─────────────────────────────────────────────────────────────
CREATE TABLE atoms (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id          UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    review_id       TEXT NOT NULL,
    atom_type       TEXT NOT NULL
                    CHECK (atom_type IN ('bug','feature_request','sentiment','ux_issue')),
    text            TEXT NOT NULL,
    severity        TEXT CHECK (severity IN ('low','medium','high','critical')),
    product_area    TEXT,
    confidence_score REAL,
    source_review   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE atoms ENABLE ROW LEVEL SECURITY;
CREATE POLICY "users see own atoms" ON atoms
    FOR ALL USING (auth.uid() = user_id);
CREATE INDEX idx_atoms_run_id ON atoms(run_id);

-- ── clusters ──────────────────────────────────────────────────────────
CREATE TABLE clusters (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id          UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    label           TEXT NOT NULL,
    atom_count      INTEGER NOT NULL DEFAULT 0,
    frequency_score REAL,
    avg_severity    TEXT,
    product_area    TEXT,
    sample_atoms    JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE clusters ENABLE ROW LEVEL SECURITY;
CREATE POLICY "users see own clusters" ON clusters
    FOR ALL USING (auth.uid() = user_id);
CREATE INDEX idx_clusters_run_id ON clusters(run_id);

-- ── artifacts ─────────────────────────────────────────────────────────
CREATE TABLE artifacts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id          UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    cluster_id      UUID REFERENCES clusters(id) ON DELETE SET NULL,
    artifact_type   TEXT NOT NULL
                    CHECK (artifact_type IN (
                        'bug_triage_matrix','feature_backlog','rice_table',
                        'executive_summary','prd_draft'
                    )),
    content         JSONB,
    markdown        TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE artifacts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "users see own artifacts" ON artifacts
    FOR ALL USING (auth.uid() = user_id);
CREATE INDEX idx_artifacts_run_id ON artifacts(run_id);
