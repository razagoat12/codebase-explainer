from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.analysis.routes import router as analysis_router
from app.auth.routes import router as auth_router
from app.config import settings
from app.database import init_db

# Error tracking — a no-op until SENTRY_DSN is set (e.g. local dev), so this
# never requires a Sentry account to run the app.
if settings.sentry_dsn:
    import sentry_sdk

    sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1, send_default_pii=False)

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Codebase Explainer",
    description="Analyse any codebase and get a plain-language explanation powered by NVIDIA Nemotron.",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes must be registered before the static mount
@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok"}

app.include_router(auth_router)
app.include_router(analysis_router)

# React frontend (Vite build output). Vite-hashed assets are served directly;
# any other path falls back to index.html so React Router can handle it client-side.
# Only present for the single-process deploy — a split deploy (frontend on
# Vercel, backend here) never builds frontend/dist, so this whole block is
# skipped rather than crashing the app at import time.
FRONTEND_DIST = Path("frontend/dist").resolve()
if (FRONTEND_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="frontend-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        candidate = (FRONTEND_DIST / full_path).resolve()
        if full_path and candidate.is_relative_to(FRONTEND_DIST) and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
