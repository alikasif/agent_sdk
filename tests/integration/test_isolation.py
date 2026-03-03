import asyncio
import pytest
from agent_sdk.db.connection import DatabaseConnection
from agent_sdk.db.repositories.session_repo import SessionRepository
from agent_sdk.persistence.memory import MemoryManager
from agent_sdk.persistence.knowledge import KnowledgeStore
from agent_sdk.isolation.scope import user_scope
from agent_sdk.db.repositories.memory_repo import MemoryRepository
from agent_sdk.db.repositories.knowledge_repo import KnowledgeRepository

@pytest.mark.asyncio
async def test_isolation(tmp_path):
    db_path = tmp_path / "test_isolation.db"
    db = DatabaseConnection(str(db_path))
    await db.initialize()

    mem_repo = MemoryRepository(db)
    know_repo = KnowledgeRepository(db)
    memory_mgr = MemoryManager(mem_repo)
    knowledge_store = KnowledgeStore(know_repo)

    # User A
    async with user_scope("userA"):
        await memory_mgr.add_short_term(None, key="foo", value="bar")
        await knowledge_store.put(user_id="userA", namespace="ns1", key="k1", content="v1")

    # User B
    async with user_scope("userB"):
        await memory_mgr.add_short_term(None, key="foo", value="baz")
        await knowledge_store.put(user_id="userB", namespace="ns1", key="k1", content="v2")

    # Verify isolation
    async with user_scope("userA"):
        mems = await mem_repo.get_by_user()
        assert any(m["value"] == "bar" for m in mems)
        know = await know_repo.get(namespace="ns1", key="k1")
        assert know["content"] == "v1"

    async with user_scope("userB"):
        mems = await mem_repo.get_by_user()
        assert any(m["value"] == "baz" for m in mems)
        know = await know_repo.get(namespace="ns1", key="k1")
        assert know["content"] == "v2"

    # ScopedQueryBuilder filtering (sessions)
    sess_repo = SessionRepository(db)
    async with user_scope("userA"):
        sA = await sess_repo.create(agent_name="agentA")
    async with user_scope("userB"):
        sB = await sess_repo.create(agent_name="agentB")
    async with user_scope("userA"):
        listed = await sess_repo.list_by_user()
        assert any(s["agent_name"] == "agentA" for s in listed)
        assert not any(s["agent_name"] == "agentB" for s in listed)

    await db._pool.join()
    for _ in range(db.pool_size):
        conn = await db._acquire()
        await conn.close()
