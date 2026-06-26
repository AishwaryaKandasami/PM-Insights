# Cursor Setup Guide — PM Insights
# Read this before opening Cursor on this repo.

---

## STEP 1 — Confirm .cursorrules is active

Open Cursor → Cmd+Shift+P → type "Cursor: Show Rules"
You should see `.cursorrules` listed. If not, restart Cursor.

---

## STEP 2 — FIRST CURSOR COMPOSER MESSAGE (Sprint 1)

Open Cursor Composer (Cmd+I). Paste this exactly:

```
Read .cursorrules fully before generating anything.

I'm building PM Insights — a multi-tenant SaaS that turns Play Store /
App Store reviews into PM artifacts (bug triage, RICE backlog, PRD drafts).

The existing AI pipeline logic lives in backend/agent/ and backend/pipeline/.
That code is PROVEN — do not rewrite it. We wrap it in a proper API.

Sprint 1 task — do these in order, one file at a time:

1. backend/core/config.py
   - pydantic-settings BaseSettings class
   - Fields: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_JWT_SECRET,
     GEMINI_API_KEY, GROQ_API_KEY, ANTHROPIC_API_KEY, REDIS_URL,
     ENVIRONMENT, LOG_LEVEL
   - Single settings = Settings() instance at bottom of file

2. backend/core/auth.py
   - get_current_user FastAPI dependency
   - Verifies Supabase JWT from Authorization: Bearer header
   - Returns user_id (UUID string) or raises 401

3. backend/core/logging.py
   - structlog configuration
   - JSON output in production, console in development
   - Export: get_logger(name) function

4. backend/services/supabase_service.py
   - Supabase client initialisation
   - Async functions: create_app, list_apps, create_run, get_run,
     update_run_status, create_artifact, list_artifacts
   - Every query filters by user_id

5. backend/api/v1/models/app_models.py
   - Pydantic v2 models for App, Run, Atom, Cluster, Artifact
   - Field names exactly as in .cursorrules Section 5
   - Request models (CreateAppRequest, CreateRunRequest)
   - Response models (AppResponse, RunResponse, RunStatusResponse)

Show me file 1 first. Wait for my confirmation before moving to file 2.
```

---

## STEP 3 — SUBSEQUENT SESSION PROMPTS

### After config + auth + supabase_service done:
```
Good. Now build the API routes — one file at a time.

backend/api/v1/routes/apps.py:
  POST /api/v1/apps — validate body, call supabase_service.create_app,
                      return AppResponse in standard envelope
  GET  /api/v1/apps — call supabase_service.list_apps(user_id),
                      return list of AppResponse

Use get_current_user dependency on both routes.
Use the response envelope from .cursorrules Section 8.
Keep the route handler under 20 lines — all logic in supabase_service.
```

### After apps routes done:
```
Now backend/api/v1/routes/runs.py:
  POST /api/v1/apps/{app_id}/runs
    - Verify app belongs to current user
    - Create Run record with status=pending
    - Trigger Celery task: run_pipeline.delay(run_id, user_id)
    - Return immediately with {run_id, status: "pending"}

  GET /api/v1/apps/{app_id}/runs
    - List runs for app, newest first
    - Return list of RunResponse

  GET /api/v1/runs/{run_id}/status
    - Lightweight poll endpoint
    - Return {run_id, status, review_count, completed_at}

  GET /api/v1/runs/{run_id}/artifacts
    - Only return if status = complete
    - Return all artifacts for the run
```

### After backend routes done — start frontend:
```
Backend Sprint 1 is complete. Now the Next.js frontend.
Build these 4 pages only — nothing else this sprint.

Start with frontend/lib/types.ts:
  TypeScript interfaces mirroring domain model from .cursorrules Section 5.
  App, Run, Atom, Cluster, Artifact interfaces.
  RunStatus type: 'pending' | 'processing' | 'complete' | 'failed'
  ApiResponse<T> wrapper type matching the envelope.

Then frontend/lib/api.ts:
  Typed async functions for every backend route we built.
  Use fetch() — not axios.
  All functions accept user JWT from Supabase session.

Show me types.ts first and wait for confirmation.
```

### After types + api client:
```
Now the 4 pages:

1. frontend/app/auth/page.tsx
   - Supabase email/password login + signup tabs
   - On success redirect to /dashboard

2. frontend/app/dashboard/page.tsx
   - List user's apps as cards (AppCard component)
   - Empty state with "Add your first app" CTA
   - "New App" button → dialog with form:
     Fields: App Name, Play Store URL (validate with Zod), App Store URL (optional)
   - On submit: createApp() then triggerRun() then redirect to run status page

3. frontend/app/apps/[appId]/runs/[runId]/page.tsx
   - Poll GET /runs/{runId}/status every 3 seconds
   - Show progress states:
     pending    → "Scraping reviews..."
     processing → "Analysing feedback with AI..."
     complete   → render ArtifactView component
     failed     → show error with retry button

4. ArtifactView component (frontend/components/ArtifactView.tsx)
   - Tabs: Bug Triage | Feature Backlog | RICE Table | Summary
   - Each tab renders the artifact content
   - "Generate PRD" button on each feature cluster card (Sprint 2 — stub it)

Build page 1 first. Wait for confirmation before page 2.
```

---

## STEP 4 — IF CURSOR GOES WRONG

| Problem | Say this |
|---------|----------|
| Rewrites backend/agent/ logic | "Stop. backend/agent/ is read-only. Wrap it in services/ only. Read .cursorrules Section 2." |
| Uses SQLite or db.py | "Remove that. PostgreSQL via Supabase only. Read .cursorrules Section 10." |
| Adds Notion SDK | "Notion is removed from this project. Delete that import." |
| Generates CLI script | "No CLI scripts. Everything via FastAPI routes." |
| Makes file too long | "Stop at 150 lines. Break into helper functions or separate file." |
| Wrong field names | "Use only field names from .cursorrules Section 5. Show me the model before using it elsewhere." |
| Pages Router in Next.js | "App Router only. Remove pages/ directory." |
| No user_id filter on query | "Every Supabase query must filter by user_id. Read .cursorrules Section 4." |

---

## STEP 5 — SPRINT SUMMARY

| Sprint | Scope | Duration |
|--------|-------|----------|
| 1 | Schema + FastAPI routes + Celery scaffold + Next.js skeleton | 2–3 weeks |
| 2 | PRD generator + competitor comparison + Stripe billing | 2–3 weeks |
| 3 | Trend tracking + Jira export + Product Hunt launch | 2 weeks |
