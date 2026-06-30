"""
Celery task wrappers. Celery workers can't `await`, so we wrap async
work with asyncio.run() inside a sync task function.
"""
import asyncio

from app.worker import celery_app


@celery_app.task(name="analysis.run", bind=True, max_retries=2)
def run_analysis_task(self, analysis_id: str, source: str, source_type: str) -> None:
    # Lazy import to avoid circular import at module load
    from app.analysis.routes import _run_analysis

    try:
        asyncio.run(_run_analysis(analysis_id, source, source_type))
    except Exception as exc:
        # Celery will retry once if it's a transient error
        raise self.retry(exc=exc, countdown=10)
