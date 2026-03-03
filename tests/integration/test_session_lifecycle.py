import asyncio
import json
import pytest
import tempfile
from agent_sdk.db.connection import DatabaseConnection
from agent_sdk.db.repositories.session_repo import SessionRepository
from agent_sdk.core.session import Session
from agent_sdk.persistence.session_store import SessionStore
from agent_sdk.types import SessionStatus

@pytest.mark.asyncio
async def test_session_lifecycle(tmp_path):
    db_path = tmp_path / "test_session.db"
    db = DatabaseConnection(str(db_path))
    await db.initialize()
    repo = SessionRepository(db)
    store = SessionStore(repo)

    # Create session
    session = await store.create_session(user_id="user1", agent_name="test_agent", metadata={"foo": "bar"})
    assert session.id
    assert session.user_id == "user1"
    assert session.agent_name == "test_agent"
    assert session.status == SessionStatus.ACTIVE

    # Load session
    loaded = await store.get_session(session.id)
    assert loaded.id == session.id
    assert loaded.user_id == "user1"

    # List sessions
    sessions = await store.list_sessions(user_id="user1")
    assert any(s.id == session.id for s in sessions)

    # Archive session
    await store.archive_session(session.id)
    archived = await store.get_session(session.id)
    assert archived.status == SessionStatus.ARCHIVED

    # Status transitions
    await store.set_status(session.id, SessionStatus.ACTIVE)
    active = await store.get_session(session.id)
    assert active.status == SessionStatus.ACTIVE

    await db._pool.join()
    for _ in range(db.pool_size):
        conn = await db._acquire()
        await conn.close()
