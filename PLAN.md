# Plan — Codebase Explainer

**Status:** Phase 0/1 (MVP) and Phase 2 done — FastAPI + Groq 5-agent pipeline, JWT auth, tier/quota system, offline-mocked test suite (12 passing), UI iterated with several pasted reference designs (3D login page, animated hero, homepage).

**Deliberate deferrals (not bugs):**
- `USE_CELERY=false` — Celery/Redis and Stripe billing are Phase 3+, not missing features.
- Postgres migration path exists but SQLite is still primary.

**Open:**
- Obsidian vault at `../Obsidian/` — user wants graphify output connected here; not yet wired up.
- LLM provider: Groq is primary; `NVIDIA_API_KEY` in `.env` is a leftover from evaluating Nemotron as an alternative — confirm which path is actually live in `app/analysis/agents` before assuming both work.
- Logout button bug was reported once ("logout button isnt working") — verify it's actually fixed, not just reported.
