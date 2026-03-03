import asyncio
import pytest
from agent_sdk.db.connection import DatabaseConnection
from agent_sdk.db.repositories.knowledge_repo import KnowledgeRepository
from agent_sdk.persistence.knowledge import KnowledgeStore
from agent_sdk.isolation.scope import user_scope

@pytest.mark.asyncio
async def test_knowledge_store(tmp_path):
    db_path = tmp_path / "test_knowledge.db"
    db = DatabaseConnection(str(db_path))
    await db.initialize()
    know_repo = KnowledgeRepository(db)
    knowledge_store = KnowledgeStore(know_repo)

    # User A, namespace ns1
    async with user_scope("userA"):
        await knowledge_store.put(user_id="userA", namespace="ns1", key="k1", content="v1")
        entry = await knowledge_store.get(user_id="userA", namespace="ns1", key="k1")
        assert entry.content == "v1"
        # Search
        results = await knowledge_store.search(user_id="userA", namespace="ns1", query="v1")
        assert any(e.key == "k1" for e in results)

    # User B, namespace ns2
    async with user_scope("userB"):
        await knowledge_store.put(user_id="userB", namespace="ns2", key="k2", content="v2")
        entry = await knowledge_store.get(user_id="userB", namespace="ns2", key="k2")
        assert entry.content == "v2"
        # Search
        results = await knowledge_store.search(user_id="userB", namespace="ns2", query="v2")
        assert any(e.key == "k2" for e in results)

    # Namespace isolation
    async with user_scope("userA"):
        entry = await knowledge_store.get(user_id="userA", namespace="ns2", key="k2")
        assert entry is None

    # User isolation
    async with user_scope("userB"):
        entry = await knowledge_store.get(user_id="userB", namespace="ns1", key="k1")
        assert entry is None

    # Delete
    async with user_scope("userA"):
        await knowledge_store.delete(user_id="userA", namespace="ns1", key="k1")
        entry = await knowledge_store.get(user_id="userA", namespace="ns1", key="k1")
        assert entry is None

    await db._pool.join()
    for _ in range(db.pool_size):
        conn = await db._acquire()
        await conn.close()
