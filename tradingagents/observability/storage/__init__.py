"""Storage backends for observability data.

This module provides storage abstractions for decision records and agent events.
"""

from typing import Optional

from tradingagents.observability.storage.sqlite_backend import SQLiteDecisionStore


def get_decision_store(
    db_path: str = "./data/observability.db",
) -> SQLiteDecisionStore:
    """Factory function for creating SQLite storage backend.

    Provides a convenient way to create storage instances with default
    configuration, following existing patterns from the confidence module.

    Args:
        db_path: Path to SQLite database file

    Returns:
        SQLiteDecisionStore instance
    """
    return SQLiteDecisionStore(db_path=db_path)


__all__ = ["SQLiteDecisionStore", "get_decision_store"]
