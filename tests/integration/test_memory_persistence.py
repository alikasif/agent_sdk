import asyncio
import pytest
from agent_sdk.db.connection import DatabaseConnection
from agent_sdk.db.repositories.memory_repo import MemoryRepository
from agent_sdk.persistence.memory import MemoryManager, MemoryType
from agent_sdk.isolation.scope import user_scope

@pytest.mark.asyncio
async def test_memory_persistence(tmp_path):
    db_path = tmp_path / "test_memory.db"
    db = DatabaseConnection(str(db_path))
    await db.initialize()
    mem_repo = MemoryRepository(db)
    memory_mgr = MemoryManager(mem_repo)

    # User A
    async with user_scope("userA"):
        # Add short-term
        await memory_mgr.add_short_term(None, key="foo", value="bar")
        st = await memory_mgr.get_short_term(None)
        assert any(m.key == "foo" and m.value == "bar" for m in st)

        # Add long-term
        await memory_mgr.add_long_term(None, key="topic", value="summary", tags=["tag1", "tag2"])
        lt = await memory_mgr.search_long_term(None, query="summary")
        assert any(m.key == "topic" and "tag1" in m.tags for m in lt)

    # User B
    async with user_scope("userB"):
        await memory_mgr.add_short_term(None, key="foo", value="baz")
        st = await memory_mgr.get_short_term(None)
        assert any(m.key == "foo" and m.value == "baz" for m in st)
        lt = await memory_mgr.search_long_term(None, query="summary")
        assert not any(m.key == "topic" for m in lt)

    await db._pool.join()
    for _ in range(db.pool_size):
        conn = await db._acquire()
        await conn.close()
