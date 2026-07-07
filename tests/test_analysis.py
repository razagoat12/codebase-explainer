import pytest
from httpx import AsyncClient


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
