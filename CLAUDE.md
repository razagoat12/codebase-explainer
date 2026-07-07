# CodeBase Explainer

FastAPI + Groq backend, React/TS/Vite frontend. Analyzes a user's repo through a 5-agent pipeline (Difficulty Assessor → Explainer → Planner → Diagram → Security Auditor), with JWT auth and a tier/quota system.

## Running it
`.claude/launch.json` has two configs: `codebase-explainer-api` (`.venv/bin/python3 -m uvicorn app.main:app --reload --port 8000`) and `codebase-explainer-frontend` (`npm --prefix frontend run dev`, port 5173). Use these instead of ad hoc Bash — the venv at `.venv` already has uvicorn/fastapi installed correctly.

## Tests
Tests must run offline — mock `app.analysis.agents._chat` (the NVIDIA/OpenAI-compatible client call) rather than hitting the network. Don't chase pytest failures caused by live API calls; check the mock first.

## Deliberate deferrals
`USE_CELERY=false` in `.env` is intentional — Celery/Redis and Stripe billing are later phases, not missing features to fix.

## UI work
When the user pastes a reference component (motion-primitives/21st.dev-style React snippets), **integrate it verbatim and only rebrand** (app name, colors from the existing design system). Don't redesign or "improve" the pasted layout — that has caused rework before ("keep it same as before remember the way i showed you u changed it").

## LLM provider
Confirmed: the pipeline runs entirely on NVIDIA Nemotron via `NVIDIA_API_KEY` (`app/analysis/agents.py`), with an optional fallback model via `FALLBACK_API_KEY`. There is no Groq code path anywhere in the app — README previously said otherwise (fixed 2026-07-05). Never paste raw key values into chat; reference the `.env` variable name only.

## Obsidian
`../Obsidian/` is a vault the user wants connected to graphify output eventually — check with the user before assuming this integration is live.
