"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Pytest Root Test Configuration & Fixtures.
"""
import sys
from pathlib import Path

# Ensure root repository and packages/ are in Python path
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool


import app.db.session as db_session_module
from app.core.config import settings
from app.core.middleware import reset_rate_limiter
from app.main import app
from app.db.base import Base
from app.db.session import get_db

# Use SQLite in-memory for fast unit testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

@event.listens_for(test_engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Monkeypatch app.db.session so scripts importing AsyncSessionLocal use test_engine
db_session_module.engine = test_engine
db_session_module.AsyncSessionLocal = TestingSessionLocal


@pytest.fixture(autouse=True)
def enforce_test_settings():
    old_env = settings.APP_ENV
    old_limit = settings.RATE_LIMIT_PER_MINUTE
    old_flag = settings.ENABLE_RATE_LIMITER_IN_TEST

    settings.APP_ENV = "test"
    settings.ENABLE_RATE_LIMITER_IN_TEST = False
    reset_rate_limiter()

    yield

    settings.APP_ENV = old_env
    settings.RATE_LIMIT_PER_MINUTE = old_limit
    settings.ENABLE_RATE_LIMITER_IN_TEST = old_flag
    reset_rate_limiter()


@pytest.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session
