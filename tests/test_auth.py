import pytest
from httpx import AsyncClient

import app.auth.routes as auth_routes


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    resp = await client.post("/auth/register", json={"email": "a@b.com", "password": "password123"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "a@b.com"
    assert "user_id" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    payload = {"email": "dup@b.com", "password": "password123"}
    await client.post("/auth/register", json=payload)
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient):
    resp = await client.post("/auth/register", json={"email": "c@b.com", "password": "short"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post("/auth/register", json={"email": "user@b.com", "password": "password123"})
    resp = await client.post("/auth/login", json={"email": "user@b.com", "password": "password123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/auth/register", json={"email": "x@b.com", "password": "password123"})
    resp = await client.post("/auth/login", json={"email": "x@b.com", "password": "wrongpass"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_email_case_insensitive(client: AsyncClient):
    """Registering Foo@B.com and logging in as foo@b.com must be the same
    account — email lookups must not be case-sensitive."""
    await client.post("/auth/register", json={"email": "Foo@B.com", "password": "password123"})
    dup = await client.post("/auth/register", json={"email": "foo@b.com", "password": "password123"})
    assert dup.status_code == 400

    resp = await client.post("/auth/login", json={"email": "FOO@B.COM", "password": "password123"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_turnstile_noop_when_unconfigured(client: AsyncClient, monkeypatch):
    """With no TURNSTILE_SECRET_KEY set (the default), registration must work
    with no turnstile_token at all — the CAPTCHA guard is opt-in."""
    monkeypatch.setattr(auth_routes.settings, "turnstile_secret_key", "")
    resp = await client.post(
        "/auth/register", json={"email": "no-captcha@b.com", "password": "password123"}
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_turnstile_blocks_missing_token_when_configured(client: AsyncClient, monkeypatch):
    """Once TURNSTILE_SECRET_KEY is configured, registering without a token
    must be rejected before a user is ever created."""
    monkeypatch.setattr(auth_routes.settings, "turnstile_secret_key", "fake-secret")
    resp = await client.post(
        "/auth/register", json={"email": "bot@b.com", "password": "password123"}
    )
    assert resp.status_code == 400
    # confirm no account was actually created
    login = await client.post("/auth/login", json={"email": "bot@b.com", "password": "password123"})
    assert login.status_code == 401


@pytest.mark.asyncio
async def test_turnstile_accepts_verified_token_when_configured(client: AsyncClient, monkeypatch):
    """A token that Cloudflare's siteverify endpoint accepts must let
    registration through."""
    monkeypatch.setattr(auth_routes.settings, "turnstile_secret_key", "fake-secret")

    class _FakeResponse:
        def json(self):
            return {"success": True}

    class _FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, *args, **kwargs):
            return _FakeResponse()

    monkeypatch.setattr(auth_routes.httpx, "AsyncClient", lambda **kwargs: _FakeAsyncClient())

    resp = await client.post(
        "/auth/register",
        json={"email": "verified@b.com", "password": "password123", "turnstile_token": "real-token"},
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_me_starts_at_zero_usage(client: AsyncClient, auth_headers):
    resp = await client.get("/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan_tier"] == "free"
    assert data["monthly_usage"] == 0
    assert data["monthly_quota"] == 10


@pytest.mark.asyncio
async def test_me_usage_increments_after_analysis(client: AsyncClient, auth_headers, tmp_path):
    (tmp_path / "main.py").write_text("print('hi')")
    await client.post(
        "/analyze/local", json={"directory_path": str(tmp_path)}, headers=auth_headers
    )
    resp = await client.get("/auth/me", headers=auth_headers)
    assert resp.json()["monthly_usage"] == 1
