# Plan — Codebase Explainer

**Status:** MVP + hardening complete — FastAPI + NVIDIA Nemotron 5-agent pipeline, JWT auth, tier/quota system, offline-mocked test suite (21 passing), UI iterated with several pasted reference designs (3D login page, animated hero, homepage).

**2026-07-06 — efficiency + clarity pass (roadmap Phases 1–3):**
- **Pipeline parallelization** — the diagram and security agents now run concurrently with the difficulty → explanation → plan chain (`app/analysis/routes.py:_run_pipeline_with_progress`). Critical path is 3 model calls, not 5 (~40% wall-clock reduction, verified). Shared AsyncSession writes are serialised behind an `asyncio.Lock`.
- **Real progress** — new `progress` column on `analyses` (0–5), committed as each agent finishes and additively migrated in `database.py:_run_lightweight_migrations`. `ResultPage` shows a real "N of 5 agents complete" bar instead of a fake rotating spinner + the old "~30 seconds" copy.
- **Product clarity** — added a real Terms of Service page (`/terms`, wired from the login footer, previously a dead `#` link); local-path submit copy now honestly states it reads the *server host's* filesystem (kept both sources per product decision).

**Deferred to a later pass (roadmap Phase 4):**
- **Follow-up Q&A chat** — let users ask questions about an analyzed codebase after the report generates (chosen direction; not built this pass). Would reuse ingested content; needs a new endpoint + chat UI + a decision on whether to persist raw snippets (currently we deliberately do not).

**Deliberate deferrals (not bugs):**
- `USE_CELERY=false` — Celery/Redis and Stripe billing are later phases, not missing features.
- Postgres migration path exists but SQLite is still primary. No Alembic yet — `_run_lightweight_migrations` handles additive columns for the dev SQLite file; production should adopt a real migration tool.

**Open:**
- Obsidian vault at `../Obsidian/` — user wants graphify output connected here; not yet wired up.
- LLM provider: confirmed 2026-07-05 — NVIDIA Nemotron (`app/analysis/agents.py`) is the only live path; README's old "Groq" description was stale docs, not a second code path. Fixed in README/CLAUDE.md.
- Logout button bug was reported once ("logout button isnt working") — checked 2026-07-05: `Layout.tsx` wires it to `clearToken()` + navigate correctly. Verified working in the running app.
