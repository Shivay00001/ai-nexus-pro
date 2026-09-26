"""Shared fixtures for the GOATCLAW test suite.

Uses an isolated sqlite database per test session (never the repo's
``memory.db``) and strips any real LLM/search API keys so the "no key"
honesty tests exercise the true no-credential code paths.
"""
import os
import tempfile

import pytest

# Point the DB at a temp file BEFORE any goatclaw module is imported.
_TMPDIR = tempfile.mkdtemp(prefix="goatclaw_test_")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TMPDIR}/test_memory.db"


@pytest.fixture
async def event_bus():
    """A started, local (non-persistent) EventBus."""
    from goatclaw.core.event_bus import EventBus

    bus = EventBus(enable_persistence=False)
    await bus.start()
    yield bus
    await bus.stop()


@pytest.fixture
async def db():
    """Initialized database with a seeded enterprise test user."""
    from goatclaw.database import db_manager, UserAccountModel
    from sqlalchemy import select

    await db_manager.init_db()
    async with await db_manager.get_session() as session:
        for user_id in ("test-user", "system_orchestrator"):
            stmt = select(UserAccountModel).where(UserAccountModel.user_id == user_id)
            if not (await session.execute(stmt)).scalar_one_or_none():
                session.add(UserAccountModel(
                    user_id=user_id,
                    balance_credits=1000.0,
                    tier="enterprise",
                ))
        await session.commit()
    yield db_manager
    await db_manager.close()


@pytest.fixture
def no_llm_keys(monkeypatch):
    """Remove all LLM/search API keys so no-credential paths are exercised."""
    for var in (
        "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY",
        "KIMI_API_KEY", "MOONSHOT_API_KEY", "NVIDIA_API_KEY",
        "SERPER_API_KEY", "TAVILY_API_KEY",
    ):
        monkeypatch.delenv(var, raising=False)
