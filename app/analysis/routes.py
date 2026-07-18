import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.agents import (
    assess_difficulty,
    audit_security,
    explain_codebase,
    generate_diagram,
    generate_plan,
)
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

# Number of agents the pipeline reports progress for: difficulty, explanation,
# plan, diagram, security.
TOTAL_PIPELINE_STAGES = 5

# Hard per-stage ceiling. The OpenAI SDK's own `timeout` covers the well-behaved
# case (and triggers the fallback model), but against an endpoint that trickles
# bytes on a kept-alive connection the read timeout can be repeatedly reset and
# a single call can hang far past its budget — observed live. This asyncio-level
# wait_for is independent of SDK/transport behaviour and guarantees a stuck stage
# surfaces as an error instead of leaving the analysis "processing" forever.
# Budget = primary (60s) + fallback (60s) + slack.
_STAGE_TIMEOUT_SECONDS = 140.0


async def _agent(fn, *args):
    """Run one agent in a worker thread with a hard timeout. On timeout the
    orphaned thread finishes on its own (blocked on network I/O that will
    eventually return); we stop waiting and let the caller fail the analysis."""
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(fn, *args), timeout=_STAGE_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError:
        raise RuntimeError(
            f"Analysis agent '{fn.__name__}' timed out after {int(_STAGE_TIMEOUT_SECONDS)}s"
        )


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
    progress: int
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
    target.progress = TOTAL_PIPELINE_STAGES
    target.completed_at = datetime.now(timezone.utc)


async def _run_pipeline_with_progress(ingestion: dict, analysis: Analysis, db: AsyncSession) -> dict:
    """Run the five agents, executing the two independent ones (diagram and
    security — they need only the ingested files) concurrently with the
    difficulty → explanation → plan chain. Critical path drops from 5 sequential
    model calls to 3. A completed-stage counter is committed as each agent
    finishes so the client can render real progress.

    All three tracks share one AsyncSession, which is *not* safe for concurrent
    use, so every DB touch is serialised behind `progress_lock`. The agent calls
    themselves run in worker threads via `to_thread` and never touch the session.
    """
    progress_lock = asyncio.Lock()

    async def stage_done() -> None:
        async with progress_lock:
            analysis.progress = (analysis.progress or 0) + 1
            await db.commit()

    async def explain_track():
        difficulty = await _agent(assess_difficulty, ingestion)
        await stage_done()
        explanation = await _agent(explain_codebase, ingestion, difficulty)
        await stage_done()
        plan = await _agent(generate_plan, ingestion, explanation)
        await stage_done()
        return difficulty, explanation, plan

    async def diagram_track():
        diagram = await _agent(generate_diagram, ingestion)
        await stage_done()
        return diagram

    async def security_track():
        security = await _agent(audit_security, ingestion)
        await stage_done()
        return security

    (difficulty, explanation, plan), diagram, security = await asyncio.gather(
        explain_track(), diagram_track(), security_track()
    )
    return {
        "difficulty": difficulty,
        "explanation": explanation,
        "plan": plan,
        "diagram": diagram,
        "security": security,
    }


async def _refund_quota(db: AsyncSession, user_id: str) -> None:
    """Give back the analysis credit consumed at submission. Quota is charged
    up-front (so concurrent submissions can't slip past the check), then
    refunded here when the analysis cost nothing (cache hit) or delivered
    nothing (pipeline error)."""
    user = await db.get(User, user_id)
    if user and user.monthly_usage > 0:
        user.monthly_usage -= 1


async def _run_analysis(analysis_id: str, source: str, source_type: str) -> None:
    """Background task: ingest → check cache → run pipeline → persist."""
    async with _session_factory() as db:
        analysis = await db.get(Analysis, analysis_id)
        if not analysis:
            return

        analysis.status = AnalysisStatus.processing
        analysis.progress = 0
        await db.commit()

        try:
            if source_type == "github":
                ingestion = await asyncio.to_thread(ingest_github, source)
            else:
                ingestion = await asyncio.to_thread(ingest_directory, source)

            content_hash = compute_content_hash(ingestion["files"])
            analysis.content_hash = content_hash

            # Cache lookup — identical content = serve from cache, no model
            # calls made, so the user gets their credit back
            cached = await _find_cached(db, content_hash)
            if cached and cached.id != analysis.id:
                _copy_cached_results(analysis, cached)
                await _refund_quota(db, analysis.user_id)
                await db.commit()
                return

            # Cache miss — run the pipeline (diagram + security run in parallel
            # with the difficulty → explanation → plan chain)
            result = await _run_pipeline_with_progress(ingestion, analysis, db)

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
            analysis.progress = TOTAL_PIPELINE_STAGES
            analysis.completed_at = datetime.now(timezone.utc)

        except Exception as exc:
            analysis.status = AnalysisStatus.error
            analysis.error_message = str(exc)
            # Failed analyses shouldn't count against the monthly quota
            await _refund_quota(db, analysis.user_id)

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
    current_user.monthly_usage += 1
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
    current_user.monthly_usage += 1
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
        progress=getattr(analysis, "progress", 0) or 0,
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
