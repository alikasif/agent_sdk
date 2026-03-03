"""Shared test fixtures for agent_sdk tests."""
import asyncio
import pytest
import pytest_asyncio
from agent_sdk.db.connection import DatabaseConnection
from agent_sdk.isolation.scope import set_user_scope, clear_user_scope

TEST_USER_ID = "test-user-001"
TEST_USER_ID_2 = "test-user-002"

@pytest_asyncio.fixture
async def db():
	"""In-memory SQLite database for testing."""
	conn = DatabaseConnection(db_path=":memory:", pool_size=1)
	await conn.initialize()
	yield conn
	await conn.close()

@pytest.fixture
def user_scope():
	"""Set user scope for isolation testing."""
	token = set_user_scope(TEST_USER_ID)
	yield TEST_USER_ID
	clear_user_scope(token)
