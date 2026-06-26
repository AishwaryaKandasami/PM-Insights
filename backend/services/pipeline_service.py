"""
Orchestrates the 5-phase AI pipeline for a given run.
Wraps backend/agent/ and backend/pipeline/ — does NOT rewrite them.
Called by Celery worker task, not directly by API routes.
"""
# TODO Sprint 1: implement execute(run_id, user_id)
# Phases: scrape → normalise → extract atoms → cluster → build artifacts
