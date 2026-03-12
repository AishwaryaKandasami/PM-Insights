# PM Insights Engine — Architecture

AI-powered feedback analysis engine that 
converts raw Spotify Google Play reviews 
(10,000 reviews) into four structured, 
PM-ready artifacts without manual tagging.

---

## 1. Project Overview

PM Insights Engine is a self-evaluating,
incrementally-updating feedback intelligence
system that routes, analyzes, and delivers
PM-ready insights with confidence scoring —
powered by Gemini AI and delivered via MCP.

Target user: PM at a growth-stage consumer 
app (Series B-C, 50K-500K MAUs) with no 
dedicated research ops team.

Build dataset: 10,000 Spotify Google Play 
reviews (Feb 21 – Mar 07, 2026)

---

## 2. Goals

- Ingest Spotify Google Play reviews 
  every 2 weeks (10,000 review cap)
- Automatically produce 4 PM-ready artifacts:
  - Bug Triage Matrix (P0-P3)
  - Feature Request Extraction
  - Executive Summary Dashboard
  - RICE-ready Prioritization Inputs
- Zero manual tagging required
- Deliver artifacts via MCP to Jira + Notion

---

## 3. Key Design Principles

- No manual labeling required
- Deterministic where possible
  (temperature=0, pinned prompt versions)
- Traceable outputs
  (every artifact row links to source reviews)
- Human-in-the-loop optional, not required
- Cost aware
  (two-tier model: Flash for bulk, 
   Pro for adjudication)

---

## 4. Scope — V1 vs V2/V3

### V1 Scope (current build)
- English-only review processing
- Manual trigger via Streamlit UI
- Scheduled scrape every 2 weeks
- Single-process pipeline
- Core NLP/LLM extraction pipeline
- 4 PM artifact builders
- MCP delivery to Jira + Notion
- SQLite storage

### V2/V3 Scope (future)
- Non-English translation pipeline
- PDF/slide summary generator
- Scheduled auto-run with notifications
- Separate compute workers
- Multi-app support
- Role-based access control

---

## 5. System Architecture

### Layer 1 — Data Collection
✅ V1 Scope

Scraper: google-play-scraper library
App: com.spotify.music
Schedule: Every 2 weeks
Cap: 10,000 reviews per run
Date filter: Last 3 months
             (manual date cutoff — 
             google-play-scraper has 
             no native date filter)
Stop condition: Date cutoff OR 
                10K limit — 
                whichever hits first
Output: CSV saved to data/raw/

### Layer 2 — Ingestion
✅ V1 Scope

Validates CSV format and required 
columns (review_id, text, date)
Deduplicates by review_id and 
(text + date) hash
Stores in Bronze layer: raw_reviews
Generates unique run_id per session

### Layer 3 — Normalization
✅ V1 Scope

Text cleanup: whitespace, emojis 
preserved, boilerplate removed
Language detection fix:
  word_count < 5 → skip langdetect
                → default to English
                → is_supported = True
  word_count >= 5 → run langdetect
PII masking: emails → [EMAIL], 
             phones → [PHONE]
Quality flagging: word_count < 3 
                  → is_low_quality = True
Output: Silver layer — reviews_normalized

Phase 1 Production Results (Mar 2026):
  Total scraped:          10,000
  Date range:    Feb 21 – Mar 07 2026
  Non-English:               422 (4.2%)
  Low quality:             2,564 (25.6%)
  Usable for Phase 2:      7,014 (70.1%)

### Layer 4 — AI Extraction Pipeline
✅ V1 Scope | Phase 2

Enhancement 1: Confidence-Based Routing
  Quick classifier runs first on each 
  review using Gemini Flash.
  Routes by intent confidence:
    High confidence bug
      → bug extraction only
    High confidence feature
      → feature extraction only
    Ambiguous
      → full multi-task extraction
    Noise/spam
      → skip entirely
  Purpose: Reduce API cost and improve
  accuracy through specialization.

Per-intent specialized extraction:
  Bug items: what is broken,
             severity signals,
             reproduction hints
  Feature items: what is requested,
                 user value statement
  Each item: title, description,
             evidence spans,
             product area,
             confidence score

### Layer 5 — Clustering + Enhancements
✅ V1 Scope | Phase 3

Clustering algorithm:
  Agglomerative Clustering (scikit-learn)
  Cosine distance threshold: 0.25
  Separate clusters for bugs 
  and feature requests

Enhancement 2: Adaptive Clustering
  Cluster quality evaluated via 
  cohesion scores after initial run:
    Too broad → tighten threshold,
                re-cluster
    Too fragmented → loosen threshold,
                     merge
  Borderline merges → Gemini Pro 
                      adjudicates
  Purpose: Better quality than 
  fixed threshold allows.

Enhancement 3: LLM-as-Judge
  After artifact generation, 
  Gemini Flash reviews outputs:
    Is bug title clear to an engineer?
    Is severity justified by evidence?
    Are features distinct enough?
  Low quality outputs flagged for 
  PM review.
  Signal Confidence score updated.
  Purpose: Close the trust gap.

Enhancement 4: Delta Processing 
              + Trend Detection
  Every 2-week scrape processes only
  NEW reviews not in previous runs.
  Existing clusters updated 
  incrementally.
  Trend detection flags:
    Clusters grew >20% since last run
    New P0/P1 not in previous run
    Fast-rising feature requests
  Purpose: Ongoing intelligence system,
  not one-time analysis.

### Layer 6 — Scoring
✅ V1 Scope | Phase 3

Frequency: unique reviews per cluster,
           % of total, trend direction
Bug severity (P0-P3):
  P0: crash, login/payment blocked,
      data loss
  P1: core feature degraded for many
  P2: partial impairment, UI broken
  P3: minor annoyance, edge case
Signal Confidence: extraction confidence
  + cluster cohesion + evidence 
  consistency

### Layer 7 — Artifact Builders
✅ V1 Scope | Phase 4

Bug Triage Matrix:
  Rows: bug clusters
  Columns: severity, title, frequency,
           product area, top quotes,
           review_ids, signal confidence

Feature Request Extraction:
  Rows: feature clusters
  Columns: title, theme, frequency,
           user value statement,
           top quotes, review_ids

Executive Summary Dashboard:
  Sentiment distribution + trends
  Top themes by volume
  Critical issues feed (P0/P1)
  Rating vs sentiment mismatches

RICE-ready Inputs:
  Reach proxy: cluster frequency
  Impact proxy: severity band (bugs)
               sentiment gap (features)
  Signal Confidence: data quality only
                     (NOT RICE Confidence
                     — PM completes that)
  Effort: blank — PM to complete

### Layer 8 — MCP Delivery
✅ V1 Scope | Phase 5

Delivery approach: Hybrid MCP
AI agent orchestrates existing 
MCP servers — no custom servers built.

Notion MCP (Official):
  Pushes executive summary as 
  formatted Notion page
  Creates RICE input table in 
  Notion database
  Triggered after every pipeline run

Why MCP over direct API:
  Agent writes ticket descriptions 
  from analysis context — not templates
  Natural language orchestration
  Adaptable to Jira project structure

---

## 6. Data Model

Bronze Layer:
  raw_reviews — immutable ingested records

Silver Layer:
  reviews_normalized — cleaned, 
  language-detected, quality-flagged

Gold Layer:
  review_atoms — atomic extracted items
  bug_clusters — consolidated bugs
  feature_clusters — consolidated features
  triage_matrix — final bug artifact
  feature_requests — final feature artifact
  dashboard_metrics — summary artifact
  rice_inputs — final RICE artifact

Run Tracking:
  pipeline_runs — status per run
  scrape_log — scrape metadata
  evaluation_set — 200-300 manually 
                   labeled baseline rows

---

## 7. Tech Stack

IDE: Google Antigravity
Primary model: Gemini 3.1 Pro
Extraction model: Gemini Flash
                  (bulk, 7,014 reviews)
Adjudication: Gemini Pro
              (borderline cases only)
Embeddings: text-embedding-004 (free)
Clustering: scikit-learn
            Agglomerative, cosine distance
Storage: SQLite (V1)
Frontend: Streamlit (V1)
File handling: pandas
Language detection: langdetect
                    (with word_count fix)
PII masking: presidio-anonymizer
MCP servers: Official Atlassian Jira MCP
             Official Notion MCP
Budget: Google Cloud $300 free trial
Estimated total API cost: < $1.00

---

## 8. Evaluation Strategy

Fixed evaluation baseline:
  200-300 manually labeled reviews
  One-time PM labeling (~2-3 hours)
  Labels: intent, severity, theme
  Regression thresholds:
    Severity shift > 10% → review
    Cluster count change > 20% → review

Schema checks:
  Valid JSON outputs from all LLM calls
  No empty evidence spans on 
  high-confidence items

---

## 9. Phase Breakdown

Phase 1 ✅ COMPLETE
  Scraper, ingestion, normalization,
  Streamlit UI, langdetect fix
  Usable reviews: 7,014

Phase 2 — AI Extraction Pipeline
  Confidence-based routing
  Specialized extractors per intent
  Atomic item generation
  Model: Gemini Flash

Phase 3 — Clustering + Enhancements
  Adaptive clustering
  LLM-as-judge
  Delta processing + trend detection
  Model: Gemini Pro for adjudication

Phase 4 — Artifact Generation
  Bug triage matrix
  Feature extraction
  RICE inputs
  Executive summary

Phase 5 — MCP Delivery
  Notion MCP connection
  Delivery trigger logic
  PM confirmation UI for P2/P3

---

## 10. V1 Acceptance Criteria

Input: 7,014 usable reviews
Output: 4 artifacts generated,
        each deduplicated and grouped,
        includes drill-down evidence,
        P0/P1 highlighted clearly,
        exports cleanly for PM workflows
Pipeline: repeatable, monitored,
          runs on incremental new reviews
