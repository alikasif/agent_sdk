"""ScopedQueryBuilder — auto-injects user_id into SQL queries."""

from __future__ import annotations

from typing import Any

from agent_sdk.isolation.scope import get_user_scope


class ScopedQueryBuilder:
    """Builds SQL statements with automatic ``user_id`` filtering.

    Every method reads the current user scope from the *ContextVar*
    and includes it in the generated SQL, ensuring tenant isolation
    at the query level.
    """

    # ------------------------------------------------------------------
    # SELECT
    # ------------------------------------------------------------------
    def select(
        self,
        table: str,
        columns: str = "*",
        where: dict[str, Any] | None = None,
        order_by: str | None = None,
        limit: int | None = None,
    ) -> tuple[str, list[Any]]:
        """Build a ``SELECT`` with ``user_id`` injected."""
        user_id = get_user_scope()
        conditions = {"user_id": user_id}
        if where:
            conditions.update(where)

        clauses = " AND ".join(f"{k} = ?" for k in conditions)
        params: list[Any] = list(conditions.values())

        sql = f"SELECT {columns} FROM {table} WHERE {clauses}"
        if order_by:
            sql += f" ORDER BY {order_by}"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        return sql, params

    # ------------------------------------------------------------------
    # INSERT
    # ------------------------------------------------------------------
    def insert(self, table: str, values: dict[str, Any]) -> tuple[str, list[Any]]:
        """Build an ``INSERT`` ensuring ``user_id`` is set."""
        user_id = get_user_scope()
        values = {**values, "user_id": user_id}
        cols = ", ".join(values.keys())
        placeholders = ", ".join("?" for _ in values)
        params = list(values.values())
        sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
        return sql, params

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------
    def update(
        self,
        table: str,
        set_: dict[str, Any],
        where: dict[str, Any] | None = None,
    ) -> tuple[str, list[Any]]:
        """Build an ``UPDATE`` scoped to current ``user_id``."""
        user_id = get_user_scope()
        set_clause = ", ".join(f"{k} = ?" for k in set_)
        params: list[Any] = list(set_.values())

        conditions = {"user_id": user_id}
        if where:
            conditions.update(where)
        where_clause = " AND ".join(f"{k} = ?" for k in conditions)
        params.extend(conditions.values())

        sql = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
        return sql, params

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------
    def delete(
        self,
        table: str,
        where: dict[str, Any] | None = None,
    ) -> tuple[str, list[Any]]:
        """Build a ``DELETE`` scoped to current ``user_id``."""
        user_id = get_user_scope()
        conditions = {"user_id": user_id}
        if where:
            conditions.update(where)
        where_clause = " AND ".join(f"{k} = ?" for k in conditions)
        params = list(conditions.values())
        sql = f"DELETE FROM {table} WHERE {where_clause}"
        return sql, params
