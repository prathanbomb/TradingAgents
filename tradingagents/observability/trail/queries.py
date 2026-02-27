"""Trail query interface for filtering and searching decision trails.

This module provides TrailQuery class for discovering and filtering decision trails
by ticker, date range, agent type, and confidence thresholds.
"""

import logging
from typing import Any, Dict, List, Optional

from tradingagents.observability.storage.sqlite_backend import SQLiteDecisionStore

logger = logging.getLogger(__name__)


class TrailQuery:
    """Query interface for filtering and searching decision trails.

    Provides methods to discover trails by filters and build complete DecisionTrail
    objects for specific run_ids.

    Example:
        >>> store = SQLiteDecisionStore("./data/observability.db")
        >>> query = TrailQuery(store)
        >>> run_ids = query.get_trails(ticker="AAPL", start_date="2026-01-01")
        >>> trail = query.get_trail(run_id="abc123")
    """

    def __init__(
        self, store: SQLiteDecisionStore, builder: Optional[Any] = None
    ) -> None:
        """Initialize trail query interface.

        Args:
            store: SQLiteDecisionStore for querying records
            builder: Optional TrailBuilder for constructing DecisionTrail objects
        """
        self.store = store
        self._builder = builder
        logger.info("TrailQuery initialized")

    def get_trails(
        self,
        ticker: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        agent_name: Optional[str] = None,
        limit: int = 50,
    ) -> List[str]:
        """Get list of run_ids matching filters.

        Args:
            ticker: Optional ticker filter
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            agent_name: Optional agent name filter
            limit: Maximum number of run_ids to return

        Returns:
            List of run_id strings matching filters
        """
        run_ids = self.store.get_unique_run_ids(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            agent_name=agent_name,
            limit=limit,
        )
        logger.debug(f"Found {len(run_ids)} trails matching filters")
        return run_ids

    def get_trail(self, run_id: str) -> Optional[Any]:
        """Build complete DecisionTrail for run_id.

        Args:
            run_id: Run identifier

        Returns:
            DecisionTrail object if found, None otherwise
        """
        if self._builder is None:
            logger.warning("No TrailBuilder configured, returning None")
            return None

        try:
            trail = self._builder.build_trail(run_id)
            logger.debug(f"Built trail for run_id: {run_id}")
            return trail
        except Exception as e:
            logger.error(f"Failed to build trail for run_id {run_id}: {e}")
            return None

    def search_trails(
        self,
        query: str,
        ticker: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Full-text search in reasoning fields.

        Args:
            query: Search string for reasoning field matching
            ticker: Optional ticker filter
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            limit: Maximum number of results to return

        Returns:
            List of summary dicts with run_id, ticker, trade_date, agent_name, reasoning
        """
        import sqlite3

        conn = self.store._get_connection()

        try:
            sql_query = """
                SELECT run_id, ticker, trade_date, agent_name, reasoning
                FROM decision_records
                WHERE reasoning LIKE ?
            """
            params = [f"%{query}%"]

            if ticker:
                sql_query += " AND ticker = ?"
                params.append(ticker)

            if start_date:
                sql_query += " AND trade_date >= ?"
                params.append(start_date)

            if end_date:
                sql_query += " AND trade_date <= ?"
                params.append(end_date)

            sql_query += " ORDER BY trade_date DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(sql_query, params)
            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

            logger.debug(f"Found {len(results)} trails matching search query: {query}")
            return results
        finally:
            conn.close()

    def get_trails_by_confidence(
        self,
        confidence_min: Optional[float] = None,
        confidence_max: Optional[float] = None,
        ticker: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50,
    ) -> List[str]:
        """Get run_ids filtered by confidence range.

        Args:
            confidence_min: Optional minimum confidence threshold (0.0-1.0)
            confidence_max: Optional maximum confidence threshold (0.0-1.0)
            ticker: Optional ticker filter
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            limit: Maximum number of run_ids to return

        Returns:
            List of unique run_id strings matching confidence filters
        """
        records = self.store.get_decision_records_by_confidence(
            confidence_min=confidence_min,
            confidence_max=confidence_max,
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            include_system_confidence=True,
            limit=limit * 2,  # Fetch more to account for deduplication
        )

        run_ids = self._deduplicate_run_ids(records)
        logger.debug(
            f"Found {len(run_ids)} trails matching confidence filters: "
            f"min={confidence_min}, max={confidence_max}"
        )
        return run_ids[:limit]

    def _deduplicate_run_ids(self, records: List[Dict[str, Any]]) -> List[str]:
        """Extract and deduplicate run_ids from records.

        Args:
            records: List of decision record dicts

        Returns:
            Sorted list of unique run_id strings
        """
        run_ids = set()
        for record in records:
            if record.get("run_id"):
                run_ids.add(record["run_id"])

        return sorted(run_ids, reverse=True)
