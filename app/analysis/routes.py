import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.agents import run_pipeline
from app.analysis.github import ingest_github, parse_github_url
from app.analysis.ingestion import compute_content_hash, ingest_directory
from app.analysis.models import Analysis, AnalysisStatus
from app.auth.models import User
from app.auth.routes import enforce_quota, get_current_user
from app.config import settings
from app.database import AsyncSessionLocal, get_db


def _dispatch(background_tasks: BackgroundTasks, analysis_id: str, source: str, source_type: str) -> None:
    """Send the analysis job to Celery if enabled, else run as a FastAPI background task."""
    if settings.use_celery:
        from app.analysis.tasks import run_analysis_task
        run_analysis_task.delay(analysis_id, source, source_type)
    else:
        background_tasks.add_task(_run_analysis, analysis_id, source, source_type)

# Overridable in tests
_session_factory = AsyncSessionLocal

router = APIRouter(prefix="/analyze", tags=["analysis"])


class LocalAnalysisRequest(BaseModel):
    directory_path: str


class GithubAnalysisRequest(BaseModel):
    repo_url: str


class AnalysisSummary(BaseModel):
    id: str
    status: str
    directory_path: str
    source_type: str
    created_at: datetime


class SecurityFinding(BaseModel):
    severity: str
    category: str
    file: str
    issue: str
    fix: str


class SecurityReport(BaseModel):
    summary: str
    risk_level: str
    findings: list[SecurityFinding]


class AnalysisResult(BaseModel):
    id: str
    status: str
    directory_path: str
    source_type: str
    difficulty: str | None
    difficulty_reason: str | None
    primary_language: str | None
    frameworks: list[str] | None
    explanation: str | None
    plan: str | None
    diagram: str | None
    security: SecurityReport | None
    served_from_cache: bool
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


async def _find_cached(db: AsyncSession, content_hash: str) -> Analysis | None:
    """Return a completed analysis with the same content hash, if any exists."""
    return await db.scalar(
        select(Analysis)
        .where(Analysis.content_hash == content_hash)
        .where(Analysis.status == AnalysisStatus.done)
        .order_by(Analysis.completed_at.desc())
        .limit(1)
    )


def _copy_cached_results(target: Analysis, source: Analysis) -> None:
    target.difficulty_level = source.difficulty_level
    target.difficulty_reason = source.difficulty_reason
    target.primary_language = source.primary_language
    target.frameworks = source.frameworks
    target.explanation = source.explanation
    target.plan = source.plan
    target.diagram = source.diagram
    target.security_findings = source.security_findings
    target.security_risk = source.security_risk
    target.content_hash = source.content_hash
    target.served_from_cache = True
    target.status = AnalysisStatus.done
    target.completed_at = datetime.now(timezone.utc)


async def _run_analysis(analysis_id: str, source: str, source_type: str) -> None:
    """Background task: ingest → check cache → run pipeline → persist."""
    async with _session_factory() as db:
        analysis = await db.get(Analysis, analysis_id)
        if not analysis:
            return

        analysis.status = AnalysisStatus.processing
        await db.commit()

        try:
            if source_type == "github":
                ingestion = await asyncio.to_thread(ingest_github, source)
            else:
                ingestion = await asyncio.to_thread(ingest_directory, source)

            content_hash = compute_content_hash(ingestion["files"])
            analysis.content_hash = content_hash

            # Cache lookup — identical content = serve from cache
            cached = await _find_cached(db, content_hash)
            if cached and cached.id != analysis.id:
                _copy_cached_results(analysis, cached)
                # Increment user quota even for cached results (still costs us nothing but a DB read)
                user = await db.get(User, analysis.user_id)
                if user:
                    user.monthly_usage += 1
                await db.commit()
                return

            # Cache miss — run full pipeline
            result = await asyncio.to_thread(run_pipeline, ingestion)

            difficulty = result["difficulty"]
            analysis.difficulty_level = difficulty.get("level")
            analysis.difficulty_reason = difficulty.get("reason")
            analysis.primary_language = difficulty.get("primary_language")
            analysis.frameworks = json.dumps(difficulty.get("frameworks", []))
            analysis.explanation = result["explanation"]
            analysis.plan = result["plan"]
            analysis.diagram = result.get("diagram")

            sec = result.get("security") or {}
            analysis.security_findings = json.dumps(sec)
            analysis.security_risk = sec.get("risk_level")

            analysis.status = AnalysisStatus.done
            analysis.completed_at = datetime.now(timezone.utc)

            user = await db.get(User, analysis.user_id)
            if user:
                user.monthly_usage += 1

        except Exception as exc:
            analysis.status = AnalysisStatus.error
            analysis.error_message = str(exc)

        await db.commit()


@router.post("/local", response_model=AnalysisSummary, status_code=202)
async def analyze_local(
    body: LocalAnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(enforce_quota),
    db: AsyncSession = Depends(get_db),
):
    try:
        from app.analysis.ingestion import is_safe_path
        is_safe_path(body.directory_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    analysis = Analysis(user_id=current_user.id, directory_path=body.directory_path, source_type="local")
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    _dispatch(background_tasks, analysis.id, body.directory_path, "local")

    return AnalysisSummary(
        id=analysis.id, status=analysis.status,
        directory_path=analysis.directory_path,
        source_type=analysis.source_type, created_at=analysis.created_at,
    )


@router.post("/github", response_model=AnalysisSummary, status_code=202)
async def analyze_github(
    body: GithubAnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(enforce_quota),
    db: AsyncSession = Depends(get_db),
):
    try:
        parse_github_url(body.repo_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    analysis = Analysis(user_id=current_user.id, directory_path=body.repo_url, source_type="github")
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    _dispatch(background_tasks, analysis.id, body.repo_url, "github")

    return AnalysisSummary(
        id=analysis.id, status=analysis.status,
        directory_path=analysis.directory_path,
        source_type=analysis.source_type, created_at=analysis.created_at,
    )


@router.get("/history", response_model=list[AnalysisSummary])
async def get_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.scalars(
        select(Analysis)
        .where(Analysis.user_id == current_user.id)
        .order_by(Analysis.created_at.desc())
        .limit(50)
    )
    return [
        AnalysisSummary(
            id=r.id, status=r.status, directory_path=r.directory_path,
            source_type=getattr(r, "source_type", "local"), created_at=r.created_at,
        )
        for r in rows
    ]


@router.get("/{analysis_id}", response_model=AnalysisResult)
async def get_analysis(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    analysis = await db.get(Analysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    if analysis.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    frameworks = json.loads(analysis.frameworks) if analysis.frameworks else None
    security = None
    if analysis.security_findings:
        try:
            sec_raw = json.loads(analysis.security_findings)
            security = SecurityReport(
                summary=sec_raw.get("summary", ""),
                risk_level=sec_raw.get("risk_level", "Low"),
                findings=[SecurityFinding(**f) for f in sec_raw.get("findings", [])],
            )
        except (json.JSONDecodeError, TypeError, ValueError):
            security = None

    return AnalysisResult(
        id=analysis.id,
        status=analysis.status,
        directory_path=analysis.directory_path,
        source_type=getattr(analysis, "source_type", "local"),
        difficulty=analysis.difficulty_level,
        difficulty_reason=analysis.difficulty_reason,
        primary_language=analysis.primary_language,
        frameworks=frameworks,
        explanation=analysis.explanation,
        plan=analysis.plan,
        diagram=analysis.diagram,
        security=security,
        served_from_cache=analysis.served_from_cache,
        error_message=analysis.error_message,
        created_at=analysis.created_at,
        completed_at=analysis.completed_at,
    )
