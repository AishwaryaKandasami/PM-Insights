# PM Insights

AI-powered feedback analysis for Product Managers. Paste your Play Store app URL → get a prioritised bug triage matrix, RICE-scored feature backlog, and one-click PRD drafts — in minutes.

## What it does

| Input | Output |
|-------|--------|
| Play Store / App Store URL | Bug Triage Matrix (severity × frequency) |
| Date range | Feature Backlog (RICE scored) |
| (Optional) Competitor app URL | Executive Summary |
| | PRD Draft — one click per feature cluster |

## Tech stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14 (App Router) + Tailwind + shadcn/ui |
| Backend | FastAPI (Python 3.11+) |
| Database | PostgreSQL via Supabase |
| Auth | Supabase Auth |
| AI — extraction | Gemini 2.5 Flash |
| AI — PRD generation | Claude Sonnet (Anthropic) |
| Queue | Celery + Redis |
| Hosting | Vercel (frontend) + Railway (backend) |

## Project structure

```
PM-Insights/
├── backend/
│   ├── agent/          ← AI pipeline — prompts, extractors, clustering
│   ├── pipeline/       ← scraping, ingestion, normalisation
│   ├── services/       ← business logic layer
│   ├── api/v1/         ← FastAPI routes + Pydantic models
│   ├── worker/         ← Celery async tasks
│   └── core/           ← config, auth, logging
├── frontend/           ← Next.js app
├── docs/               ← architecture docs
└── legacy/             ← reference only (old Streamlit + CLI scripts)
```

## Getting started

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env          # fill in your keys
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
cp ../.env.frontend.example .env.local   # fill in your keys
npm run dev
```

### Environment variables

See `.env.example` (backend) and `.env.frontend.example` (frontend) for all required variables.

## Sprint roadmap

| Sprint | Focus | Status |
|--------|-------|--------|
| 1 | Supabase schema + FastAPI routes + Next.js skeleton | 🔄 In progress |
| 2 | PRD generator + competitor comparison + Stripe | ⏳ Planned |
| 3 | Trend tracking + Jira export + Product Hunt launch | ⏳ Planned |

## Cursor users

Read `.cursorrules` at the repo root before starting any session. It contains the full project context, preserved code map, domain model, and hard rules Cursor must follow.

---

Built by [@AishwaryaKandasami](https://github.com/AishwaryaKandasami)
