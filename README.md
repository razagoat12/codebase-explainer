# Codebase Explainer

FastAPI + Groq (LLaMA 3.1) app that ingests a codebase and returns a plain-language explanation, phased plan, architecture diagram, and security audit.

## Quick start

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env             # fill in GROQ_API_KEY + JWT_SECRET_KEY
.venv/bin/uvicorn app.main:app --reload
```

Open <http://localhost:8000>.

## What it does

Five Groq agents run sequentially per analysis:

| # | Agent | Output |
|---|-------|--------|
| 1 | Difficulty Assessor | JSON: level, language, frameworks |
| 2 | Explainer | Markdown explanation tailored to the difficulty |
| 3 | Planner | Phased Phase 0 → 1 → 2 plan |
| 4 | Diagram | Mermaid `graph TD` of module structure |
| 5 | Security Auditor | JSON: risk level + findings (secrets, injection, etc.) |

Inputs supported: local directory path or GitHub repo URL (public).

## Features

- JWT auth (register / login / `/auth/me`)
- Free/Pro tier system with monthly quotas (free: 10/mo, pro: 500/mo)
- Content-hash cache — identical codebases return instantly
- Background processing — submit returns 202 + analysis_id, client polls
- Three-page web UI: submit, dashboard, result viewer
- 12 passing pytest cases (`.venv/bin/pytest tests/`)

## Production deployment (Phase 3+)

### Swap SQLite → PostgreSQL

Set `DATABASE_URL` in `.env`:

```
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
```

Install the driver:

```bash
pip install asyncpg
```

No code changes needed — SQLAlchemy handles both.

### Add Stripe billing

The tier system is wired but `plan_tier` is only updated manually in the DB. To go live with Stripe:

1. Create products in Stripe (e.g. "Pro $9/mo")
2. Add `pip install stripe` and a `/billing/checkout` endpoint that creates a Stripe Checkout Session
3. Add `/billing/webhook` to receive `customer.subscription.created/deleted` events and set `user.plan_tier` accordingly
4. Set `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET` in `.env`

### Add Celery + Redis for large codebases

`BackgroundTasks` runs in the same process as your web server. For genuine scale:

1. Run Redis (`brew install redis && redis-server`)
2. Add `pip install celery redis`
3. Create `app/worker.py` with a Celery instance pointing at Redis
4. Convert `_run_analysis` to a `@celery.task` decorated function
5. Run a separate worker process: `celery -A app.worker worker --loglevel=info`

This lets you scale workers independently of the API.

### Hosting

- **Backend:** Railway, Render, Fly.io (all support Postgres + background workers)
- **Frontend:** served by the same FastAPI process (no separate hosting needed for the included static UI)

## Environment variables

| Name | Required | Purpose |
|------|----------|---------|
| `GROQ_API_KEY` | Yes | Groq API key — get one at <https://console.groq.com> |
| `JWT_SECRET_KEY` | Yes | Random hex string — `openssl rand -hex 32` |
| `JWT_ALGORITHM` | No | Default `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | Default `1440` (24h) |
| `DATABASE_URL` | No | Default SQLite; swap for Postgres in production |
| `CORS_ORIGINS` | No | Comma-separated list of allowed origins |
| `RATE_LIMIT_PER_HOUR` | No | Default `10` |
| `MAX_FILE_SIZE_BYTES` | No | Default `512000` |
| `MAX_TOTAL_CONTENT_BYTES` | No | Default `2097152` |
