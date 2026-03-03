"""Forward-only schema migration runner for SQLite."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_sdk.db.connection import DatabaseConnection

logger = logging.getLogger("agent_sdk.db.migrations")

# Ordered list of (version, description, sql_statements)
_MIGRATIONS: list[tuple[int, str, list[str]]] = [
    (
        1,
        "Create sessions table",
        [
            """CREATE TABLE IF NOT EXISTS sessions (
                id          TEXT PRIMARY KEY,
                user_id     TEXT NOT NULL,
                agent_name  TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'active',
                metadata    TEXT NOT NULL DEFAULT '{}',
                created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
            )""",
            "CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(user_id, status)",
        ],
    ),
    (
        2,
        "Create messages table",
        [
            """CREATE TABLE IF NOT EXISTS messages (
                id           TEXT PRIMARY KEY,
                session_id   TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                user_id      TEXT NOT NULL,
                role         TEXT NOT NULL,
                content      TEXT,
                tool_calls   TEXT,
                tool_call_id TEXT,
                name         TEXT,
                metadata     TEXT NOT NULL DEFAULT '{}',
                timestamp    TEXT NOT NULL DEFAULT (datetime('now')),
                ordinal      INTEGER NOT NULL
            )""",
            "CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, ordinal)",
            "CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_id)",
        ],
    ),
    (
        3,
        "Create steps table",
        [
            """CREATE TABLE IF NOT EXISTS steps (
                id              TEXT PRIMARY KEY,
                session_id      TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                user_id         TEXT NOT NULL,
                step_number     INTEGER NOT NULL,
                status          TEXT NOT NULL DEFAULT 'pending',
                input_messages  TEXT NOT NULL DEFAULT '[]',
                output_message  TEXT,
                tool_calls      TEXT NOT NULL DEFAULT '[]',
                tool_results    TEXT NOT NULL DEFAULT '[]',
                checkpoint      BLOB,
                idempotency_key TEXT NOT NULL,
                error           TEXT,
                started_at      TEXT,
                completed_at    TEXT,
                UNIQUE(session_id, step_number)
            )""",
            "CREATE INDEX IF NOT EXISTS idx_steps_session ON steps(session_id, step_number)",
            "CREATE INDEX IF NOT EXISTS idx_steps_user ON steps(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_steps_idempotency ON steps(idempotency_key)",
        ],
    ),
    (
        4,
        "Create idempotency_keys table",
        [
            """CREATE TABLE IF NOT EXISTS idempotency_keys (
                key         TEXT PRIMARY KEY,
                session_id  TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                user_id     TEXT NOT NULL,
                result      TEXT NOT NULL,
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            )""",
            "CREATE INDEX IF NOT EXISTS idx_idempotency_session ON idempotency_keys(session_id)",
        ],
    ),
    (
        5,
        "Create memory table",
        [
            """CREATE TABLE IF NOT EXISTS memory (
                id          TEXT PRIMARY KEY,
                user_id     TEXT NOT NULL,
                session_id  TEXT,
                key         TEXT NOT NULL,
                value       TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                tags        TEXT NOT NULL DEFAULT '[]',
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            )""",
            "CREATE INDEX IF NOT EXISTS idx_memory_user ON memory(user_id, memory_type)",
            "CREATE INDEX IF NOT EXISTS idx_memory_session ON memory(session_id)",
            "CREATE INDEX IF NOT EXISTS idx_memory_user_key ON memory(user_id, key)",
        ],
    ),
    (
        6,
        "Create knowledge table",
        [
            """CREATE TABLE IF NOT EXISTS knowledge (
                user_id     TEXT NOT NULL,
                namespace   TEXT NOT NULL,
                key         TEXT NOT NULL,
                content     TEXT NOT NULL,
                metadata    TEXT NOT NULL DEFAULT '{}',
                created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (user_id, namespace, key)
            )""",
            "CREATE INDEX IF NOT EXISTS idx_knowledge_user_ns ON knowledge(user_id, namespace)",
        ],
    ),
    (
        7,
        "Create approvals table",
        [
            """CREATE TABLE IF NOT EXISTS approvals (
                id              TEXT PRIMARY KEY,
                session_id      TEXT NOT NULL REFERENCES sessions(id),
                user_id         TEXT NOT NULL,
                step_number     INTEGER NOT NULL,
                tool_name       TEXT NOT NULL,
                tool_arguments  TEXT NOT NULL,
                required_policy TEXT NOT NULL,
                status          TEXT NOT NULL DEFAULT 'pending',
                requested_at    TEXT NOT NULL DEFAULT (datetime('now')),
                resolved_at     TEXT,
                resolved_by     TEXT,
                reason          TEXT
            )""",
            "CREATE INDEX IF NOT EXISTS idx_approvals_user ON approvals(user_id, status)",
            "CREATE INDEX IF NOT EXISTS idx_approvals_session ON approvals(session_id)",
        ],
    ),
    (
        8,
        "Create audit_log table",
        [
            """CREATE TABLE IF NOT EXISTS audit_log (
                id          TEXT PRIMARY KEY,
                timestamp   TEXT NOT NULL DEFAULT (datetime('now')),
                user_id     TEXT NOT NULL,
                session_id  TEXT,
                action      TEXT NOT NULL,
                details     TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )""",
            "CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action)",
            "CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(timestamp)",
        ],
    ),
    (
        9,
        "Create agent_registry table",
        [
            """CREATE TABLE IF NOT EXISTS agent_registry (
                name            TEXT PRIMARY KEY,
                description     TEXT NOT NULL,
                base_url        TEXT NOT NULL,
                tools           TEXT NOT NULL DEFAULT '[]',
                version         TEXT NOT NULL,
                health_url      TEXT NOT NULL,
                registered_at   TEXT NOT NULL DEFAULT (datetime('now')),
                last_seen_at    TEXT NOT NULL DEFAULT (datetime('now'))
            )""",
        ],
    ),
]


class MigrationRunner:
    """Forward-only schema migration runner."""

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    async def _ensure_schema_version_table(self) -> None:
        await self._db.execute(
            """CREATE TABLE IF NOT EXISTS schema_version (
                version     INTEGER PRIMARY KEY,
                applied_at  TEXT NOT NULL DEFAULT (datetime('now')),
                description TEXT
            )"""
        )

    async def current_version(self) -> int:
        await self._ensure_schema_version_table()
        row = await self._db.fetch_one("SELECT MAX(version) AS v FROM schema_version")
        if row and row["v"] is not None:
            return int(row["v"])
        return 0

    async def run(self) -> None:
        """Apply all pending migrations in order."""
        await self._ensure_schema_version_table()
        current = await self.current_version()
        for version, description, statements in _MIGRATIONS:
            if version <= current:
                continue
            logger.info("Applying migration %d: %s", version, description)
            for sql in statements:
                await self._db.execute(sql)
            await self._db.execute(
                "INSERT INTO schema_version (version, description) VALUES (?, ?)",
                [version, description],
            )
        new_version = await self.current_version()
        if new_version > current:
            logger.info("Migrations complete. Schema at version %d.", new_version)
