import pytest
from httpx import AsyncClient

import app.analysis.agents as agents


@pytest.mark.asyncio
async def test_analyze_local_invalid_path(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/analyze/local",
        json={"directory_path": "/nonexistent/path/xyz"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_analyze_local_requires_auth(client: AsyncClient, tmp_path):
    resp = await client.post("/analyze/local", json={"directory_path": str(tmp_path)})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_analyze_local_accepted(client: AsyncClient, auth_headers, tmp_path):
    (tmp_path / "main.py").write_text("print('hello')")
    resp = await client.post(
        "/analyze/local",
        json={"directory_path": str(tmp_path)},
        headers=auth_headers,
    )
    assert resp.status_code == 202
    data = resp.json()
    assert "id" in data
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_get_analysis_not_found(client: AsyncClient, auth_headers):
    resp = await client.get("/analyze/nonexistent-id", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_history_empty(client: AsyncClient, auth_headers):
    resp = await client.get("/analyze/history", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_history_after_submit(client: AsyncClient, auth_headers, tmp_path):
    (tmp_path / "app.py").write_text("x = 1")
    await client.post(
        "/analyze/local",
        json={"directory_path": str(tmp_path)},
        headers=auth_headers,
    )
    resp = await client.get("/analyze/history", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_ingestion_path_traversal(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/analyze/local",
        json={"directory_path": "../../etc"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_analyze_local_rejects_system_directory(client: AsyncClient, auth_headers):
    """A directly-supplied absolute system path (no traversal needed) must
    also be rejected — the previous check only validated existence, so any
    authenticated user could point /analyze/local at /etc, /Users, etc. and
    have the contents shipped to the LLM and stored in their analysis."""
    resp = await client.post(
        "/analyze/local",
        json={"directory_path": "/etc"},
        headers=auth_headers,
    )
    assert resp.status_code == 400

    resp = await client.post(
        "/analyze/local",
        json={"directory_path": "/Users"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_analyze_local_completes_with_full_pipeline(client: AsyncClient, auth_headers, tmp_path):
    (tmp_path / "main.py").write_text("print('hello')")
    submit = await client.post(
        "/analyze/local",
        json={"directory_path": str(tmp_path)},
        headers=auth_headers,
    )
    analysis_id = submit.json()["id"]

    resp = await client.get(f"/analyze/{analysis_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "done"
    assert data["difficulty"] == "Intermediate"
    assert data["primary_language"] == "Python"
    assert "FastAPI" in data["frameworks"]
    assert data["explanation"]
    assert data["plan"]
    assert data["diagram"].startswith("graph TD")
    assert data["security"]["risk_level"] == "Low"
    assert data["served_from_cache"] is False
    # All five agents ran to completion (diagram + security execute in parallel
    # with the difficulty→explanation→plan chain; order must not affect the count)
    assert data["progress"] == 5


@pytest.mark.asyncio
async def test_identical_content_served_from_cache(client: AsyncClient, auth_headers, tmp_path):
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()
    (dir_a / "main.py").write_text("print('same content')")
    (dir_b / "main.py").write_text("print('same content')")

    first = await client.post(
        "/analyze/local", json={"directory_path": str(dir_a)}, headers=auth_headers
    )
    first_id = first.json()["id"]
    first_result = await client.get(f"/analyze/{first_id}", headers=auth_headers)
    assert first_result.json()["served_from_cache"] is False

    second = await client.post(
        "/analyze/local", json={"directory_path": str(dir_b)}, headers=auth_headers
    )
    second_id = second.json()["id"]
    second_result = await client.get(f"/analyze/{second_id}", headers=auth_headers)
    data = second_result.json()
    assert data["status"] == "done"
    assert data["served_from_cache"] is True
    assert data["explanation"] == first_result.json()["explanation"]


@pytest.mark.asyncio
async def test_github_invalid_url_rejected(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/analyze/github",
        json={"repo_url": "not-a-valid-url"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_github_non_github_host_rejected(client: AsyncClient, auth_headers):
    """A URL shaped like <host>/<owner>/<repo> but on a non-GitHub host must
    be rejected instead of silently treated as a GitHub owner/repo pair."""
    resp = await client.post(
        "/analyze/github",
        json={"repo_url": "https://gitlab.com/owner/repo"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_quota_consumed_at_submission_not_completion(client: AsyncClient, auth_headers, tmp_path):
    """monthly_usage must increment as soon as a request is accepted, not
    after the background pipeline finishes — otherwise concurrent submissions
    made before any of them complete could all pass the quota check."""
    (tmp_path / "main.py").write_text("print('hi')")
    resp = await client.post(
        "/analyze/local", json={"directory_path": str(tmp_path)}, headers=auth_headers
    )
    assert resp.status_code == 202

    me = await client.get("/auth/me", headers=auth_headers)
    assert me.json()["monthly_usage"] == 1


@pytest.mark.asyncio
async def test_quota_refunded_on_cache_hit(client: AsyncClient, auth_headers, tmp_path):
    """A cache-served analysis makes no model calls, so the credit charged at
    submission must be given back once the cached result is copied over."""
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()
    (dir_a / "main.py").write_text("print('refund me')")
    (dir_b / "main.py").write_text("print('refund me')")

    await client.post("/analyze/local", json={"directory_path": str(dir_a)}, headers=auth_headers)
    second = await client.post(
        "/analyze/local", json={"directory_path": str(dir_b)}, headers=auth_headers
    )
    result = await client.get(f"/analyze/{second.json()['id']}", headers=auth_headers)
    assert result.json()["served_from_cache"] is True

    me = await client.get("/auth/me", headers=auth_headers)
    # First run consumed 1; the cache hit was charged then refunded
    assert me.json()["monthly_usage"] == 1


@pytest.mark.asyncio
async def test_quota_refunded_on_pipeline_error(client: AsyncClient, auth_headers, tmp_path, monkeypatch):
    """A failed analysis delivers nothing — the credit must be refunded."""
    def _broken_chat(system, user, temperature=0.3, max_tokens=4096):
        raise RuntimeError("upstream exploded")

    monkeypatch.setattr(agents, "_chat", _broken_chat)

    (tmp_path / "main.py").write_text("print('boom')")
    submit = await client.post(
        "/analyze/local", json={"directory_path": str(tmp_path)}, headers=auth_headers
    )
    result = await client.get(f"/analyze/{submit.json()['id']}", headers=auth_headers)
    assert result.json()["status"] == "error"

    me = await client.get("/auth/me", headers=auth_headers)
    assert me.json()["monthly_usage"] == 0


# ── Difficulty agent hardening ─────────────────────────────────────────────────

_INGESTION_STUB = {
    "file_tree": "repo\n└── main.py",
    "files": [{"path": "main.py", "content": "print('x')", "size": 10}],
    "stats": {"language_counts": {".py": 3}},
}


def test_difficulty_retry_recovers_from_bad_json(monkeypatch):
    """One malformed response must trigger a retry, not sink the chain."""
    responses = iter([
        "Sure! Here's my assessment: it's moderately hard.",  # unparseable
        '{"level": "Advanced", "reason": "r", "primary_language": "Python", "frameworks": []}',
    ])
    monkeypatch.setattr(agents, "_chat", lambda *a, **kw: next(responses))

    result = agents.assess_difficulty(_INGESTION_STUB)
    assert result["level"] == "Advanced"


def test_difficulty_falls_back_to_default_after_two_bad_responses(monkeypatch):
    monkeypatch.setattr(agents, "_chat", lambda *a, **kw: "not json, still not json")

    result = agents.assess_difficulty(_INGESTION_STUB)
    assert result["level"] == "Intermediate"
    # Primary language inferred from extension stats, not left blank
    assert result["primary_language"] == "Python"
    assert result["frameworks"] == []


def test_difficulty_normalizes_invalid_level(monkeypatch):
    monkeypatch.setattr(
        agents, "_chat",
        lambda *a, **kw: '{"level": "Expert", "reason": "r", "primary_language": "Go", "frameworks": []}',
    )
    result = agents.assess_difficulty(_INGESTION_STUB)
    assert result["level"] == "Intermediate"
    assert result["primary_language"] == "Go"


# ── File selection ─────────────────────────────────────────────────────────────

def _f(path, content="x" * 100):
    return {"path": path, "content": content, "size": len(content)}


def test_select_files_prioritizes_readme_manifest_and_entrypoints():
    files = [
        _f("src/utils/deeply/nested/helper_seventeen.py"),
        _f("styles/theme.css"),
        _f("README.md"),
        _f("package.json"),
        _f("src/main.py"),
    ]
    selected = {f["path"] for f in agents._select_files(files, 3)}
    assert selected == {"README.md", "package.json", "src/main.py"}


def test_select_files_security_keywords_boost():
    files = [
        _f("src/widgets/tooltip.py"),
        _f("src/auth/login.py"),
    ]
    selected = [f["path"] for f in agents._select_files(files, 1, keywords=agents._SECURITY_KEYWORDS)]
    assert selected == ["src/auth/login.py"]


def test_select_files_deprioritizes_tests():
    files = [
        _f("src/core.py"),
        _f("tests/test_core.py"),
    ]
    selected = [f["path"] for f in agents._select_files(files, 1)]
    assert selected == ["src/core.py"]
