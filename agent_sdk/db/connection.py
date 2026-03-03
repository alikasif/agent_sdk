"""Async SQLite connection pool using aiosqlite."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from typing import Any

import aiosqlite

logger = logging.getLogger("agent_sdk.db")


class DatabaseConnection:
    """Queue-based async connection pool for aiosqlite."""

    def __init__(self, db_path: str = "agent_sdk.db", pool_size: int = 5) -> None:
        self.db_path = db_path
        self.pool_size = pool_size
        self._pool: asyncio.Queue[aiosqlite.Connection] = asyncio.Queue(maxsize=pool_size)
        self._initialized = False

    async def initialize(self) -> None:
        """Create the connection pool, enable WAL mode, and run migrations."""
        if self._initialized:
            return
        for _ in range(self.pool_size):
            conn = await aiosqlite.connect(self.db_path)
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute("PRAGMA busy_timeout=5000")
            await conn.execute("PRAGMA foreign_keys=ON")
            self._pool.put_nowait(conn)
        self._initialized = True
        # Run migrations
        from agent_sdk.db.migrations import MigrationRunner

        runner = MigrationRunner(self)
        await runner.run()
        logger.info("Database initialized at %s (pool_size=%d)", self.db_path, self.pool_size)

    async def _acquire(self) -> aiosqlite.Connection:
        return await self._pool.get()

    async def _release(self, conn: aiosqlite.Connection) -> None:
        await self._pool.put(conn)

    async def execute(self, sql: str, params: list[Any] | None = None) -> aiosqlite.Cursor:
        """Execute a single SQL statement."""
        conn = await self._acquire()
        try:
            cursor = await conn.execute(sql, params or [])
            await conn.commit()
            return cursor
        finally:
            await self._release(conn)

    async def fetch_one(self, sql: str, params: list[Any] | None = None) -> dict[str, Any] | None:
        """Execute and return a single row as a dict, or None."""
        conn = await self._acquire()
        try:
            cursor = await conn.execute(sql, params or [])
            row = await cursor.fetchone()
            if row is None:
                return None
            return dict(row)
        finally:
            await self._release(conn)

    async def fetch_all(self, sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        """Execute and return all rows as list of dicts."""
        conn = await self._acquire()
        try:
            cursor = await conn.execute(sql, params or [])
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
        finally:
            await self._release(conn)

    async def execute_many(self, sql: str, params_list: list[list[Any]]) -> None:
        """Execute the same statement with multiple parameter sets."""
        conn = await self._acquire()
        try:
            await conn.executemany(sql, params_list)
            await conn.commit()
        finally:
            await self._release(conn)

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[aiosqlite.Connection]:
        """Atomic transaction context manager."""
        conn = await self._acquire()
        try:
            await conn.execute("BEGIN")
            yield conn
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise
        finally:
            await self._release(conn)

    async def close(self) -> None:
        """Drain pool and close all connections."""
        while not self._pool.empty():
            conn = self._pool.get_nowait()
            await conn.close()
        self._initialized = False
        logger.info("Database connections closed.")
