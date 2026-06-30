"""
Celery worker entry point. Run with:
    .venv/bin/celery -A app.worker worker --loglevel=info

Only active when USE_CELERY=true. Otherwise FastAPI BackgroundTasks
handles analyses in-process — no Redis required.
"""
from celery import Celery

from app.config import settings

celery_app = Celery(
    "codebase_explainer",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.analysis.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    task_track_started=True,
    # When True, tasks execute synchronously in the calling process (used by tests).
    task_always_eager=False,
)
