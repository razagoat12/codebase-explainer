import json

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.analysis.agents as _agents
import app.analysis.routes as _analysis_routes
from app.database import Base, get_db
from app.main import app


def _fake_chat(system: str, user: str, temperature: float = 0.3) -> str:
    """Stand-in for Groq calls so tests never hit the network."""
    if "codebase difficulty" in system:
        return json.dumps({
            "level": "Intermediate",
            "reason": "Fixture-generated reason for test purposes.",
            "primary_language": "Python",
            "frameworks": ["FastAPI"],
        })
    if "security engineer" in system:
        return json.dumps({
            "summary": "No issues found in test fixture.",
            "risk_level": "Low",
            "findings": [],
        })
    if "Mermaid diagram" in system:
        return "graph TD\n  A[main.py] --> B[app]"
    if "coding mentor" in system:
        return "## Overview\nThis is a fixture explanation for tests."
    if "software architect" in system:
        return "## Phase 0 — MVP\nGoals: ship the fixture plan."
    return "mock response"


@pytest.fixture(autouse=True)
def mock_groq(monkeypatch):
    monkeypatch.setattr(_agents, "_chat", _fake_chat)

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = async_sessionmaker(test_engine, expire_on_commit=False)


async def override_get_db():
    async with TestSession() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db
_analysis_routes._session_factory = TestSession


@pytest_asyncio.fixture(autouse=True)
async def reset_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def auth_headers(client):
    await client.post("/auth/register", json={"email": "dev@b.com", "password": "password123"})
    resp = await client.post("/auth/login", json={"email": "dev@b.com", "password": "password123"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
