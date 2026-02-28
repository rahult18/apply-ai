"""
Base repository utilities.

Provides RealDictCursor context manager for automatic dict conversion
and common query building helpers.
"""
from contextlib import contextmanager
from typing import Any
import psycopg2.extras


@contextmanager
def get_cursor(connection):
    """
    Context manager that yields a RealDictCursor.

    Usage:
        with get_cursor(supabase.db_connection) as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            row = cursor.fetchone()  # Returns dict or None
    """
    cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield cursor
    finally:
        cursor.close()


def build_update_query(
    table: str,
    updates: dict[str, Any],
    where: dict[str, Any],
    extra_sets: list[str] | None = None,
) -> tuple[str, list[Any]]:
    """
    Build a dynamic UPDATE query from a dict of field updates.

    Args:
        table: Table name
        updates: Dict of {column: value} to update (None values are skipped)
        where: Dict of {column: value} for WHERE clause
        extra_sets: Additional SET clauses like "updated_at = NOW()"

    Returns:
        Tuple of (query_string, params_list)

    Example:
        query, params = build_update_query(
            "users",
            {"full_name": "John", "email": None},  # email skipped
            {"id": user_id},
            extra_sets=["updated_at = NOW()"]
        )
    """
    set_clauses = []
    params = []

    for column, value in updates.items():
        if value is not None:
            set_clauses.append(f"{column} = %s")
            params.append(value)

    if extra_sets:
        set_clauses.extend(extra_sets)

    if not set_clauses:
        return None, []

    where_clauses = []
    for column, value in where.items():
        where_clauses.append(f"{column} = %s")
        params.append(value)

    query = f"UPDATE {table} SET {', '.join(set_clauses)} WHERE {' AND '.join(where_clauses)}"
    return query, params
