"""SQLite storage backend for decision records and events.

This module implements SQLiteDecisionStore with WAL mode optimization
for concurrent writes and efficient querying (Pitfall #4 from research).
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from tradingagents.observability.confidence.calibration import (
    CalibrationMetrics,
    CalibrationTracker,
)
from tradingagents.observability.models.agent_event import AgentEvent
from tradingagents.observability.models.decision_record import DecisionRecord

logger = logging.getLogger(__name__)


class SQLiteDecisionStore:
    """SQLite storage backend for decision records and events.

    Uses WAL mode for better concurrency and optimized PRAGMA settings
    for performance (from research Pitfall #4).

    Example:
        ```python
        store = SQLiteDecisionStore("./data/observability.db")

        # Store batch of records
        await store.store_batch([decision_record, agent_event])

        # Query pending outcomes
        pending = store.get_pending_outcomes(ticker="AAPL")
        ```
    """

    def __init__(self, db_path: str = "./data/observability.db"):
        """Initialize SQLite storage backend.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._initialize_db()
        logger.info(f"SQLiteDecisionStore initialized: {db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """Create optimized SQLite connection with WAL mode.

        Returns:
            SQLite connection with optimized settings
        """
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path, check_same_thread=False)

        # Enable WAL mode for better concurrency
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA cache_size=-10000")  # 10MB cache
        conn.execute("PRAGMA page_size=4096")

        return conn

    def _initialize_db(self):
        """Create tables if they don't exist and migrate schema."""
        conn = self._get_connection()

        # Decision records table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS decision_records (
                decision_id TEXT PRIMARY KEY,
                ticker TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                run_id TEXT,
                agent_name TEXT NOT NULL,
                agent_type TEXT NOT NULL,
                decision TEXT NOT NULL,
                reasoning TEXT,
                outcome_pending BOOLEAN DEFAULT 1,
                entry_price REAL,
                exit_price REAL,
                hold_days INTEGER DEFAULT 7,
                return_pct REAL,
                outcome_calculated BOOLEAN DEFAULT 0,
                outcome_calculated_at TEXT,
                confidence REAL,
                bull_signal TEXT,
                bear_signal TEXT,
                risk_signal TEXT,
                final_signal TEXT,
                debate_state TEXT,
                metadata TEXT
            )
        """
        )

        # Migration: Add system_confidence and agent_confidences columns if not exists
        try:
            conn.execute("ALTER TABLE decision_records ADD COLUMN system_confidence REAL")
        except sqlite3.OperationalError:
            pass  # Column already exists

        try:
            conn.execute("ALTER TABLE decision_records ADD COLUMN agent_confidences TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Agent events table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                run_id TEXT,
                data TEXT,
                metadata TEXT,
                model TEXT,
                prompt_tokens INTEGER,
                completion_tokens INTEGER,
                total_tokens INTEGER,
                tool_name TEXT,
                tool_input TEXT,
                tool_output TEXT,
                from_state TEXT,
                to_state TEXT,
                error_type TEXT,
                error_message TEXT
            )
        """
        )

        # Indexes for efficient queries
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ticker_date ON decision_records(ticker, trade_date)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_run_id_decisions ON decision_records(run_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_outcome_pending ON decision_records(outcome_pending)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_agent_name_decisions ON decision_records(agent_name)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_run_id_events ON agent_events(run_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_agent_name_events ON agent_events(agent_name)"
        )

        # Calibration outcomes table (for Phase 2: Confidence Calibration)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS calibration_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                agent_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                was_correct BOOLEAN NOT NULL,
                recorded_at TEXT NOT NULL,
                FOREIGN KEY (decision_id) REFERENCES decision_records(decision_id)
            )
        """
        )

        # Indexes for calibration queries
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_calibration_agent ON calibration_outcomes(agent_name, recorded_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_calibration_decision ON calibration_outcomes(decision_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_calibration_correct ON calibration_outcomes(was_correct)"
        )

        # Indexes for confidence queries (Phase 2: Confidence History)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_confidence ON decision_records(confidence)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_system_confidence ON decision_records(system_confidence)"
        )

        conn.commit()
        conn.close()

        logger.debug("Database tables and indexes initialized")

    async def store_batch(self, batch: List[Union[DecisionRecord, AgentEvent]]) -> int:
        """Store a batch of records/events.

        Args:
            batch: List of DecisionRecord or AgentEvent objects

        Returns:
            Number of records successfully stored
        """
        if not batch:
            return 0

        conn = self._get_connection()
        stored = 0

        try:
            for item in batch:
                if isinstance(item, DecisionRecord):
                    self._store_decision(conn, item)
                    stored += 1
                elif isinstance(item, AgentEvent):
                    self._store_event(conn, item)
                    stored += 1
                else:
                    logger.warning(f"Unknown item type: {type(item)}")

            conn.commit()
            logger.debug(f"Stored {stored} records in batch")
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to store batch: {e}", exc_info=True)
            raise
        finally:
            conn.close()

        return stored

    def _store_decision(self, conn: sqlite3.Connection, record: DecisionRecord):
        """Store a single decision record.

        Args:
            conn: SQLite connection
            record: DecisionRecord to store
        """
        # Convert debate_state to JSON if present
        debate_state_json = (
            json.dumps(record.debate_state.dict()) if record.debate_state else None
        )

        conn.execute(
            """
            INSERT OR REPLACE INTO decision_records
            (decision_id, ticker, trade_date, timestamp, run_id, agent_name, agent_type,
             decision, reasoning, outcome_pending, entry_price, exit_price, hold_days,
             return_pct, outcome_calculated, outcome_calculated_at, confidence,
             bull_signal, bear_signal, risk_signal, final_signal, debate_state, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                record.decision_id,
                record.ticker,
                record.trade_date,
                record.timestamp,
                record.run_id,
                record.agent_name,
                record.agent_type,
                record.decision,
                record.reasoning,
                1 if record.outcome_pending else 0,
                record.entry_price,
                record.exit_price,
                record.hold_days,
                record.return_pct,
                1 if record.outcome_calculated else 0,
                record.outcome_calculated_at.isoformat()
                if record.outcome_calculated_at
                else None,
                record.confidence,
                record.bull_signal.value if record.bull_signal else None,
                record.bear_signal.value if record.bear_signal else None,
                record.risk_signal.value if record.risk_signal else None,
                record.final_signal.value,
                debate_state_json,
                json.dumps(record.metadata) if record.metadata else None,
            ),
        )

    def _store_event(self, conn: sqlite3.Connection, event: AgentEvent):
        """Store a single agent event.

        Args:
            conn: SQLite connection
            event: AgentEvent to store
        """
        conn.execute(
            """
            INSERT INTO agent_events
            (event_id, event_type, agent_name, timestamp, run_id, data, metadata,
             model, prompt_tokens, completion_tokens, total_tokens,
             tool_name, tool_input, tool_output, from_state, to_state,
             error_type, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                event.event_id,
                event.event_type,
                event.agent_name,
                event.timestamp,
                event.run_id,
                json.dumps(event.data) if event.data else None,
                json.dumps(event.metadata) if event.metadata else None,
                event.model,
                event.prompt_tokens,
                event.completion_tokens,
                event.total_tokens,
                event.tool_name,
                json.dumps(event.tool_input) if event.tool_input else None,
                event.tool_output,
                event.from_state,
                event.to_state,
                event.error_type,
                event.error_message,
            ),
        )

    def get_pending_outcomes(
        self, ticker: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get decision records with pending outcomes.

        Args:
            ticker: Optional ticker filter
            limit: Maximum number of records to return

        Returns:
            List of decision records with outcome_pending=True
        """
        conn = self._get_connection()

        try:
            if ticker:
                cursor = conn.execute(
                    """
                    SELECT * FROM decision_records
                    WHERE outcome_pending = 1 AND ticker = ?
                    ORDER BY trade_date DESC
                    LIMIT ?
                """,
                    (ticker, limit),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT * FROM decision_records
                    WHERE outcome_pending = 1
                    ORDER BY trade_date DESC
                    LIMIT ?
                """,
                    (limit,),
                )

            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

            return results
        finally:
            conn.close()

    def get_decision_records(
        self,
        ticker: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get decision records with optional filters.

        Args:
            ticker: Optional ticker filter
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            limit: Maximum number of records to return

        Returns:
            List of decision records
        """
        conn = self._get_connection()

        try:
            query = "SELECT * FROM decision_records WHERE 1=1"
            params = []

            if ticker:
                query += " AND ticker = ?"
                params.append(ticker)

            if start_date:
                query += " AND trade_date >= ?"
                params.append(start_date)

            if end_date:
                query += " AND trade_date <= ?"
                params.append(end_date)

            query += " ORDER BY trade_date DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(query, params)
            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

            return results
        finally:
            conn.close()

    def get_decision_records_by_run_id(self, run_id: str) -> List[Dict[str, Any]]:
        """Get all decision records for a specific run_id.

        Args:
            run_id: Run identifier grouping related events

        Returns:
            List of decision records as dicts, sorted by timestamp ASC
        """
        conn = self._get_connection()

        try:
            cursor = conn.execute(
                """
                SELECT * FROM decision_records
                WHERE run_id = ?
                ORDER BY timestamp ASC
                """,
                (run_id,),
            )
            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

            return results
        finally:
            conn.close()

    def get_agent_events_by_run_id(self, run_id: str) -> List[Dict[str, Any]]:
        """Get all agent events for a specific run_id.

        Args:
            run_id: Run identifier grouping related events

        Returns:
            List of agent events as dicts, sorted by timestamp ASC
        """
        conn = self._get_connection()

        try:
            cursor = conn.execute(
                """
                SELECT * FROM agent_events
                WHERE run_id = ?
                ORDER BY timestamp ASC
                """,
                (run_id,),
            )
            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

            return results
        finally:
            conn.close()

    def get_unique_run_ids(
        self,
        ticker: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        agent_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[str]:
        """Get unique run_ids matching filters for trail discovery.

        Args:
            ticker: Optional ticker filter
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            agent_name: Optional agent name filter
            limit: Maximum number of run_ids to return

        Returns:
            List of unique run_id strings matching filters
        """
        conn = self._get_connection()

        try:
            query = "SELECT DISTINCT run_id FROM decision_records WHERE run_id IS NOT NULL"
            params = []

            if ticker:
                query += " AND ticker = ?"
                params.append(ticker)

            if start_date:
                query += " AND trade_date >= ?"
                params.append(start_date)

            if end_date:
                query += " AND trade_date <= ?"
                params.append(end_date)

            if agent_name:
                query += " AND agent_name = ?"
                params.append(agent_name)

            query += " ORDER BY trade_date DESC, run_id DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(query, params)
            results = [row[0] for row in cursor.fetchall() if row[0]]

            return results
        finally:
            conn.close()

    def get_agent_events(
        self, run_id: Optional[str] = None, agent_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get agent events with optional filters.

        Args:
            run_id: Optional run_id filter
            agent_name: Optional agent name filter

        Returns:
            List of agent events
        """
        conn = self._get_connection()

        try:
            query = "SELECT * FROM agent_events WHERE 1=1"
            params = []

            if run_id:
                query += " AND run_id = ?"
                params.append(run_id)

            if agent_name:
                query += " AND agent_name = ?"
                params.append(agent_name)

            query += " ORDER BY timestamp ASC"

            cursor = conn.execute(query, params)
            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

            return results
        finally:
            conn.close()

    def update_outcome(
        self, decision_id: str, entry_price: float, exit_price: float, return_pct: float
    ) -> bool:
        """Update outcome calculation for a decision record.

        Args:
            decision_id: Decision record ID
            entry_price: Entry price
            exit_price: Exit price
            return_pct: Return percentage

        Returns:
            True if updated, False if not found
        """
        conn = self._get_connection()

        try:
            cursor = conn.execute(
                """
                UPDATE decision_records
                SET outcome_pending = 0,
                    outcome_calculated = 1,
                    outcome_calculated_at = ?,
                    entry_price = ?,
                    exit_price = ?,
                    return_pct = ?
                WHERE decision_id = ?
            """,
                (
                    datetime.utcnow().isoformat(),
                    entry_price,
                    exit_price,
                    return_pct,
                    decision_id,
                ),
            )

            conn.commit()
            updated = cursor.rowcount > 0

            if updated:
                logger.debug(f"Updated outcome for decision {decision_id}")

            return updated
        finally:
            conn.close()

    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics.

        Returns:
            Dict with total_decisions, total_events, pending_outcomes
        """
        conn = self._get_connection()

        try:
            total_decisions = conn.execute(
                "SELECT COUNT(*) FROM decision_records"
            ).fetchone()[0]
            total_events = conn.execute(
                "SELECT COUNT(*) FROM agent_events"
            ).fetchone()[0]
            pending_outcomes = conn.execute(
                "SELECT COUNT(*) FROM decision_records WHERE outcome_pending = 1"
            ).fetchone()[0]

            return {
                "total_decisions": total_decisions,
                "total_events": total_events,
                "pending_outcomes": pending_outcomes,
                "db_path": self.db_path,
            }
        finally:
            conn.close()

    def record_calibration_outcome(
        self,
        decision_id: str,
        agent_name: str,
        agent_type: str,
        confidence: float,
        was_correct: bool,
    ) -> None:
        """Record a confidence calibration outcome.

        Args:
            decision_id: Decision record ID
            agent_name: Name of the agent
            agent_type: Type of agent (analyst, researcher, etc.)
            confidence: Confidence score (0.0-1.0)
            was_correct: Whether the prediction was correct
        """
        conn = self._get_connection()

        try:
            conn.execute(
                """
                INSERT INTO calibration_outcomes
                (decision_id, agent_name, agent_type, confidence, was_correct, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    decision_id,
                    agent_name,
                    agent_type,
                    confidence,
                    1 if was_correct else 0,
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()
            logger.debug(
                f"Recorded calibration outcome: decision_id={decision_id}, "
                f"agent={agent_name}, confidence={confidence:.3f}, correct={was_correct}"
            )
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to record calibration outcome: {e}", exc_info=True)
            raise
        finally:
            conn.close()

    def get_calibration_outcomes(
        self,
        agent_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Get calibration outcomes with optional filters.

        Args:
            agent_name: Optional agent name filter
            start_date: Optional start date (ISO format string)
            end_date: Optional end date (ISO format string)
            limit: Maximum number of records to return

        Returns:
            List of calibration outcomes as dicts
        """
        conn = self._get_connection()

        try:
            query = "SELECT * FROM calibration_outcomes WHERE 1=1"
            params = []

            if agent_name:
                query += " AND agent_name = ?"
                params.append(agent_name)

            if start_date:
                query += " AND recorded_at >= ?"
                params.append(start_date)

            if end_date:
                query += " AND recorded_at <= ?"
                params.append(end_date)

            query += " ORDER BY recorded_at DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(query, params)
            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

            return results
        finally:
            conn.close()

    def get_calibration_metrics(
        self,
        agent_name: Optional[str] = None,
        n_bins: int = 10,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> CalibrationMetrics:
        """Get calibration metrics from stored outcomes.

        Args:
            agent_name: Optional agent name filter
            n_bins: Number of bins for ECE calculation
            start_date: Optional start date (ISO format string)
            end_date: Optional end date (ISO format string)

        Returns:
            CalibrationMetrics with ECE, Brier score, etc.
        """
        # Load outcomes from storage
        outcomes = self.get_calibration_outcomes(
            agent_name=agent_name, start_date=start_date, end_date=end_date, limit=10000
        )

        if not outcomes:
            logger.debug(f"No calibration outcomes found for agent: {agent_name}")
            return CalibrationMetrics(
                ece=0.0,
                brier_score=0.0,
                sample_count=0,
                is_well_calibrated=False,
                bin_data=[],
            )

        # Create tracker and populate with data
        tracker = CalibrationTracker(agent_name=agent_name)
        for outcome in outcomes:
            tracker.record_outcome(
                confidence=outcome["confidence"], was_correct=bool(outcome["was_correct"])
            )

        # Return metrics
        return tracker.get_calibration_metrics(n_bins=n_bins)

    def get_per_agent_calibration(
        self, n_bins: int = 10
    ) -> Dict[str, CalibrationMetrics]:
        """Get calibration metrics for each agent separately.

        Args:
            n_bins: Number of bins for ECE calculation

        Returns:
            Dict mapping agent_name to CalibrationMetrics
        """
        conn = self._get_connection()

        try:
            # Get all unique agent names
            cursor = conn.execute(
                "SELECT DISTINCT agent_name FROM calibration_outcomes"
            )
            agent_names = [row[0] for row in cursor.fetchall()]

            # Get metrics for each agent
            per_agent_metrics = {}
            for agent_name in agent_names:
                metrics = self.get_calibration_metrics(agent_name=agent_name, n_bins=n_bins)
                per_agent_metrics[agent_name] = metrics

            return per_agent_metrics
        finally:
            conn.close()

    def get_decision_records_by_confidence(
        self,
        confidence_min: Optional[float] = None,
        confidence_max: Optional[float] = None,
        ticker: Optional[str] = None,
        agent_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        include_system_confidence: bool = True,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Query decision records with confidence range filters.

        Args:
            confidence_min: Optional minimum confidence threshold
            confidence_max: Optional maximum confidence threshold
            ticker: Optional ticker filter
            agent_type: Optional agent type filter
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            include_system_confidence: Whether to also filter by system_confidence
            limit: Maximum number of records to return

        Returns:
            List of decision records as dicts, sorted by trade_date DESC
        """
        conn = self._get_connection()

        try:
            query = "SELECT * FROM decision_records WHERE 1=1"
            params = []

            # Confidence range filters
            if confidence_min is not None:
                query += " AND (confidence >= ? OR confidence IS NULL)"
                params.append(confidence_min)

            if confidence_max is not None:
                query += " AND (confidence <= ? OR confidence IS NULL)"
                params.append(confidence_max)

            # System confidence filter
            if include_system_confidence:
                if confidence_min is not None:
                    query += " OR (system_confidence >= ?)"
                    params.append(confidence_min)
                if confidence_max is not None:
                    query += " OR (system_confidence <= ?)"
                    params.append(confidence_max)

            # Other filters
            if ticker:
                query += " AND ticker = ?"
                params.append(ticker)

            if agent_type:
                query += " AND agent_type = ?"
                params.append(agent_type)

            if start_date:
                query += " AND trade_date >= ?"
                params.append(start_date)

            if end_date:
                query += " AND trade_date <= ?"
                params.append(end_date)

            query += " ORDER BY trade_date DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(query, params)
            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

            return results
        finally:
            conn.close()

    def get_confidence_statistics(
        self,
        ticker: Optional[str] = None,
        agent_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, float]:
        """Compute aggregate confidence statistics using SQL aggregates.

        Args:
            ticker: Optional ticker filter
            agent_type: Optional agent type filter
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)

        Returns:
            Dict with avg_confidence, min_confidence, max_confidence, count
        """
        conn = self._get_connection()

        try:
            query = "SELECT AVG(confidence), MIN(confidence), MAX(confidence), COUNT(*) FROM decision_records WHERE confidence IS NOT NULL"
            params = []

            if ticker:
                query += " AND ticker = ?"
                params.append(ticker)

            if agent_type:
                query += " AND agent_type = ?"
                params.append(agent_type)

            if start_date:
                query += " AND trade_date >= ?"
                params.append(start_date)

            if end_date:
                query += " AND trade_date <= ?"
                params.append(end_date)

            cursor = conn.execute(query, params)
            row = cursor.fetchone()

            return {
                "avg_confidence": float(row[0]) if row[0] else 0.0,
                "min_confidence": float(row[1]) if row[1] else 0.0,
                "max_confidence": float(row[2]) if row[2] else 0.0,
                "count": int(row[3]) if row[3] else 0,
            }
        finally:
            conn.close()

    def get_confidence_time_series(
        self,
        ticker: str,
        agent_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Tuple[str, float, float]]:
        """Get confidence time series data for trend analysis.

        Args:
            ticker: Ticker symbol
            agent_type: Optional agent type filter
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)

        Returns:
            List of tuples: [(trade_date, confidence, system_confidence), ...]
            Sorted by trade_date ASC (chronological)
        """
        conn = self._get_connection()

        try:
            query = """
                SELECT trade_date, confidence, system_confidence
                FROM decision_records
                WHERE ticker = ?
            """
            params = [ticker]

            if agent_type:
                query += " AND agent_type = ?"
                params.append(agent_type)

            if start_date:
                query += " AND trade_date >= ?"
                params.append(start_date)

            if end_date:
                query += " AND trade_date <= ?"
                params.append(end_date)

            query += " ORDER BY trade_date ASC"

            cursor = conn.execute(query, params)
            results = [(row[0], row[1], row[2]) for row in cursor.fetchall()]

            return results
        finally:
            conn.close()

    def get_agent_confidence_comparison(
        self,
        trade_date: Optional[str] = None,
        ticker: Optional[str] = None,
    ) -> Dict[str, Dict[str, float]]:
        """Get per-agent confidence for comparison.

        Args:
            trade_date: Optional trade date filter (YYYY-MM-DD)
            ticker: Optional ticker filter

        Returns:
            Dict mapping agent_name to {avg_confidence, count, last_confidence}
        """
        conn = self._get_connection()

        try:
            query = """
                SELECT agent_name, AVG(confidence), COUNT(*), MAX(confidence)
                FROM decision_records
                WHERE confidence IS NOT NULL
            """
            params = []

            if ticker:
                query += " AND ticker = ?"
                params.append(ticker)

            if trade_date:
                query += " AND trade_date = ?"
                params.append(trade_date)

            query += " GROUP BY agent_name"

            cursor = conn.execute(query, params)
            results = {}

            for row in cursor.fetchall():
                agent_name = row[0]
                results[agent_name] = {
                    "avg_confidence": float(row[1]) if row[1] else 0.0,
                    "count": int(row[2]) if row[2] else 0,
                    "last_confidence": float(row[3]) if row[3] else 0.0,
                }

            return results
        finally:
            conn.close()

    def query_debates(
        self,
        ticker: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        has_debate: bool = True,
        judgment_pattern: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query DecisionRecord for entries with debate_state.

        Extends existing query_records() with debate-specific filtering.

        Args:
            ticker: Filter by ticker symbol
            start_date: Filter by trade_date >= start_date
            end_date: Filter by trade_date <= end_date
            has_debate: If True, only return records with non-null debate_state
            judgment_pattern: Optional substring to match in judge_decision
            limit: Maximum records to return

        Returns:
            List of DecisionRecord with debate_state populated
        """
        conn = self._get_connection()

        try:
            query = "SELECT * FROM decision_records WHERE 1=1"
            params = []

            if ticker:
                query += " AND ticker = ?"
                params.append(ticker)

            if start_date:
                query += " AND trade_date >= ?"
                params.append(start_date)

            if end_date:
                query += " AND trade_date <= ?"
                params.append(end_date)

            if has_debate:
                query += " AND debate_state IS NOT NULL"
                # Additionally filter for valid debate_state JSON
                query += " AND debate_state != ''"

            if judgment_pattern:
                # Search in debate_state JSON for judge_decision field
                query += " AND debate_state LIKE ?"
                params.append(f"%{judgment_pattern}%")

            query += " ORDER BY trade_date DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(query, params)
            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

            return results
        finally:
            conn.close()

    def search_debate_content(
        self,
        query: str,
        debate_field: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Full-text search across debate_state fields.

        Uses LIKE queries for text search across debate_state JSON content.

        Args:
            query: Search query string
            debate_field: Specific field to search ("bull_history", "bear_history",
                "risky_history", "safe_history", "neutral_history"), if None searches
                all debate_state fields
            limit: Maximum records to return

        Returns:
            List of DecisionRecord where debate_state matches query
        """
        conn = self._get_connection()

        try:
            # Build LIKE query for JSON text search
            sql = "SELECT * FROM decision_records WHERE debate_state IS NOT NULL"
            params = []

            if debate_field:
                # Search specific field using json_extract
                sql += f" AND json_extract(debate_state, '$.{debate_field}') LIKE ?"
                params.append(f"%{query}%")
            else:
                # Search all debate_state fields
                sql += " AND debate_state LIKE ?"
                params.append(f"%{query}%")

            sql += " ORDER BY trade_date DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(sql, params)
            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

            logger.debug(f"Debate content search for '{query}' returned {len(results)} results")
            return results
        finally:
            conn.close()
