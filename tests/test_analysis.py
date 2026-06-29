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
