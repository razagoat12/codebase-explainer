import pytest
from httpx import AsyncClient


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
